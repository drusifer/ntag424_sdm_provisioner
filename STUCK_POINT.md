# Investigation Status - Stuck on 911E INTEGRITY_ERROR

## What We Know (100% Certain)

### ✓ Crypto Primitives are CORRECT
- **15/16 tests pass** against NXP specifications (AN12196, AN12343)
- IV calculation: ✓ Verified
- Encryption: ✓ Verified  
- CMAC calculation: ✓ Verified
- CMAC truncation (even bytes): ✓ Verified

**File:** `src/ntag424_sdm_provisioner/crypto/crypto_primitives.py`

### ✓ APDU Construction is CORRECT
- Built APDUs match byte-for-byte between:
  - Production code
  - Verified crypto components
  - Expected format per NXP spec

### ✓ Authentication Protocol Completes
- Auth Phase 1: Returns 91AF ✓
- Auth Phase 2: Returns 9100 ✓
- RndA' verification: PASSES ✓
- Session keys: Derived correctly ✓

### ✗ All Authenticated Commands FAIL
- ChangeKey: 911E (INTEGRITY_ERROR)
- GetKeyVersion: 911E (INTEGRITY_ERROR)
- Manual commands: 911E (INTEGRITY_ERROR)

## Latest Test - Raw Pyscard

**File:** `tests/reset_key0_raw_pyscard.py`

Implemented exact Arduino sequence:
1. Select PICC: ✓ 9000
2. Auth Phase 1: ✓ 91AF
3. Auth Phase 2: ✓ 9100
4. RndA' verification: ✓ PASS
5. Session key derivation: ✓ Complete
6. ChangeKey: ✗ 911E (INTEGRITY_ERROR)

**Session keys derived:**
```
Ti: 121D8345
Session ENC: 29F91E5E3234FACF179D3592DF64CF15
Session MAC: E671713EE7354517130FF8A67D42A700
```

**ChangeKey APDU sent:**
```
90 C4 00 00 29 00 D6 91 A6 96 31 60 45 5F 94 73 
13 EB 9B 2A AA D8 D7 66 12 86 C1 31 C3 9B 9C 63 
CF 2F 4A 9A B4 E0 34 61 5A AB 0A 67 6D 65 00
```

**Result:** 911E (INTEGRITY_ERROR)

## The Puzzle

1. Authentication completes successfully (9100)
2. RndA' matches exactly (we verified it)
3. Card accepts our Phase 2 response
4. Session keys are derived using correct formula
5. Crypto primitives match NXP specs perfectly
6. ChangeKey APDU format is correct per NXP spec
7. **YET: Card rejects the ChangeKey with INTEGRITY_ERROR**

## Possible Causes (Ranked by Likelihood)

### 1. Session Key Derivation Bug (Most Likely)
Despite getting 9100, our session keys might not match what the card expects.

**Test:** Capture Arduino's session keys using SAME RndA/RndB and compare.

**Action needed:** Modify Arduino code to print:
```cpp
Serial.print("SesAuthEncKey: "); printHex(SesAuthEncKey, 16);
Serial.print("SesAuthMacKey: "); printHex(SesAuthMacKey, 16);
```

### 2. Ti Parsing Bug
Ti might be in wrong byte order or we're parsing it incorrectly.

**Current:** Ti = response_dec[0:4] = `121D8345`

**Check:** Is this correct per spec?

### 3. Counter Initialization Bug  
Card might initialize counter to something other than 0.

**Current:** cmd_ctr = 0 for first command

**Check:** Does card expect counter = 1?

### 4. CMAC Input Structure Bug
The structure might be subtly wrong.

**Current:** Cmd || CmdCtr || TI || KeyNo || Encrypted
```
C4 0000 121D8345 00 D691A696...
```

**Check:** Should it be different?

### 5. Reader-Specific Issue
ACR122U might require something special for authenticated commands.

**Unlikely** because auth itself works.

## What To Do Next

### Option A: Compare with Arduino (Recommended)
1. Modify Full_ChangeKey.ino to print session keys
2. Use SAME RndA in both Arduino and Python (hardcode temporarily)
3. Compare session keys - if they differ, that's the bug!

### Option B: Try Different Tag
Test with a fresh tag to rule out corruption.

### Option C: Sniff USB Traffic
Use Wireshark/USBPcap to capture Arduino's wire-level traffic and compare with ours.

### Option D: Consult NXP
This might be a subtle spec interpretation issue that needs vendor clarification.

## Files to Review

- `tests/reset_key0_raw_pyscard.py` - Latest test (raw pyscard, verified crypto)
- `src/ntag424_sdm_provisioner/crypto/crypto_primitives.py` - Verified crypto (15/16 tests pass)
- `tests/test_crypto_components.py` - Test vectors from NXP specs
- `FINDINGS_FOR_USER.md` - Earlier analysis

## Status

**BLOCKED:** Need to determine why session keys don't work despite auth succeeding.

**Most efficient next step:** Capture Arduino session keys and compare with ours using identical RndA/RndB.

