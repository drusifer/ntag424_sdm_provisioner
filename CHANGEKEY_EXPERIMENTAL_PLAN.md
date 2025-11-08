# ChangeKey Root Cause Analysis - Experimental Plan

## Goal
Isolate and fix the crypto operations causing ChangeKey to fail with 0x911E (INTEGRITY_ERROR).

## Current Status
- **Format correct**: 32-byte key data with proper padding
- **Structure correct**: Matches Arduino MFRC522 library
- **Problem**: CMAC verification fails (0x911E INTEGRITY_ERROR)
- **Hypothesis**: Subtle crypto implementation bug in encryption, IV, or CMAC

## Root Cause Strategy

### Phase 1: Extract & Isolate Crypto Components
**Goal**: Create standalone, testable crypto functions with known test vectors

#### Experiment 1.1: Create Standalone Crypto Module
```python
# File: tests/crypto_components.py
# Extract these into pure functions (no class dependencies):

def calculate_iv_for_command(ti: bytes, cmd_ctr: int, session_enc_key: bytes) -> bytes:
    """Calculate IV for command encryption"""
    pass

def encrypt_key_data(key_data: bytes, iv: bytes, session_enc_key: bytes) -> bytes:
    """Encrypt 32-byte key data using AES-CBC"""
    pass

def calculate_cmac(cmd: int, cmd_ctr: int, ti: bytes, cmd_header: bytes, 
                   encrypted_data: bytes, session_mac_key: bytes) -> bytes:
    """Calculate 8-byte truncated CMAC"""
    pass

def build_key_data(key_no: int, new_key: bytes, old_key: bytes, version: int) -> bytes:
    """Build 32-byte key data with padding and CRC32"""
    pass
```

**Test Data**: Use AN12196 Table 26 and AN12343 Table 40 as reference

#### Experiment 1.2: Unit Tests with NXP Test Vectors
```python
# File: tests/test_crypto_components.py

def test_iv_calculation_an12196():
    """Test IV calculation against AN12196 Table 26"""
    ti = bytes.fromhex("7614281A")
    cmd_ctr = 3
    session_enc_key = bytes.fromhex("4CF3CB41A22583A61E89B158D252FC53")
    
    # Expected from AN12196 Step 12
    expected_iv_plaintext = bytes.fromhex("A55A7614281A03000000000000000000")
    expected_iv_encrypted = bytes.fromhex("01602D579423B2797BE8B478B0B4D27B")
    
    # Test both plaintext construction and encryption
    ...

def test_encryption_an12196():
    """Test key data encryption against AN12196 Table 26"""
    plaintext = bytes.fromhex("5004BF991F408672B1EF00F08F9E864701800000000000000000000000000000")
    iv = bytes.fromhex("01602D579423B2797BE8B478B0B4D27B")
    session_enc_key = bytes.fromhex("4CF3CB41A22583A61E89B158D252FC53")
    
    expected_encrypted = bytes.fromhex("C0EB4DEEFEDDF0B513A03A95A75491818580503190D4D05053FF75668A01D6FD")
    
    encrypted = encrypt_key_data(plaintext, iv, session_enc_key)
    assert encrypted == expected_encrypted

def test_cmac_truncation_an12196():
    """Test CMAC calculation and truncation against AN12196 Table 26"""
    mac_input = bytes.fromhex("C40300761428""1A00C0EB4DEEFEDDF0B513A03A95A75491818580503190D4D05053FF75668A01D6FD")
    session_mac_key = bytes.fromhex("5529860B2FC5FB6154B7F28361D30BF9")
    
    expected_cmac_full = bytes.fromhex("B7A60161F202EC3489BD4BEDEF64BB32")
    expected_cmac_truncated = bytes.fromhex("A6610234BDED6432")
    
    # Test full CMAC first
    cmac_full = calculate_cmac_full(mac_input, session_mac_key)
    assert cmac_full == expected_cmac_full
    
    # Test truncation (ODD indices: 1,3,5,7,9,11,13,15)
    cmac_truncated = truncate_cmac(cmac_full)
    assert cmac_truncated == expected_cmac_truncated

def test_cmac_truncation_an12343():
    """Test against AN12343 Table 40 (different test vector)"""
    # Use AN12343 values for second verification
    ...

def test_crc32_calculation():
    """Test CRC32 calculation against Arduino"""
    new_key = bytes(16)  # All zeros
    # Arduino: crc = CRC32::calculate(message16, 16) & 0xFFFFFFFF ^ 0xFFFFFFFF
    # Python:  crc = zlib.crc32(new_key) ^ 0xFFFFFFFF
    ...
```

