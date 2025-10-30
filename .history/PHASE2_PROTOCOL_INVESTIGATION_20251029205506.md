# Phase 2 Protocol Investigation

**Date**: Current session  
**Status**: ⏳ **IN PROGRESS** - Testing variations

---

## Summary

Phase 1 is **verified correct**, but Phase 2 fails with SW=91AE. Testing various protocol variations to find what Seritag expects.

---

## Current Status

### ✅ **What Works**
- **Phase 1**: ✅ Correct (returns SW=91AF with 16 bytes, no additional frames needed)
- **RndB Extraction**: ✅ Correct (first 16 bytes = encrypted RndB)
- **RndB Rotation**: ✅ Correct (left by 1 byte: `rndb[1:] + rndb[0:1]`)

### ❌ **What Fails**
- **Phase 2 Standard**: SW=91CA (Command Aborted) ⚠️ **Interesting!**
- **Phase 2 Variations**: SW=91AE (Authentication Error)

---

## Phase 2 Variation Test Results

### **Test 1: Standard (RndA || RndB')**
- **Format**: `E(Kx, RndA || RndB')` where RndB' = left-rotated RndB
- **Result**: SW=91CA (Command Aborted) ⚠️ **Different from others!**
- **Observation**: Not SW=91AE like other variations
- **Implication**: Command sequence or state issue?

### **Test 2: Reverse (RndB' || RndA)**
- **Format**: `E(Kx, RndB' || RndA)`
- **Result**: SW=91AE (Authentication Error)
- **Conclusion**: Order matters, RndA must come first

### **Test 3: No Rotation (RndA || RndB)**
- **Format**: `E(Kx, RndA || RndB)` (no rotation)
- **Result**: SW=91AE (Authentication Error)
- **Conclusion**: Rotation is required

### **Test 4: Right Rotate (RndA || RndB_right)**
- **Format**: `E(Kx, RndA || RndB_right)` where RndB_right = right-rotated RndB
- **Result**: SW=91AE (Authentication Error)
- **Conclusion**: Left rotation is correct, right rotation doesn't work

---

## Key Findings

### **1. Standard Protocol Gets Different Error**
- Standard protocol returns **SW=91CA** (Command Aborted)
- Other variations return **SW=91AE** (Authentication Error)
- **This is significant!** SW=91CA means "Previous Command was not fully completed"

### **2. Data Format Confirmed**
- ✅ RndA must come first (Reverse order fails)
- ✅ Rotation is required (No rotation fails)
- ✅ Left rotation is correct (Right rotation fails)

### **3. Command Sequence Issue?**
- SW=91CA on Standard suggests Phase 1 might not be "complete"
- Or Phase 2 command format/sequence is wrong

---

## SW=91CA Analysis

### **What SW=91CA Means**
- **SW=91CA**: "Previous Command was not fully completed. Not all Frames were requested or provided."
- This suggests Phase 1 transaction wasn't properly completed

### **Possible Causes**
1. **Phase 1 needs completion**
   - Phase 1 returns SW=91AF (Additional Frame)
   - Maybe we need to send GetAdditionalFrame to complete Phase 1?
   - But test showed SW=917E when we try that...

2. **Phase 2 command format wrong**
   - Maybe Phase 2 needs different command format?
   - Maybe it needs to be sent as continuation of Phase 1?

3. **State management issue**
   - Tag might be in wrong state
   - Maybe need to reset state somehow?

---

## Next Steps

### **Immediate**
1. **Investigate SW=91CA on Standard**
   - Why different from other variations?
   - Check Phase 1 completion sequence
   - Test if GetAdditionalFrame after Phase 1 helps

2. **Test Phase 2 as Continuation**
   - Maybe Phase 2 should be sent without Le?
   - Maybe Phase 2 command format is different?
   - Test chained frame format

3. **Review Seritag Documentation**
   - Check for Phase 2 protocol differences
   - Look for command sequence requirements

### **Alternative Path**
- Continue with **static URL provisioning** (works now)
- Investigation can continue in parallel

---

## Related Files

- **Variation Test**: `examples/seritag/test_phase2_variations.py`
- **Fresh Tag Test**: `examples/seritag/test_fresh_tag.py`
- **Auth Session**: `src/ntag424_sdm_provisioner/crypto/auth_session.py`
- **Findings**: `FRESH_TAG_FINDINGS.md`

---

**Status**: ⏳ All variations return SW=91AE - investigating Phase 2 protocol differences

---

## Update: Variation Test Results

### **Test Results** (fresh tag for each variation needed)

1. **Standard (RndA || RndB')**
   - Phase 1: SW=91CA (Command Aborted)
   - **Key**: After previous Phase 2 failure, Phase 1 returns SW=91CA
   - Need fresh tag to test Standard

2. **Reverse (RndB' || RndA)**
   - Phase 1: ✅ Success
   - Phase 2: SW=91AE (Authentication Error)
   - Data order wrong

3. **No Rotation (RndA || RndB)**
   - Phase 1: ✅ Success
   - Phase 2: SW=91AE (Authentication Error)
   - Rotation required

4. **Right Rotate (RndA || RndB_right)**
   - Phase 1: ✅ Success
   - Phase 2: SW=91AE (Authentication Error)
   - Left rotation correct

### **Key Finding**
- After Phase 2 failure, tag won't accept another Phase 1 (SW=91CA)
- Need fresh tag for each Phase 2 variation
- Standard protocol format likely correct, but needs fresh tag to test

