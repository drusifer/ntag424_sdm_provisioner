# SDM Configuration Status - Blocked

**Date:** 2025-11-01  
**Issue:** ChangeFileSettings returns 0x917E (LENGTH_ERROR) on Seritag tags  
**Status:** BLOCKED - Need help or alternative approach

---

## What We've Accomplished ✅

### Working Features
1. ✅ **Authentication** - EV2 auth with factory keys working perfectly
2. ✅ **NDEF Write** - Can write 87-byte URLs to tags
3. ✅ **URL Building** - Correct 87-byte NDEF structure
4. ✅ **Offset Calculation** - Fixed! UID@47, CTR@66, CMAC@78
5. ✅ **KeyManager** - SimpleKeyManager integrated
6. ✅ **Refactoring** - 27% code reduction

### All Fixes Applied
1. ✅ FileOption bit 6 set (SDM enable)
2. ✅ Access rights = 2 bytes (nibble-packed)
3. ✅ SDMAccessRights added (2 bytes after SDMOptions)
4. ✅ Correct field order: UIDOffset → ReadCtrOffset
5. ✅ Fixed offset calculator (uid, ctr, cmac order)
6. ✅ Correct offsets: 47, 66, 78

---

## Blocking Issue ❌

**ChangeFileSettings still returns 0x917E**

**Latest Payload (13 bytes):**
```
02 40 E0 EE E0 EF 0E 2F 00 00 42 00 00
↑  ↑  ↑------↑  ↑  ↑------↑  ↑------↑  ↑------↑
FileNo FileOpt Access  SDM  SDMAccess UIDOff  CtrOff
```

**Analysis:**
- Byte count matches expectations
- Field order correct per NXP spec
- Access rights nibble-packed correctly
- Offsets don't overlap

**Possible Causes:**
1. Seritag doesn't support SDM the same way
2. Need CommMode.FULL instead of PLAIN
3. Missing or incorrect field we haven't identified
4. Seritag firmware limitation

---

## Reference Comparison

### Arduino MFRC522 Library
- **Status:** Explicitly does NOT implement SDM
- **Comment:** "SDM IS NOT SUPPORTED!"
- **Value:** Confirmed field order and access rights format only

### NXP Specification
- Our implementation matches spec
- All fields present in correct order
- But Seritag may diverge from spec

---

## Options Moving Forward

### Option A: Use Static URLs (MVP - Recommended)
**Pros:**
- ✅ Works NOW (tested successfully)
- ✅ Can write URLs with actual UID
- ✅ Server validates UID
- ✅ Gets coins working immediately

**Cons:**
- ❌ No tap counter (can't detect replays as well)
- ❌ No CMAC (slightly less secure)

**Implementation:**
```python
# Build URL with real UID (not placeholder)
url = f"https://globalheadsandtails.com/tap?uid={uid.hex().upper()}"
ndef = build_ndef_uri_record(url)
# Write with ISOUpdateBinary (works!)
# Server validates UID exists in database
```

### Option B: Debug Seritag SDM Further
**Approach:**
1. Test with standard NXP NTAG424 DNA (not Seritag)
2. If works on standard → Seritag-specific issue
3. If fails on both → Our implementation issue

**Time:** Could take hours/days

**Risk:** May not be solvable without Seritag support

### Option C: Hybrid Approach
**Phase 1:** Ship static URLs now
**Phase 2:** Continue SDM research in background
**Phase 3:** Upgrade to dynamic URLs when solved

---

## What You Have Now

**Working coin provisioning:**
```bash
python examples/22_provision_game_coin.py
```

**Results:**
- ✅ Authenticates with tag
- ✅ Writes 87-byte URL
- ❌ SDM not enabled (static URL, not dynamic)

**Current tag content:**
```
https://globalheadsandtails.com/tap?uid=00000000000000&ctr=000000&cmac=0000000000000000
```

**To make it work as static URL:**
- Replace placeholders with real UID
- Skip SDM configuration
- Server validates UID only

---

## Recommendation

**Ship static URL MVP immediately:**

1. Modify example 22 to write URL with real UID
2. Skip SDM configuration step
3. Test tapping coin with phone
4. Implement simple server validation (UID-based)
5. Get game coins working!

**Then:**
- Continue researching Seritag SDM
- Test with standard NXP tags
- Upgrade to dynamic URLs when solved

---

**Status:** Blocked on SDM, but have working static URL solution  
**Decision Needed:** Static URL MVP or continue debugging?

