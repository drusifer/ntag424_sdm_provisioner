# Refactoring Analysis - Code Bloat Assessment

**Date:** 2025-11-01

---

## File Size Analysis

### Commands Module
| File | Lines | Classes | Status |
|------|-------|---------|--------|
| sdm_commands.py | 428 | 11 | ❌ BLOATED |
| sdm_helpers.py | 282 | 0 | ⚠️ Large helpers |
| sun_commands.py | 266 | 3 | ⚠️ Moderate |
| change_file_settings.py | 55 | 1 | ✅ Good size |
| base.py | 95 | 2 | ✅ Good size |

### Root Module
| File | Lines | Status |
|------|-------|--------|
| constants.py | 707 | ❌ BLOATED |
| hal.py | 265 | ⚠️ Moderate |
| seritag_simulator.py | 304 | ⚠️ Test code |
| key_manager.py | 189 | ✅ Reasonable |
| key_manager_interface.py | 166 | ✅ Reasonable |

---

## Refactoring Priority

### HIGH PRIORITY (This Session)
1. **sdm_commands.py (428 lines)** - Split into 11 files (~40 lines each)
2. **sun_commands.py (266 lines)** - Split into 3 files (~90 lines each)

### MEDIUM PRIORITY (Future)
3. **constants.py (707 lines)** - Group constants by domain
4. **sdm_helpers.py (282 lines)** - Split into focused helpers

### LOW PRIORITY (Keep for now)
5. hal.py (265 lines) - Single responsibility, reasonable
6. Simulator/test code - Keep separate

---

## Refactoring Approach

### Phase 1: Commands (This Session)
**Target:** 14 command classes → 14 separate files

**Principle:** One command = one file = easy to find

**Before:**
- sdm_commands.py: 428 lines with 11 mixed commands
- Hard to find specific command
- Lots of scrolling

**After:**
- 11 focused files, ~40 lines each
- Clear responsibility
- Easy navigation

### Phase 2: Constants (Future Session)
**Target:** Split constants.py by domain

**Proposed structure:**
```
constants/
├── __init__.py
├── status_words.py    # SW_OK, StatusWord enum, etc
├── commands.py        # APDU command codes
├── files.py           # File numbers, options
├── sdm.py             # SDM-specific constants
└── ndef.py            # NDEF constants
```

---

## Immediate Action Plan

### Step 1: Test Current State (Baseline)
```bash
# Verify current imports work
python -c "from ntag424_sdm_provisioner.commands import GetFileCounters; print('OK')"
```

### Step 2: Extract GetFileCounters (Test Pattern)
- Create commands/get_file_counters.py
- Move class + imports
- Update __init__.py
- Test import still works
- **If successful, continue**

### Step 3: Extract Remaining Commands (Systematic)
**Order (simplest first):**
1. GetFileCounters (done in step 2)
2. GetFileIds
3. GetKeyVersion
4. ReadData
5. WriteData
6. ChangeKey
7. GetFileSettings
8. GetChipVersion
9. SelectPiccApplication
10. AuthenticateEV2First
11. AuthenticateEV2Second

### Step 4: Extract sun_commands.py
1. WriteNdefMessage
2. ReadNdefMessage
3. ConfigureSunSettings (review if still needed)

### Step 5: Clean Up
- Remove old sdm_commands.py
- Remove old sun_commands.py
- Keep change_file_settings.py (already separate)
- Update __init__.py with all exports

---

## Test Strategy

### Smoke Test (After Each Extraction)
```python
from ntag424_sdm_provisioner.commands import CommandName
cmd = CommandName(test_args)
assert str(cmd) != ""
```

### Integration Test (After All Extractions)
```bash
# Run working examples
python examples/20_get_file_counters.py  # If tag present
python examples/21_build_sdm_url.py
python examples/22_provision_game_coin.py  # If tag present
```

### Regression Test (Final)
```bash
# Verify syntax
python -m py_compile src/ntag424_sdm_provisioner/commands/*.py

# Check imports
python -c "from ntag424_sdm_provisioner.commands import *; print('All imports OK')"
```

---

## Benefits

### Maintainability
- ✅ Easy to find specific command
- ✅ Clear what belongs where
- ✅ Easier to add new commands

### Readability
- ✅ Focused, single-purpose files
- ✅ Less scrolling
- ✅ Better IDE navigation

### Testing
- ✅ Test one command at a time
- ✅ Clear dependencies
- ✅ Easier mocking

### Documentation
- ✅ Docstring at top of file
- ✅ Command purpose clear
- ✅ Related dataclasses together

---

**Status:** Plan created, ready to execute  
**Start with:** GetFileCounters extraction (test pattern)  
**Success metric:** All examples still run after refactoring

