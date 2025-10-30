# Assuming ApduCommand, NTag424CardConnection, ApduError, and hexb are defined elsewhere

from abc import ABC, abstractmethod
from typing import List, Tuple
from ntag424_sdm_provisioner.commands.base import ApduCommand

# --- APDU Commands for MIFARE Classic (Escape Commands) ---

# Command 1: Load Key (FF 82 00 00 06 [Key])
CLA_LOAD_KEY = 0xFF
INS_LOAD_KEY = 0x82
P1_LOAD_KEY = 0x00
P2_LOAD_KEY = 0x00
LC_LOAD_KEY = 0x06 # Length of the key

# Command 2: Authenticate (FF 86 00 00 05 [Version, Key ID, Block])
CLA_AUTH = 0xFF
INS_AUTH = 0x86
P1_AUTH = 0x00
P2_AUTH = 0x00
LC_AUTH = 0x05 # Length of authentication data block

# Default Factory Key A (MIFARE Classic 1K)
DEFAULT_KEY_A = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]

class MFA_Authenticate(ApduCommand):
    """
    Performs the two-step MIFARE Classic authentication process.
    """
    def __init__(self, block_address: int, key: List[int] = DEFAULT_KEY_A, use_escape: bool = True):
        super().__init__(use_escape=use_escape)
        self.block_address = block_address
        self.key = key
        
    def execute(self, connection) -> Tuple[bool, int, int]:
        """
        Executes the Load Key and Authenticate commands.
        """
        # --- Step 1: Load Key into Reader Volatile Memory (Slot 0) ---
        
        # FF 82 00 00 06 [Key]
        load_key_apdu = [CLA_LOAD_KEY, INS_LOAD_KEY, P1_LOAD_KEY, P2_LOAD_KEY, LC_LOAD_KEY] + self.key
        
        print(f"\n--- Auth Block {self.block_address} ---")
        print("  1. Load Key...")
        data, sw1, sw2 = self.send_apdu(connection, load_key_apdu)

        if (sw1, sw2) != (0x90, 0x00):
            print(f"!! ERROR: Load Key failed with SW: {sw1:02X}{sw2:02X}")
            return False, sw1, sw2

        # --- Step 2: Authenticate with the Loaded Key ---
        
        # The key structure: 
        # [Version, Key Index (0 for volatile), Key Type (0x60=KeyA, 0x61=KeyB), Block Address]
        # Version 0x01 is often used for this reader type
        auth_data = [0x01, 0x00, 0x60, self.block_address]
        
        # FF 86 00 00 05 [auth_data]
        # Note: The ACR122U documentation sometimes omits the 0x01 version byte in the auth_data,
        # but the standard PC/SC wrapper usually requires the full 5 bytes including the 0x01.
        auth_apdu = [CLA_AUTH, INS_AUTH, P1_AUTH, P2_AUTH, LC_AUTH] + auth_data
        
        print("  2. Authenticate...")
        data, sw1, sw2 = self.send_apdu(connection, auth_apdu)

        if (sw1, sw2) == (0x90, 0x00):
            print("  ✅ Authentication Successful.")
            return True, sw1, sw2
        else:
            print(f"!! ERROR: Authentication failed with SW: {sw1:02X}{sw2:02X}")
            return False, sw1, sw2
        
# --- APDU Commands for MIFARE Classic (Escape Commands) ---
# Command 3: Read Block (FF B0 00 [Block Address] [Length=10h])
CLA_READ_BLOCK = 0xFF
INS_READ_BLOCK = 0xB0
P1_READ_BLOCK = 0x00
LEN_READ_BLOCK = 0x10 # 16 bytes (standard MIFARE Classic block size)

class MFC_ReadBlock(ApduCommand):
    """
    Reads a single MIFARE Classic data block (16 bytes).
    Requires prior authentication of the block's sector.
    """
    def __init__(self, block_address: int, use_escape: bool = True):
        super().__init__(use_escape=use_escape)
        self.block_address = block_address

    def execute(self, connection) -> Tuple[List[int], int, int]:
        """
        Executes the Read Block command.
        """
        # FF B0 00 [Block Address] [Length]
        read_apdu = [
            CLA_READ_BLOCK, INS_READ_BLOCK, P1_READ_BLOCK, 
            self.block_address, LEN_READ_BLOCK
        ]
        
        print(f"  3. Reading Block {self.block_address}...")
        return self.send_apdu(connection, read_apdu)

class MFC_ListSectors(ApduCommand):
    """
    Performs a full dump of the readable sectors (1-15) of a MIFARE Classic 1K chip.
    It attempts to authenticate each sector with the default key (FFFFFFFFFFFF).
    """
    # A MIFARE Classic 1K chip has 16 sectors (0-15).
    # Each sector has 4 blocks (0-3). Block 3 is the Sector Trailer (keys/access bits).
    # Block 0 of Sector 0 is reserved (Manufacturer Block).
    NUM_SECTORS = 16

    def __init__(self, key: List[int] = DEFAULT_KEY_A, use_escape: bool = True):
        super().__init__(use_escape=use_escape)
        self.key = key

    def execute(self, connection) -> bool:
        """
        Loops through all sectors, attempts authentication, and reads data blocks.
        """
        print("\n=======================================================")
        print("Starting MIFARE Classic 1K Sector Listing (Default Key)")
        print("=======================================================")
        
        for sector_index in range(self.NUM_SECTORS):
            # The Sector Trailer is always the last block in the sector (index 3)
            # Sector Trailer block address is (Sector * 4) + 3
            trailer_block_address = (sector_index * 4) + 3
            
            # --- Step A: Authenticate the Sector ---
            authenticator = MFA_Authenticate(trailer_block_address, self.key, self.use_escape)
            authenticated, sw1, sw2 = authenticator.execute(connection)
            
            if not authenticated:
                print(f"!! Skipping Sector {sector_index}. Authentication Failed.")
                print("-------------------------------------------------------")
                continue # Move to the next sector

            # --- Step B: Read the Data Blocks (Blocks 0, 1, 2) ---
            print(f"  Authenticated. Reading Data Blocks for Sector {sector_index}:")
            
            # Data blocks are (Sector * 4) + 0, + 1, + 2
            # NOTE: Skip Block 0 for Sector 0 (Manufacturer block) as it is read-only.
            start_block = 1 if sector_index == 0 else 0
            
            for block_index in range(start_block, 4):
                block_address = (sector_index * 4) + block_index
                
                # Use the ReadBlock command
                reader = MFC_ReadBlock(block_address, self.use_escape)
                data, sw1, sw2 = reader.execute(connection)
                
                if (sw1, sw2) == (0x90, 0x00):
                    data_hex = ''.join(f'{b:02X}' for b in data)
                    print(f"    Block {block_address:02X}: {data_hex}")
                else:
                    print(f"    Block {block_address:02X}: !! READ FAILED (SW: {sw1:02X}{sw2:02X})")
            
            print("-------------------------------------------------------")
            
        print("\n=======================================================")
        print("MIFARE Classic Listing Complete.")
        print("=======================================================")
        return True