**Success Criteria**: All unit tests pass with NXP reference values

---

### Phase 2: Validate Against Arduino Implementation
**Goal**: Ensure our crypto primitives match Arduino byte-for-byte

#### Experiment 2.1: Arduino Wire Capture
```cpp
// Modify Full_ChangeKey.ino to print intermediate values:

void loop() {
    // ... auth ...
    
    // CAPTURE INTERMEDIATE VALUES
    Serial.print("Ti: "); printHex(ntag.TI, 4);
    Serial.print("CmdCtr: "); printHex(ntag.CmdCtr, 2);
    Serial.print("SesAuthEncKey: "); printHex(ntag.SesAuthEncKey, 16);
    Serial.print("SesAuthMacKey: "); printHex(ntag.SesAuthMacKey, 16);
    
    byte keyData[32] = {};
    memcpy(keyData, newKey, 16);
    keyData[16] = newKeyVersion;
    keyData[17] = 0x80;
    Serial.print("KeyData (plaintext): "); printHex(keyData, 32);
    
    // Calculate IV
    byte IVCmd[16];
    ntag.DNA_CalculateIVCmd(IVCmd);
    Serial.print("IV: "); printHex(IVCmd, 16);
    
    // Encrypt
    byte dataEnc[32];
    cbc.setKey(SesAuthEncKey, 16);
    cbc.setIV(IVCmd, 16);
    cbc.encrypt(dataEnc, keyData, 32);
    Serial.print("Encrypted: "); printHex(dataEnc, 32);
    
    // CMAC input
    byte CMACinput[40];
    CMACinput[0] = 0xC4;
    CMACinput[1] = CmdCtr[0];
    CMACinput[2] = CmdCtr[1];
    memcpy(&CMACinput[3], TI, 4);
    CMACinput[7] = keyNumber;
    memcpy(&CMACinput[8], dataEnc, 32);
    Serial.print("CMAC Input: "); printHex(CMACinput, 40);
    
    // CMAC
    byte CMAC[16];
    cmac.generateMAC(CMAC, SesAuthMacKey, CMACinput, 40);
    Serial.print("CMAC Full: "); printHex(CMAC, 16);
    
    byte CMACt[8];
    for (byte i = 0; i < 8; i++)
        CMACt[i] = CMAC[i * 2 + 1];
    Serial.print("CMAC Truncated: "); printHex(CMACt, 8);
    
    // EXECUTE
    dna_statusCode = ntag.DNA_Full_ChangeKey(keyNumberToChange, oldKey, newKey, newKeyVersion);
}
```

#### Experiment 2.2: Python Reference Capture
```python
# File: tests/test_changekey_wire_compare.py

def test_changekey_crypto_vs_arduino():
    """Compare our crypto output with Arduino captured values"""
    
    # Use SAME session keys as Arduino (from auth)
    ti = bytes.fromhex("...")  # From Arduino Serial
    cmd_ctr = 0
    session_enc_key = bytes.fromhex("...")  # From Arduino Serial
    session_mac_key = bytes.fromhex("...")  # From Arduino Serial
    
    # Build key data
    key_data = build_key_data(0, new_key, None, 0x01)
    assert key_data.hex() == "..."  # Match Arduino KeyData
    
    # Calculate IV
    iv = calculate_iv_for_command(ti, cmd_ctr, session_enc_key)
    assert iv.hex() == "..."  # Match Arduino IV
    
    # Encrypt
    encrypted = encrypt_key_data(key_data, iv, session_enc_key)
    assert encrypted.hex() == "..."  # Match Arduino Encrypted
    
    # CMAC
    cmac = calculate_cmac(0xC4, cmd_ctr, ti, bytes([0]), encrypted, session_mac_key)
    assert cmac.hex() == "..."  # Match Arduino CMACt
    
    print("ALL CRYPTO MATCHES ARDUINO! ✓")
```

**Success Criteria**: Every intermediate value matches Arduino output

---

### Phase 3: Test with Raw pyscard API
**Goal**: Bypass our auth session to rule out session management bugs

