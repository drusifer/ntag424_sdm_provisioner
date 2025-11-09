# Cleanup Plan - Temporary and Outdated Artifacts

TLDR; Authentication solved. Investigation scripts archived to `examples/seritag/investigation/`. Keep canonical examples. Updated docs reflect current state.

---

## Files to Archive (Move to `examples/seritag/investigation/`)

### Temporary Investigation Scripts
These were used during the authentication debugging phase and are now obsolete:

1. `examples/15_auth_flow_detailed.py` - Detailed auth flow logging (superseded by working auth)
2. `examples/16_reader_mode_comparison.py` - Reader hardware comparison (issue resolved)
3. `examples/17_auth_flow_comparison.py` - Auth flow comparison (led to CBC fix, now obsolete)
4. `examples/18_test_cbc_mode.py` - CBC mode test (fix verified, can archive)

### Seritag Investigation Scripts (Already in `examples/seritag/`)
These can be archived to `examples/seritag/investigation/`:

- `test_phase2_*` scripts (all Phase 2 investigation scripts)
- `test_phase1_*` scripts (Phase 1 investigation scripts)
- `test_authentication_delay.py` - Delay investigation (documented)
- `test_ev2_*` scripts - EV2 investigation variants
- `test_factory_key_variations.py` - Key testing (all tested)
- `test_lrp_and_alternatives.py` - Alternative auth methods
- `test_0x51_detailed.py` - Command 0x51 investigation
- `test_command_0x77.py` - Command 0x77 investigation
- `test_ev2_then_nonfirst.py` - Auth sequence testing

### Keep Active
- `examples/19_full_chip_diagnostic.py` - Canonical API example ✅
- `examples/10_auth_session.py` - Simple auth example ✅
- `examples/13_working_ndef.py` - Working NDEF example ✅
- `examples/seritag/provision_static_url.py` - Production example ✅

---

## Documentation Updates Needed

1. ✅ `CURRENT_STEP.md` - Updated with authentication fix
2. ✅ `MINDMAP.md` - Updated with authentication SOLVED status
3. ⏳ `README.md` - Update to reflect authentication working
4. ⏳ `AUTH_FLOW_ANALYSIS.md` - Mark as historical (pre-CBC fix)
5. ✅ `SERITAG_INVESTIGATION_COMPLETE.md` - Already comprehensive

---

## Archive Structure

Create `examples/seritag/investigation/` directory and move:
- Phase 1/2 investigation scripts
- Key testing scripts
- Alternative auth method scripts
- Comparison/test scripts

Keep main examples clean and focused.

---

## Status - COMPLETE ✅

- [x] Documentation updated
- [x] Archive directory created (`examples/seritag/investigation/`)
- [x] Temporary scripts moved (23 files archived)
- [x] Archive README created
- [x] README updated with authentication status
- [x] Progress summary created (`PROGRESS_SUMMARY.md`)
- [x] Changelog created (`CHANGELOG.md`)

## Files Archived (23 total)

### Main Examples Directory (6 files)
- `15_auth_flow_detailed.py`
- `16_reader_mode_comparison.py`
- `17_auth_flow_comparison.py`
- `18_test_cbc_mode.py`
- `10_ndef_investigation.py`
- `12_test_keys.py`

### Seritag Investigation Scripts (17 files)
- All `test_phase1_*.py` scripts (2 files)
- All `test_phase2_*.py` scripts (12 files)
- All `test_ev2_*.py` scripts (3 files)
- Additional investigation scripts:
  - `test_authentication_delay.py`
  - `test_factory_key_variations.py`
  - `test_lrp_and_alternatives.py`
  - `test_0x51_detailed.py`
  - `test_command_0x77.py`
  - `test_ev2_then_nonfirst.py`

## Active Examples Remaining

Canonical examples kept in `examples/`:
- `01_connect.py` - Basic connection
- `02_get_version.py` - Version reading
- `04_authenticate.py` - Authentication
- `10_auth_session.py` - Auth session example
- `13_working_ndef.py` - Working NDEF provisioning
- `19_full_chip_diagnostic.py` - Full diagnostic (canonical example) ⭐

Plus production examples and core functionality scripts.

