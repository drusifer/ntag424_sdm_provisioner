# NTAG424 SDM Provisioner - Investigation Mindmap

**TLDR;**: Static URL provisioning works ✅ | Phase 2 auth fails (SW=91AE - Wrong RndB') ❌ | All protocol steps verified correct per NXP spec ✅ | Reader/Hardware ruled out ✅ | **UNKNOWN if Seritag-specific** - Need standard NXP tag for comparison 🔍

---

## Investigation Status

### ✅ Verified Working
- **Static URL NDEF Provisioning**: Works without authentication (production-ready)
- **Phase 1 Authentication**: Returns encrypted RndB correctly (SW=91AF, 16 bytes)
- **RndB Extraction**: First 16 bytes = encrypted RndB ✅
- **RndB Rotation**: Left rotate by 1 byte verified byte-by-byte ✅
- **Phase 2 Format**: Standard left rotate accepted (SW=91AE, not SW=911C)
- **APDU Structure**: Matches NXP spec exactly ✅
- **Byte Alignment**: Correct (32 bytes = 2 AES blocks) ✅
- **Command Format**: Correct (90 AF 00 00 20 [32 bytes] 00) ✅
- **Encryption**: AES-ECB mode correct ✅

### ❌ Known Issues
- **Phase 2 Authentication**: Fails with SW=91AE (Wrong RndB')
- **SDM/SUN Configuration**: Blocked (requires Phase 2 auth)
- **Key Management**: Implemented but untested

---

## Phase 2 Protocol Deep Dive Results

### What Was Tested
1. **15 Key/Rotation Combinations**: All failed
   - Factory Key (all zeros) + Standard rotation → SW=91AE
   - All Ones Key + Standard rotation → SW=91AE  
   - Weak Key + Standard rotation → SW=91AE
   - Non-standard rotations → SW=911C (format rejected)

2. **Phase 1 Analysis**: ✅ VERIFIED CORRECT
   - Response: 16 bytes encrypted RndB (SW=91AF)
   - Decryption: AES-ECB works correctly
   - No additional frames needed (GetAdditionalFrame returns SW=917E)

3. **Phase 2 Analysis**: ✅ FORMAT CORRECT, ❌ AUTH FAILS
   - Plaintext: RndA || RndB' (32 bytes, block-aligned) ✅
   - Encryption: AES-ECB (2 blocks of 16 bytes) ✅
   - APDU Format: Matches spec exactly ✅
   - Result: SW=91AE (Wrong RndB') ❌

### Key Findings

#### Format Validation
- **Standard left rotate (1 byte)**: ONLY rotation that passes format check (SW=91AE)
- **Non-standard rotations**: Format rejected (SW=911C) before authentication
- **Conclusion**: Format is correct, but RndB' calculation doesn't match tag's expectation

#### Error Code Analysis
- **SW=91AE**: "Wrong RndB'" - Tag can decrypt Phase 2 data, extracts RndB', but it doesn't match
- **SW=911C**: "Illegal Command Code" - Format rejected (non-standard rotations)
- **SW=91CA**: "Command Aborted" - Transaction state issue (seen after Phase 2 failure)

#### What This Tells Us
1. ✅ Tag validates Phase 2 format before authentication
2. ✅ Tag can decrypt our Phase 2 data
3. ✅ Tag extracts RndB' from our data
4. ❌ Tag's expected RndB' ≠ our calculated RndB'

---

## Hypothesis Space

### Hypothesis 1: Wrong Factory Key
**Status**: ✅ **RULED OUT** - Tested 9 key variations
- Factory Key (all zeros): ❌ SW=91AE
- All Ones Key: ❌ SW=91AE
- Weak Key Pattern: ❌ SW=91AE
- UID-based (repeat 3x): ❌ SW=91AE
- UID-based (first 4 bytes, repeat 4x): ❌ SW=91AE
- UID-based (first 4 bytes, pad with 00): ❌ SW=91AE
- UID-based (first 4 bytes, pad with FF): ❌ SW=91AE
- UID-based (CMAC with factory master): ❌ SW=91AE
- UID-based (CMAC with UID master): ❌ SW=91AE

**CRITICAL FINDING**: Phase 1 works with ALL keys (even wrong ones!)
- Phase 1 doesn't validate the key - it just encrypts RndB with whatever key it has
- Phase 2 is where validation happens
- **Conclusion**: Issue is NOT with key derivation - Phase 2 rejects RndB' regardless of key used

**Likelihood**: ❌ **RULED OUT** - All 9 variations tested, all fail identically

### Hypothesis 2: Wrong RndB Extraction
**Status**: Verified ✅
- Phase 1 returns exactly 16 bytes
- First 16 bytes = encrypted RndB
- No additional frames needed

**Likelihood**: Low (already verified)

### Hypothesis 3: Wrong RndB Decryption
**Status**: Verified ✅
- AES-ECB decryption works
- Decrypted RndB has high entropy (random-looking)
- CBC tested for comparison (different result, as expected)

**Likelihood**: Low (but verify key used for decryption)

### Hypothesis 4: Wrong RndB Rotation
**Status**: ⚠️ **HIGH PRIORITY** - Needs deeper investigation
- Left rotate by 1 byte is correct format (passes format check) ✅
- Rotation math verified: `rndb[1:] + rndb[0:1]` ✅
- Python `bytes` type confirmed correct (16-byte immutable sequence) ✅
- **BUT**: Seritag may rotate/storage RndB differently internally ❓

**Likelihood**: **HIGH** - Most likely remaining cause
- Format check passes, so rotation method is accepted
- But calculated RndB' doesn't match tag's expectation
- **Possible issues**:
  - Byte ordering (big-endian vs little-endian) - unlikely but possible
  - Rotation direction ambiguity ("left" could mean different things)
  - Tag rotates RndB BEFORE storing (vs after decryption)
  - Tag uses bit-level rotation instead of byte-level rotation (unlikely - spec says "byte")
  - Tag stores RndB in different format internally
  - Phase 1 encryption key ≠ Phase 2 validation key

**Python Byte Array Verification**:
- Type: `bytes` (16-byte immutable sequence) ✅ Correct
- Size: 16 bytes ✅ Correct (AES-128, RndB is 16 bytes)
- Rotation: `rndb[1:] + rndb[0:1]` ✅ Correct (left rotate by 1 byte)
- Example: `01 02 03 ... 10` → `02 03 04 ... 10 01` ✅ Verified

### Hypothesis 5: Wrong Phase 2 Encryption
**Status**: Verified ✅
- AES-ECB mode correct (2 blocks of 16 bytes)
- Encryption round-trip verified
- Block-by-block matches single encrypt

**Likelihood**: Low (but verify key used for encryption)

### Hypothesis 6: Phase 1/Phase 2 Transaction State
**Status**: Partially tested
- Phase 1 completes (SW=91AF)
- Phase 2 sent immediately after Phase 1
- **Observation**: Sometimes get SW=91CA instead of SW=91AE
- **Question**: Is there a timing/state issue?

**Likelihood**: Medium
- SW=91CA suggests transaction state issue
- Maybe need to complete Phase 1 differently?
- **Next**: Test Phase 1 completion sequence

### Hypothesis 7: Seritag-Specific Protocol Variant
**Status**: Likely 🔍
- All NXP spec steps verified correct
- Tag accepts format but rejects authentication
- **Possibility**: Seritag uses different:
  - Key derivation (UID-based?)
  - RndB storage/rotation internally
  - Transaction state management

**Likelihood**: High
- This would explain why format is correct but auth fails
- **Next**: Search Seritag documentation, test alternative protocols

---

## Critical Observations

### Phase 1 Response
- **Response**: SW=91AF with 16 bytes (encrypted RndB)
- **Complete**: No additional frames (GetAdditionalFrame returns SW=917E)
- **Key Used**: Factory key (all zeros) - but maybe Seritag uses different key?

### RndB Rotation
- **Method**: Left rotate by 1 byte (`rndb[1:] + rndb[0:1]`)
- **Format Check**: ✅ Passes (SW=91AE, not SW=911C)
- **Authentication**: ❌ Fails (Wrong RndB')

**Key Insight**: Tag validates format BEFORE checking RndB' value
- This means our format is correct, but our RndB' calculation is wrong

### Phase 2 Plaintext
- **Construction**: RndA (16 bytes) || RndB' (16 bytes) = 32 bytes
- **Block Alignment**: ✅ 2 AES blocks (16 bytes each)
- **Encryption**: AES-ECB mode (each block encrypted independently)

### Keys Tested (9 variations - all failed)
1. **Factory Key**: `00 00 00 00 ... 00` (16 bytes) → SW=91AE ❌
2. **All Ones Key**: `FF FF FF FF ... FF` (16 bytes) → SW=91AE ❌
3. **UID-based (repeat 3x)**: `04 1B 67 4A ...` (16 bytes) → SW=91AE ❌
4. **UID-based (first 4 bytes, repeat 4x)**: `04 1B 67 4A ...` → SW=91AE ❌
5. **UID-based (first 4 bytes, pad with 00)**: `04 1B 67 4A 00 ...` → SW=91AE ❌
6. **UID-based (first 4 bytes, pad with FF)**: `04 1B 67 4A FF ...` → SW=91AE ❌
7. **UID-based (CMAC with factory master)**: Derived via CMAC → SW=91AE ❌
8. **UID-based (CMAC with UID master)**: Derived via CMAC → SW=91AE ❌
9. **Weak Pattern Key**: `01 23 45 67 ...` → SW=91AE ❌

**CRITICAL INSIGHT**: Phase 1 works with ALL keys (even obviously wrong ones!)
- Phase 1 returns encrypted RndB regardless of key correctness
- This suggests Phase 1 doesn't validate the key at all
- Phase 2 validation is where the key/RndB' mismatch is detected

---

## Next Investigation Priorities

### Priority 1: ✅ COMPLETED - Test UID-Based Key Derivation
**Status**: ✅ **TESTED** - All 9 key variations failed identically
**Result**: Key derivation is NOT the issue
- Tested 9 different key derivation methods
- All fail with SW=91AE (Wrong RndB')
- Phase 1 works with all keys (wrong or right)
- Phase 2 rejects RndB' regardless of key

**Conclusion**: Issue is with RndB rotation/storage, not key derivation

### Priority 2: Analyze Phase 1/Phase 2 Key Relationship ⚠️ **CRITICAL**
**Rationale**: Phase 1 works with ANY key - how does Phase 2 know which key to use?
**Key Question**: Does Phase 2 validate RndB' using the SAME key that Phase 1 used to encrypt?

**Approach**:
1. **Test key mismatch**: Use different key for Phase 1 vs Phase 2 decryption
   - Phase 1 with key A, Phase 2 decrypt/encrypt with key B
   - Does error change? (SW=91AE vs different error?)
   
2. **Verify Phase 1 encryption**: 
   - If we decrypt Phase 1 response with wrong key, do we get garbage?
   - If we decrypt with correct key, does RndB make sense?
   - Does Phase 1 actually use the key we send in the command?
   
3. **Test Phase 1/Phase 2 consistency**:
   - Maybe Phase 1 stores RndB internally with tag's key
   - Maybe Phase 2 expects RndB' calculated from tag's key (not ours)
   - Maybe Seritag uses a different internal key than what we send

**Current Status**: Phase 1 returns exactly 16 bytes, works with any key
**Critical Insight**: Phase 1 doesn't validate key - it just encrypts with whatever it has

### Priority 3: Test Alternative RndB' Calculations ⚠️ **HIGH PRIORITY**
**Rationale**: All keys fail identically - suggests RndB rotation/storage issue
**Approach**:
1. **Verify Phase 1/Phase 2 key consistency**: 
   - Does Phase 1 encrypt with same key Phase 2 expects?
   - Test if Phase 1 response is actually encrypted with the key we think
   
2. **Test RndB storage/rotation variations**:
   - Maybe tag rotates RndB BEFORE storing (during Phase 1 generation)?
   - Maybe tag stores RndB in different byte order?
   - Maybe "left" means different direction in Seritag implementation?
   
3. **Test rotation alternatives** (even if format check passes):
   - Right rotate by 1 byte (might pass format check but fail auth differently)
   - No rotation (SW=911C - format rejected, but test anyway)
   - Different byte transformations (XOR with constant, etc.)
   
4. **Verify Python bytes handling**:
   - Confirm no byte ordering issues
   - Verify slice operations work correctly
   - Test with explicit bytearray if needed

**Current Status**: Only left-rotate-by-1-byte passes format check
**Next**: Deep dive into how Seritag stores/rotates RndB internally

### Priority 4: Investigate Transaction State
**Rationale**: SW=91CA suggests state issue
**Approach**:
1. Test if Phase 1 needs explicit completion
2. Test timing between Phase 1 and Phase 2
3. Test if aborting and restarting helps

**Current Status**: Phase 1 completes, Phase 2 sent immediately

### Priority 5: Search Seritag Documentation
**Rationale**: Official docs might reveal protocol differences
**Approach**:
1. Review `docs/seritag/` for authentication protocol
2. Search online for Seritag NTAG424 authentication differences
3. Check if Seritag has custom EV2 variant

---

## Test Results Summary

### Comprehensive Key Variation Test (9 keys × 1 rotation = 9 tests)
**Date**: Current session
**Result**: **0/9 keys succeeded** - All fail with SW=91AE

| Key Type | Phase 1 | Phase 2 | SW | Notes |
|----------|---------|---------|----|----|
| Factory (00...) | ✅ Works | ❌ FAIL | 91AE | Phase 1 works with wrong key! |
| All Ones (FF...) | ✅ Works | ❌ FAIL | 91AE | Phase 1 works with wrong key! |
| UID (repeat 3x) | ✅ Works | ❌ FAIL | 91AE | Phase 1 works with wrong key! |
| UID (4 bytes × 4) | ✅ Works | ❌ FAIL | 91AE | Phase 1 works with wrong key! |
| UID (pad with 00) | ✅ Works | ❌ FAIL | 91AE | Phase 1 works with wrong key! |
| UID (pad with FF) | ✅ Works | ❌ FAIL | 91AE | Phase 1 works with wrong key! |
| UID (CMAC factory) | ✅ Works | ❌ FAIL | 91AE | Phase 1 works with wrong key! |
| UID (CMAC UID) | ✅ Works | ❌ FAIL | 91AE | Phase 1 works with wrong key! |
| Weak Pattern | ✅ Works | ❌ FAIL | 91AE | Phase 1 works with wrong key! |

**CRITICAL FINDINGS**:
1. ✅ Phase 1 works with ALL keys (even obviously wrong ones!)
2. ❌ Phase 2 fails with ALL keys (identical SW=91AE)
3. ✅ Rotation format is correct (SW=91AE, not SW=911C)
4. ❌ RndB' calculation doesn't match tag's expectation

**Conclusion**: Issue is NOT key derivation. Most likely RndB rotation/storage internal to tag.

### Deep Dive Analysis Results
1. ✅ Phase 1 Response: 16 bytes encrypted RndB - Correct
2. ✅ Phase 1 Decryption: AES-ECB works - Correct (but works with ANY key!)
3. ✅ RndB Rotation: Left by 1 byte verified byte-by-byte - Correct
   - Python `bytes` type: ✅ Correct (16-byte immutable sequence)
   - Rotation operation: ✅ `rndb[1:] + rndb[0:1]` verified
   - Byte size: ✅ 16 bytes (AES-128 key size)
4. ✅ Phase 2 Plaintext: RndA || RndB' (32 bytes, block-aligned) - Correct
5. ✅ Phase 2 Encryption: AES-ECB (2 blocks of 16 bytes) - Correct
6. ✅ Phase 2 APDU: Format matches spec exactly - Correct
7. ❌ Phase 2 Result: SW=91AE (Wrong RndB') - Tag rejects

**Conclusion**: All steps correct per NXP spec, but Seritag rejects Phase 2
**New Insight**: Phase 1 doesn't validate key - works with any key, even wrong ones!

---

## Code Reference Points

### Phase 1 Implementation
**File**: `src/ntag424_sdm_provisioner/crypto/auth_session.py`
- Line 78-108: `_phase1_get_challenge()` - Gets encrypted RndB
- Line 160-172: `_decrypt_rndb()` - Decrypts RndB with AES-ECB

### Phase 2 Implementation
**File**: `src/ntag424_sdm_provisioner/crypto/auth_session.py`
- Line 110-158: `_phase2_authenticate()` - Complete Phase 2 flow
- Line 132: RndB rotation: `rndb_rotated = rndb[1:] + rndb[0:1]`
- Line 174-188: `_encrypt_response()` - Encrypts RndA || RndB'

### Test Scripts
- `examples/seritag/test_phase2_deep_dive.py` - Deep dive analysis
- `examples/seritag/test_phase2_comprehensive_variations.py` - 15 variations
- `examples/seritag/test_sun_configuration_acceptance.py` - SUN/SDM tests

---

## Investigation Documents

1. **PHASE2_PROTOCOL_INVESTIGATION.md** - Phase 2 protocol variations
2. **COMPREHENSIVE_PHASE2_VARIATIONS_RESULTS.md** - 15 combinations tested
3. **RNDB_ROTATION_INVESTIGATION.md** - RndB extraction/rotation analysis
4. **IMPLEMENTATION_VERIFICATION.md** - Protocol implementation verified
5. **BYTE_ALIGNMENT_INVESTIGATION.md** - Byte alignment checked
6. **FRESH_TAG_FINDINGS.md** - Fresh tag test results
7. **SERITAG_INVESTIGATION_COMPLETE.md** - Complete findings summary

---

## Next Actions (Updated After Reader/Hardware Testing)

1. ✅ **COMPLETED: Test UID-based key derivation** - All 9 variations failed
2. ✅ **COMPLETED: Reader mode comparison** - Both escape and transmit modes fail identically (SW=91AE)
3. ✅ **COMPLETED: Timing delays** - No improvement with delays up to 100ms
4. ✅ **COMPLETED: Fresh Phase 1 for each Phase 2** - Confirmed not a state issue

**CRITICAL FINDING**: Reader/Hardware is NOT the issue
- Phase 2 fails identically with escape mode (control) and transmit mode
- Both modes get SW=91AE (Wrong RndB')
- Timing delays don't help
- Issue is protocol-level, not hardware-level

**CONCLUSION**: This is likely NOT reader-specific, NOT Seritag-specific (need standard tag to confirm)
- Format is correct (SW=91AE, not SW=911C)
- Rotation is correct (left by 1 byte, verified)
- Key derivation tested (all fail identically)
- But calculated RndB' doesn't match tag's expectation

**Remaining Hypothesis**:
- Phase 1/Phase 2 key mismatch: Maybe Phase 1 encrypts with different key than we think?
- RndB storage: Maybe tag stores/rotates RndB differently internally?
- Need standard NXP tag for comparison to confirm if this is Seritag-specific or universal

---

**Last Updated**: Current session - After comprehensive key testing  
**Status**: Ready for next phase - Wrong RndB' investigation  
**Key Focus**: RndB rotation/storage internally, Phase 1/Phase 2 key relationship

---

## NXP Datasheet Findings

### Phase 2 Protocol (from NXP NTAG424 DNA datasheet)

**Table 28 - AuthenticateEV2First Part2 Command Parameters**:
- `RndB': 16 byte RndB rotated left by 1 byte`
- Specification: Line 1746 - "rotated left by 1 byte"
- Specification: Line 906 - "rotating it left by one byte"

**Table 29 - Response Parameters**:
- `RndA': 16 byte RndA rotated left by 1 byte`
- Specification confirms: Both RndA and RndB use same rotation method

### Rotation Verification

**Python Implementation**: ✅ **CORRECT**
```python
rndb_rotated = rndb[1:] + rndb[0:1]  # Left rotate by 1 byte
```

**Verification**:
- Python `bytes` type: ✅ Correct (16-byte immutable sequence, network byte order)
- Key size: ✅ 16 bytes (AES-128)
- RndB size: ✅ 16 bytes
- Rotation operation: ✅ Left rotate by 1 byte verified
- Example: `01 02 03 ... 10` → `02 03 04 ... 10 01` ✅

**Seritag Claims**: 100% ISO compliant
- If true, rotation should match NXP spec exactly
- But Phase 2 still fails - suggests internal storage/rotation difference

### Possible Rotation Issues to Investigate

1. **Timing of Rotation**:
   - Does tag rotate RndB BEFORE storing (during Phase 1)?
   - Do we need to rotate the STORED RndB, not the decrypted one?
   
2. **Rotation Direction Ambiguity**:
   - "Left" could mean MSB→LSB shift (bytes) or LSB→MSB shift (bits)
   - Current: MSB→LSB byte shift (first byte to end) ✅ Correct per spec
   - But maybe Seritag implements it differently?
   
3. **Internal Storage Format**:
   - Maybe tag stores RndB in a different byte order internally?
   - Maybe tag rotates RndB during storage and we need to account for that?

4. **Phase 1/Phase 2 Key Mismatch**:
   - Phase 1 works with ANY key - does it use a different key internally?
   - Maybe Phase 1 encrypts with tag's internal key (not the one we send)?
   - Maybe Phase 2 expects RndB' calculated from tag's internal key?
   - **CRITICAL**: If Phase 1 encrypts with different key than we think, our RndB decryption is wrong!

---

## Critical Insight: Phase 1/Phase 2 Key Relationship

**DISCOVERY**: Phase 1 works with ANY key (even obviously wrong ones)
- This suggests Phase 1 doesn't validate the key at all
- Phase 1 may encrypt RndB with its INTERNAL key (not the one we send)
- If true, we're decrypting Phase 1 response with wrong key → wrong RndB → wrong RndB'

**Hypothesis**: Phase 1 might be encrypting RndB with tag's internal factory key, regardless of what we send in the command. Then Phase 2 expects RndB' calculated from that same internal key.

**Test Needed**: Decrypt Phase 1 response with the key we used for Phase 1 vs. tag's internal key
- If decryption with our key produces garbage → tag uses different key internally
- If decryption with our key produces valid-looking RndB → key is correct, issue is rotation

**Seritag ISO Compliance**: If 100% compliant, this shouldn't happen - but HW 48.0 suggests modifications.

---

## Java Implementation Comparison

**Reference**: Working Java implementation (from user-provided code)

### Key Differences Found:

1. **AES Mode**: 
   - Java: `AES/CBC/NoPadding` with zero IV
   - Python: `AES.MODE_ECB`
   - **VERIFIED**: For single 16-byte blocks, CBC with zero IV = ECB ✅
   - **Conclusion**: Our mode choice is correct

2. **Rotation**:
   - Java: `ByteUtil.rotateLeft(b, 1)`
   - Python: `rndb[1:] + rndb[0:1]`
   - **Conclusion**: Both are left rotation by 1 byte ✅

3. **Key Usage**:
   - Java: Uses the provided `keyData` to decrypt Phase 1 response
   - Python: Uses `self.key` to decrypt Phase 1 response
   - **Conclusion**: Same approach ✅

### Critical Observation:

The Java implementation follows the exact same pattern we do:
- Phase 1: Get encrypted RndB
- Decrypt RndB with provided key
- Rotate RndB left by 1 byte
- Encrypt RndA || RndB' with provided key
- Send Phase 2

**This confirms our implementation matches a working reference!**

### Critical Uncertainty:

**We don't know if this is Seritag-specific!** We've only tested on Seritag tags.

**Possible Issues (not necessarily Seritag-specific):**

1. **Implementation Bug** (affects all tags):
   - Wrong key number selection
   - APDU format issue
   - Key not actually being used correctly

2. **Seritag-Specific Behavior**:
   - Different key derivation (tested, ruled out)
   - Different RndB rotation/storage internally
   - Phase 1 encryption uses different key than we think

**What We Need**:
- Test on standard NXP NTAG424 DNA tag to compare behavior
- Verify the Java implementation works on Seritag tags (or doesn't)
- Double-check our APDU construction against NXP spec byte-by-byte

---

## Hardware/Reader Investigation

**Reference**: [Arduino MFRC522 NTAG424DNA Implementation](https://github.com/Obsttube/MFRC522_NTAG424DNA)

### Key Differences:

1. **Hardware Stack**:
   - **Our Setup**: ACR122U → PC/SC (pyscard) → Escape Mode (`control()`) or Standard (`transmit()`)
   - **Arduino Reference**: MFRC522 → Direct hardware interface (no PC/SC abstraction)
   - **Impact**: PC/SC adds abstraction layer that could introduce timing/delays

2. **ACR122U Escape Mode**:
   - Uses `control(IOCTL_CCID_ESCAPE, apdu)` for proprietary commands
   - Manually parses response: `resp[:-2]` (data), `resp[-2]` (sw1), `resp[-1]` (sw2)
   - **Potential Issue**: Response parsing might miss edge cases or timing issues

3. **Reader-Specific Considerations**:
   - ACR122U firmware version differences
   - PC/SC driver differences (Windows vs Linux)
   - Escape mode vs transmit() mode inconsistencies
   - **Phase 2 Response**: 32 bytes encrypted data - reader might truncate or delay

### Potential Hardware/Reader Issues:

1. **Timing Issues**:
   - Delay between Phase 1 and Phase 2
   - Reader needs time to process Phase 1 before Phase 2
   - Arduino implementation might have different timing

2. **Response Parsing**:
   - Phase 2 returns 32 bytes + SW
   - Reader might not be delivering complete response
   - Escape mode response parsing might be incorrect

3. **PC/SC Abstraction**:
   - Standard `transmit()` might handle responses differently than `control()`
   - Escape mode might introduce delays or buffer issues

### Investigation Results:

1. ✅ **Response Parsing**: Verified correct - 32 bytes sent, SW correctly parsed
2. ✅ **Transmission Modes**: Tested both escape (control) and transmit - identical failures (SW=91AE)
3. ✅ **Timing Delays**: Tested delays (0ms, 10ms, 50ms, 100ms) - no improvement
4. ✅ **Fresh Phase 1**: Each Phase 2 test uses fresh Phase 1 - still fails

**Result**: Reader/Hardware is NOT the issue
- Both transmission modes fail identically
- Timing doesn't matter
- State management is correct

**Remaining Issue**: RndB' calculation doesn't match tag's expectation
- All tests return SW=91AE (Wrong RndB')
- Format is correct (not SW=911C)
- Rotation is correct (verified)
- Keys tested (all fail identically)

**SOLVED**: ✅✅✅ Authentication now works!

**Root Cause Identified**:
- **Issue**: Using ECB mode instead of CBC mode with zero IV
- **Arduino Implementation**: Uses CBC mode with zero IV (as shown in user-provided code)
- **NXP Spec Section 9.1.4**: States "Encryption and decryption are calculated using AES-128 according to the CBC mode of NIST SP800-38A"
- **Our Original Implementation**: Used ECB mode (incorrect!)

**Fix Applied**:
- Changed `_decrypt_rndb()` to use CBC mode with zero IV
- Changed `_encrypt_response()` to use CBC mode with zero IV  
- Changed `_parse_card_response()` to use CBC mode with zero IV
- Fixed status code check to accept both SW_OK (0x9000) and SW_OK_ALTERNATIVE (0x9100)

**Test Results**:
- ✅ Phase 1 authentication: SUCCESS
- ✅ Phase 2 authentication: SUCCESS
- ✅ Session keys derived correctly
- ✅ Transaction ID received from tag

**Key Learning**:
- For single 16-byte blocks (Phase 1 RndB): CBC with zero IV = ECB (equivalent)
- For 32-byte blocks (Phase 2 RndA||RndB'): CBC chains blocks differently than ECB
- This is why Phase 2 failed with SW=91AE (Wrong RndB') - the tag decrypted with CBC and got different plaintext than our ECB encryption

