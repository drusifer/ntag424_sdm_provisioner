# Seritag Protocol Differences Investigation

**Date**: Current session  
**Status**: 🔍 Active investigation into Seritag-specific protocol differences

---

## Summary

Investigating potential Seritag protocol differences that could explain Phase 2 authentication failures. Our implementation matches NXP spec exactly, so differences must be Seritag-specific.

---

## Known Seritag Differences

### ✅ **Confirmed**
1. **Hardware Version**: 48.0 (not NXP 4.2)
2. **Phase 1**: ✅ Works (standard protocol)
3. **Phase 2**: ❌ Fails with SW=91AE (Wrong RndB')
4. **Command 0x51**: Returns SW=91CA (Command Aborted) - Seritag-specific

### ❓ **Potential Differences (To Test)**
1. **Different Factory Keys**: Maybe non-zero keys or UID-based derivation
2. **LRP Authentication**: Uses same 0x71 command but PCDcap2.1 bit 1 = 1
3. **AuthenticateEV2NonFirst (0x77)**: Alternative authentication method
4. **Command 0x51**: Seritag-specific command after Phase 1
5. **PCDcap2 Configuration**: Different capability bytes in Phase 1
6. **Different Encryption Mode**: Maybe Seritag uses different padding/encryption

---

## Investigation Plan

### 1. **LRP Authentication Test**
**Rationale**: LRP uses same command (0x71) but requires PCDcap2.1 bit 1 = 1

**Test**: Phase 1 with PCDcap2 = [0x02] (LRP mode)

**Expected**: If Seritag is LRP-enabled, Phase 1 should return AuthMode=0x01 and different response

### 2. **AuthenticateEV2NonFirst (0x77)**
**Rationale**: Alternative authentication method - maybe Seritag requires this

**Test**: Use 0x77 instead of 0x71 for Phase 1

**Expected**: Might work if Seritag expects NonFirst flow

### 3. **Command 0x51 Variations**
**Rationale**: Seritag-specific command - might be alternative Phase 2

**Test**: Various formats:
- `90 51 00 00 00` - Basic
- `90 51 00 00 20 [32 bytes] 00` - With Phase 2 data
- `90 51 00 00 02 [KeyNo] 00 00` - Like Phase 1
- Different P1/P2 values

### 4. **PCDcap2 Variations**
**Rationale**: Phase 1 accepts PCDcap2 bytes - maybe Seritag needs specific values

**Test**: Phase 1 with different PCDcap2 configurations:
- Standard: LenCap=0x00 (no PCDcap2)
- LRP: LenCap=0x01, PCDcap2=[0x02]
- Custom: Various PCDcap2 values

### 5. **Key Variations**
**Rationale**: Maybe Seritag uses different factory keys

**Test**: Try keys based on:
- UID-based derivation
- All-ones key
- Known Seritag patterns
- Different key numbers

### 6. **Phase 2 Command Variations**
**Rationale**: Maybe Phase 2 needs different format

**Test**: 
- Different INS byte (maybe 0x77?)
- Different P1/P2 values
- Different data format

---

## Test Scripts Needed

1. `test_lrp_authentication.py` - Test LRP mode
2. `test_ev2_nonfirst.py` - Test 0x77 authentication
3. `test_command_51_variations.py` - Comprehensive 0x51 test
4. `test_pcdcap2_variations.py` - Different PCDcap2 configs
5. `test_key_variations.py` - Different key formats
6. `test_phase2_variations_comprehensive.py` - All Phase 2 format variations

---

## Resources

- **Seritag SVG Pages**: `investigation_ref/seritag_svg/` (9 pages)
- **Investigation Reference**: `investigation_ref/seritag_investigation_reference.md`
- **NXP Spec**: `docs/seritag/NT4H2421Gx.md`

---

## Next Steps

1. **Review Seritag SVG pages** for protocol hints
2. **Test LRP authentication** (most likely alternative)
3. **Test Command 0x51** variations systematically
4. **Test AuthenticateEV2NonFirst (0x77)**
5. **Explore key derivation** possibilities

---

**Status**: 🔍 Ready to test potential differences

