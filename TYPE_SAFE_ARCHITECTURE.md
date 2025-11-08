# Type-Safe Authenticated Command Architecture

## Overview

This document describes the type-safe architecture for NTAG424 authenticated commands. The design uses Python type hints and method signatures to enforce correct usage at development time.

## Core Principle

**Commands declare their authentication requirements through method signatures.**

- `ApduCommand.execute(connection: NTag424CardConnection)` - No auth needed
- `AuthApduCommand.execute(auth_conn: AuthenticatedConnection)` - Auth required

Type checkers (mypy, IDE) catch errors before runtime.

## Type Hierarchy

```
Connection Types:
    NTag424CardConnection (raw PC/SC connection)
        └─ AuthenticatedConnection (wraps + adds crypto)

Command Types:
    ApduCommand (base)
        ├─ AuthApduCommand (requires auth)
        ├─ SelectPiccApplication
        ├─ GetChipVersion
        ├─ GetFileSettings
        └─ AuthenticateEV2 (bridge - returns AuthenticatedConnection)
            
    AuthApduCommand (authenticated)
        ├─ ChangeKey
        ├─ ChangeFileSettings
        └─ WriteData
```

## Implementation Guide

### Step 1: Connection Types

#### NTag424CardConnection (Raw Connection)

```python
class NTag424CardConnection:
    """
    Raw card connection from CardManager.
    Provides basic APDU transmission without crypto awareness.
    """
    
    def transmit(self, apdu: List[int]) -> Tuple[List[int], int, int]:
        """
        Send APDU to card.
        
        Args:
            apdu: APDU command bytes
            
        Returns:
            (response_data, sw1, sw2)
        """
        # PC/SC transmission logic
        pass
    
    def control(self, control_code: int, data: bytes) -> bytes:
        """Send control command (for escape mode)."""
        pass
    
    def is_present(self) -> bool:
        """Check if card is still present."""
        pass
```

#### AuthenticatedConnection (Crypto Wrapper)

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession

class AuthenticatedConnection:
    """
    Authenticated connection wrapper.
    
    Wraps NTag424CardConnection and provides automatic encryption/CMAC
    for authenticated commands. This is the ONLY place crypto happens.
    
    Usage:
        with AuthenticateEV2(key, 0).execute(card) as auth_conn:
            ChangeKey(0, new, old).execute(auth_conn)
    """
    
    def __init__(
        self, 
        connection: NTag424CardConnection,
        session: 'Ntag424AuthSession'
    ):
        """
        Create authenticated connection.
        
        Args:
            connection: Underlying raw connection
            session: Authenticated session with keys
        """
        self._connection = connection
        self._session = session
    
    @property
    def connection(self) -> NTag424CardConnection:
        """Access underlying connection for APDU transmission."""
        return self._connection
    
    @property
    def session(self) -> 'Ntag424AuthSession':
        """Access session for key access (if needed)."""
        return self._session
    
    # ====================================================================
    # CRYPTO OPERATIONS (Single source of truth)
    # ====================================================================
    
    def encrypt_and_mac(
        self,
        cmd: int,
        cmd_header: bytes,
        plaintext_data: bytes
    ) -> bytes:
        """
        Encrypt data and apply CMAC for CommMode.FULL.
        
        This is used by ALL authenticated commands that need encryption.
        
        Args:
            cmd: Command byte (e.g., 0xC4 for ChangeKey, 0x5F for ChangeFileSettings)
            cmd_header: Command-specific header (key_no, file_no, etc.)
            plaintext_data: Data to encrypt (must be pre-padded to 16-byte multiple)
        
        Returns:
            encrypted_data + CMAC (8 bytes)
        
        Process:
            1. Get current CmdCtr (before incrementing)
            2. Calculate IV: E(KSesAuthENC, A5 5A || TI || CmdCtr || zeros)
            3. Encrypt: E(KSesAuthENC, IV, plaintext_data)
            4. Build CMAC input: Cmd || CmdCtr || TI || CmdHeader || Encrypted
            5. Calculate CMAC and truncate to 8 bytes (even indices)
            6. Increment CmdCtr
            7. Return encrypted + CMAC
        
        Example:
            # ChangeKey uses this
            key_data = self._build_key_data()  # 32 bytes with padding
            encrypted_with_mac = auth_conn.encrypt_and_mac(
                cmd=0xC4,
                cmd_header=bytes([self.key_no]),
                plaintext_data=key_data
            )
        """
        from Crypto.Cipher import AES
        from Crypto.Hash import CMAC
        
        # Get current counter (before incrementing!)
        cmd_ctr_bytes = self._session.session_keys.cmd_counter.to_bytes(2, 'little')
        ti = self._session.session_keys.ti
        
        # 1. Calculate IV for encryption
        #    IV = E(KSesAuthENC, zero_iv, A5 5A || TI || CmdCtr || 00 00 00 00 00 00 00 00)
        plaintext_iv = b'\xA5\x5A' + ti + cmd_ctr_bytes + b'\x00' * 8
        cipher_iv = AES.new(
            self._session.session_keys.session_enc_key,
            AES.MODE_CBC,
            iv=b'\x00' * 16
        )
        actual_iv = cipher_iv.encrypt(plaintext_iv)
        
        # 2. Encrypt the data
        cipher = AES.new(
            self._session.session_keys.session_enc_key,
            AES.MODE_CBC,
            iv=actual_iv
        )
        encrypted_data = cipher.encrypt(plaintext_data)
        
        # 3. Build CMAC input: Cmd || CmdCtr || TI || CmdHeader || EncryptedData
        cmac_input = (
            bytes([cmd]) +
            cmd_ctr_bytes +
            ti +
            cmd_header +
            encrypted_data
        )
        
        # 4. Calculate CMAC
        cmac_obj = CMAC.new(
            self._session.session_keys.session_mac_key,
            ciphermod=AES
        )
        cmac_obj.update(cmac_input)
        mac_full = cmac_obj.digest()  # 16 bytes
        
        # 5. Truncate CMAC: Take even-numbered bytes (1, 3, 5, 7, 9, 11, 13, 15)
        #    This gives us 8 bytes for the final MAC
        mac = bytes([mac_full[i] for i in range(1, 16, 2)])
        
        # 6. Increment command counter AFTER building the command
        self._session.session_keys.cmd_counter += 1
        
        return encrypted_data + mac
    
    def apply_mac_only(
        self,
        cmd: int,
        cmd_header: bytes,
        plaintext_data: bytes
    ) -> bytes:
        """
        Apply CMAC only (no encryption) for CommMode.MAC.
        
        Args:
            cmd: Command byte
            cmd_header: Command-specific header
            plaintext_data: Data to MAC (unencrypted)
        
        Returns:
            plaintext_data + CMAC (8 bytes)
        
        Process:
            1. Get current CmdCtr
            2. Build CMAC input: Cmd || CmdCtr || TI || CmdHeader || PlaintextData
            3. Calculate CMAC and truncate
            4. Increment CmdCtr
            5. Return plaintext + CMAC
        """
        from Crypto.Hash import CMAC
        from Crypto.Cipher import AES
        
        cmd_ctr_bytes = self._session.session_keys.cmd_counter.to_bytes(2, 'little')
        ti = self._session.session_keys.ti
        
        # Build CMAC input (no encryption step)
        cmac_input = (
            bytes([cmd]) +
            cmd_ctr_bytes +
            ti +
            cmd_header +
            plaintext_data
        )
        
        cmac_obj = CMAC.new(
            self._session.session_keys.session_mac_key,
            ciphermod=AES
        )
        cmac_obj.update(cmac_input)
        mac_full = cmac_obj.digest()
        mac = bytes([mac_full[i] for i in range(1, 16, 2)])
        
        self._session.session_keys.cmd_counter += 1
        
        return plaintext_data + mac
    
    # ====================================================================
    # Context Manager (Auto cleanup)
    # ====================================================================
    
    def __enter__(self) -> 'AuthenticatedConnection':
        """Enter authentication context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit authentication context."""
        # Could zero out session keys here for security
        pass
```

### Step 2: Command Base Classes

#### ApduCommand (Unauthenticated)

```python
from abc import ABC, abstractmethod
from typing import Any

