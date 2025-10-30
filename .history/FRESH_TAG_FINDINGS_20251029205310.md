# Fresh Tag Investigation Findings

**Date**: Current session  
**Status**: ✅ **Phase 1 verified, Phase 2 still fails**

---

## Summary

Testing with a fresh tag (clean delay counter) revealed that **Phase 1 is correct**, but **Phase 2 protocol differs for Seritag**.

---

## Key Findings

### ✅ **Phase 1: CORRECT**

1. **Response Format**
   - Returns SW=91AF (Additional Frame) with exactly **16 bytes** (encrypted RndB)
   - **Complete with those 16 bytes** - no additional frames needed
   - When we try GetAdditionalFrame, we get SW=917E (Length Error)
   - **Conclusion**: Phase 1 is complete with just the 16 bytes

2. **RndB Extraction**
   - ✅ First 16 bytes = encrypted RndB (correct)
   - ✅ Extraction is working as expected
   - No additional data to parse

3. **RndB Rotation**
   - ✅ Rotation is correct: `rndb[1:] + rndb[0:1]` (left by 1 byte)
   - ✅ Matches NXP spec: `rotl(RndB)`
   - Rotation logic is verified

### ❌ **Phase 2: Still Fails**

1. **Response**
   - Returns SW=91AE (Authentication Error)
   - Protocol format still incorrect for Seritag

2. **Multi-Frame Handling**
   - Phase 2 doesn't return SW=91AF (no additional frames)
   - Multi-frame handling isn't the issue

3. **Root Cause**
   - Phase 2 protocol format differs for Seritag
   - Not a multi-frame issue
   - Not an RndB rotation issue
   - **Likely**: Encryption format, data format, or command format

---

## Test Results

### **Phase 1 Test**
```
Command: 90 71 00 00 02 00 00 00
Response: SW=91AF, Data=16 bytes
Encrypted RndB: 65E0B1DA56238EF8A2D4406B76E643AB

Decrypted RndB: 3F1402B7A78B6D66BB33E975FADA87D0
Rotated RndB:  1402B7A78B6D66BB33E975FADA87D03F
                (first byte '3F' moved to end)
```

### **Phase 2 Test**
```
Command: 90 AF 00 00 20 [E(Kx, RndA || RndB')] 00
Response: SW=91AE (Authentication Error)
Conclusion: Protocol format incorrect
```

---

## Implications

### **What We Know**
1. ✅ Phase 1 protocol is correct
2. ✅ RndB extraction is correct
3. ✅ RndB rotation is correct
4. ❌ Phase 2 protocol is wrong

### **What We Need**
1. ⏳ Determine correct Phase 2 protocol for Seritag
2. ⏳ Test different encryption formats
3. ⏳ Test different data formats
4. ⏳ Test different command formats

---

## Next Steps

1. **Investigate Phase 2 Data Format**
   - Test different encryption modes
   - Test different data ordering
   - Test different padding (if any)

2. **Review Seritag Documentation**
   - Check for Phase 2 protocol differences
   - Look for Seritag-specific authentication methods

3. **Test Phase 2 Variations**
   - Different data formats (RndB' || RndA?)
   - Different encryption modes
   - Different command formats

---

## Related Files

- **Test Script**: `examples/seritag/test_fresh_tag.py`
- **Auth Session**: `src/ntag424_sdm_provisioner/crypto/auth_session.py`
- **Commands**: `src/ntag424_sdm_provisioner/commands/sdm_commands.py`
- **RndB Investigation**: `RNDB_ROTATION_INVESTIGATION.md`

---

**Status**: ✅ Phase 1 verified, ⏳ Phase 2 protocol investigation continues

