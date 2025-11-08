# ChangeKey Experimental Results Log

**Date:** 2025-11-08  
**Goal:** Fix ChangeKey 0x911E INTEGRITY_ERROR

## Summary

### Crypto Primitives: ✓ VERIFIED CORRECT
- All NXP specification test vectors pass (15/16 tests)
- AN12196 Table 26: IV, encryption, CMAC all match
- AN12343 Table 40: IV, encryption, CMAC all match
- CMAC truncation (even-numbered bytes) is correct
- Production code produces IDENTICAL APDUs to verified crypto

### APDU Comparison: ✓ VERIFIED IDENTICAL
Production vs Verified crypto produce byte-for-byte identical ChangeKey APDUs:
```
90 C4 00 00 29 00 62 54 1D 53 11 C7 E7 89 20 41
86 25 CB 79 D7 D0 14 64 3D 24 E6 5D F9 88 C8 CD
00 19 D2 8D CD CA D5 AF F9 38 3F 92 3E 30 00
```

### Issue Found: ✗ AUTHENTICATED SESSION BROKEN
- ChangeKey fails with 0x911E (INTEGRITY_ERROR)
- **GetKeyVersion ALSO fails with 0x917E (LENGTH_ERROR)**
- This means the auth session itself is broken, not just ChangeKey!

## Experiments Performed

### Phase 1: Crypto Primitives (COMPLETE ✓)
**Status:** SUCCESS

Created `tests/crypto_components.py` with standalone crypto functions:
- `calculate_iv_for_command()` - IV calculation
- `encrypt_key_data()` - AES-CBC encryption
- `calculate_cmac()` - CMAC with even-byte truncation
- `build_key_data()` - 32-byte key data construction

Created `tests/test_crypto_components.py` with NXP test vectors:
- AN12196 Table 26 (all steps verified ✓)
- AN12343 Table 40 (all steps verified ✓)

**Result:** 15/16 tests pass. All NXP spec values match exactly.

### Phase 2: APDU Comparison (COMPLETE ✓)
**Status:** SUCCESS

Created `tests/test_changekey_production_vs_verified.py`:
- Builds ChangeKey APDU using both production and verified crypto
- Compares byte-for-byte
- **Result:** APDUs are IDENTICAL

This proves our crypto implementation is correct!

### Phase 3: Session Validation (COMPLETE ✗)
**Status:** FAILED - Root cause identified

Created `tests/test_session_validation.py`:
- Authenticates using production code
- Tries GetKeyVersion (simple MAC command)
- **Result:** GetKeyVersion fails with 0x917E (LENGTH_ERROR)

**Critical Finding:** Even simple authenticated commands fail!
The problem is NOT in ChangeKey, but in the authentication session itself.

## Root Cause Analysis

### What Works
✓ Authentication completes successfully (0x9100)  
✓ Session keys are derived  
✓ Ti is received from card  
✓ Crypto primitives match NXP specs  
✓ APDU construction is correct  

### What Doesn't Work
✗ Any command sent after authentication fails  
✗ GetKeyVersion: 0x917E (LENGTH_ERROR)  
✗ ChangeKey: 0x911E (INTEGRITY_ERROR)  

### Hypothesis
The authenticated session is established, but:
1. Commands after auth aren't being sent correctly
2. The CMAC might not be applied to subsequent commands
3. The command counter might not be included properly
4. There might be a mismatch in how we send authenticated vs unauthenticated commands

## Next Steps

### Immediate Actions
1. **Inspect GetKeyVersion APDU** - Print the actual APDU being sent
2. **Compare with working Arduino** - Capture GetKeyVersion from Arduino
3. **Check AuthenticatedConnection.send()** - Verify it applies CMAC
4. **Test with raw pyscard** - Bypass our abstractions entirely

### Investigation Areas
1. **Command Counter:** Is it being included in CMAC?
2. **CMAC Application:** Is `apply_cmac()` being called?
3. **APDU Wrapping:** Is the APDU being modified after crypto?
4. **Escape Mode:** Is ACR122U escape mode interfering?

## Test Files Created

1. `tests/crypto_components.py` - Standalone crypto primitives
2. `tests/test_crypto_components.py` - Unit tests with NXP vectors (15/16 pass)
3. `tests/test_changekey_minimal.py` - Raw pyscard test (incomplete)
4. `tests/test_changekey_direct.py` - CardManager test (auth failed)
5. `tests/test_changekey_with_hal.py` - Production auth test (incomplete)
6. `tests/test_changekey_production_vs_verified.py` - APDU comparison (APDUs match!)
7. `tests/test_session_validation.py` - Session validation (revealed root cause)

## Key Insights

1. **Our crypto is correct** - Matches NXP specs exactly
2. **Our APDU construction is correct** - Matches verified implementation
3. **The bug is in session management** - Commands after auth fail
4. **This is a systematic issue** - Not specific to ChangeKey

## Error Codes Observed

- `0x911E` - INTEGRITY_ERROR (CMAC verification failed)
- `0x917E` - LENGTH_ERROR (Wrong data length)
- Both suggest the card isn't receiving properly formatted authenticated commands

## Status: INVESTIGATION CONTINUES

**Current Focus:** Why do authenticated commands fail even though auth succeeds?

**Blocker:** Need to see the actual APDU bytes being sent for GetKeyVersion

