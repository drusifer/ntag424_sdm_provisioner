"""
EV2 Authentication Test Suite

Comprehensive tests for the Seritag simulator to verify EV2 authentication 
compliance with NXP NTAG424 DNA specification.
"""
import unittest

import pytest

from ntag424_sdm_provisioner.seritag_simulator import SeritagCardManager, SeritagSimulator
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.constants import FACTORY_KEY

class TestSeritagEV2Authentication(unittest.TestCase):
    """Test suite for Seritag EV2 authentication compliance."""
    
    def setUp(self):
        """Set up test environment."""
        self.simulator = SeritagSimulator()
        self.card_manager = SeritagCardManager(0)
        
    def test_connection(self):
        """Test basic connection to simulator."""
        with self.card_manager as card:
            self.assertIsNotNone(card)
            
    def test_select_application(self):
        """Test SelectPICCApplication command."""
        with self.card_manager as card:
            SelectPiccApplication().execute(card)
            
    def test_get_version(self):
        """Test GetChipVersion command."""
        with self.card_manager as card:
            SelectPiccApplication().execute(card)
            version_info = GetChipVersion().execute(card)
            
            # Verify Seritag-specific version info
            self.assertEqual(version_info.hw_major_version, 48)
            self.assertEqual(version_info.hw_minor_version, 0)
            self.assertEqual(version_info.uid, b'\x04\x3F\x68\x4A\x2F\x70\x80')
            
    def test_ev2_authentication_phase1(self):
        """Test EV2 authentication phase 1."""
        with self.card_manager as card:
            SelectPiccApplication().execute(card)
            
            # Test AuthenticateEV2First
            from ntag424_sdm_provisioner.commands.sdm_commands import AuthenticateEV2First
            
            cmd = AuthenticateEV2First(key_no=0)
            response = cmd.execute(card)
            
            # Verify response
            self.assertEqual(len(response.challenge), 16)
            self.assertEqual(response.key_no_used, 0)
            
    def test_ev2_authentication_full(self):
        """Test complete EV2 authentication flow."""
        with self.card_manager as card:
            SelectPiccApplication().execute(card)
            
            # Test full authentication
            session = Ntag424AuthSession(FACTORY_KEY)
            session_keys = session.authenticate(card, key_no=0)
            
            # Verify session keys
            self.assertIsNotNone(session_keys)
            self.assertIsNotNone(session_keys.ti)
            self.assertIsNotNone(session_keys.session_enc_key)
            self.assertIsNotNone(session_keys.session_mac_key)
            self.assertEqual(len(session_keys.ti), 4)
            self.assertEqual(len(session_keys.session_enc_key), 16)
            self.assertEqual(len(session_keys.session_mac_key), 16)
            
    def test_ev2_authentication_all_keys(self):
        """Test EV2 authentication with all 5 keys."""
        with self.card_manager as card:
            SelectPiccApplication().execute(card)
            
            for key_no in range(5):
                session = Ntag424AuthSession(FACTORY_KEY)
                session_keys = session.authenticate(card, key_no=key_no)
                
                self.assertIsNotNone(session_keys)
            
    def test_ev2_authentication_wrong_key(self):
        """Test EV2 authentication with wrong key."""
        with self.card_manager as card:
            SelectPiccApplication().execute(card)
            
            # Use wrong key (all ones instead of all zeros)
            wrong_key = b'\xFF' * 16
            session = Ntag424AuthSession(wrong_key)
            
            with self.assertRaises(Exception):
                session.authenticate(card, key_no=0)
            
    def test_ev2_authentication_invalid_key_number(self):
        """Test EV2 authentication with invalid key number."""
        with self.card_manager as card:
            SelectPiccApplication().execute(card)
            
            session = Ntag424AuthSession(FACTORY_KEY)
            
            # Try key number 5 (invalid)
            with self.assertRaises(Exception):
                session.authenticate(card, key_no=5)

def main():
    """Entry point for command-line script."""
    unittest.main()

if __name__ == "__main__":
    main()
