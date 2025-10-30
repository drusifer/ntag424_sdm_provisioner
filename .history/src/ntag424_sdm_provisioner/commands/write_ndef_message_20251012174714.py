"""
Implements the NTAG424 WriteData command, specifically for NDEF messages.
"""
from smartcard.CardConnection import CardConnection

from .base import ApduCommand, ApduError, SW_OK
from ..session import Ntag424Session

# -- NTAG424 Constants for WriteData Command --
CLA_PROPRIETARY = 0x90
INS_WRITE_DATA = 0x8D
NDEF_FILE_NO = 0x02

# -- NDEF Constants --
# "URI" Record Type Indicator
URI_IDENTIFIER_CODE = 0x55
# "http://www." prefix
URI_PREFIX_HTTP_WWW = 0x01
# "https://www." prefix
URI_PREFIX_HTTPS_WWW = 0x02
# "http://" prefix
URI_PREFIX_HTTP = 0x03
# "https://" prefix
URI_PREFIX_HTTPS = 0x04


def _construct_ndef_uri_payload(uri: str) -> bytes:
    """
    Constructs a minimal NDEF message payload for a URI.
    This function handles basic prefix substitution.
    """
    if uri.startswith("https://www."):
        prefix_code = URI_PREFIX_HTTPS_WWW
        uri_body = uri[12:].encode('utf-8')
    elif uri.startswith("http://www."):
        prefix_code = URI_PREFIX_HTTP_WWW
        uri_body = uri[11:].encode('utf-8')
    elif uri.startswith("https://"):
        prefix_code = URI_PREFIX_HTTPS
        uri_body = uri[8:].encode('utf-8')
    elif uri.startswith("http://"):
        prefix_code = URI_PREFIX_HTTP
        uri_body = uri[7:].encode('utf-8')
    else:
        raise ValueError("URI must start with a recognized http(s) prefix")

    # NDEF Record Header
    # MB=1, ME=1, CF=0, SR=1, IL=0, TNF=0x01 (Well-Known Type)
    header = 0b11010001
    type_length = 1  # Length of the record type ('U')
    payload_length = 1 + len(uri_body)  # Length of prefix + URI body

    record = bytearray([
        header,
        type_length,
        payload_length,
        ord('U'),  # Record Type ('U' for URI)
        prefix_code,
        *uri_body
    ])

    # Prepend NDEF message header (2-byte length)
    message_length = len(record)
    return message_length.to_bytes(2, 'big') + record


class WriteNdefMessage(ApduCommand):
    """
    A command to write a URI as an NDEF message to the tag.
    This may require an authenticated session depending on file settings.
    """
    def __init__(self, session: Ntag424Session | None, uri: str):
        __super().__init__(use_escape=True)
        self.session = session
        self.ndef_payload = _construct_ndef_uri_payload(uri)

    def execute(self, connection: CardConnection) -> None:
        """Executes the WriteData command in chunks."""
        # The NDEF message must first be written with its length.
        # We need to write the 2-byte length first, then the data.
        # The NTAG expects a 0 length to be written first to erase the file.
        
        # Write 0 length to erase
        self._write_chunk(connection, b'\x00\x00', 0)
        
        # Write actual NDEF data
        self._write_chunk(connection, self.ndef_payload, 0)

        print(f"INFO: Successfully wrote {len(self.ndef_payload)} bytes of NDEF data.")

    def _write_chunk(self, connection: CardConnection, data: bytes, offset: int) -> None:
        """Sends a single chunk of data to the card."""
        # The WriteData command for NDEF files uses a different structure.
        # The data is sent directly.
        chunk_size = 55
        
        current_offset = offset
        while current_offset < offset + len(data):
            chunk = data[current_offset - offset:current_offset - offset + chunk_size]
            
            p1 = NDEF_FILE_NO
            # The offset and length are part of the data payload
            payload = current_offset.to_bytes(3, 'little') + len(chunk).to_bytes(3, 'little') + chunk

            response, sw1, sw2 = self._send_apdu(
                connection,
                cla=CLA_PROPRIETARY,
                ins=INS_WRITE_DATA,
                p1=p1,
                p2=0x00,
                data=payload
            )

            if (sw1, sw2) != SW_OK:
                raise ApduError(f"WriteData failed at offset {current_offset}", sw1, sw2)
            
            current_offset += len(chunk)
