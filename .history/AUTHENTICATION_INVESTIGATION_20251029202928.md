# Comprehensive Authentication Investigation

**Date**: Current session  
**Status**: ⏳ **IN PROGRESS** - All protocols under investigation

---

## Summary

Comprehensive investigation of **ALL** possible authentication protocols on Seritag NTAG424 DNA tags, including EV2, EV1, LRP, and alternative methods.

---

## Test Coverage

### **Protocols Under Investigation**

1. **EV2 Standard** ✅ Tested
   - Phase 1: Command 0x71
   - Phase 2: Command 0xAF
   - Format: `E(Kx, RndA || RndB')`
   - Status: ❌ Fails with SW=91AE

2. **EV2 Variations** ✅ Tested
   - No rotation (RndB as-is)
   - Right rotate RndB
   - Rotate by 2 bytes
   - Reverse RndA
   - Status: ❌ All variations fail

3. **LRP Authentication** ✅ Tested
   - Command 0x71 with PCDcap2 bit 1 set
   - Lightweight Remote Protocol
   - Uses MAC instead of encryption
   - Status: ⏳ Testing...

4. **Legacy EV1** ✅ Tested
   - Command 0x70 (if exists)
   - Various parameter combinations
   - Status: ⏳ Testing...

5. **Command 0x51** ✅ Tested
   - Recognized (SW=91CA)
   - Tested with various sequences
   - Status: ⏳ Parameters unknown

6. **Alternative Commands** ✅ Tested
   - Commands 0x72-0x79
   - AuthenticateEV2NonFirst (0x72)
   - AuthenticateLRPFirst (0x73)
   - AuthenticateLRPNonFirst (0x74)
   - Status: ⏳ Testing...

---

## Test Script

**File**: `examples/seritag/test_all_authentication_protocols.py`

### **Usage**
```bash
python examples/seritag/test_all_authentication_protocols.py
```

### **What It Tests**

1. **EV2 Standard Protocol**
   - Complete Phase 1 + Phase 2 flow
   - Standard encryption format

2. **EV2 Protocol Variations**
   - Different RndB rotation methods
   - Different data formats
   - All tested with fresh Phase 1

3. **LRP Authentication**
   - Request LRP mode (PCDcap2 bit 1 set)
   - Attempt Phase 2 with MAC

4. **Legacy EV1 Authentication**
   - Command 0x70 basic
   - Command 0x70 with KeyNo
   - Command 0x70 with data

5. **Command 0x51 Sequences**
   - Before Phase 1
   - Immediately after Phase 1
   - With challenge data

6. **Alternative Commands**
   - Commands 0x72-0x79 systematically
   - Checks for recognition vs support

---

## Current Findings

### ✅ **What Works**
- **Phase 1**: ✅ Works perfectly (gets encrypted RndB challenge)
- **NDEF Read/Write**: ✅ Works without authentication

### ❌ **What Fails**
- **EV2 Phase 2**: ❌ All variations return SW=91AE
- **LRP**: ⏳ Testing...
- **EV1**: ⏳ Testing...
- **Command 0x51**: ⏳ Parameters unknown

### **Key Discoveries**

1. **Phase 1 State Expiration**
   - Expires after ~0.5 seconds
   - Must send Phase 2 immediately

2. **Command 0x51 Recognition**
   - Returns SW=91CA (Command Aborted)
   - Command exists but wrong state/parameters

3. **Protocol Differences**
   - Standard EV2 doesn't work on Seritag
   - Seritag uses modified protocol (unknown)

---

## Next Steps

### **When Tag Available:**
1. Run comprehensive test (`test_all_authentication_protocols.py`)
2. Analyze results for working protocols
3. Document findings

### **If No Protocol Works:**
1. Continue command 0x51 investigation
2. Review Seritag documentation
3. Consider static URL approach (already works!)

---

## Related Files

- **Comprehensive Test**: `examples/seritag/test_all_authentication_protocols.py`
- **EV2 Phase 2 Test**: `examples/seritag/test_ev2_phase2_detailed.py`
- **Command 0x51 Test**: `examples/seritag/test_0x51_detailed.py`
- **Fixed Protocol Test**: `examples/seritag/test_ev2_with_fixed_protocol.py`
- **Investigation Reference**: `investigation_ref/seritag_investigation_reference.md`
- **EV2 Investigation**: `EV2_PHASE2_INVESTIGATION.md`
- **Static URL Guide**: `STATIC_URL_PROVISIONING.md`

---

**Status**: ⏳ Waiting for tag to run comprehensive test  
**Next**: Execute comprehensive test and analyze results

