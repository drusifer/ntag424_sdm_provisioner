# Seritag NTAG424 DNA Investigation Summary

**Date**: Current session  
**Status**: ⏳ Phase 2 authentication blocked - investigating protocol differences

---

## TLDR

**Game coin use case**: NFC tags must serve authenticated URLs (UID+MAC+Counter) for server verification.

**Current Status**:
- ✅ **Static URL provisioning works** - Can provision tags immediately without authentication
- ✅ **Phase 1 authentication works** - Verified correct with fresh tags
- ✅ **RndB extraction/rotation correct** - Matches NXP spec
- ❌ **Phase 2 authentication fails** - Returns SW=91AE (Authentication Error)
- ❌ **SDM/SUN configuration requires authentication** - Blocked until Phase 2 works

---

## What Works ✅

### **1. Static URL Provisioning**
- ✅ NDEF read/write without authentication
- ✅ Can provision static URLs immediately
- ✅ Works with fresh tags
- **File**: `examples/seritag/provision_static_url.py`

### **2. Phase 1 Authentication**
- ✅ Returns SW=91AF with 16 bytes (encrypted RndB)
- ✅ Complete with just the 16 bytes (no additional frames)
- ✅ RndB decryption works
- ✅ RndB rotation correct (left by 1 byte)

### **3. Protocol Fixes**
- ✅ CLA bytes fixed (ISO commands use 00, proprietary use 90)
- ✅ File selection fixed (P1=0x02)
- ✅ Command formats correct
- ✅ Multi-frame handling implemented

---

## What Doesn't Work ❌

### **1. Phase 2 Authentication**
- ❌ Returns SW=91AE (Authentication Error) on all variations
- ❌ Protocol format differs for Seritag
- ❌ Blocking SDM/SUN configuration

### **2. SDM/SUN Configuration**
- ❌ Requires authentication (Change access right = KEY_0)
- ❌ Blocked until Phase 2 works

### **3. Authentication Delay Counter**
- ❌ Persists in non-volatile memory
- ❌ Doesn't reset with power loss (fresh tap)
- ❌ Blocks rapid testing
- ❌ Requires waiting or fresh tags

---

## Key Findings

### **Phase 1: Verified Correct**
- Format: `90 71 00 00 02 [KeyNo] 00 00`
- Response: `SW=91AF` with 16 bytes (encrypted RndB)
- Complete: No additional frames needed
- RndB: First 16 bytes = encrypted RndB ✅
- Rotation: Left by 1 byte ✅

### **Phase 2: Fails with All Variations**
- Format: `90 AF 00 00 20 [E(Kx, RndA || RndB')] 00`
- Response: `SW=91AE` (Authentication Error)
- Variations tested:
  1. Standard (RndA || RndB'): SW=91AE
  2. Reverse (RndB' || RndA): SW=91AE
  3. No rotation: SW=91AE
  4. Right rotate: SW=91AE
  5. 2-byte rotate: Not tested yet

### **Phase 2 State Management**
- After Phase 2 failure, Phase 1 returns SW=91CA (Command Aborted)
- Need fresh tag for each Phase 2 test
- Suggests command sequence issue

---

## Protocol Confirmation

According to NXP spec (Section 10.4.1):

**Phase 1**:
- Command: `90 71 00 00 02 [KeyNo] 00 00`
- Response: `E(Kx, RndB) || 91AF` ✅ **Matches!**

**Phase 2**:
- Command: `90 AF 00 00 20 [E(Kx, RndA || RndB')] 00`
- Response: `E(Kx, TI || RndA' || PDcap2 || PCDcap2) || 9000`
- RndB' = RndB rotated left by one byte ✅ **Matches our implementation!**

**Our implementation matches the spec, but Seritag rejects it with SW=91AE**

---

## Possible Causes

### **1. Wrong Encryption Key**
- Using factory key (all zeros): `00000000000000000000000000000000`
- Maybe Seritag uses different factory keys?

### **2. Encryption Mode Issue**
- Using AES-ECB (matches spec)
- Maybe Seritag requires different mode?

### **3. Command Format Issue**
- Using correct format per spec
- Maybe Seritag requires different format?

### **4. Phase 1 Completion Issue**
- Phase 1 returns SW=91AF (Additional Frame)
- Maybe we need to send GetAdditionalFrame to "complete" Phase 1?
- Test showed SW=917E when we try that

### **5. Timing/Sequence Issue**
- Maybe Phase 2 needs to be sent immediately (we do this)
- Maybe there's a timing requirement?

---

## Next Steps

### **Short Term**
1. ✅ Document findings (this document)
2. ⏳ Review Seritag SVG authentication pages
3. ⏳ Test factory key variations (if different keys exist)
4. ⏳ Test Phase 1 completion sequence variations

### **Medium Term**
1. ⏳ Continue Phase 2 protocol investigation
2. ⏳ Test static URL provisioning with phone
3. ⏳ Evaluate if static URLs are sufficient for MVP

### **Long Term**
1. ⏳ Get Seritag authentication documentation
2. ⏳ Implement working Phase 2 protocol
3. ⏳ Enable SDM/SUN configuration
4. ⏳ Full authenticated URL provisioning

---

## Working Solution: Static URLs

**Current best path forward**:
- ✅ Static URL provisioning **works now**
- ✅ Can provision tags immediately
- ✅ Server can verify tags are from your game (via UID)
- ⚠️ Less secure than SDM/SUN (no MAC/counter)
- ✅ Suitable for MVP/prototype

**Files**:
- **Guide**: `STATIC_URL_PROVISIONING.md`
- **Script**: `examples/seritag/provision_static_url.py`

---

## Related Documentation

- **Fresh Tag Findings**: `FRESH_TAG_FINDINGS.md`
- **Phase 2 Investigation**: `PHASE2_PROTOCOL_INVESTIGATION.md`
- **Authentication Delay**: `AUTHENTICATION_DELAY_FINDINGS.md`
- **EV2 Investigation**: `EV2_PHASE2_INVESTIGATION.md`
- **RndB Investigation**: `RNDB_ROTATION_INVESTIGATION.md`
- **Static URLs**: `STATIC_URL_PROVISIONING.md`

---

**Status**: ⏳ Phase 2 protocol investigation continues  
**Next**: Review Seritag documentation, test key variations, continue protocol investigation

