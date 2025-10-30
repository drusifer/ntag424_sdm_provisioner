from typing import List, Optional
from ntag424_sdm_provisioner.hal import NTag424CardConnection
from ntag424_sdm_provisioner.commands.base import ApduCommand, SW_OK, ApduError, Ntag424VersionInfo
from dataclasses import dataclass
from enum import Enum

class KeyType(Enum):
    """Key type for MIFARE Classic authentication."""
    
    # $60h = Key is used as a TYPE A key for authentication. 
    TYPE_A = 0x60
    
    # $61h = Key is used as a TYPE B key for authentication. 
    TYPE_B = 0x61
# file: commands.py
        
class GetData(ApduCommand):
    """
    Returns the serial number (UID) or Answer to Select (ATS) of the connected PICC. [cite: 180]
    """
    def __init__(self, get_ats: bool = False, use_escape: bool = False):
        """
        Args:
            get_ats: If True, gets the ATS[cite: 191]. If False, gets the UID[cite: 190].
        """
        super().__init__(use_escape)
        self._p1 = 0x01 if get_ats else 0x00 # [cite: 182]

    def execute(self, connection: NTag424CardConnection) -> List[int]:
        """
        Executes the Get Data command.

        Returns:
            A list of integers representing the UID or ATS.
        """
        apdu = [
            0xFF,  # Class [cite: 182]
            0xCA,  # INS [cite: 182]
            self._p1, # P1 [cite: 182]
            0x00,  # P2 [cite: 182]
            0x00   # Le (Full Length) [cite: 182]
        ]
        data, sw1, sw2 = self.send_apdu(connection, apdu)

        if (sw1, sw2) == SW_OK: # [cite: 188]
            return data
        else:
            raise ApduError("Get Data operation failed", sw1, sw2) # [cite: 188]


#########################################            
# PICC Commands for MiFARE Classic
#########################################            

class LoadAuthenticationKeys(ApduCommand):
    """
    Loads authentication keys into the reader's volatile memory. [cite: 199, 200]
    """
    def __init__(self, key_number: int, key: List[int], use_escape: bool = False):
        """
        Args:
            key_number: The key location (0x00 or 0x01). [cite: 204]
            key: The 6-byte key value. [cite: 204]
        """
        super().__init__(use_escape)
        if key_number not in [0x00, 0x01]:
            raise ValueError("Key Number must be 0x00 or 0x01.") # [cite: 204]
        if len(key) != 6:
            raise ValueError("Key must be 6 bytes long.") # [cite: 204]
        self.key_number = key_number
        self.key = key

    def execute(self, connection: NTag424CardConnection) -> None:
        """Executes the Load Authentication Keys command."""
        apdu = [
            0xFF,  # Class [cite: 202]
            0x82,  # INS [cite: 202]
            0x00,  # P1 (Key Structure: volatile memory) [cite: 202, 204]
            self.key_number,  # P2 (Key Number) [cite: 202, 204]
            0x06,  # Lc (Length of key) [cite: 202, 204]
            *self.key # Data In (Key) [cite: 202, 204]
        ]
        _, sw1, sw2 = self.send_apdu(connection, apdu)

        if (sw1, sw2) != (0x90, 0x00): # [cite: 208]
            raise ApduError("Load Authentication Keys failed", sw1, sw2) # [cite: 208]

class Authenticate(ApduCommand):
    """
    Authenticates a sector of a MIFARE Classic card using a key stored in the reader. [cite: 219]
    """
    def __init__(self, block_number: int, key_type: KeyType, key_number: int, use_escape: bool = False):
        """
        Args:
            block_number: The memory block to be authenticated. [cite: 227]
            key_type: The type of key to use (TYPE_A or TYPE_B). [cite: 227]
            key_number: The location of the key in the reader (0x00 or 0x01). [cite: 227]
        """
        super().__init__(use_escape)
        self.block_number = block_number
        self.key_type = key_type
        self.key_number = key_number

    def execute(self, connection: NTag424CardConnection) -> None:
        """Executes the Authenticate command."""
        auth_data = [
            0x01, # Version [cite: 226]
            0x00, # Byte 2 (0x00) [cite: 226]
            self.block_number, # Byte 3 (Block Number) [cite: 226]
            self.key_type.value, # Byte 4 (Key Type) [cite: 226]
            self.key_number # Byte 5 (Key Number) [cite: 226]
        ]
        apdu = [
            0xFF, # Class [cite: 224]
            0x86, # INS [cite: 224]
            0x00, # P1 [cite: 224]
            0x00, # P2 [cite: 224]
            0x05, # Lc [cite: 224]
            *auth_data # Authenticate Data Bytes [cite: 224]
        ]
        _, sw1, sw2 = self.send_apdu(connection, apdu)

        if (sw1, sw2) != (0x90, 0x00): # [cite: 238]
            raise ApduError("Authentication failed", sw1, sw2) # [cite: 238]