class ApduCommand(ABC):
    """
    Base class for unauthenticated APDU commands.
    
    These commands work with a raw NTag424CardConnection and don't
    require authentication or crypto operations.
    
    Subclasses implement:
    - execute(connection: NTag424CardConnection) -> Response
    """
    
    def __init__(self, use_escape: bool = True):
        """
        Initialize command.
        
        Args:
            use_escape: True for escape mode (control), False for transmit
        """
        self.use_escape = use_escape
    
    @abstractmethod
    def execute(self, connection: NTag424CardConnection) -> Any:
        """
        Execute the command.
        
        Args:
            connection: Raw card connection
            
        Returns:
            Command-specific response
            
        Note:
            Type checker enforces that connection is NTag424CardConnection
        """
        pass
    
    def send_command(
        self,
        connection: NTag424CardConnection,
        apdu: List[int],
        allow_alternative_ok: bool = True
    ) -> Tuple[bytes, int, int]:
        """
        Send APDU and check status.
        
        Args:
            connection: Card connection
            apdu: APDU command bytes
            allow_alternative_ok: Allow 0x91XX as success
            
        Returns:
            (response_data, sw1, sw2)
            
        Raises:
            ApduError: If status word indicates error
        """
        # Implementation handles escape vs transmit
        # Handles multi-frame responses
        # Checks status words
        pass
```

#### AuthApduCommand (Authenticated)

```python
class AuthApduCommand(ApduCommand):
    """
    Base class for authenticated APDU commands.
    
    These commands require an AuthenticatedConnection and use crypto
    operations (encryption/CMAC) automatically.
    
    Commands just build data - connection handles crypto.
    
    Subclasses implement:
    - execute(auth_conn: AuthenticatedConnection) -> Response
    - build_command_data() -> bytes (optional helper)
    """
    
    @abstractmethod
    def execute(self, auth_conn: AuthenticatedConnection) -> Any:
        """
        Execute the command with authenticated connection.
        
        Args:
            auth_conn: Authenticated connection (wraps connection + session)
            
        Returns:
            Command-specific response
            
        Note:
            Type checker enforces that auth_conn is AuthenticatedConnection.
            This is the key to type safety!
        """
        pass
    
    def build_command_data(self) -> bytes:
        """
        Build the plaintext command data.
        
        Optional helper method that subclasses can implement.
        This data will be passed to auth_conn.encrypt_and_mac().
        
        Returns:
            Plaintext command data (pre-padded if needed)
        """
        raise NotImplementedError("Subclass should implement if needed")
```

### Step 3: Implement Commands

#### Example: Unauthenticated Command

```python
class SelectPiccApplication(ApduCommand):
    """Select the PICC application (unauthenticated)."""
    
    def __init__(self):
        super().__init__(use_escape=True)
    
    def __str__(self) -> str:
        return "SelectPiccApplication()"
    
    def execute(self, connection: NTag424CardConnection) -> SuccessResponse:
        """
        Select PICC application.
        
        Args:
            connection: Raw card connection (type-safe!)
            
        Returns:
            SuccessResponse
        """
        apdu = [0x90, 0x5A, 0x00, 0x00, 0x00]
        _, sw1, sw2 = self.send_command(connection, apdu)
        return SuccessResponse("PICC application selected")
