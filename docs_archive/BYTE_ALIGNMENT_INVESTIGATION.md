# Byte Alignment Investigation

**Date**: Current session  
**Status**: ✅ APDU structure correct - alignment not the issue

---

## Summary

Investigated byte alignment issues for Phase 2 authentication. **APDU structure is correct**, and alignment is not the cause of SW=91AE failures.

---

## APDU Structure Analysis

### Current Implementation

**Phase 2 APDU**:
```
90 AF 00 00 20 [32 bytes data] 00
│  │  │  │  │  └─ Encrypted data (E(Kx, RndA || RndB'))
│  │  │  │  └──── Lc = 0x20 (32 bytes - single byte encoding)
│  │  │  └─────── P2 = 0x00
│  │  └────────── P1 = 0x00
│  └───────────── INS = 0xAF (Additional Frame)
└──────────────── CLA = 0x90
```

**Total length**: 38 bytes
- Header: 5 bytes (CLA, INS, P1, P2, Lc)
- Data: 32 bytes
- Le: 1 byte

---

## Alignment Checks

### ✅ Length Field Encoding
- **Lc = 32 (0x20)**: Single byte encoding ✅
- **No extended length needed**: Lc < 256 ✅
- **Matches spec**: Table 28 shows Lc = 20h (32 bytes) ✅

### ✅ Data Alignment
- **Encrypted data**: 32 bytes = exactly 2 AES blocks ✅
- **Each block**: 16 bytes (aligned) ✅
- **Encryption**: ECB mode, no padding ✅

### ⚠️ APDU Alignment
- **Total APDU**: 38 bytes
- **Alignment to 4 bytes**: ❌ (38 % 4 = 2)
- **Alignment to 8 bytes**: ❌ (38 % 8 = 6)
- **Alignment to 16 bytes**: ❌ (38 % 16 = 6)

**Note**: Spec does **NOT** require APDU-level alignment. Only encrypted data must be 16-byte aligned, which it is.

---

## Escape Mode Comparison

Tested Phase 2 with both transmission paths:

| Mode | Path | Result |
|------|------|--------|
| Escape | `control()` | SW=91AE ❌ |
| No-Escape | `transmit()` | SW=91AE ❌ |

**Conclusion**: Both paths fail identically, so alignment/padding differences between escape/no-escape are not the issue.

---

## Findings

### ✅ **What's Correct**
1. **Length encoding**: Single byte (0x20) ✅
2. **Data structure**: 32 bytes = 2 AES blocks ✅
3. **APDU format**: Matches spec exactly ✅
4. **Byte order**: MSB first (as per spec) ✅

### ❌ **What's Not the Issue**
1. **APDU alignment**: Not required by spec
2. **Reader padding**: Both paths fail same way
3. **Length encoding**: Correct (no extended length needed)
4. **Data encryption**: Correct (16-byte aligned blocks)

---

## Conclusion

**Byte alignment is NOT the issue**. Our implementation:
- ✅ Matches NXP spec exactly
- ✅ Uses correct length encoding (single byte)
- ✅ Sends correctly aligned encrypted data (32 bytes = 2 blocks)
- ✅ Fails identically with both escape/no-escape paths

**Root cause**: Seritag protocol differences (key, encryption, or command format), not alignment/padding issues.

---

## Related Files

- `examples/seritag/test_phase2_apdu_structure.py` - APDU structure verification
- `examples/seritag/test_phase2_byte_alignment.py` - Alignment testing
- `examples/seritag/test_phase2_escape_toggle.py` - Escape mode comparison
- `IMPLEMENTATION_VERIFICATION.md` - Full implementation verification

---

**Status**: ✅ Alignment verified - issue is elsewhere