#### Experiment 3.1: Direct pyscard ChangeKey
```python
# File: tests/test_changekey_pyscard_direct.py

from smartcard.System import readers

def test_changekey_with_pyscard_direct():
    """
    Execute ChangeKey using raw pyscard, bypassing our auth session.
    This isolates whether the bug is in crypto primitives or session management.
    """
    
    # 1. Get reader
    r = readers()[0]
    connection = r.createConnection()
    connection.connect()
    
    # 2. Manual authentication (capture session keys)
    apdu_select = [0x90, 0x5A, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00]
    response, sw1, sw2 = connection.transmit(apdu_select)
    assert (sw1, sw2) == (0x90, 0x00)
    
    # 3. Auth Phase 1
    rnda = os.urandom(16)
    apdu_auth1 = [0x90, 0x71, 0x00, 0x00, 0x11, 0x00, *list(rnda), 0x00]
    response, sw1, sw2 = connection.transmit(apdu_auth1)
    assert (sw1, sw2) == (0x91, 0xAF)
    
    # 4. Decrypt response, get RndB, Ti
    rndb_enc = bytes(response[:16])
    # ... decrypt ...
    ti = ...
    
    # 5. Derive session keys (use our existing function)
    session_enc_key = ...
    session_mac_key = ...
    
    # 6. Auth Phase 2
    # ... complete auth ...
    
    # 7. Now try ChangeKey with our crypto primitives
    key_data = build_key_data(0, new_key, None, 0x01)
    iv = calculate_iv_for_command(ti, 0, session_enc_key)
    encrypted = encrypt_key_data(key_data, iv, session_enc_key)
    cmac = calculate_cmac(0xC4, 0, ti, bytes([0]), encrypted, session_mac_key)
    
    # 8. Build and send APDU
    apdu_changekey = [0x90, 0xC4, 0x00, 0x00, 0x29, 0x00, *list(encrypted), *list(cmac), 0x00]
    response, sw1, sw2 = connection.transmit(apdu_changekey)
    
    print(f"Response: {sw1:02X} {sw2:02X}")
    assert (sw1, sw2) == (0x91, 0x00), f"ChangeKey failed: {sw1:02X}{sw2:02X}"
```

**Success Criteria**: ChangeKey succeeds with raw pyscard, isolating the problem

---

### Phase 4: Binary Search for Discrepancy
**Goal**: If tests still fail, systematically compare each byte

#### Experiment 4.1: Hex Diff Tool
```python
# File: tests/test_hex_diff.py

def hex_diff(label: str, python_bytes: bytes, arduino_hex: str):
    """Visually compare byte arrays"""
    arduino_bytes = bytes.fromhex(arduino_hex)
    
    print(f"\n{label}:")
    print(f"Python:  {python_bytes.hex()}")
    print(f"Arduino: {arduino_bytes.hex()}")
    
    if python_bytes == arduino_bytes:
        print("  ✓ MATCH")
    else:
        print("  ✗ MISMATCH")
        for i, (p, a) in enumerate(zip(python_bytes, arduino_bytes)):
            if p != a:
                print(f"    Byte {i}: Python={p:02X} Arduino={a:02X}")

def test_changekey_full_comparison():
    """Run ChangeKey and compare every intermediate value"""
    
    # Get Arduino values from serial capture
    arduino_values = {
        'ti': "...",
        'cmd_ctr': "0000",
        'session_enc_key': "...",
        'session_mac_key': "...",
        'key_data_plaintext': "...",
        'iv': "...",
        'encrypted': "...",
        'cmac_input': "...",
        'cmac_full': "...",
        'cmac_truncated': "...",
    }
    
    # Calculate Python values
    python_values = {
        'ti': ti.hex(),
        'key_data_plaintext': key_data.hex(),
        'iv': iv.hex(),
        'encrypted': encrypted.hex(),
        'cmac_input': cmac_input.hex(),
        'cmac_full': cmac_full.hex(),
        'cmac_truncated': cmac_truncated.hex(),
    }
    
    # Compare each step
    for key in arduino_values:
        hex_diff(key, bytes.fromhex(python_values[key]), arduino_values[key])
```

**Success Criteria**: Identify EXACT byte where discrepancy occurs

---

### Phase 5: Known Bug Checklist
**Goal**: Verify fixes for all known issues

