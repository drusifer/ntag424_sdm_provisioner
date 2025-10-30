# Seritag Investigation Status

**Date**: Current session  
**Status**: 🔍 Active investigation - multiple paths explored

---

## Summary

Phase 2 authentication fails with SW=91AE (Wrong RndB') despite our implementation matching NXP spec exactly. Investigating Seritag-specific protocol differences.

---

## What We've Ruled Out ✅

1. **✅ Command Format**: Matches spec exactly (90 AF 00 00 20 [32 bytes] 00)
2. **✅ Encryption Format**: Correct (32 bytes = 2 AES blocks in ECB)
3. **✅ RndB Rotation**: Correct (left by 1 byte)
4. **✅ Escape Mode**: Both escape/no-escape fail identically
5. **✅ Byte Alignment**: Not the issue
6. **✅ LRP Authentication**: SW=917E (Length Error) - format incorrect or not enabled
7. **✅ AuthenticateEV2NonFirst (0x77)**: 
   - SW=919D (Permission Denied) when used directly
   - SW=91CA (Command Aborted) when used after Phase 1
   - Requires completed transaction (Phase 1+2 done)

---

## Current Findings 🔍

### **Phase 1**: ✅ Works
- Standard EV2First (0x71) works perfectly
- Returns SW=91AF with 16 bytes encrypted RndB
- RndB extraction/rotation verified correct

### **Phase 2**: ❌ Fails with SW=91AE
- **Error**: "Wrong RndB'" (Authentication Error)
- Our implementation matches spec exactly
- All variations tested fail:
  - Standard format: SW=91AE
  - Data order variations: SW=91AE
  - Rotation variations: SW=91AE

### **Command 0x51**: ⚠️ Recognized but format unknown
- Returns SW=91CA (Command Aborted) - command exists
- With Phase 2 data: SW=91CA
- With no data: SW=91AE (Authentication Error)
- **Note**: SW=91AE suggests auth-related function

---

## Remaining Investigation Paths

### 1. **Key Variations** 🔑
- Different factory keys (not all zeros)
- UID-based key derivation
- Key number variations (already tried 0-4)
- Seritag-specific key derivation

### 2. **Command 0x51 Deep Dive** 🔬
- Might be alternative Phase 2 format
- Test different data formats
- Test with different transaction states
- Analyze response structure

### 3. **Seritag SVG Pages Review** 📖
- `investigation_ref/seritag_svg/` contains 9 pages
- May reveal Seritag-specific protocol differences
- Should review for authentication hints

### 4. **Phase 2 Data Format Variations** 🔄
- Maybe Seritag expects different encryption format
- Different padding/alignment requirements
- Different block structure

### 5. **Transaction State Issues** 🔄
- Maybe Phase 1 establishes wrong state
- Maybe need to complete Phase 1 differently
- Maybe tag expects different command sequence

---

## Next Steps

1. **Review Seritag SVG pages** (highest priority - may reveal protocol differences)
2. **Test Command 0x51 systematically** (might be alternative Phase 2)
3. **Test key variations** (UID-based, all-ones, etc.)
4. **Test Phase 2 with different encryption formats**
5. **Contact Seritag** for official documentation

---

## Test Scripts Created

- ✅ `test_lrp_and_alternatives.py` - LRP, 0x77, 0x51 tests
- ✅ `test_ev2_then_nonfirst.py` - 0x77 after Phase 1
- ✅ `test_phase2_escape_toggle.py` - Escape mode comparison
- ✅ `test_phase2_byte_alignment.py` - Alignment testing
- ✅ `test_phase2_command_format.py` - Format verification
- ✅ `test_phase2_encryption_format.py` - Encryption verification

---

**Status**: 🔍 Multiple paths ruled out - continuing investigation

