# Delay Counter Critical Finding

**Date**: Current session  
**Status**: 🚨 **CRITICAL** - Delay counter persists after power loss

---

## Summary

**Key Discovery**: Authentication delay counter (SW=91AD) persists in **non-volatile memory** and does **NOT reset** with power loss (fresh tap).

---

## Critical Findings

### **1. Delay Counter Persistence** 🚨

**Observation**: After fresh tap (remove/replace tag):
- Still get **SW=91AD** (Authentication Delay)
- Delay counter **does NOT reset** with power loss
- Counter persists in **non-volatile memory (EEPROM/flash)**

**Implication**: 
- This is a **persistent security feature**
- Designed to prevent brute force attacks
- Counter may persist **indefinitely** until reset or time expires

### **2. Delay Pattern Observed**

From test results:
- **Attempt 1**: SW=91AD (delay)
- **Attempt 2**: SW=91AD (delay)
- **Attempt 3**: SW=91AD (delay)
- **Attempt 4**: ✅ **Success** (no delay!)
- **Attempt 5**: SW=91AD (delay)

**Analysis**:
- ~20% success rate (1 in 5)
- Most attempts delayed
- Occasional window where authentication allowed

### **3. Root Cause**

**Problem**: Every failed Phase 2 attempt (SW=91AE) **increments delay counter**

```
Phase 1 → Phase 2 (SW=91AE) → Delay Counter++
```

**Result**: Counter accumulates with each failed attempt, causing delays

---

## Impact

### **On Investigation** ⚠️

- **Rapid testing impossible**: Can't make many authentication attempts quickly
- **Fresh tap doesn't help**: Counter persists across power cycles
- **Need correct protocol**: Only way to avoid delays is working Phase 2

### **On Solution Paths**

1. **Static URLs** ✅ **Works immediately** - No authentication needed!
2. **Find Phase 2 protocol** ⏳ **Blocked by delays** - Hard to test
3. **Find delay reset** ⏳ **Unknown** - May not exist

---

## Possible Delay Mechanisms

### **Hypothesis 1: Time-Based Window**
- Delay counter decrements over time
- Occasionally opens window for authentication
- Explains why Attempt 4 succeeded

### **Hypothesis 2: Exponential Backoff**
- Delay duration increases exponentially
- After N attempts, requires minutes/hours wait
- Very common in security systems

### **Hypothesis 3: Permanent Block**
- After threshold, permanently blocks authentication
- Requires reset command (if exists)
- Most secure, but prevents recovery

### **Hypothesis 4: Successful Auth Resets**
- Successful authentication resets counter
- But we can't get successful auth (Phase 2 fails)
- Catch-22 situation

---

## Recommendations

### **Immediate** 🚨

1. **STOP making authentication attempts** until we understand delay mechanism
2. **Use static URL provisioning** for immediate progress
3. **Research delay reset commands** (may not exist)

### **Short Term**

1. **Test longer wait times**: Minutes/hours between attempts
2. **Search Seritag documentation**: Delay reset mechanism
3. **Find Phase 2 protocol**: Working auth resets counter

### **Long Term**

1. **Get correct authentication protocol** from Seritag
2. **Implement working Phase 2**
3. **Then configure SDM/SUN** after authentication

---

## Workaround: Static URLs

**Current best path forward**:
- ✅ Static URL provisioning **works without authentication**
- ✅ Can provision tags **immediately**
- ✅ Server can verify static URLs
- ⚠️ Less secure than SDM/SUN, but functional

---

## Related Files

- **Test Script**: `examples/seritag/test_authentication_delay.py`
- **Findings**: `AUTHENTICATION_DELAY_FINDINGS.md`
- **Investigation**: `EV2_PHASE2_INVESTIGATION.md`

---

**Status**: 🚨 **CRITICAL** - Delay counter blocks authentication testing  
**Next**: Research delay reset mechanism or wait for time-based reset

