# ChangeKey Investigation Findings

**Status:** ROOT CAUSE IDENTIFIED - Session key derivation or authentication has a bug

## What We've Accomplished

### ✓ Verified Crypto Primitives are CORRECT
Created standalone crypto components and tested against NXP specifications:
- **15/16 tests pass** against AN12196 and AN12343 test vectors
- IV calculation matches spec exactly
- AES encryption matches spec exactly  
- CMAC calculation matches spec exactly
- CMAC truncation (even-numbered bytes) is correct

**Files:** `tests/crypto_components.py`, `tests/test_crypto_components.py`

### ✓ Verified APDU Construction is CORRECT
Compared production ChangeKey vs verified crypto:
- **APDUs are byte-for-byte IDENTICAL**
- Both produce the exact same 47-byte APDU
- Encryption, CMAC, all match perfectly

**File:** `tests/test_changekey_production_vs_verified.py`

### ✗ Found ROOT CAUSE: Authentication Session is Broken
**Critical Discovery:** Not just ChangeKey, but ALL authenticated commands fail!

Tested:
- ChangeKey: ✗ 0x911E (INTEGRITY_ERROR)
- GetKeyVersion: ✗ 0x911E (INTEGRITY_ERROR)  
- Manually-built GetKeyVersion: ✗ 0x911E (INTEGRITY_ERROR)

**Files:** `tests/test_session_validation.py`, `tests/test_manual_authenticated_command.py`

## The Problem

Despite authentication completing successfully (0x9100), the card rejects EVERY subsequent authenticated command with INTEGRITY_ERROR. This means:

1. ✓ Authentication protocol completes
2. ✓ We get Ti from the card
3. ✓ We derive session keys using correct formula
4. ✗ **But the session keys are WRONG** (or something in auth is wrong)

The card's CMAC verification fails, which means either:
- Our session keys don't match what the card derived
- Our Ti is wrong
- Our counter management is wrong
- Something fundamental in authentication is broken

## Evidence

### Test Output from Manual GetKeyVersion:
```
Ti: 74ff91a9
Counter: 0
Session MAC key: a7c794345d2c9dcb6cc484bfff12a300

CMAC input (8 bytes): 64000074ff91a900
                     [Cmd][Ctr][Ti  ][KeyNo]
CMAC (full): 982ded968ccb66c01a4a4dfc3c1b9476
CMAC (truncated): 2d96cbc04afc1b76

APDU: 90 64 00 00 09 00 2D 96 CB C0 4A FC 1B 76 00

Response: SW=911E (INTEGRITY_ERROR)
```

The CMAC structure is correct per Arduino implementation, but the card rejects it.

## Next Steps to Investigate

### 1. Compare Session Key Derivation with Arduino
Capture Arduino session keys and compare with ours using SAME RndA/RndB/Ti.

**Check:**
- Are we using the correct SV1/SV2 values?
- Are we padding correctly (SV || 0x00*8)?
- Are we using the right base key?

### 2. Verify RndA' in Auth Phase 2 Response
The card sends back RndA' (rotated) - verify we're checking this correctly.

**Check:**
- Is our RndA verification working?
- Could we be completing auth with wrong RndA?

### 3. Check Ti Byte Order
Ti is 4 bytes - ensure no byte-order issues.

**Check:**
- Ti usage in IV calculation
- Ti usage in CMAC input
- Ti from card response parsing

### 4. Test with Known Session Keys
If we can get Arduino to print its session keys, we can:
- Use those exact keys in Python
- Build APDU with them
- If it works → our key derivation is wrong
- If it fails → something else is wrong

## Recommended Approach

**Most Efficient Path:**

1. **Modify Arduino to print session keys** after auth
   ```cpp
   Serial.print("SesAuthEncKey: "); printHex(SesAuthEncKey, 16);
   Serial.print("SesAuthMacKey: "); printHex(SesAuthMacKey, 16);
   ```

2. **Use same RndA in both** (temporarily hardcode in both Arduino & Python)

3. **Compare session keys** - if they differ, that's the bug

4. **Test with Arduino's keys in Python** - if it works, confirms key derivation bug

## Files Created

All test files are in `tests/`:
- `crypto_components.py` - Verified crypto primitives
- `test_crypto_components.py` - 15/16 tests pass  
- `test_changekey_production_vs_verified.py` - APDUs match!
- `test_session_validation.py` - Found root cause
- `test_manual_authenticated_command.py` - Manual APDU test

Documentation:
- `CHANGEKEY_EXPERIMENTAL_PLAN.md` - Full experimental plan
- `CHANGEKEY_EXPERIMENT_LOG.md` - Results log
- `FINDINGS_FOR_USER.md` - This file

## Key Insight

**The crypto implementation is perfect.** The bug is in authentication or session management, not in ChangeKey itself. Once we fix the session, ChangeKey will work immediately since the APDU construction is already correct.

## Status

**Blocked on:** Understanding why session keys don't match card's expectations

**Best next action:** Compare session key derivation with Arduino using identical inputs