```

#### Example: Authenticated Command

```python
class ChangeKey(AuthApduCommand):
    """
    Change a key on the card (authenticated command).
    
    Requires AuthenticatedConnection - type checker enforces this!
    """
    
    def __init__(
        self,
        key_no: int,
        new_key: bytes,
        old_key: bytes,
        key_version: int = 0
    ):
        super().__init__(use_escape=False)  # Use transmit
        self.key_no = key_no
        self.new_key = new_key
        self.old_key = old_key
        self.key_version = key_version
    
    def __str__(self) -> str:
        return f"ChangeKey(key_no=0x{self.key_no:02X})"
    
    def _build_key_data(self) -> bytes:
        """
        Build 32-byte key data for encryption.
        
        Format:
        - Key 0: newKey(16) + version(1) + 0x80 + padding(14) = 32 bytes
        - Others: XOR(16) + version(1) + CRC32(4) + 0x80 + padding(10) = 32 bytes
        
        Returns:
            32-byte padded key data ready for encryption
        """
        import zlib
        
        key_data = bytearray(32)
        
        if self.key_no == 0:
            # Key 0 format
            key_data[0:16] = self.new_key
            key_data[16] = self.key_version
            key_data[17] = 0x80  # Padding marker
            # Rest is zeros
        else:
            # Other keys format
            xored = bytes(a ^ b for a, b in zip(self.new_key, self.old_key))
            key_data[0:16] = xored
            key_data[16] = self.key_version
            
            # CRC32 of new key (inverted)
            crc = zlib.crc32(self.new_key) & 0xFFFFFFFF
            crc_inverted = crc ^ 0xFFFFFFFF
            key_data[17:21] = crc_inverted.to_bytes(4, 'little')
            
            key_data[21] = 0x80  # Padding marker
            # Rest is zeros
        
        return bytes(key_data)
    
    def execute(self, auth_conn: AuthenticatedConnection) -> SuccessResponse:
        """
        Execute ChangeKey command.
        
        Args:
            auth_conn: Authenticated connection (type-safe!)
            
        Returns:
            SuccessResponse
        
        Process:
            1. Build plaintext key data (our job)
            2. Delegate encryption+CMAC to connection (connection's job)
            3. Build APDU with encrypted data
            4. Send via underlying connection
        """
        # Step 1: Build plaintext key data (command's responsibility)
        key_data = self._build_key_data()  # 32 bytes with padding
        
        # Step 2: Let connection handle crypto (connection's responsibility)
        encrypted_with_mac = auth_conn.encrypt_and_mac(
            cmd=0xC4,
            cmd_header=bytes([self.key_no]),
            plaintext_data=key_data
        )
        
        # Step 3: Build APDU
        apdu = [
            0x90, 0xC4, 0x00, 0x00,
            len(encrypted_with_mac) + 1,  # LC (+1 for key_no)
            self.key_no,
            *encrypted_with_mac,  # Encrypted data + CMAC
            0x00  # LE
        ]
        
        # Step 4: Send via underlying connection
        _, sw1, sw2 = self.send_command(
            auth_conn.connection,  # Access wrapped connection
            apdu,
            allow_alternative_ok=False
        )
        
        return SuccessResponse(f"Key {self.key_no:02X} changed")
```

#### Example: Bridge Command (AuthenticateEV2)

```python
class AuthenticateEV2(ApduCommand):
    """
    Authenticate with EV2 protocol.
    
    Bridge command: Takes NTag424CardConnection, returns AuthenticatedConnection
    """
    
    def __init__(self, key: bytes, key_no: int = 0):
        super().__init__(use_escape=True)
        self.key = key
        self.key_no = key_no
    
    def __str__(self) -> str:
        return f"AuthenticateEV2(key_no=0x{self.key_no:02X})"
    
    def execute(self, connection: NTag424CardConnection) -> AuthenticatedConnection:
        """
        Perform EV2 authentication.
        
        Args:
            connection: Raw card connection
            
        Returns:
            AuthenticatedConnection (context manager)
            
        Process:
            1. Create session
            2. Authenticate (Phase 1 + Phase 2)
            3. Wrap connection with session
            4. Return as context manager
        """
        from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
        
        # Create session and authenticate
        session = Ntag424AuthSession(self.key)
        session.authenticate(connection, self.key_no)
        
        # Wrap connection with session
        return AuthenticatedConnection(connection, session)
```

### Step 4: Usage Pattern

#### Type-Safe Usage

```python
def provision_tag():
    """Demonstrate type-safe usage."""
    
    # Get raw connection
    with CardManager() as card:  # card is NTag424CardConnection
        
        # ============================================================
        # UNAUTHENTICATED COMMANDS
        # Type checker ensures we pass NTag424CardConnection
        # ============================================================
        
        SelectPiccApplication().execute(card)  # ✅ Type-safe
        version = GetChipVersion().execute(card)  # ✅ Type-safe
        
        # ============================================================
        # AUTHENTICATED COMMANDS
        # Type checker ensures we pass AuthenticatedConnection
        # ============================================================
        
        # Get authenticated connection (context manager)
        with AuthenticateEV2(FACTORY_KEY, 0).execute(card) as auth_conn:
            # auth_conn is AuthenticatedConnection
            
            ChangeKey(0, NEW_KEY, FACTORY_KEY).execute(auth_conn)  # ✅ Type-safe
            ChangeFileSettings(config).execute(auth_conn)  # ✅ Type-safe
        
        # Auth session closed, keys wiped
```

#### Type Errors Caught

```python
# ❌ ERROR: Type checker catches this
with CardManager() as card:
    ChangeKey(0, new, old).execute(card)
    # ERROR: Argument 1 has incompatible type "NTag424CardConnection"
    #        expected "AuthenticatedConnection"

