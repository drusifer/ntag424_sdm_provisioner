# RndB Rotation Investigation

**Date**: Current session  
**Status**: ⏳ Investigating if RndB extraction/rotation is correct

---

## Summary

Investigation of whether we're correctly extracting and rotating RndB from Phase 1 response.

---

## Current Implementation

### **Phase 1 Response Handling**
```python
# Phase 1 returns SW=91AF with encrypted RndB
# We now try to read additional frames
full_response = bytearray(data)

while (sw1, sw2) == SW_ADDITIONAL_FRAME:
    # Send GetAdditionalFrame
    af_apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
    data, sw1, sw2 = self.send_apdu(connection, af_apdu)
    full_response.extend(data)

# Use first 16 bytes as encrypted RndB
encrypted_rndb = bytes(full_response[:16])
```

### **RndB Rotation**
```python
# Decrypt RndB
rndb = cipher.decrypt(encrypted_rndb)

# Rotate RndB (left shift 1 byte)
rndb_rotated = rndb[1:] + rndb[0:1]
```

---

## Potential Issues

### **1. RndB Location**
- **Assumption**: First 16 bytes = encrypted RndB
- **Question**: What if Phase 1 returns more data?
- **Question**: What if encrypted RndB is in a different location?

### **2. Rotation Direction**
- **Spec says**: `rotl(RndB)` = rotate left
- **Implementation**: `rndb[1:] + rndb[0:1]` = left rotation ✓
- **Status**: Matches spec

### **3. Rotation Amount**
- **Spec says**: Left by 1 byte
- **Implementation**: 1 byte ✓
- **Status**: Matches spec

### **4. Multi-Frame Handling**
- **Phase 1**: Returns SW=91AF (Additional Frame)
- **We now read**: Additional frames
- **Question**: Do we read enough frames?
- **Question**: Is encrypted RndB complete after first frame?

---

## Next Steps

1. **Verify Phase 1 response**: See what Phase 1 actually returns (all frames)
2. **Verify RndB extraction**: Ensure encrypted RndB is 16 bytes
3. **Test rotation**: Verify rotation produces expected result
4. **Check for Seritag differences**: Maybe Seritag uses different format?

---

## Related Files

- **Auth Session**: `src/ntag424_sdm_provisioner/crypto/auth_session.py`
- **Commands**: `src/ntag424_sdm_provisioner/commands/sdm_commands.py`
- **Test Script**: `examples/seritag/test_phase1_response_data.py`

---

**Status**: ⏳ Need to test Phase 1 response when delay expires

