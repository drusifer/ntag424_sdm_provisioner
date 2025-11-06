# Current Step: API Design & Exception Handling Refactoring - COMPLETE ✅

TLDR; **CSV Key Manager Complete** ✅ (51 tests). Discovered CMAC truncation bug (even-numbered bytes per AN12196). ChangeKey format correct but CMAC still fails (0x911E). Need to debug counter/IV sequencing or find working reference implementation.

---

## Current Status

**COMPLETED Today:**
1. ✅ CSV Key Manager with two-phase commit (22 tests)
2. ✅ Example 22 updated to proper provisioning sequence
3. ✅ Discovered CMAC truncation bug (even-numbered bytes per AN12196/NXP spec)
4. ✅ Fixed ChangeKey format (32 bytes, CRC32, padding, encryption, IV)
5. ✅ Applied global CMAC fix to apply_cmac()

**BLOCKED:**
- ChangeKey: 0x911E INTEGRITY_ERROR (16+ attempts)
- ChangeFileSettings: 0x911E INTEGRITY_ERROR  
- Both use authenticated CommMode.FULL

## Current Step Goal

**Debug ChangeKey and ChangeFileSettings CMAC** (both failing with 0x911E)

## Investigation Needed

**Verified Correct (per AN12196):**
- Format: 32 bytes with 0x80 padding
- CRC32: Inverted for non-zero keys
- IV: E(KSesAuthENC, zero_iv, A5 5A || TI || CmdCtr || zeros)
- CMAC input: Cmd || CmdCtr || TI || CmdHeader || EncryptedData
- CMAC truncation: Even-numbered bytes [1,3,5,7,9,11,13,15]
- Counter: 0 after auth, increment after command

**Still Failing:**
- ChangeKey: 0x911E after 16+ attempts
- ChangeFileSettings: 0x911E 

**Next Steps:**
1. Find working Python NTAG424 implementation for comparison
2. Capture wire data from Arduino to compare bytes
3. Verify session keys are derived correctly
4. Check if reader (ACR122U) requires different format than spec
5. Post to NXP community with our AN12196 comparison

**ACHIEVED:**
1. ✅ Simplified command base layer with `send_command()`
2. ✅ Enum constants with consistent `__str__()` formatting  
3. ✅ AuthenticatedConnection context manager pattern
4. ✅ Clean abstractions (no bitwise math, no manual encoding)
5. ✅ Specific exception classes with descriptive messages
6. ✅ Dataclass-based configuration (no dicts with `.get()`)
7. ✅ Encapsulated encoding (`SDMConfiguration` handles `AccessRights` encoding)
8. ✅ All 29 tests passing
9. ✅ Verified with real chip

**NEXT:** Resume SDM configuration debugging (ChangeFileSettings 0x917E error)

---

## Refactoring Summary

### 1. Command Base Layer Enhancement
- **Added `send_command()`**: Automatic multi-frame handling + error checking
- **Removed `send_apdu()` wrapper**: Simplified architecture (one less layer)
- **Refactored 11 commands**: ~50 lines duplicate code removed
- **Uses reflection**: Command names in errors via `self.__class__.__name__`

### 2. Enum Constants for Status Words
- **Created `StatusWordPair` enum**: Beautiful debug output
- **Auto-formatting**: Shows `"SW_OK (0x9000)"` instead of `"(144, 0)"`
- **Backward compatible**: Old tuple constants still work
- **All enums updated**: Consistent `__str__()` across all enum classes

### 3. AuthenticatedConnection Pattern
- **Context manager**: Explicit authentication scope
- **`AuthenticateEV2` command**: Returns `AuthenticatedConnection`
- **Dual methods**: `send_apdu()` for plain, `send_authenticated_apdu()` for CMAC
- **CommMode-aware**: Check file's CommMode before authenticating

### 4. Clean Abstractions
- **`FileSettingsResponse.get_comm_mode()`**: No bitwise math
- **`FileSettingsResponse.requires_authentication()`**: Clean boolean
- **`CommMode.from_file_option()`**: Enum extraction
- **`CommMode.requires_auth()`**: Instance method

### 5. Exception Handling Architecture
- **Specific exception classes**: `AuthenticationRateLimitError`, `CommandLengthError`, etc.
- **Messages at throw time**: Exceptions contain full context when raised
- **Polymorphic handling**: Exception type determines behavior (no if/else)
- **Single catch point**: `except ApduError` catches all APDU-related errors

