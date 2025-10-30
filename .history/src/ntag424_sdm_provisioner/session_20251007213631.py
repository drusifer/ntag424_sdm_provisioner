"""
Manages an authenticated session with an NTAG424 DNA tag.
"""
from typing import Optional
from smartcard.CardConnection import CardConnection
from Crypto.Cipher import AES
from Crypto.Hash import CMAC

from .commands.authenticate_ev2_first import AuthenticateEV2First
from .commands.authenticate_ev2_part2 import AuthenticateEV2Part2
from .hal import CardManager


class Ntag424Session:
    """
    Handles the authentication process and session key derivation for an
    NTAG424 DNA tag.

    The special  values below are  **session key diversification constants** defined by the NXP NTAG424 DNA protocol. 
    They are not keys themselves.

    Here's the breakdown:
    **Purpose:** Their sole purpose is to ensure that the two session keys we derive—one for MACing (`SesAuthMACKey`) 
    and one for encryption (`SesEncKey`)—are cryptographically unique and independent. 
    This is a critical security practice known as **domain separation**. You never want to use the same 
    key for two different cryptographic functions.

    **How They Work:**
    * The session key derivation process uses the original authentication key as a root of trust 
      and combines it with the random numbers from the authentication handshake (`RndA` and `RndB`).
    * To create the **MAC key**, the protocol specifies that we must run a 
      CMAC function over the concatenation of `_SV1_SES_AUTH_MAC_KEY` and parts of `RndA` and `RndB`.
    * To create the **Encryption key**, we do the same, but with the different 
      constant `_SV2_SES_ENC_KEY` and *different* parts of `RndA` and `RndB`.

    In short, they are fixed "magic numbers" mandated by the NXP standard. By using these different, 
    hardcoded constants as input to the key derivation function, the protocol guarantees we get two different, 
    unrelated keys for our session, even though both originate from the same master key.
    """

    _SV1_SES_AUTH_MAC_KEY = b'\x3c\xc3\x00\x01\x00\x80'
    _SV2_SES_ENC_KEY = b'\xc3\x3c\x00\x01\x00\x80'

    def __init__(self, connection: CardConnection, key_no: int, key: bytes):
        """
        Args:
            connection: An active CardConnection.
            key_no: The number of the key to authenticate with (0-4).
            key: The 16-byte AES-128 key.
        """
        if len(key) != 16:
            raise ValueError("Key must be 16 bytes")

        self.connection = connection
        self._key_no = key_no
        self._key = key
        # cipher is created when needed for authenticate part 2
        self._cipher: Optional[AES] = None
        self.ses_auth_mac_key: Optional[bytes] = None
        self.ses_enc_key: Optional[bytes] = None
        self._rndA: Optional[bytes] = None
        self._rndB: Optional[bytes] = None

    def _derive_session_keys(self) -> None:
        """
        Derives the session MAC and encryption keys after a successful
        authentication, as per NXP AN12196.
        """
        if not self._rndA or not self._rndB:
            raise RuntimeError(
                "Cannot derive session keys before authentication")

        # Diversification input for SesAuthMACKey
        mac_div_input = self._SV1_SES_AUTH_MAC_KEY + self._rndA[:8] + self._rndB[:8]
        # Diversification input for SesEncKey
        enc_div_input = self._SV2_SES_ENC_KEY + self._rndA[8:] + self._rndB[8:]

        cmac = CMAC.new(self._key, ciphermod=AES)
        self.ses_auth_mac_key = cmac.update(mac_div_input).digest()

        cmac = CMAC.new(self._key, ciphermod=AES)
        self.ses_enc_key = cmac.update(enc_div_input).digest()

        print("INFO: Session keys derived successfully.")

    def authenticate(self) -> None:
        """
        Performs the full EV2 authentication handshake and derives session keys.

        Raises:
            ApduError: If any stage of the authentication fails.
        """
        # Part 1: Backend authenticates to PICC
        # AuthenticateEV2First expects the raw key bytes and will create its own cipher
        auth1 = AuthenticateEV2First(self._key_no, self._key)
        self._rndB = auth1.execute(self.connection)
        print("INFO: Authentication Part 1 successful.")

        # Part 2: PICC authenticates to Backend
        # Create cipher for Part 2 using the same key
        self._cipher = AES.new(self._key, AES.MODE_CBC, iv=b"\x00" * 16)
        auth2 = AuthenticateEV2Part2(self._cipher, self._rndB)
        auth2.execute(self.connection)
        self._rndA = auth2.rndA
        print("INFO: Authentication Part 2 successful.")

        # Derive session keys for future commands
        self._derive_session_keys()