#### Experiment 5.1: CMAC Truncation Verification
```python
def test_cmac_truncation_correct():
    """Verify we're using ODD indices (even-numbered bytes)"""
    cmac_full = bytes(range(16))  # [0, 1, 2, 3, ..., 15]
    
    # WRONG (old implementation)
    wrong = cmac_full[:8]  # [0, 1, 2, 3, 4, 5, 6, 7]
    
    # CORRECT (per AN12196)
    correct = bytes([cmac_full[i] for i in range(1, 16, 2)])  # [1, 3, 5, 7, 9, 11, 13, 15]
    
    # Our implementation
    truncated = truncate_cmac(cmac_full)
    assert truncated == correct, "CMAC truncation is WRONG!"
```

#### Experiment 5.2: CRC32 Verification
```python
def test_crc32_matches_arduino():
    """Verify CRC32 calculation matches Arduino"""
    import zlib
    
    new_key = bytes([1] + [0]*15)  # 1 followed by 15 zeros
    
    # Arduino: crc = CRC32::calculate(message16, 16) & 0xFFFFFFFF ^ 0xFFFFFFFF
    # Python equivalent
    crc = zlib.crc32(new_key) ^ 0xFFFFFFFF
    crc_bytes = crc.to_bytes(4, byteorder='little')
    
    # Verify against Arduino captured value
    assert crc_bytes.hex() == "..."  # From Arduino serial
```

#### Experiment 5.3: Counter Verification
```python
def test_counter_usage():
    """Verify we're using correct counter value"""
    
    # After auth, counter should be 0
    # For first authenticated command, use counter = 0 (not 1)
    # Arduino: uses current counter, increments AFTER command succeeds
    
    assert cmd_ctr == 0, "Counter should be 0 for first command after auth"
```

#### Experiment 5.4: IV Calculation Verification
```python
def test_iv_calculation_detailed():
    """Verify IV calculation matches spec exactly"""
    
    ti = bytes.fromhex("7614281A")
    cmd_ctr = 3
    session_enc_key = bytes.fromhex("4CF3CB41A22583A61E89B158D252FC53")
    
    # Step 1: Build plaintext IV
    plaintext_iv = bytearray(16)
    plaintext_iv[0] = 0xA5
    plaintext_iv[1] = 0x5A
    plaintext_iv[2:6] = ti
    plaintext_iv[6:8] = cmd_ctr.to_bytes(2, 'little')
    # Rest is zeros
    
    assert plaintext_iv.hex() == "a55a7614281a03000000000000000000"
    
    # Step 2: Encrypt plaintext IV with zero IV
    from Crypto.Cipher import AES
    cipher = AES.new(session_enc_key, AES.MODE_CBC, iv=b'\x00'*16)
    iv_encrypted = cipher.encrypt(bytes(plaintext_iv))
    
    assert iv_encrypted.hex() == "01602d579423b2797be8b478b0b4d27b"
```

---

### Phase 6: APDU Sequence Testing
**Goal**: If crypto checks out, verify the exact APDU sequence and session state