class ReadBinaryBlocks(ApduCommand):
    """
    Retrieves data from a binary block of the PICC after authentication. [cite: 366]
    """
    def __init__(self, block_number: int, num_bytes_to_read: int, use_escape: bool = False):
        """
        Args:
            block_number: The block to be accessed. [cite: 370]
            num_bytes_to_read: The number of bytes to read (Maximum 16). [cite: 370]
        """
        super().__init__(use_escape)
        self.block_number = block_number
        self.num_bytes = num_bytes_to_read

    def execute(self, connection: NTag424CardConnection) -> List[int]:
        """Executes the Read Binary Blocks command."""
        apdu = [
            0xFF, # Class [cite: 368]
            0xB0, # INS [cite: 368]
            0x00, # P1 [cite: 368]
            self.block_number, # P2 [cite: 368]
            self.num_bytes # Le [cite: 368]
        ]
        data, sw1, sw2 = self.send_apdu(connection, apdu)

        if (sw1, sw2) == (0x90, 0x00): # [cite: 374]
            return data
        else:
            raise ApduError("Read Binary Blocks failed", sw1, sw2) # [cite: 374]

class UpdateBinaryBlocks(ApduCommand):
    """
    Writes data to a block on the PICC after authentication. [cite: 389]
    """
    def __init__(self, block_number: int, block_data: List[int], use_escape: bool = False):
        """
        Args:
            block_number: The starting block to be updated. [cite: 393]
            block_data: The data to write (4 bytes for MIFARE Ultralight, 16 for 1K/4K). [cite: 393]
        """
        super().__init__(use_escape)
        if len(block_data) not in [4, 16]:
            raise ValueError("Block data must be 4 or 16 bytes.") # [cite: 393]
        self.block_number = block_number
        self.block_data = block_data

    def execute(self, connection: NTag424CardConnection) -> None:
        """Executes the Update Binary Blocks command."""
        apdu = [
            0xFF, # Class [cite: 391]
            0xD6, # INS [cite: 391]
            0x00, # P1 [cite: 391]
            self.block_number, # P2 [cite: 391]
            len(self.block_data), # Lc [cite: 391]
            *self.block_data # Data In [cite: 391]
        ]
        _, sw1, sw2 = self.send_apdu(connection, apdu)
        if (sw1, sw2) != (0x90, 0x00): # [cite: 395]
            raise ApduError("Update Binary Blocks failed", sw1, sw2) # [cite: 395]

            
            

#########################################            
# Pseudo-ADPUI Commands
#########################################            
class GetFirmwareVersion(ApduCommand):
    """Retrieves the firmware version of the reader. [cite: 538]"""
    def __init__(self, use_escape: bool = True):
        super().__init__(use_escape)

    def execute(self, connection: NTag424CardConnection) -> str:
        """
        Executes the command to get the reader's firmware version.

        Returns:
            The firmware version as an ASCII string. [cite: 544]
        """
        apdu = [
            0xFF, # Class [cite: 540]
            0x00, # INS [cite: 540]
            0x48, # P1 [cite: 540]
            0x00, # P2 [cite: 540]
            0x00  # Le [cite: 540]
        ]
        # This pseudo-APDU doesn't return standard SW1/SW2 in the same way.
        # It just returns the data.
        data, _, _ = self.send_apdu(connection, apdu)
        return bytes(data).decode('ascii') # [cite: 544]

@dataclass
class LedStatus:
    """Represents the current state of the reader's LEDs."""
    red_led_on: bool # Bit 0 [cite: 521]
    green_led_on: bool # Bit 1 [cite: 521]

