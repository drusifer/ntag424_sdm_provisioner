#!/usr/bin/env python3
"""
Investigate Seritag command 0x51 that returns 91AE instead of 911C.

This command appears to be recognized but requires authentication.
"""

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

def probe_command_51_variations():
    """Try different variations of command 0x51."""
    
    variations = [
        # Different P1/P2 values
        [0x90, 0x51, 0x00, 0x00, 0x00],  # Original
        [0x90, 0x51, 0x01, 0x00, 0x00],  # P1=01
        [0x90, 0x51, 0x02, 0x00, 0x00],  # P1=02
        [0x90, 0x51, 0x00, 0x01, 0x00],  # P2=01
        [0x90, 0x51, 0x00, 0x02, 0x00],  # P2=02
        [0x90, 0x51, 0xFF, 0xFF, 0x00],  # P1=FF, P2=FF
        
        # With data
        [0x90, 0x51, 0x00, 0x00, 0x01, 0x00, 0x00],  # 1 byte data
        [0x90, 0x51, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00],  # 2 bytes data
        [0x90, 0x51, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00],  # 4 bytes
        
        # Different CLA values
        [0x80, 0x51, 0x00, 0x00, 0x00],  # CLA=80
        [0x00, 0x51, 0x00, 0x00, 0x00],  # CLA=00 (ISO standard)
        [0xFF, 0x51, 0x00, 0x00, 0x00],  # CLA=FF (pseudo-APDU)
    ]
    
    try:
        with CardManager(0) as card:
            SelectPiccApplication().execute(card)
            
            for i, apdu in enumerate(variations):
                try:
                    log.info(f"Trying variation {i}: {[hex(x) for x in apdu]}")
                    response, sw1, sw2 = card.send_apdu(apdu)
                    
                    status = f"{sw1:02X}{sw2:02X}"
                    if status != "911C":  # Not the generic "unsupported" response
                        log.info(f"🔍 INTERESTING: Variation {i} = {status}")
                        if response:
                            log.info(f"   Response data: {bytes(response).hex()}")
                    else:
                        log.debug(f"   Standard response: {status}")
                        
                except Exception as e:
                    log.debug(f"   Exception: {e}")
                    
    except Exception as e:
        log.error(f"Investigation failed: {e}")

def check_standard_commands():
    """Check what 0x51 might be in standard NXP documentation."""
    
    log.info("Standard NXP NTAG424/DESFire commands near 0x51:")
    log.info("  0x4F = GetKeySettings")  
    log.info("  0x50 = ChangeKeySettings")
    log.info("  0x51 = ? (UNKNOWN - possibly Seritag specific)")
    log.info("  0x52 = ?")
    log.info("  0x53 = ?")
    log.info("  0x54 = GetCardUID")
    log.info("  0x5A = SelectApplication")
    log.info("  0x5F = ChangeFileSettings")

def probe_nearby_commands():
    """Probe commands near 0x51 to see if there's a pattern."""
    
    nearby_commands = [0x4F, 0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A]
    
    try:
        with CardManager(0) as card:
            SelectPiccApplication().execute(card)
            
            log.info("Probing commands around 0x51:")
            for cmd in nearby_commands:
                try:
                    apdu = [0x90, cmd, 0x00, 0x00, 0x00]
                    response, sw1, sw2 = card.send_apdu(apdu)
                    
                    status = f"{sw1:02X}{sw2:02X}"
                    if status not in ["911C", "6D00"]:  # Skip generic "unsupported" 
                        log.info(f"📍 Command {cmd:02X}: {status}")
                        if response:
                            log.info(f"   Data: {bytes(response).hex()}")
                    
                except Exception as e:
                    pass
                    
    except Exception as e:
        log.error(f"Nearby command probe failed: {e}")

def try_authenticated_0x51():
    """Try command 0x51 after attempting authentication."""
    
    log.info("This would require successful authentication first...")
    log.info("Since we can't authenticate with Seritag, we can't test this yet.")
    log.info("But this confirms 0x51 is a real command that needs auth!")

def main():
    """Run all investigations on command 0x51."""
    
    log.info("🔬 Investigating Seritag Command 0x51")
    log.info("This command returned 91AE (auth error) instead of 911C (unsupported)")
    
    check_standard_commands()
    
    log.info("\n1️⃣ Probing nearby commands...")
    probe_nearby_commands()
    
    log.info("\n2️⃣ Trying 0x51 variations...")
    probe_command_51_variations()
    
    log.info("\n3️⃣ Analysis...")
    try_authenticated_0x51()
    
    log.info("\n🎯 CONCLUSION:")
    log.info("Command 0x51 is recognized by Seritag firmware!")
    log.info("It requires authentication, suggesting it's a privileged operation.")
    log.info("This could be a Seritag-specific configuration or factory command.")

if __name__ == "__main__":
    main()
