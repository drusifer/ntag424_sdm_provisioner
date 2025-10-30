#!/usr/bin/env python3
"""
Test if SDM works with just Phase 1 authentication
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, AuthenticateEV2First
from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
from ntag424_sdm_provisioner.constants import FACTORY_KEY, SDMConfiguration, CommMode, FileNo, AccessRightsPresets, SDMOption
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

class SeritagAuthSession:
    """Simplified authentication session for Seritag (Phase 1 only)"""
    
    def __init__(self, key: bytes):
        self.key = key
        self.session_enc_key = None
        self.session_mac_key = None
        self.ti = None
        
    def authenticate(self, card, key_no: int = 0):
        """Authenticate using only Phase 1 (Seritag approach)"""
        print(f"Authenticating with Seritag Phase 1 only...")
        
        # Phase 1
        cmd1 = AuthenticateEV2First(key_no=key_no)
        response1 = cmd1.execute(card)
        print(f"Phase 1 SUCCESS: {response1.challenge.hex().upper()}")
        
        # Decrypt RndB
        cipher = AES.new(self.key, AES.MODE_ECB)
        rndb = cipher.decrypt(response1.challenge)
        print(f"Decrypted RndB: {rndb.hex().upper()}")
        
        # Generate session keys (simplified - using RndB as basis)
        # This is a simplified approach - real implementation would derive proper keys
        self.session_enc_key = rndb[:16]
        self.session_mac_key = rndb[1:] + rndb[0:1]  # Rotated RndB
        self.ti = get_random_bytes(4)  # Transaction ID
        
        print(f"Session keys derived:")
        print(f"  ENC: {self.session_enc_key.hex().upper()}")
        print(f"  MAC: {self.session_mac_key.hex().upper()}")
        print(f"  TI:  {self.ti.hex().upper()}")
        
        return self
    
    def apply_cmac(self, cmd_header: bytes, cmd_data: bytes) -> bytes:
        """Apply CMAC protection (simplified for testing)"""
        # This is a placeholder - real CMAC would use proper algorithm
        print(f"Applying CMAC protection (simplified)")
        return cmd_data

def test_sdm_with_phase1():
    print("Testing SDM with Phase 1 only authentication...")
    
    try:
        with CardManager(0) as card:
            print("Card connected")
            
            # Select application
            try:
                SelectPiccApplication().execute(card)
                print("Application selected")
            except Exception as se:
                if "0x6985" in str(se):
                    print("Application already selected")
                else:
                    print(f"Selection warning: {se}")
            
            # Authenticate with Phase 1 only
            session = SeritagAuthSession(FACTORY_KEY)
            session.authenticate(card, key_no=0)
            
            # Try to configure SDM with PLAIN mode (no CMAC required)
            print("\nTesting SDM configuration with PLAIN mode...")
            config = SDMConfiguration(
                file_no=FileNo.NDEF_FILE,
                comm_mode=CommMode.PLAIN,  # No CMAC required
                access_rights=AccessRightsPresets.FREE_READ_KEY0_WRITE.to_bytes(),
                enable_sdm=True,
                sdm_options=int(SDMOption.SDM_WITH_COUNTER),
                picc_data_offset=10,  # Placeholder offsets
                mac_input_offset=10,
                mac_offset=20
            )
            
            try:
                ChangeFileSettings(config).execute(card)
                print("SUCCESS: SDM configured with PLAIN mode!")
            except Exception as e:
                print(f"FAILED: SDM configuration failed: {e}")
                
                # Try with MAC mode using our simplified session
                print("\nTesting SDM configuration with MAC mode...")
                config.comm_mode = CommMode.MAC
                try:
                    ChangeFileSettings(config).execute(card, session=session)
                    print("SUCCESS: SDM configured with MAC mode!")
                except Exception as e2:
                    print(f"FAILED: SDM MAC mode also failed: {e2}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sdm_with_phase1()
