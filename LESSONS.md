# Implementation Lessons Learned

This file tracks failed attempts, issues encountered, and solutions during SDM/SUN implementation.

---

## 2025-11-01 - Session Start

### Issue: Pytest import errors for modules
**Attempted:** Running pytest on test files
**Error:** `ModuleNotFoundError` for various ntag424_sdm_provisioner submodules
**Root Cause:** Missing `commands/__init__.py` - fixed by creating proper package structure
**Solution:** Created `src/ntag424_sdm_provisioner/commands/__init__.py` with exports
**Status:** ✅ RESOLVED

### Issue: Unicode characters in console output
**Attempted:** Using ✓✗ characters in print statements
**Error:** `UnicodeEncodeError: 'charmap' codec can't encode character`
**Root Cause:** Windows console (cp1252) doesn't support Unicode box-drawing characters
**Solution:** Use ASCII alternatives: [OK], [FAIL], [INFO], ->, etc.
**Status:** ✅ RESOLVED

### Finding: GetFileCounters requires SDM enabled
**Test:** Ran GetFileCounters on Seritag NTAG424 DNA (HW 48.0, UID 04B7664A2F7080)
**Result:** All files returned 0x911C (NTAG_ILLEGAL_COMMAND_CODE)
**Interpretation:** GetFileCounters only works when SDM is enabled on the file
**Next:** Need to configure SDM on NDEF file first (Phase 2), then counters will work
**Status:** Expected behavior - not a bug

### Issue: AuthSessionKeys attribute error
**Test:** Running example 22 with real chip
**Error:** `'AuthSessionKeys' object has no attribute 'keys'`
**Root Cause:** Code checked `session_keys.keys` but should use `session_enc_key` and `session_mac_key`
**Fix:** Changed to access correct attributes
**Status:** ✅ RESOLVED - Authentication now works!

### Issue: WriteData signature mismatch
**Test:** Running example 22 with real chip
**Error:** `WriteData.__init__() got an unexpected keyword argument 'data'`
**Root Cause:** WriteData expects `data_to_write` not `data`
**Fix:** Changed to data_to_write
**Status:** ✅ RESOLVED

### Issue: SDM configuration length error
**Test:** Running ChangeFileSettings on real chip
**Error:** 0x917E (NTAG_LENGTH_ERROR)
**Root Cause:** ChangeFileSettings payload construction incorrect
**Investigation:** build_sdm_settings_payload() may have wrong format
**Status:** Need to debug payload construction
**Note:** NDEF write works! Just SDM config failing

### Success: NDEF Write Working!
**Test:** WriteNdefMessage (ISOUpdateBinary) on real chip
**Result:** ✅ SUCCESS - wrote 87 bytes
**Key Steps:** 1) Select NDEF file (ISOSelectFile), 2) Write with ISOUpdateBinary
**Status:** ✅ Working - can write URLs to coins
**Note:** SDM not enabled yet, so placeholders won't be replaced (need to fix ChangeFileSettings)

---

## Implementation Progress Tracking

### Phase 1: Core SDM Commands ✅ COMPLETE
- [x] Add SDM constants to constants.py (GET_FILE_COUNTERS = 0xC1)
- [x] Implement GetFileCounters command (returns 24-bit counter)
- [x] Implement ChangeFileSettings command (already existed)
- [x] Add commands/__init__.py for proper package structure
- [x] Verify commands import and instantiate correctly
- [x] Test GetFileCounters with real chip (Seritag HW 48.0)
  - Result: 0x911C (command not valid - SDM not enabled yet)
  - Expected behavior for non-SDM-configured tag

### Phase 2: NDEF URL Building ✅ COMPLETE
- [x] Add NDEF constants (TLV types, URI prefixes) - already existed
- [x] Create NDEF URI record builder - build_ndef_uri_record() exists
- [x] Calculate SDM offsets - calculate_sdm_offsets() exists
- [x] Create example showing SDM URL with placeholders (example 21)
- [x] Test NDEF building (verified - 87 byte message for game coin URL)

### Phase 3: Complete Provisioning Integration - TESTED
- [x] KeyManager interface created
- [x] SimpleKeyManager implemented
- [x] Create basic provisioning example (example 22)
- [x] Add authentication step with SimpleKeyManager
- [x] Add SDM configuration (ChangeFileSettings with SDMConfiguration)
- [x] Add NDEF write (WriteData command)
- [x] Test complete flow with real chip (Seritag HW 48.0, UID 04B3664A2F7080)
  - ✅ Authentication: SUCCESS!
  - ✅ NDEF Write: SUCCESS! (87 bytes written)
  - ❌ SDM Configuration: Length error (needs debugging)

### Phase 4: CMAC Calculation - IN PROGRESS
- [ ] Implement SDM CMAC algorithm (matches tag behavior)
- [ ] Create server-side validation helper
- [ ] Create URL parser
- [ ] Test CMAC calculation
- [ ] Create validation example

### Phase 5: Mock HAL Enhancement
- [ ] SDM state machine
- [ ] CMAC generation
- [ ] Counter incrementing

### Phase 6: Complete Workflow
- [ ] High-level provisioner
- [ ] End-to-end provisioning

### Phase 7: Server Integration
- [ ] Validation endpoint
- [ ] Counter database

---

**Last Updated:** 2025-11-01