#### Experiment 6.1: Minimal Arduino Sequence Replication
```python
# File: tests/test_apdu_sequence_minimal.py

def test_minimal_changekey_sequence():
    """
    Replicate EXACT Arduino sequence with pyscard.
    Compare wire-level APDUs byte-for-byte.
    """
    from smartcard.System import readers
    
    r = readers()[0]
    connection = r.createConnection()
    connection.connect()
    
    print("\n=== MINIMAL CHANGEKEY SEQUENCE ===\n")
    
    # Arduino sequence from Full_ChangeKey.ino:
    # 1. SelectPiccApplication
    # 2. AuthenticateEV2First
    # 3. ChangeKey
    
    # Step 1: Select PICC Application
    apdu = [0x90, 0x5A, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00]
    print(f">>> SELECT: {' '.join(f'{b:02X}' for b in apdu)}")
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"<<< Response: SW={sw1:02X}{sw2:02X}")
    assert (sw1, sw2) == (0x90, 0x00)
    
    # Step 2: AuthenticateEV2First (using factory key 0x00*16)
    key = bytes(16)  # Factory default
    rnda = os.urandom(16)
    
    # Phase 1
    apdu = [0x90, 0x71, 0x00, 0x00, 0x11, 0x00, *list(rnda), 0x00]
    print(f"\n>>> AUTH PHASE 1: {' '.join(f'{b:02X}' for b in apdu)}")
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"<<< Response: {len(response)} bytes, SW={sw1:02X}{sw2:02X}")
    assert (sw1, sw2) == (0x91, 0xAF)
    
    # Decrypt and parse (use our existing crypto)
    # ... perform auth phase 2 ...
    # ... derive session keys ...
    
    # Step 3: ChangeKey IMMEDIATELY after auth
    # NO OTHER COMMANDS IN BETWEEN!
    
    # Build ChangeKey APDU using our crypto primitives
    key_data = build_key_data(0, new_key, None, 0x01)
    iv = calculate_iv_for_command(ti, 0, session_enc_key)  # Counter = 0!
    encrypted = encrypt_key_data(key_data, iv, session_enc_key)
    cmac = calculate_cmac(0xC4, 0, ti, bytes([0]), encrypted, session_mac_key)
    
    apdu = [0x90, 0xC4, 0x00, 0x00, 0x29, 0x00, *list(encrypted), *list(cmac), 0x00]
    print(f"\n>>> CHANGEKEY: {' '.join(f'{b:02X}' for b in apdu)}")
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"<<< Response: SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) == (0x91, 0x00):
        print("\n✓✓✓ CHANGEKEY SUCCEEDED! ✓✓✓")
    else:
        print(f"\n✗✗✗ CHANGEKEY FAILED: {sw1:02X}{sw2:02X} ✗✗✗")

def test_our_implementation_sequence():
    """
    Test our production code's APDU sequence.
    Print every APDU to compare with Arduino.
    """
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Patch connection to log APDUs
    original_transmit = connection.send_apdu
    
    def logged_transmit(apdu):
        print(f">>> OUR CODE: {' '.join(f'{b:02X}' for b in apdu)}")
        result = original_transmit(apdu)
        print(f"<<< Response: {result[1]:02X}{result[2]:02X}")
        return result
    
    connection.send_apdu = logged_transmit
    
    # Now run our production code
    with CardManager() as card:
        SelectPiccApplication().execute(card)
        
        with AuthenticateEV2(factory_key, 0).execute(card) as auth_conn:
            # Try ChangeKey
            ChangeKey(0, new_key, None, 0x01).execute(auth_conn)
```

#### Experiment 6.2: Command Counter State Testing
```python
# File: tests/test_counter_state.py

def test_counter_after_auth():
    """Verify counter is 0 immediately after auth"""
    
    with CardManager() as card:
        SelectPiccApplication().execute(card)
        
        auth = AuthenticateEV2(factory_key, 0)
        auth_response = auth._perform_authentication(card)
        
        # Check counter state
        assert auth_response.cmd_counter == 0, f"Counter should be 0, got {auth_response.cmd_counter}"
        
        # Now build ChangeKey with counter = 0
        ...

def test_counter_increment_timing():
    """Test when counter gets incremented"""
    
    # Arduino behavior from line 1078:
    # 1. Send command
    # 2. Get response
    # 3. Check SW == 0x9100
    # 4. THEN increment counter: DNA_IncrementCmdCtr()
    
    # Our implementation should:
    # - Use counter = 0 for first command
    # - Increment ONLY after successful response
    # - Use counter = 1 for second command
    ...

def test_multiple_authenticated_commands():
    """Test counter across multiple commands"""
    
    with CardManager() as card:
        SelectPiccApplication().execute(card)
        
        with AuthenticateEV2(factory_key, 0).execute(card) as auth_conn:
            # Command 1: counter = 0
            version = GetKeyVersion(0).execute(auth_conn)
            assert auth_conn.session.cmd_counter == 1
            
            # Command 2: counter = 1
            settings = GetFileSettings(2).execute(auth_conn)
            assert auth_conn.session.cmd_counter == 2
            
            # Command 3: counter = 2
            ChangeKey(0, new_key, None, 0x01).execute(auth_conn)
            assert auth_conn.session.cmd_counter == 3
```

