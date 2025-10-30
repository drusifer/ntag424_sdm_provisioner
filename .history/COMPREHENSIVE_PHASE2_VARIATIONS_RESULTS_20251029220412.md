# Comprehensive Phase 2 Authentication Variations Test Results

## Date: 2025-10-29

## Test Setup

- **Reader**: ACR122U (EscapeCommandEnable = 1, confirmed)
- **Tag**: Seritag NTAG424 DNA
- **Test Script**: `examples/seritag/test_phase2_comprehensive_variations.py`
- **Total Tests**: 15 combinations

## Tested Variations

### Key Variations
1. **Factory Key (All Zeros)**: `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`
2. **All Ones Key**: `FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF`
3. **Weak Key**: `01 23 45 67 89 AB CD EF 01 23 45 67 89 AB CD EF`
4. **UID-Based Keys**: Could not test (GetCardUID returned SW=91CA)

### Rotation Variations
1. **Standard Left Rotate (1 byte)**: NXP spec - rotate left by 1 byte
2. **No Rotation**: Use RndB as-is
3. **Right Rotate (1 byte)**: Rotate right by 1 byte
4. **Left Rotate (2 bytes)**: Rotate left by 2 bytes
5. **Left Rotate (4 bytes)**: Rotate left by 4 bytes

## Results Summary

| Test # | Key | Rotation | Result | SW | Notes |
|--------|-----|----------|--------|----|----|
| 1 | Factory (All Zeros) | Standard Left (1 byte) | FAIL | 91AE | Format accepted, Wrong RndB' |
| 2 | Factory (All Zeros) | No Rotation | FAIL | 911C | Format rejected |
| 3 | Factory (All Zeros) | Right Rotate (1 byte) | FAIL | 911C | Format rejected |
| 4 | Factory (All Zeros) | Left Rotate (2 bytes) | FAIL | 911C | Format rejected |
| 5 | Factory (All Zeros) | Left Rotate (4 bytes) | FAIL | 911C | Format rejected |
| 6 | All Ones | Standard Left (1 byte) | FAIL | 91AE | Format accepted, Wrong RndB' |
| 7 | All Ones | No Rotation | FAIL | 911C | Format rejected |
| 8 | All Ones | Right Rotate (1 byte) | FAIL | 911C | Format rejected |
| 9 | All Ones | Left Rotate (2 bytes) | FAIL | 911C | Format rejected |
| 10 | All Ones | Left Rotate (4 bytes) | FAIL | 911C | Format rejected |
| 11 | Weak Key | Standard Left (1 byte) | FAIL | 91AE | Format accepted, Wrong RndB' |
| 12 | Weak Key | No Rotation | FAIL | 911C | Format rejected |
| 13 | Weak Key | Right Rotate (1 byte) | FAIL | 911C | Format rejected |
| 14 | Weak Key | Left Rotate (2 bytes) | FAIL | 911C | Format rejected |
| 15 | Weak Key | Left Rotate (4 bytes) | FAIL | 911C | Format rejected |

## Key Findings

### 1. Standard Left Rotate is Correct Format
- **Evidence**: Standard left rotate (1 byte) is the ONLY rotation that passes format check (SW=91AE vs SW=911C)
- **Conclusion**: NXP spec rotation method is correct for Seritag

### 2. RndB' Calculation Issue
- **Evidence**: ALL tests with standard left rotate return SW=91AE (Wrong RndB')
- **Pattern**: Same error across all keys tested
- **Conclusion**: The issue is NOT the rotation method, but either:
  - Wrong RndB extraction from Phase 1
  - Wrong Phase 1 decryption (key issue)
  - Wrong Phase 2 encryption format
  - Missing Seritag-specific step

### 3. Command Format Validation
- **Evidence**: Non-standard rotations return SW=911C (Illegal Command Code)
- **Conclusion**: Seritag validates the Phase 2 data format before authentication
- **Implication**: The tag expects exactly 32 bytes: `E(Kx, RndA || RndB')` where RndB' = RndB rotated left by 1 byte

### 4. Key Testing Results
- **Factory Key (All Zeros)**: SW=91AE (Wrong RndB')
- **All Ones Key**: SW=91AE (Wrong RndB')
- **Weak Key**: SW=91AE (Wrong RndB')
- **Conclusion**: None of the tested keys work, but all pass format check
- **Implication**: The factory key might be different, OR the Phase 1 decryption is wrong

## Error Code Breakdown

- **SW=91AE (Authentication Error - Wrong RndB')**: 3 times
  - Always with standard left rotate (1 byte)
  - Format accepted, but RndB' doesn't match tag's expectation
  
- **SW=911C (Illegal Command Code)**: 12 times
  - All non-standard rotations
  - Command format rejected before authentication

## What This Tells Us

1. **Protocol Format is Correct**: Standard left rotate (1 byte) is accepted by Seritag
2. **Phase 2 APDU Format is Correct**: The command structure (90 AF 00 00 20 [32 bytes] 00) is correct
3. **RndB' Calculation is Wrong**: The tag can decrypt our Phase 2 data, but RndB' doesn't match

## Next Steps to Investigate

### 1. Verify Phase 1 RndB Extraction
- **Hypothesis**: Maybe Phase 1 doesn't return plain RndB, but something else?
- **Test**: Inspect Phase 1 response byte-by-byte
- **Action**: Add logging to show exactly what Phase 1 returns

### 2. Verify Phase 1 Decryption
- **Hypothesis**: Maybe Phase 1 encryption isn't AES-ECB?
- **Test**: Try different decryption methods (CBC, CTR, etc.)
- **Action**: Test Phase 1 decryption variations

### 3. Verify RndB Rotation
- **Hypothesis**: Maybe the rotation is applied differently?
- **Test**: Verify byte-by-byte rotation math
- **Action**: Add detailed logging showing rotation calculation

### 4. Verify Phase 2 Encryption
- **Hypothesis**: Maybe Phase 2 encryption needs padding or different mode?
- **Test**: Try CBC, CTR, or other modes
- **Action**: Test different encryption formats (but this is less likely given format check passes)

### 5. Test UID-Based Keys
- **Hypothesis**: Maybe factory key is UID-based?
- **Test**: Get UID first (need to complete/abort Phase 1 transaction)
- **Action**: Modify test to get UID before starting authentication tests

### 6. Review Seritag-Specific Documentation
- **Hypothesis**: Maybe Seritag has custom protocol documented?
- **Test**: Search for Seritag NTAG424 documentation
- **Action**: Review `docs/seritag/` and search online

## Conclusions

1. **Registry Key Fix Was Necessary**: EscapeCommandEnable registry key was missing - this is now fixed
2. **Format Validation Works**: Seritag validates Phase 2 format correctly
3. **Protocol Steps Are Correct**: Our implementation matches NXP spec for format
4. **Core Issue**: RndB' calculation or key derivation is wrong for Seritag

The fact that ALL keys return the same error (SW=91AE) with standard left rotate suggests:
- Either the factory key is wrong (but we've tried multiple)
- Or there's a Seritag-specific RndB extraction/rotation/encryption method

## Recommendations

1. **Focus on Phase 1**: Deep dive into Phase 1 response extraction and decryption
2. **Get UID**: Find way to get UID without Phase 1 transaction conflict
3. **Seritag Documentation**: Search for official Seritag protocol documentation
4. **Alternative Approaches**: Consider static URL provisioning as workaround while investigating

