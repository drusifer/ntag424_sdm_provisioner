#!/usr/bin/env python3
"""
Analyze Seritag EV2 Phase 2 Differences

Since Phase 1 works but Phase 2 fails, let's examine what might be different
in Seritag's EV2 implementation.
"""

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, AuthenticateEV2First
from ntag424_sdm_provisioner.constants import FACTORY_KEY
from Crypto.Cipher import AES
import logging
import secrets

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

def analyze_phase1_behavior():
    """Analyze the Phase 1 challenge/response pattern."""
    
    challenges = []
    
    try:
        with CardManager(0) as card:
            SelectPiccApplication().execute(card)
            
            # Collect multiple challenges to analyze patterns
            for i in range(3):
                log.info(f"Challenge {i+1}:")
                
                try:
                    cmd = AuthenticateEV2First(key_no=0)
                    response = cmd.execute(card)
                    
                    encrypted_rndb = response.challenge
                    challenges.append(encrypted_rndb)
                    
                    log.info(f"  Encrypted RndB: {encrypted_rndb.hex()}")
                    
                    # Try to decrypt with factory key
                    cipher = AES.new(FACTORY_KEY, AES.MODE_ECB)
                    decrypted = cipher.decrypt(encrypted_rndb)
                    log.info(f"  Decrypted (factory key): {decrypted.hex()}")
                    
                except Exception as e:
                    log.error(f"  Challenge {i+1} failed: {e}")
                    
    except Exception as e:
        log.error(f"Phase 1 analysis failed: {e}")
    
    return challenges

def try_modified_phase2():
    """Try different Phase 2 approaches that Seritag might expect."""
    
    try:
        with CardManager(0) as card:
            SelectPiccApplication().execute(card)
            
            # Get a challenge first
            cmd = AuthenticateEV2First(key_no=0)
            response = cmd.execute(card)
            encrypted_rndb = response.challenge
            
            log.info(f"Got challenge: {encrypted_rndb.hex()}")
            
            # Decrypt RndB
            cipher = AES.new(FACTORY_KEY, AES.MODE_ECB)
            rndb = cipher.decrypt(encrypted_rndb)
            log.info(f"Decrypted RndB: {rndb.hex()}")
            
            # Generate RndA
            rnda = secrets.token_bytes(16)
            log.info(f"Generated RndA: {rnda.hex()}")
            
            # Try different Phase 2 variations
            variations = [
                # Standard NXP approach
                ("Standard NXP", rnda + rndb[1:] + rndb[0:1]),
                
                # Try different rotations
                ("RndB rotate right", rnda + rndb[-1:] + rndb[:-1]),
                ("No RndB rotation", rnda + rndb),
                ("Different RndA rotation", rnda[1:] + rnda[0:1] + rndb[1:] + rndb[0:1]),
                
                # Try swapped order
                ("Swapped order", rndb[1:] + rndb[0:1] + rnda),
                
                # Try XOR instead of concatenation
                ("XOR approach", bytes(a ^ b for a, b in zip(rnda, rndb))),
                
                # Try with padding
                ("With padding", rnda + rndb[1:] + rndb[0:1] + b'\x00' * 16),
            ]
            
            for name, payload in variations:
                try:
                    log.info(f"Trying {name}: {len(payload)} bytes")
                    
                    # Encrypt the payload
                    if len(payload) % 16 != 0:
                        # Pad to 16-byte boundary
                        pad_len = 16 - (len(payload) % 16)
                        payload = payload + b'\x00' * pad_len
                    
                    encrypted_payload = b''
                    for i in range(0, len(payload), 16):
                        block = payload[i:i+16]
                        if len(block) == 16:
                            encrypted_block = cipher.encrypt(block)
                            encrypted_payload += encrypted_block
                    
                    # Send Phase 2 command
                    apdu = [0x90, 0xAF, 0x00, 0x00, len(encrypted_payload)] + list(encrypted_payload) + [0x00]
                    response_data, sw1, sw2 = card.send_apdu(apdu)
                    
                    result = f"{sw1:02X}{sw2:02X}"
                    if result != "91AE":
                        log.info(f"🎯 {name} got different response: {result}")
                        if response_data:
                            log.info(f"   Response data: {bytes(response_data).hex()}")
                    else:
                        log.debug(f"   {name}: {result}")
                        
                except Exception as e:
                    log.debug(f"   {name} failed: {e}")
                    
    except Exception as e:
        log.error(f"Modified Phase 2 analysis failed: {e}")

def try_command_51_variations():
    """Try command 0x51 with different approaches after getting a challenge."""
    
    try:
        with CardManager(0) as card:
            SelectPiccApplication().execute(card)
            
            # First get a challenge (this works)
            cmd = AuthenticateEV2First(key_no=0)
            response = cmd.execute(card)
            encrypted_rndb = response.challenge
            
            log.info("Now trying command 0x51 variations after getting challenge...")
            
            # Try 0x51 with different parameters after challenge
            variations = [
                [0x90, 0x51, 0x00, 0x00, 0x00],
                [0x90, 0x51, 0x01, 0x00, 0x00],
                [0x90, 0x51, 0x00, 0x01, 0x00], 
                [0x90, 0x51, 0x00, 0x00, 0x01, 0x00, 0x00],
                [0x90, 0x51, 0x00, 0x00, 0x10] + list(encrypted_rndb) + [0x00],  # Include the challenge
            ]
            
            for i, apdu in enumerate(variations):
                try:
                    response_data, sw1, sw2 = card.send_apdu(apdu)
                    result = f"{sw1:02X}{sw2:02X}"
                    log.info(f"0x51 variation {i}: {result}")
                    if response_data:
                        log.info(f"   Data: {bytes(response_data).hex()}")
                except Exception as e:
                    log.debug(f"0x51 variation {i} failed: {e}")
                    
    except Exception as e:
        log.error(f"Command 0x51 analysis failed: {e}")

def main():
    """Run comprehensive Seritag EV2 analysis."""
    
    log.info("🔬 Analyzing Seritag EV2 Differences")
    
    log.info("\n1️⃣ Analyzing Phase 1 behavior...")
    challenges = analyze_phase1_behavior()
    
    log.info("\n2️⃣ Trying modified Phase 2 approaches...")
    try_modified_phase2()
    
    log.info("\n3️⃣ Testing command 0x51 after challenge...")
    try_command_51_variations()
    
    log.info("\n📊 Analysis Summary:")
    log.info("- Phase 1 works: Seritag uses standard EV2 challenge generation")
    log.info("- Phase 2 fails: Seritag expects different response format")
    log.info("- Command 0x51: Requires authentication but might be the key to recovery")
    
if __name__ == "__main__":
    main()