# ❌ ERROR: Type checker catches this
with CardManager() as card:
    with AuthenticateEV2(key, 0).execute(card) as auth_conn:
        GetChipVersion().execute(auth_conn)
        # ERROR: Argument 1 has incompatible type "AuthenticatedConnection"
        #        expected "NTag424CardConnection"
```

## Benefits

### 1. Type Safety
- IDE autocomplete shows correct connection type
- mypy catches errors at development time
- No runtime errors from wrong connection type

### 2. Single Source of Truth
- All crypto in `AuthenticatedConnection.encrypt_and_mac()`
- No duplicate implementations
- Easy to update/fix crypto logic

### 3. Clean Separation
- Commands build data (their job)
- Connections handle crypto (their job)
- No mixed responsibilities

### 4. Explicit Scope
- `with` blocks make auth lifetime clear
- Auto-cleanup when exiting
- No leaked session keys

### 5. Easy Testing
- Mock `AuthenticatedConnection` for command tests
- Mock `NTag424CardConnection` for integration tests
- Test crypto separately from commands

## Testing Guide

### Unit Test: Command (Mock AuthenticatedConnection)

```python
def test_change_key_builds_correct_data():
    """Test ChangeKey builds correct key data."""
    
    # Create command
    cmd = ChangeKey(
        key_no=0,
        new_key=b'\x01' * 16,
        old_key=b'\x00' * 16,
        key_version=1
    )
    
    # Build key data
    key_data = cmd._build_key_data()
    
    # Verify structure
    assert len(key_data) == 32
    assert key_data[16] == 1  # Version
    assert key_data[17] == 0x80  # Padding marker
```

### Integration Test: Real Hardware

```python
def test_provision_real_tag():
    """Test provisioning with real hardware."""
    
    with CardManager() as card:
        SelectPiccApplication().execute(card)
        
        with AuthenticateEV2(FACTORY_KEY, 0).execute(card) as auth_conn:
            # Change key
            result = ChangeKey(
                key_no=0,
                new_key=NEW_KEY,
                old_key=FACTORY_KEY,
                key_version=1
            ).execute(auth_conn)
            
            assert result.success
```

## Migration Path

### From Current Code

**Current (mixed responsibilities)**:
```python
# Change key with session parameter
def execute(self, connection, session=None):
    dna_calc = DNA_Calc(session.keys.enc, session.keys.mac, session.keys.ti)
    apdu = dna_calc.full_change_key(...)
    # Crypto mixed with command logic
```

**New (clean separation)**:
```python
def execute(self, auth_conn: AuthenticatedConnection):
    key_data = self._build_key_data()  # Command builds data
    encrypted = auth_conn.encrypt_and_mac(...)  # Connection handles crypto
    apdu = self._build_apdu(encrypted)  # Command builds APDU
    # Clean separation
```

### Refactoring Steps

1. **Create `AuthenticatedConnection` class** with `encrypt_and_mac()`
2. **Update `AuthenticateEV2`** to return `AuthenticatedConnection`
3. **Create `AuthApduCommand`** base class
4. **Refactor `ChangeKey`** to use new pattern
5. **Refactor `ChangeFileSettings`** to use new pattern
6. **Delete `DNA_Calc`** class
7. **Update all tests**
8. **Verify with real hardware**

## Implementation Checklist

- [ ] Create `AuthenticatedConnection` class
- [ ] Implement `encrypt_and_mac()` method
- [ ] Implement `apply_mac_only()` method
- [ ] Create `AuthApduCommand` base class
- [ ] Update `AuthenticateEV2` to return `AuthenticatedConnection`
- [ ] Refactor `ChangeKey` to use new pattern
- [ ] Refactor `ChangeFileSettings` to use new pattern
- [ ] Delete `DNA_Calc` class
- [ ] Update unit tests
- [ ] Update integration tests
- [ ] Verify with real hardware
- [ ] Update documentation

## References

- `ARCH.md` - Complete architecture overview with diagrams
- `Plan.md` - Implementation plan and status
- `LESSONS.md` - Design decisions and refactoring history
- NXP AN12196 - NTAG 424 DNA and NTAG 424 DNA TagTamper features and hints
- NXP AN12343 - NTAG 424 DNA, NTAG 424 DNA TT, NTAG 424 TT Advanced features

