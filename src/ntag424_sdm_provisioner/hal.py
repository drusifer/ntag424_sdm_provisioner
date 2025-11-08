import logging
from typing import List, Optional, Tuple, Union

from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.CardConnection import CardConnection
# ✅ Import the necessary low-level functions and constants
from smartcard.scard import (SCARD_SCOPE_USER, SCARD_STATE_PRESENT,
                             SCARD_STATE_UNAWARE, SCardEstablishContext,
                             SCardGetStatusChange, SCardReleaseContext)
from smartcard.System import readers
from ntag424_sdm_provisioner.constants import StatusWord

# --- PC/SC Constants (Corrected Cross-Platform Import) ---
try:
    # This is the correct import for Windows systems
    from smartcard.scard import SCARD_CTL_CODE
    IOCTL_CCID_ESCAPE = SCARD_CTL_CODE(3500)
except ImportError:
    # This is the correct import for PCSC-Lite (Linux/macOS)
    IOCTL_CCID_ESCAPE = 3500

def hexb(data: Union[bytes, List[int]]) -> str:
    """Format bytes or list of ints as hex string (no smartcard dependency)."""
    if isinstance(data, bytes):
        return ' '.join(f'{b:02X}' for b in data)
    elif isinstance(data, (list, tuple)):
        return ' '.join(f'{b:02X}' for b in data)
    else:
        return str(data)

def format_status_word(sw1: int, sw2: int) -> str:
    """Format status word with enum name for readability."""
    sw_value = (sw1 << 8) | sw2
    try:
        sw_enum = StatusWord(sw_value)
        return f"{sw_enum.name} (0x{sw1:02X}{sw2:02X})"
    except ValueError:
        # Not a known status word
        return f"0x{sw1:02X}{sw2:02X}"

log = logging.getLogger("hal")

class NTag242ConnectionError(Exception):
    """Custom exception for connection failures."""
    pass

class NTag242NoReadersError(Exception):
    """Custom exception for when no readers are found."""
    pass

class CardManager:
    """
    A robust context manager that uses a direct, blocking call to wait for a
    card tap, then establishes a clean connection.
    """
    def __init__(self, reader_index: int = 0, timeout_seconds: int = 15):
        self.reader_index = reader_index
        self.timeout_ms = timeout_seconds * 1000
        self.connection: Optional[CardConnection] = None
        self.context = None

    def __enter__(self) -> NTag424CardConnection:
        try:
            # 1. Establish a PC/SC context. This is the handle to the resource manager.
            hresult, self.context = SCardEstablishContext(SCARD_SCOPE_USER)
            if hresult != 0:
                raise NTag242ConnectionError(f"Failed to establish PC/SC context: {hresult}")

            all_readers = readers()
            if not all_readers:
                raise NTag242NoReadersError("No PC/SC readers found.")

            reader = all_readers[self.reader_index]
            log.info(f"Using reader '{reader}'. Waiting for a card tap...")

            # 2. Set up the state we are waiting for.
            reader_states = [(str(reader), SCARD_STATE_UNAWARE)]

            # 3. Make the blocking call with the correct arguments.
            hresult, current_states = SCardGetStatusChange(self.context, self.timeout_ms, reader_states)
            if hresult != 0:
                raise NTag242ConnectionError(f"SCardGetStatusChange failed: {hresult}")

            (reader_name, event_state, atr) = current_states[0]

            # 4. Check if a card was actually presented.
            if not (event_state & SCARD_STATE_PRESENT):
                raise NTag242ConnectionError("Timeout: No card was presented.")
            
            log.info(f"Card detected with ATR: {''.join(f'{b:02X}' for b in atr)}. Connecting...")

            # 5. Now, create a standard connection and connect to it.
            self.connection = reader.createConnection()
            self.connection.connect()
            log.info("Successfully connected to the card.")
            
            return NTag424CardConnection(self.connection)

        except Exception as e:
            # Ensure context is released on failure
            self.__exit__(None, None, None)
            log.error(f"Failed to establish card connection: {e}")
            raise NTag242ConnectionError(f"Failed to connect: {e}") from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            log.info("Disconnecting from the card.")
            self.connection.disconnect()
        # 6. Release the PC/SC context to clean up resources.
        if self.context:
            SCardReleaseContext(self.context)
        return False

    
