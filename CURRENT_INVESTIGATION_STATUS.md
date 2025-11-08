# Current Investigation Status

## From MINDMAP Analysis

### Authentication: ✅ FIXED (Was broken, now works)
**Root Cause (Line 648-660):** Was using ECB instead of CBC  
**Fix Applied:** Changed to CBC mode with zero IV  
**Status:** Authentication completes successfully (9100)

### Current Problem: Post-Auth Commands Fail (911E)
- Authentication succeeds ✅
- Session keys derived ✅  
- BUT: Every command after auth fails with 911E (INTEGRITY_ERROR)

## What We've Tested

### ✓ Crypto Primitives: 15/16 NXP Spec Tests Pass
**File:** `src/ntag424_sdm_provisioner/crypto/crypto_primitives.py`
- IV calculation ✓
- Encryption ✓
- CMAC calculation ✓
- CMAC truncation (even bytes) ✓

### ✓ APDU Construction: Byte-Perfect
APDUs match NXP specifications exactly

### ✗ Authenticated Commands: ALL FAIL
- GetKeyVersion: 911E
- ChangeKey: 911E
- Even with raw pyscard + crypto_primitives: 911E

## The Mystery

**Authentication:**
```
Phase 1: 91AF ✓
Phase 2: 9100 ✓
RndA' verified ✓
Session keys derived ✓
```

**First Authenticated Command:**
```
Counter: 0
Ti: Correct
CMAC input: Cmd || 0000 || Ti || Data
CMAC: Calculated with session MAC key
Result: 911E (INTEGRITY_ERROR)
```

## Hypothesis

The card accepts our authentication but rejects our CMAC. This means:
1. Session keys we derive ≠ Session keys card derives
2. OR: CMAC structure is wrong for post-auth commands
3. OR: Counter management is wrong

## What Datasheet Says (Section 9.1.4)

**For Authentication (Line 886):**
> "For the encryption during authentication, the IV will be 128 bits of 0"

**For Commands (Line 880):**
> "IV for CmdData = E(SesAuthENCKey; A5h || 5Ah || TI || CmdCtr || 0000000000000000h)"

**CMAC Structure:**
> "MAC is calculated over: Cmd || CmdCtr || TI || CmdHeader || CmdData"

**Counter (Line 882):**
> "CmdCtr to be used in IV are the current values"
> "if CmdCtr = n before reception, after validation CmdCtr = n + 1"

## Next Actions

### Test with Fresh Tag
To rule out tag corruption from experiments.

###Compare Session Keys with Arduino
Need to capture Arduino's session keys using SAME RndA/RndB and compare.

This requires modifying Full_ChangeKey.ino to print:
```cpp
Serial.print("SesAuthEncKey: "); printHex(SesAuthEncKey, 16);
Serial.print("SesAuthMacKey: "); printHex(SesAuthMacKey, 16);
```

Then use identical RndA in both to compare.

## Files Available

- `tests/raw_readonly_test.py` - GetKeyVersion test (raw pyscard + crypto_primitives only)
- `tests/reset_key0_raw_pyscard.py` - ChangeKey test (raw pyscard + crypto_primitives only)  
- `tests/test_fresh_tag_readonly.py` - Safe test for fresh tag

All use ONLY crypto_primitives.py, no other production code.