### 6. API Design - Encapsulation & Pythonic Defaults
- **`SDMOffsets` dataclass**: Replaces dict with sane defaults (no `.get()`)
- **`AccessRights` in `SDMConfiguration`**: Pass object, not bytes
- **Encapsulated encoding**: `get_access_rights_bytes()` is internal
- **Type safety**: Dataclasses catch errors at construction time
- **Self-documenting**: No magic bytes (`b'\xE0\xEE'` → `AccessRights(...)`)

---

## User Story

**As a developer**, I want to enable SDM on the NDEF file, so that the tag generates tap-unique URLs with UID, counter, and CMAC authentication.

**Acceptance Criteria:**
- [x] Can authenticate with tag
- [x] Can build SDM configuration
- [ ] ChangeFileSettings succeeds (SW=9000)
- [ ] GetFileCounters returns counter (not 0x911C)
- [ ] Tag fills placeholders when tapped

---

## Investigation Plan

### Step 1: Debug ChangeFileSettings Payload
1. Log exact APDU bytes being sent
2. Compare with NXP specification
3. Check build_sdm_settings_payload() output
4. Identify length mismatch

### Step 2: Test Simpler SDM Configuration
1. Try minimal SDM config (just enable, no options)
2. Test without CMAC mirroring
3. Test with just UID mirroring
4. Find what works

### Step 3: Research Seritag-Specific Requirements
1. Check if Seritag SDM differs from standard
2. Review NT4H2421Gx.md for ChangeFileSettings spec
3. Look for byte-level examples

### Step 4: Fix and Verify
1. Implement fix based on findings
2. Test with real chip
3. Verify GetFileCounters works after config
4. Tap coin and verify dynamic URL

---

## Implementation Plan

### Phase 1: Add Detailed Logging
Create diagnostic script to see exact bytes:

```python
def debug_sdm_config():
    # Build SDM config
    config = SDMConfiguration(...)
    
    # Log payload
    payload = build_sdm_settings_payload(config)
    print(f"Payload: {payload.hex()}")
    print(f"Payload length: {len(payload)}")
    
    # Build full APDU
    apdu = build_change_file_settings_apdu(config)
    print(f"APDU: {' '.join(f'{b:02X}' for b in apdu)}")
    print(f"APDU length: {len(apdu)}")
```

### Phase 2: Test Minimal Config
Try absolute simplest SDM configuration:

```python
# Minimal: Just enable SDM, no mirroring
config = SDMConfiguration(
    file_no=0x02,
    comm_mode=CommMode.PLAIN,
    access_rights=b'\xEE\xEE',  # All free
    enable_sdm=False,  # Start with SDM disabled
)
# If this works, add features one by one
```

### Phase 3: Compare with Working Example
Check if any existing examples successfully use ChangeFileSettings.

### Phase 4: Implement Fix
Based on findings, fix:
- Payload length calculation
- SDM options byte encoding
- Offset encoding (3 bytes LSB-first)
- Access rights format

---

## Acceptance Tests

**Test 1: ChangeFileSettings Succeeds**
```python
def test_change_file_settings_minimal():
    """ChangeFileSettings with minimal config succeeds"""
    # Authenticate
    # Configure SDM (minimal)
    # Expect: SW=9000
```

**Test 2: GetFileCounters Works After SDM**
```python
def test_file_counters_after_sdm():
    """GetFileCounters returns counter after SDM enabled"""
    # Configure SDM
    # Read counter
    # Expect: Integer 0-16777215 (not error)
```

**Test 3: Tag Fills Placeholders**
```python
def test_tap_generates_dynamic_url():
    """Tapping tag generates URL with real values"""
    # Configure SDM
    # Write NDEF with placeholders
    # Read back (simulates tap)
    # Expect: Real UID, not 00000000000000
```

---

## Expected Outcome

After this step:
- ✅ ChangeFileSettings succeeds
- ✅ SDM enabled on NDEF file
- ✅ GetFileCounters returns actual counter
- ✅ Tag generates tap-unique URLs
- ✅ Ready for server-side validation (Phase 4)

---

## Progress Tracking

### Completed
- [x] Identified blocking issue (ChangeFileSettings length error)
- [x] Authentication pipeline working
- [x] NDEF write pipeline working
- [x] URL building working

### In Progress
- [ ] Debug ChangeFileSettings payload
- [ ] Test simpler SDM configurations
- [ ] Fix length error
- [ ] Verify SDM works

### Pending
- [ ] CMAC validation (Phase 4)
- [ ] Server endpoint examples (Phase 4)
- [ ] Mock HAL SDM simulation (Phase 5)

---

**Status:** Starting debug of ChangeFileSettings  
**Estimated Duration:** 1-2 hours  
**Blockers:** None - have all tools and access to chip  
**Next:** Create debug script for ChangeFileSettings