# --- NTag424CardConnection (with send_apdu method restored) ---
class NTag424CardConnection:
    """
    A wrapper for a pyscard CardConnection that handles the low-level
    details of APDU transmission.
    """
    def __init__(self, connection: CardConnection):
        self.connection = connection

    def __str__(self) -> str:
        return str(self.connection.getReader())

    def wait_for_atr(self) -> List[int]:
        return wait_for_card_atr()

    def check_response(
        self, 
        sw1: int, 
        sw2: int, 
        expected: StatusWord = StatusWord.OK,
        error_message: str = "Command failed"
    ) -> None:
        """
        Check response status word and raise ApduError if not expected.
        
        Args:
            sw1: Status word 1
            sw2: Status word 2
            expected: Expected status word (default: OK)
            error_message: Error message prefix
        
        Raises:
            ApduError: If status word doesn't match expected
        """
        sw = StatusWord.from_bytes(sw1, sw2)
        
        if sw != expected:
            raise NTag242NoReadersError(error_message, sw1, sw2)
        
    def send(self, command):
        """
        Send a command to the card (NEW PATTERN).
        
        This is the preferred way to send commands:
            response = connection.send(GetVersion())
        
        Args:
            command: ApduCommand to send
            
        Returns:
            Command-specific response (parsed by command.parse_response())
        """
        # Build APDU from command
        apdu = command.build_apdu()
        
        # Send and get raw response
        data, sw1, sw2 = self.send_apdu(apdu, use_escape=command.use_escape)
        
        # Handle multi-frame responses (SW_ADDITIONAL_FRAME = 0x91AF)
        full_response = bytearray(data)
        while sw1 == 0x91 and sw2 == 0xAF:
            # Send GET_ADDITIONAL_FRAME (0x90AF0000)
            more_data, sw1, sw2 = self.send_apdu([0x90, 0xAF, 0x00, 0x00, 0x00])
            full_response.extend(more_data)
        
        # Let command parse the response
        return command.parse_response(bytes(full_response), sw1, sw2)
    
    def send_write_chunked(
        self, 
        cla: int, 
        ins: int, 
        offset: int, 
        data: bytes, 
        chunk_size: int = 52,
        use_escape: bool = False
    ) -> Tuple[int, int]:
        """
        Send write command with automatic chunking for large data.
        
        For ISO UpdateBinary (0xD6) or similar write commands that use offset addressing.
        Splits large writes into multiple chunks to respect reader limits.
        
        This handles UNAUTHENTICATED writes. For authenticated writes, use
        AuthenticatedConnection which would apply crypto to each chunk.
        
        Args:
            cla: Class byte (e.g., 0x00 for ISO)
            ins: Instruction byte (e.g., 0xD6 for UpdateBinary)
            offset: Starting offset for write
            data: Data to write
            chunk_size: Max bytes per chunk (default 52 for most readers)
            use_escape: Whether to use escape mode
        
        Returns:
            Final (sw1, sw2) status word
        """
        data_length = len(data)
        current_offset = offset
        
        log.debug(f"  >> Chunked write: {data_length} bytes, chunk_size={chunk_size}")
        
        while current_offset < offset + data_length:
            chunk_start = current_offset - offset
            chunk_end = min(chunk_start + chunk_size, data_length)
            chunk = data[chunk_start:chunk_end]
            
            # P1[7]=0: P1-P2 encodes 15-bit offset
            p1 = (current_offset >> 8) & 0x7F
            p2 = current_offset & 0xFF
            
            apdu = [cla, ins, p1, p2, len(chunk)] + list(chunk)
            
            log.debug(f"  >> Chunk: offset={current_offset}, size={len(chunk)}")
            _, sw1, sw2 = self.send_apdu(apdu, use_escape=use_escape)
            
            # Check for errors
            if (sw1, sw2) not in [(0x90, 0x00), (0x91, 0x00)]:
                log.error(f"  << Write chunk failed at offset {current_offset}: SW={sw1:02X}{sw2:02X}")
                return sw1, sw2
            
            current_offset += len(chunk)
        
        log.debug(f"  >> Chunked write complete: {data_length} bytes written")
        return sw1, sw2  # Return final status
    
    def send_apdu(self, apdu: List[int], use_escape: bool = False) -> Tuple[List[int], int, int]:
        """
        Sends a raw APDU command to the card and returns the response.

        This method contains the pyscard-specific logic, abstracting it away
        from the command classes.
        """
        log.debug(f"  >> C-APDU: {hexb(apdu)}")

        # Environment overrides for escape mode behavior
        try:
            import os
            if os.environ.get('FORCE_NO_ESCAPE', '').strip() == '1':
                use_escape = False
                log.debug("  >> Mode override: FORCED transmit() (no-escape)")
            elif os.environ.get('FORCE_ESCAPE', '').strip() == '1':
                use_escape = True
                log.debug("  >> Mode override: FORCED control() (escape)")
        except Exception:
            pass

        if use_escape:
            try:
                # Use the low-level control() for readers that need it (e.g., ACR122U)
                resp = self.connection.control(IOCTL_CCID_ESCAPE, apdu)
                
                if len(resp) < 2:
                    raise NTag242NoReadersError(f"APDU response via control() was too short: [{hexb(resp)}]")
                
                # Manually parse the raw response
                data, sw1, sw2 = resp[:-2], resp[-2], resp[-1]
                log.debug(f"  << R-APDU (Control): {hexb(data)} [{format_status_word(sw1, sw2)}]")
                return list(data), sw1, sw2
            except Exception as e:
                log.error(f"Error during control() command: {e}")
                log.error(f"Will Retry with transmit()")
                return self.send_apdu(apdu, use_escape=False)
        else:
            # Use the standard transmit() for compliant readers
            data, sw1, sw2 = self.connection.transmit(apdu)
            log.debug(f"  << R-APDU (Transmit): {hexb(data)} [{format_status_word(sw1, sw2)}]")
            return data, sw1, sw2