#### Experiment 6.3: Session State Validation
```python
# File: tests/test_session_state.py

def test_session_keys_after_auth():
    """Validate session keys match expected values"""
    
    # Use KNOWN rnda, rndb from captured Arduino session
    rnda = bytes.fromhex("...")  # From Arduino serial
    rndb = bytes.fromhex("...")  # From Arduino serial
    ti = bytes.fromhex("...")    # From Arduino serial
    key = bytes(16)  # Factory default
    
    # Derive session keys using our code
    session = Ntag424AuthSession(key, 0)
    session_keys = session._derive_session_keys(rnda, rndb, ti)
    
    # Compare with Arduino values
    assert session_keys.session_enc_key.hex() == "..."  # From Arduino
    assert session_keys.session_mac_key.hex() == "..."  # From Arduino
    assert session_keys.ti == ti
    assert session_keys.cmd_counter == 0
    
    print("✓ Session keys match Arduino!")

def test_session_persistence():
    """Verify session state doesn't get corrupted"""
    
    with CardManager() as card:
        SelectPiccApplication().execute(card)
        
        with AuthenticateEV2(factory_key, 0).execute(card) as auth_conn:
            # Capture initial state
            ti_initial = auth_conn.session.session_keys.ti
            enc_key_initial = auth_conn.session.session_keys.session_enc_key
            mac_key_initial = auth_conn.session.session_keys.session_mac_key
            
            # Execute command
            GetKeyVersion(0).execute(auth_conn)
            
            # Verify state unchanged (except counter)
            assert auth_conn.session.session_keys.ti == ti_initial
            assert auth_conn.session.session_keys.session_enc_key == enc_key_initial
            assert auth_conn.session.session_keys.session_mac_key == mac_key_initial
            assert auth_conn.session.session_keys.cmd_counter == 1  # Incremented
```

#### Experiment 6.4: ACR122U-Specific Testing
```python
# File: tests/test_reader_variations.py

def test_escape_vs_transmit():
    """Test both reader modes for ChangeKey"""
    
    # Some readers need escape commands, others don't
    # ACR122U can use both
    
    for use_escape in [True, False]:
        print(f"\n=== Testing use_escape={use_escape} ===")
        
        with CardManager() as card:
            SelectPiccApplication(use_escape=False).execute(card)
            
            with AuthenticateEV2(factory_key, 0, use_escape=False).execute(card) as auth_conn:
                try:
                    ChangeKey(0, new_key, None, 0x01, use_escape=use_escape).execute(auth_conn)
                    print(f"✓ SUCCESS with use_escape={use_escape}")
                    return  # Success!
                except ApduError as e:
                    print(f"✗ FAILED with use_escape={use_escape}: {e}")

def test_timing_delays():
    """Test if timing matters between commands"""
    import time
    
    with CardManager() as card:
        SelectPiccApplication().execute(card)
        
        with AuthenticateEV2(factory_key, 0).execute(card) as auth_conn:
            # Try with various delays
            for delay_ms in [0, 10, 50, 100]:
                print(f"\nTrying with {delay_ms}ms delay...")
                time.sleep(delay_ms / 1000.0)
                
                try:
                    ChangeKey(0, new_key, None, 0x01).execute(auth_conn)
                    print(f"✓ SUCCESS with {delay_ms}ms delay")
                    return
                except ApduError as e:
                    print(f"✗ Failed: {e}")
```

#### Experiment 6.5: Compare Against Working Command
```python
# File: tests/test_working_vs_failing.py

def test_working_command_structure():
    """
    Use a KNOWN WORKING authenticated command (e.g., GetKeyVersion)
    to verify our session/CMAC is correct.
    """
    
    with CardManager() as card:
        SelectPiccApplication().execute(card)
        
        with AuthenticateEV2(factory_key, 0).execute(card) as auth_conn:
            # This command works, so session is valid
            version = GetKeyVersion(0).execute(auth_conn)
            print(f"✓ GetKeyVersion succeeded: version={version}")
            
            # Capture the APDU that worked
            # Compare structure with ChangeKey APDU
            
            # Now try ChangeKey with SAME session
            try:
                ChangeKey(0, new_key, None, 0x01).execute(auth_conn)
                print("✓ ChangeKey succeeded!")
            except ApduError as e:
                print(f"✗ ChangeKey failed: {e}")
                print("\nSomething specific to ChangeKey is wrong!")

def test_changekey_vs_getversion_apdu():
    """Compare APDU structure between working and failing commands"""
    
    # GetKeyVersion (MAC mode - this works):
    # 90 64 00 00 09 00 CMAC(8) 00
    
    # ChangeKey (FULL mode):
    # 90 C4 00 00 29 00 ENC(32) CMAC(8) 00
    
    # Key differences:
    # 1. ChangeKey has encrypted data (32 bytes)
    # 2. ChangeKey uses different command (0xC4 vs 0x64)
    # 3. CMAC is calculated differently (includes encrypted data)
    
    # Verify our CMAC includes the encrypted data properly
    ...
```