class LedAndBuzzerControl(ApduCommand):
    """Controls the bi-color LED and buzzer states. [cite: 494]"""
    def __init__(self, final_red_on: Optional[bool] = None,
                 final_green_on: Optional[bool] = None,
                 initial_red_blink: bool = False,
                 initial_green_blink: bool = False,
                 red_blinks: bool = False,
                 green_blinks: bool = False,
                 t1_duration_100ms: int = 0,
                 t2_duration_100ms: int = 0,
                 repetitions: int = 0,
                 link_buzzer_t1: bool = False,
                 link_buzzer_t2: bool = False,
                 use_escape: bool = True):
        super().__init__(use_escape)

        # Build P2 - LED State Control Byte [cite: 499, 502]
        p2 = 0
        if final_red_on is not None:
            p2 |= (0b1 << 0) if final_red_on else 0 # Final Red LED State [cite: 502]
            p2 |= (0b1 << 2) # State Mask Red LED [cite: 502]
        if final_green_on is not None:
            p2 |= (0b1 << 1) if final_green_on else 0 # Final Green LED State [cite: 502]
            p2 |= (0b1 << 3) # State Mask Green LED [cite: 502]
        p2 |= (0b1 << 4) if initial_red_blink else 0 # Initial Red Blink State [cite: 502]
        p2 |= (0b1 << 5) if initial_green_blink else 0 # Initial Green Blink State [cite: 502]
        p2 |= (0b1 << 6) if red_blinks else 0 # Blinking Mask Red LED [cite: 502]
        p2 |= (0b1 << 7) if green_blinks else 0 # Blinking Mask Green LED [cite: 502]
        self.p2 = p2

        # Build Data In - Blinking Duration Control [cite: 503, 505]
        buzzer_byte = 0
        if link_buzzer_t1: buzzer_byte |= 0b01 # [cite: 510]
        if link_buzzer_t2: buzzer_byte |= 0b10 # [cite: 511]
        self.data_in = [
            t1_duration_100ms, # T1 Duration (Unit = 100ms) [cite: 505]
            t2_duration_100ms, # T2 Duration (Unit = 100ms) [cite: 505]
            repetitions, # Number of repetition [cite: 505]
            buzzer_byte  # Link to Buzzer [cite: 505, 506]
        ]

    def execute(self, connection: NTag424CardConnection) -> LedStatus:
        """
        Executes the LED and Buzzer control command.

        Returns:
            An LedStatus object representing the current state of the LEDs after the operation.
        """
        apdu = [
            0xFF, # Class [cite: 496]
            0x00, # INS [cite: 496]
            0x40, # P1 [cite: 496]
            self.p2, # P2 (LED State Control) [cite: 496]
            0x04, # Lc [cite: 496]
            *self.data_in # Data In [cite: 496]
        ]
        _, sw1, sw2 = self.send_apdu(connection, apdu)

        if sw1 == 0x90: # [cite: 519]
            # SW2 contains the current LED state [cite: 519, 520]
            return LedStatus(red_led_on=bool(sw2 & 0b01), green_led_on=bool(sw2 & 0b10)) # [cite: 521]
        else:
            raise ApduError("LED and Buzzer Control failed", sw1, sw2) # [cite: 519]

class TurnAntennaOn(ApduCommand):
    """Turns the reader's antenna power on."""
    def __init__(self, use_escape: bool = True):
        super().__init__(use_escape)

    def execute(self, connection: NTag424CardConnection) -> None:
        # This is a direct command, best sent via Direct Transmit or as an escape command.
        # It's constructed from a different part of the manual.
        # The command is D4 32 01 01h. [cite: 616]
        # We wrap it in a pseudo-APDU for direct transmission.
        payload = [0xD4, 0x32, 0x01, 0x01] # [cite: 616]
        apdu = [
            0xFF, # Class [cite: 483]
            0x00, # INS [cite: 483]
            0x00, # P1 [cite: 483]
            0x00, # P2 [cite: 483]
            len(payload), # Lc [cite: 483]
            *payload # Data In [cite: 483]
        ]
        # The response for this is not well-documented, we just check for general success.
        _, sw1, sw2 = self.send_apdu(connection, apdu)
        if (sw1, sw2) != (0x90, 0x00):
             # General success code from other commands.
            raise ApduError("Turn Antenna On failed", sw1, sw2)

class TurnAntennaOff(ApduCommand):
    """Turns the reader's antenna power off to save power. [cite: 614]"""
    def __init__(self, use_escape: bool = True):
        super().__init__(use_escape)

    def execute(self, connection: NTag424CardConnection) -> None:
        # The command is D4 32 01 00h. [cite: 615]
        # We wrap it in a pseudo-APDU for direct transmission.
        payload = [0xD4, 0x32, 0x01, 0x00] # [cite: 615]
        apdu = [
            0xFF, # Class [cite: 483]
            0x00, # INS [cite: 483]
            0x00, # P1 [cite: 483]
            0x00, # P2 [cite: 483]
            len(payload), # Lc [cite: 483]
            *payload # Data In [cite: 483]
        ]
        _, sw1, sw2 = self.send_apdu(connection, apdu)
        if (sw1, sw2) != (0x90, 0x00):
            raise ApduError("Turn Antenna Off failed", sw1, sw2)