from typing import Optional, Iterator
import threading



class _AtrObserver(CardObserver):
    def __init__(self, target_reader: Optional[str] = None):
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._atr: Optional[bytes] = None
        self._target_reader = target_reader

    def update(self, observable, cards):
        try:
            added = cards[0] if isinstance(cards, (list, tuple)) and len(cards) >= 1 else cards
            for card in added or []:
                reader_name = getattr(card, "reader", None) or getattr(card, "readerName", None)
                if self._target_reader and reader_name is not None:
                    if self._target_reader not in str(reader_name):
                        continue

                atr_val = getattr(card, "atr", None)
                if atr_val is None:
                    get_atr = getattr(card, "getATR", None)
                    if callable(get_atr):
                        atr_val = get_atr()

                if atr_val is None:
                    continue

                if isinstance(atr_val, (list, tuple)):
                    atr_bytes = bytes(atr_val)
                elif isinstance(atr_val, bytes):
                    atr_bytes = atr_val
                else:
                    try:
                        atr_bytes = bytes(atr_val)
                    except Exception:
                        continue

                with self._lock:
                    self._atr = atr_bytes
                    self._event.set()
                    return
        except Exception:
            return

    def wait_for_next_atr(self, timeout: Optional[float] = None) -> Optional[bytes]:
        got = self._event.wait(timeout)
        if not got:
            return None
        with self._lock:
            atr = self._atr
            self._atr = None
            self._event.clear()
        return atr


def watch_atrs(target_reader: Optional[str] = None) -> Iterator[bytes]:
    monitor = CardMonitor()
    obs = _AtrObserver(target_reader=target_reader)
    monitor.addObserver(obs)
    try:
        while True:
            atr = obs.wait_for_next_atr(timeout=None)
            if atr is None:
                continue
            yield atr
    finally:
        monitor.deleteObserver(obs)


def wait_for_card_atr(target_reader: Optional[str] = None, timeout: Optional[float] = None) -> Optional[bytes]:
    """Block until the next card is presented (or timeout) and return ATR bytes.

    Returns None on timeout.
    """
    monitor = CardMonitor()
    obs = _AtrObserver(target_reader=target_reader)
    monitor.addObserver(obs)
    try:
        return obs.wait_for_next_atr(timeout=timeout)
    finally:
        monitor.deleteObserver(obs)
