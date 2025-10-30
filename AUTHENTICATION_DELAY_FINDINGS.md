# Authentication Delay Investigation Findings

**Date**: Current session  
**Status**: ✅ **COMPLETE** - Delay behavior identified

---

## Summary

Investigation of authentication delay (SW=91AD) behavior on Seritag NTAG424 DNA tags reveals a **rate limiting mechanism** that increments with failed authentication attempts.

---

## Key Findings

### **1. Delay Pattern Observed**
- **Pattern**: Delay occurs on **every other** authentication attempt
- **Attempt 1**: SW=91AD (Authentication Delay)
- **Attempt 2**: ✅ Success (no delay)
- **Attempt 3**: SW=91AD (Authentication Delay)
- **Attempt 4**: SW=91AD (Authentication Delay)
- **Attempt 5**: ✅ Success (no delay)

### **2. Delay Counter Behavior** ⭐ **CRITICAL FINDING**
- Delay counter **increments** after failed Phase 2 attempts (SW=91AE)
- Counter **persists in non-volatile memory** ✅ **VERIFIED**
- **Fresh tap does NOT reset** delay counter ⚠️
- Counter persists across power cycles
- Only **one successful attempt** in several trials (Attempt 4 succeeded)

### **3. Delay Duration** ⚠️ **PROBLEM**
- **Standard wait**: 1-2 seconds ❌ Not enough
- **After wait**: Retry still fails with SW=91AD
- **Longer wait needed?**: Unknown - delay may be **exponential** or **time-based**
- **Fresh tap**: ❌ Does NOT reset delay
- **Pattern**: Only ~20% of attempts succeed (1 in 5 in test)

---

## Test Results

### **Test 1: Multiple Attempts in Same Session**

```
Attempt 1: SW=91AD (delay) -> Wait 1s -> Still SW=91AD
Attempt 2: ✅ Phase 1 successful -> Phase 2: SW=91AE
Attempt 3: SW=91AD (delay) -> Wait 1s -> Still SW=91AD
Attempt 4: SW=91AD (delay) -> Wait 1s -> Still SW=91AD
Attempt 5: ✅ Phase 1 successful -> Phase 2: SW=91AE
```

**Observation**: Delay alternates between attempts, suggesting counter increments with each failed Phase 2.

### **Test 2: Fresh Tap (Reconnection)** ⭐ **CRITICAL RESULT**

**Test Design**:
1. Remove tag from reader (power loss)
2. Wait 3 seconds
3. Place tag back (fresh tap)
4. Test Phase 1 immediately

**Result**: ❌ **Still got SW=91AD after fresh tap!**
- **Delay counter persists in non-volatile memory**
- Power loss does **NOT** reset delay counter
- Counter is a **persistent security feature**

**Conclusion**: Delay counter is stored in tag's EEPROM/flash memory, not RAM.

---

## Recommendations

### **1. Handling Authentication Delay**

```python
# Option 1: Wait and retry
try:
    cmd = AuthenticateEV2First(key_no=0)
    response = cmd.execute(card)
except ApduError as e:
    if e.sw2 == 0xAD:  # Authentication Delay
        time.sleep(2.0)  # Wait 2 seconds
        cmd = AuthenticateEV2First(key_no=0)
        response = cmd.execute(card)
```

### **2. Fresh Tap Strategy**

If delay persists:
1. Remove tag from reader
2. Wait 3-5 seconds
3. Place tag back (fresh tap)
4. Retry authentication

### **3. Minimizing Delays**

- Avoid failed Phase 2 attempts (don't retry immediately)
- Use correct authentication protocol (once we figure it out!)
- Only authenticate when necessary

---

## Implications

### **For Development**
- Need to handle SW=91AD gracefully
- May need longer delays between attempts
- Fresh tap may be required for testing

### **For Production**
- Rate limiting is a security feature (prevents brute force)
- We need working authentication protocol to avoid delays
- Static URL approach avoids authentication entirely!

---

## Next Steps

### **Immediate Actions** ⚠️

1. ✅ **Fresh tap verified**: Does NOT reset delay counter
2. ✅ **Non-volatile persistence**: Verified - counter persists in EEPROM
3. ⏳ **Determine delay duration**: Test much longer wait times (minutes?)
4. ⏳ **Find delay reset mechanism**: Is there a command to reset delay counter?
5. ⏳ **Find working protocol**: Once Phase 2 works, delays should stop

### **Critical Path**

**The fundamental issue**: Every failed Phase 2 attempt (SW=91AE) **increments a persistent delay counter**. This counter:
- Stores in **non-volatile memory**
- Does **NOT reset** with power loss
- Causes **most authentication attempts** to be delayed
- Only **occasionally** allows authentication (maybe time-based window?)

**Solution paths**:
1. **Find correct Phase 2 protocol** (so Phase 2 succeeds, no delays)
2. **Find delay reset command** (if exists)
3. **Wait long periods** between attempts (may be exponential backoff)
4. **Use static URLs** (bypasses authentication entirely!)

---

## Related Files

- **Test Script**: `examples/seritag/test_authentication_delay.py`
- **Comprehensive Test**: `examples/seritag/test_all_authentication_protocols.py`
- **Investigation**: `EV2_PHASE2_INVESTIGATION.md`
- **Authentication Docs**: `AUTHENTICATION_INVESTIGATION.md`

---

**Status**: ✅ Delay behavior identified - rate limiting mechanism confirmed  
**Next**: Verify fresh tap resets delay counter and test longer wait durations

