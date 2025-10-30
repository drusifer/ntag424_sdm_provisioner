#!/usr/bin/env python3
"""
Seritag NTAG424 DNA Recovery Attempts

Try various methods to reset or recover Seritag devices to standard NXP behavior.
"""

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.constants import APDUInstruction
import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

def attempt_format_picc():
    """Try FORMAT_PICC command to reset configuration."""
    try:
        with CardManager(0) as card:
            # Select application first
            SelectPiccApplication().execute(card)
            
            # Try FORMAT_PICC command (dangerous - might brick tag!)
            log.warning("⚠️  Attempting FORMAT_PICC - THIS MIGHT BRICK THE TAG!")
            apdu = [0x90, APDUInstruction.FORMAT_PICC, 0x00, 0x00]
            
            response, sw1, sw2 = card.send_apdu(apdu)
            log.info(f"FORMAT_PICC result: SW={sw1:02X}{sw2:02X}")
            
            if sw1 == 0x90 and sw2 == 0x00:
                log.info("✅ FORMAT_PICC succeeded - tag may be reset!")
                return True
            else:
                log.error(f"❌ FORMAT_PICC failed: {sw1:02X}{sw2:02X}")
                return False
                
    except Exception as e:
        log.error(f"FORMAT_PICC attempt failed: {e}")
        return False

def attempt_factory_key_variations():
    """Try different possible factory keys that Seritag might use."""
    
    # Possible Seritag factory keys to try
    possible_keys = [
        b'\x00' * 16,  # Standard NXP
        b'\xFF' * 16,  # All FF
        b'SERITAG424DNA\x00\x00',  # Seritag branded key
        b'seritag424dna\x00\x00',  # Lowercase
        bytes.fromhex('01234567890ABCDEFFEDCBA0987654321'),  # Sequential pattern
        bytes.fromhex('DEADBEEFCAFEBABE1234567890ABCDEF'),  # Common test pattern
    ]
    
    try:
        with CardManager(0) as card:
            SelectPiccApplication().execute(card)
            
            for i, key in enumerate(possible_keys):
                log.info(f"Trying key {i}: {key.hex()}")
                
                try:
                    from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
                    session = Ntag424AuthSession(key)
                    session.authenticate(card, key_no=0)
                    
                    log.info(f"🎉 SUCCESS! Key {i} worked: {key.hex()}")
                    return key
                    
                except Exception as e:
                    log.debug(f"Key {i} failed: {e}")
                    continue
                    
            log.error("❌ All factory key attempts failed")
            return None
            
    except Exception as e:
        log.error(f"Factory key attempt failed: {e}")
        return None

def attempt_ev1_authentication():
    """Try EV1 authentication instead of EV2."""
    # EV1 uses different command codes
    # This would require implementing EV1 authentication
    log.info("EV1 authentication not yet implemented")
    pass

def probe_seritag_commands():
    """Probe for Seritag-specific commands."""
    
    # Try various instruction codes that might be Seritag-specific
    seritag_instructions = [
        0x50, 0x51, 0x52, 0x53,  # Potential custom commands
        0x70, 0x72, 0x73,        # Near EV2 auth commands
        0xA0, 0xA1, 0xA2,        # Application commands
        0xF0, 0xF1, 0xF2, 0xF3,  # Factory/diagnostic commands
    ]
    
    try:
        with CardManager(0) as card:
            SelectPiccApplication().execute(card)
            
            for ins in seritag_instructions:
                try:
                    apdu = [0x90, ins, 0x00, 0x00, 0x00]
                    response, sw1, sw2 = card.send_apdu(apdu)
                    
                    if sw1 != 0x6D:  # 6D00 = INS not supported
                        log.info(f"📍 Instruction {ins:02X} responded: {sw1:02X}{sw2:02X}")
                        if response:
                            log.info(f"   Data: {bytes(response).hex()}")
                except:
                    pass
                    
    except Exception as e:
        log.error(f"Command probing failed: {e}")

def main():
    """Run all recovery attempts."""
    
    log.info("🔧 Starting Seritag NTAG424 DNA Recovery Attempts")
    log.warning("⚠️  WARNING: Some operations might permanently damage the tag!")
    
    # 1. Try different factory keys (safest)
    log.info("\n1️⃣ Attempting factory key variations...")
    working_key = attempt_factory_key_variations()
    if working_key:
        log.info(f"Found working key: {working_key.hex()}")
        return True
    
    # 2. Probe for custom commands
    log.info("\n2️⃣ Probing for Seritag-specific commands...")
    probe_seritag_commands()
    
    # 3. Try FORMAT_PICC (DANGEROUS!)
    choice = input("\n3️⃣ Attempt FORMAT_PICC? This might BRICK the tag! (y/N): ")
    if choice.lower() == 'y':
        success = attempt_format_picc()
        if success:
            return True
    
    log.error("❌ All recovery attempts failed")
    return False

if __name__ == "__main__":
    main()
