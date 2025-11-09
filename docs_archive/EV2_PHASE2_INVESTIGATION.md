# EV2 Phase 2 Authentication Investigation

**Date**: Current session  
**Status**: ⏳ **IN PROGRESS** - Phase 2 still fails, investigating variations

---

## Summary

**EV2 Phase 2 authentication still fails** (SW=91AE) with our protocol fixes. Investigating alternative approaches and command variations.

---

## Current Status

### ✅ **What Works**
- **Phase 1**: ✅ Works perfectly (gets encrypted RndB challenge)
- **NDEF Read/Write**: ✅ Works without authentication
- **Protocol Fixes**: ✅ All command formats correct (CLA, file selection, etc.)

### ❌ **What Fails**
- **Phase 2**: ❌ Fails with SW=91AE (Authentication Error)
- **SDM/SUN Configuration**: ❌ Requires authentication (Change access right = KEY_0)

---

## Protocol Fixes Applied

### 1. **CLA Byte Fixed**
- ISO commands: CLA=00 (ISO 7816-4 standard)
- Proprietary commands: CLA=90 (NTAG424 specific)

### 2. **File Selection Fixed**
- P1=0x02 (select EF under current DF) instead of P1=0x04

### 3. **Command Format Fixed**
- All APDU formats match NXP specification

---

## Phase 2 Test Results

### **Test 1: Standard Phase 2 Protocol**
- **Format**: `E(Kx, RndA || RndB')` where RndB' = left-rotated RndB
- **Result**: ❌ SW=91AE (Authentication Error)
- **Status**: Standard format doesn't work on Seritag

### **Test 2: Reverse Order (RndB' || RndA)**
- **Format**: `E(Kx, RndB' || RndA)`
- **Result**: ❌ SW=911C (Illegal Command Code)
- **Status**: Wrong data format

### **Test 3: Right Rotate RndB**
- **Format**: Right-rotate instead of left-rotate
- **Result**: ❌ SW=911C (Illegal Command Code)
- **Status**: Wrong rotation direction

### **Test 4: Command 0x51 After Phase 1**
- **Format**: Various 0x51 command attempts
- **Results**:
  - `90 51 00 00 00`: SW=91CA ✅ (Command Aborted - recognized!)
  - Different P1/P2: SW=6A86 (Wrong P1/P2)
  - With data: SW=917E (Length Error)
  - **Timing variations**:
    - 0.1s delay: SW=91CA (Command Aborted)
    - 0.5s+ delay: SW=91AE (Authentication Error - state expired!)
- **Status**: Command 0x51 exists and is recognized. **Phase 1 state expires after ~0.5s**

---

## Key Findings

### **Command 0x51 Recognition**
- **SW=91CA** (Command Aborted) indicates command **exists and is recognized**
- This is different from SW=911C (Illegal Command Code)
- **Implication**: Command 0x51 may be a Seritag-specific authentication method
- **Status**: No working format found yet, but command is recognized

### **Authentication Delay (SW=91AD)**
- **Occurs after failed Phase 2 attempts**
- **Pattern observed**: Delay on every other authentication attempt
- **Behavior**: Delay counter increments with failed attempts
- **Conclusion**: Tag enforces rate limiting on authentication attempts
- **Workaround**: Fresh tap resets delay counter, or wait 1+ seconds

### **Phase 1 State Expiration**
- **0.1s after Phase 1**: SW=91CA (Command Aborted)
- **0.5s+ after Phase 1**: SW=91AE (Authentication Error)
- **Conclusion**: Phase 1 authentication state **expires after ~0.5 seconds**!
- **Implication**: Must send Phase 2 **immediately** after Phase 1 (within ~0.3s)

### **Phase 2 Protocol Differences**
- Standard NXP Phase 2 doesn't work (SW=91AE)
- Alternative formats don't work (SW=911C)
- **Conclusion**: Seritag uses modified Phase 2 protocol (unknown modification)
- **Timing**: Phase 2 must be sent immediately after Phase 1 (no delay)

---

## Next Steps

### **1. Investigate Command 0x51 Further**
- Test with different P1/P2 values
- Test with Phase 1 challenge data
- Test with timing variations
- Test as multi-frame command sequence

### **2. Analyze Seritag Documentation**
- Review SVG authentication pages in `investigation_ref/`
- Look for Phase 2 protocol differences
- Check for Seritag-specific commands

### **3. Test Alternative Authentication Methods**
- Try EV1 authentication (legacy protocol)
- Try different key formats
- Try authentication with different preconditions

### **4. Test Command Sequences**
- Phase 1 → 0x51 (instead of Phase 2)
- Phase 1 → Wait → 0x51
- Phase 1 → 0x51 → Phase 2

---

## Status Words Observed

| Status Word | Meaning | Context |
|------------|---------|---------|
| **91AE** | Authentication Error | Phase 2 authentication fails |
| **91CA** | Command Aborted / Wrong Session State | Command 0x51 recognized but wrong state |
| **911C** | Illegal Command Code | Wrong command format |
| **917E** | Length Error | Wrong data length |
| **9000** | Success | Phase 1 works |

---

## Working Solution: Static URLs

**While Phase 2 investigation continues, we can:**
- ✅ Provision static URLs without authentication
- ✅ Use NDEF read/write for basic game coin functionality
- ✅ Continue Phase 2 investigation in parallel

See `STATIC_URL_PROVISIONING.md` for details on static URL provisioning.

---

## Files

- **Investigation Script**: `examples/seritag/test_ev2_phase2_detailed.py`
- **Test Script**: `examples/seritag/test_ev2_with_fixed_protocol.py`
- **Command 0x51 Test**: `examples/seritag/test_0x51_detailed.py`
- **Comprehensive Test**: `examples/seritag/test_all_authentication_protocols.py` ⭐ **NEW**
- **Reference**: `investigation_ref/seritag_investigation_reference.md`

---

## Comprehensive Authentication Test

**Created**: `examples/seritag/test_all_authentication_protocols.py`

This test covers **ALL** possible authentication protocols:

### **1. EV2 Standard Protocol**
- Standard Phase 1 + Phase 2
- Format: `E(Kx, RndA || RndB')`

### **2. EV2 Variations**
- No rotation (RndB as-is)
- Right rotate RndB
- Rotate by 2 bytes
- Reverse RndA
- All tested with fresh Phase 1

### **3. LRP Authentication**
- Lightweight Remote Protocol
- Command 0x71 with PCDcap2 bit 1 set
- Uses MAC instead of encryption

### **4. Legacy EV1 Authentication**
- Command 0x70 (if exists)
- Various parameter combinations

### **5. Command 0x51 Sequences**
- Before Phase 1
- Immediately after Phase 1
- With challenge data

### **6. Alternative Commands**
- Commands 0x72-0x79
- AuthenticateEV2NonFirst (0x72)
- AuthenticateLRPFirst (0x73)
- AuthenticateLRPNonFirst (0x74)
- Other experimental codes

---

**Status**: ⏳ Investigation ongoing - Phase 2 protocol modification unknown  
**Next**: Run comprehensive test when tag is available, analyze results

