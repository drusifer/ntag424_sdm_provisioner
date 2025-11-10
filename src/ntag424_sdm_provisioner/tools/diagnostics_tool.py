"""
Diagnostics Tool - Display complete tag information.

Shows:
- Chip version and hardware info
- Key versions
- File IDs and settings
- NDEF content
- Database status
"""

import logging
from ntag424_sdm_provisioner.tools.base import Tool, TagState, TagPrecondition
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.hal import NTag424CardConnection, hexb
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.get_key_version import GetKeyVersion
from ntag424_sdm_provisioner.commands.get_file_ids import GetFileIds
from ntag424_sdm_provisioner.commands.iso_commands import ISOSelectFile, ISOReadBinary, ISOFileID
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.commands.base import ApduError

log = logging.getLogger(__name__)


class DiagnosticsTool:
    """
    Display complete tag diagnostics.
    
    Always available - no preconditions.
    Useful for troubleshooting and understanding tag state.
    """
    
    name = "Show Diagnostics"
    description = "Display complete tag information (chip, keys, NDEF)"
    preconditions = TagPrecondition.NONE  # Always available
    
    def execute(self, tag_state: TagState, card: NTag424CardConnection, 
                key_mgr: CsvKeyManager) -> bool:
        """Display full diagnostics."""
        print("\n" + "="*70)
        print("FULL TAG DIAGNOSTICS")
        print("="*70)
        
        # Chip information
        self._print_chip_info(card)
        
        # Database status
        self._print_database_status(tag_state)
        
        # Key versions
        self._print_key_versions(card)
        
        # File IDs
        self._print_file_ids(card)
        
        # CC File
        self._print_cc_file(card)
        
        # NDEF File
        self._print_ndef_file(card)
        
        # Backups
        self._print_backups(tag_state, key_mgr)
        
        print("="*70)
        
        return True  # Always succeeds
    
    def _print_chip_info(self, card: NTag424CardConnection):
        """Print chip version and hardware information."""
        print("\nChip Information:")
        
        try:
            version_info = card.send(GetChipVersion())
            
            print(f"  UID:              {version_info.uid.hex().upper()}")
            print(f"  Asset Tag:        {self._format_asset_tag(version_info.uid)}")
            print(f"  HW Vendor ID:     0x{version_info.hw_vendor_id:02X}")
            print(f"  HW Type:          0x{version_info.hw_type:02X}")
            print(f"  HW Subtype:       0x{version_info.hw_subtype:02X}")
            print(f"  HW Version:       {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"  HW Storage:       {version_info.hw_storage_size} bytes")
            print(f"  HW Protocol:      {version_info.hw_protocol}")
            print(f"  SW Vendor ID:     0x{version_info.sw_vendor_id:02X}")
            print(f"  SW Type:          0x{version_info.sw_type:02X}")
            print(f"  SW Subtype:       0x{version_info.sw_subtype:02X}")
            print(f"  SW Version:       {version_info.sw_major_version}.{version_info.sw_minor_version}")
            print(f"  SW Storage:       {version_info.sw_storage_size} bytes")
            print(f"  SW Protocol:      {version_info.sw_protocol}")
            print(f"  Batch Number:     {version_info.batch_no.hex().upper()}")
            print(f"  Fabrication Date: Week {version_info.fab_week}, 20{version_info.fab_year}")
        
        except Exception as e:
            print(f"  Error reading chip info: {e}")
    
    def _print_database_status(self, tag_state: TagState):
        """Print database entry status."""
        print("\nDatabase Status:")
        
        if tag_state.in_database and tag_state.keys:
            print(f"  Status:           {tag_state.keys.status.upper()}")
            print(f"  Provisioned Date: {tag_state.keys.provisioned_date}")
            if tag_state.keys.notes:
                print(f"  Notes:            {tag_state.keys.notes}")
            print(f"  PICC Master Key:  {tag_state.keys.picc_master_key[:16]}...")
        else:
            print("  Status:           NOT IN DATABASE")
    
    def _print_key_versions(self, card: NTag424CardConnection):
        """Print key versions (unauthenticated read)."""
        print("\nKey Versions (unauthenticated read):")
        
        for key_no in range(5):
            try:
                resp = card.send(GetKeyVersion(key_no))
                print(f"  Key {key_no}: v0x{resp.version:02X}")
            except Exception as e:
                print(f"  Key {key_no}: Error - {e}")
    
    def _print_file_ids(self, card: NTag424CardConnection):
        """Print available file IDs."""
        print("\nFile IDs:")
        
        try:
            file_ids = card.send(GetFileIds())  # Returns List[int] directly
            if file_ids:
                for file_id in file_ids:
                    print(f"  File 0x{file_id:02X}")
            else:
                print("  No files returned (GetFileIDs not supported on NTAG424)")
        except ApduError as e:
            if e.sw1 == 0x91 and e.sw2 == 0x1C:
                print("  GetFileIDs not supported (expected on NTAG424)")
            else:
                print(f"  Error: {e}")
    
    def _print_cc_file(self, card: NTag424CardConnection):
        """Print Capability Container file."""
        print("\nCapability Container (CC) File:")
        
        try:
            card.send(ISOSelectFile(ISOFileID.CC_FILE))
            cc_data = card.send(ISOReadBinary(0, 15))
            
            print(f"  Raw Data: {cc_data.hex().upper()}")
            
            # Parse CC file
            if len(cc_data) >= 15:
                magic = int.from_bytes(cc_data[0:2], 'big')
                version = f"{cc_data[2]}.{cc_data[3]}"
                mle = int.from_bytes(cc_data[4:6], 'big')
                mlc = int.from_bytes(cc_data[6:8], 'big')
                ndef_file_id = int.from_bytes(cc_data[9:11], 'big')
                ndef_max_size = int.from_bytes(cc_data[11:13], 'big')
                ndef_read_access = cc_data[13]
                ndef_write_access = cc_data[14]
                
                print(f"    Magic:       {magic:04X}")
                print(f"    Version:     {version}")
                print(f"    MLe:         {mle} bytes")
                print(f"    MLc:         {mlc} bytes")
                print(f"    NDEF File:   {ndef_file_id:04X}")
                print(f"    Max Size:    {ndef_max_size} bytes")
                print(f"    Read Access: 0x{ndef_read_access:02X}")
                print(f"    Write Access: 0x{ndef_write_access:02X}")
            
            # Re-select PICC app
            card.send(SelectPiccApplication())
        
        except Exception as e:
            print(f"  Error reading CC file: {e}")
            card.send(SelectPiccApplication())
    
    def _print_ndef_file(self, card: NTag424CardConnection):
        """Print NDEF file content."""
        print("\nNDEF File:")
        
        try:
            card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
            ndef_data = card.send(ISOReadBinary(0, 200))
            
            print(f"  Length:      {len(ndef_data)} bytes")
            print(f"  Data (first 100 bytes):")
            
            # Print in 32-byte hex lines
            for i in range(0, min(100, len(ndef_data)), 32):
                chunk = ndef_data[i:i+32]
                print(f"    {chunk.hex().upper()}")
            
            # Re-select PICC app
            card.send(SelectPiccApplication())
        
        except Exception as e:
            print(f"  Error reading NDEF: {e}")
            card.send(SelectPiccApplication())
    
    def _print_backups(self, tag_state: TagState, key_mgr: CsvKeyManager):
        """Print backup information."""
        print("\nBackups:")
        
        if tag_state.backups_count == 0:
            print("  No backups found")
        else:
            print(f"  Total backups: {tag_state.backups_count}")
            print(f"  Successful backups: {'Yes' if tag_state.has_successful_backup else 'No'}")
    
    def _format_asset_tag(self, uid: bytes) -> str:
        """Format UID as asset tag (e.g., 'B3-664A')."""
        uid_hex = uid.hex().upper()
        if len(uid_hex) >= 6:
            return f"{uid_hex[2:4]}-{uid_hex[4:8]}"
        return uid_hex