#### Experiment 6.6: Byte Order Validation
```python
# File: tests/test_byte_order.py

def test_counter_byte_order():
    """Verify counter is little-endian"""
    cmd_ctr = 3
    
    # Arduino: CmdCtr[0] = LSB, CmdCtr[1] = MSB
    # Little-endian: 0x0300
    counter_bytes = cmd_ctr.to_bytes(2, byteorder='little')
    assert counter_bytes == b'\x03\x00'
    
def test_crc32_byte_order():
    """Verify CRC32 is little-endian"""
    import zlib
    
    new_key = bytes([1] + [0]*15)
    crc = zlib.crc32(new_key) ^ 0xFFFFFFFF
    
    # Arduino: memcpy(&keyData[17], &crc, 4)
    # Little-endian 4-byte integer
    crc_bytes = crc.to_bytes(4, byteorder='little')
    
    # Verify matches Arduino captured value
    ...

def test_ti_byte_order():
    """Verify Ti byte order in IV and CMAC"""
    
    # Ti from card is 4 bytes
    # Used in: A5 5A || Ti || CmdCtr || zeros
    # No byte-order conversion needed (just copy)
    
    ti = bytes.fromhex("7614281A")
    
    # In IV: should be exactly as received
    iv_plaintext = b'\xA5\x5A' + ti + b'\x03\x00' + b'\x00'*8
    assert iv_plaintext[2:6] == ti
```

---

## Execution Order

1. **Start with Phase 1.1-1.2**: Extract crypto, verify against NXP specs
2. **If Phase 1 passes**: Move to Phase 2, compare with Arduino
3. **If Phase 2 fails**: Use Phase 4 binary search to find discrepancy
4. **If Phase 1 or 2 fail**: Check Phase 5 for known bugs
5. **If all primitives match**: Move to Phase 3 (pyscard direct) to isolate session management
6. **Once working**: Integrate fixes back into production code

## Expected Outcomes

### Scenario A: Crypto Primitive Bug
- **Symptoms**: Phase 1 tests fail against NXP vectors
- **Fix**: Correct the specific crypto function
- **Verification**: Re-run all phases

### Scenario B: Session Management Bug
- **Symptoms**: Phase 1-2 pass, Phase 3 (pyscard) also passes, but production fails
- **Fix**: Bug in `AuthenticatedConnection` or `Ntag424AuthSession`
- **Verification**: Compare session state between working (pyscard) and failing (production)

### Scenario C: Counter Management Bug
- **Symptoms**: First command works, subsequent fail
- **Fix**: Counter increment timing or value
- **Verification**: Test sequence of multiple authenticated commands

### Scenario D: Reader-Specific Issue
- **Symptoms**: Everything matches spec, but still fails
- **Fix**: ACR122U escape mode, timing, or command framing
- **Verification**: Test with different reader or sniff USB traffic

## Files to Create

1. `tests/crypto_components.py` - Standalone crypto primitives
2. `tests/test_crypto_components.py` - Unit tests with NXP vectors
3. `tests/test_changekey_wire_compare.py` - Arduino comparison
4. `tests/test_changekey_pyscard_direct.py` - Raw pyscard test
5. `tests/test_hex_diff.py` - Binary comparison tool
6. `CHANGEKEY_EXPERIMENT_LOG.md` - Document results as we go

## Success Definition

ChangeKey command succeeds (0x9100) with:
1. All crypto unit tests passing
2. All values matching Arduino implementation
3. Working both via pyscard and production code
4. Documented root cause and fix in LESSONS.md

## Estimated Time

- Phase 1: 2-3 hours (extract + test)
- Phase 2: 1-2 hours (Arduino capture + compare)
- Phase 3: 1 hour (pyscard direct)
- Phase 4: 1-2 hours (binary search if needed)
- Phase 5: 30 min (verify known bugs)
- **Total**: 5-8 hours for complete root cause analysis

## Notes

- Work incrementally - fix one thing at a time
- Document every finding in experiment log
- Use tag for live testing (don't brick it!)
- Keep Arduino serial captures for reference
- Compare against BOTH AN12196 and AN12343 test vectors

