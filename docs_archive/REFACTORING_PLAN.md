# Commands Module Refactoring Plan

**Date:** 2025-11-01  
**Goal:** Organize commands into separate files for better maintainability

---

## Current Structure Analysis

### Files
```
src/ntag424_sdm_provisioner/commands/
├── __init__.py              # Package exports
├── base.py                  # Base classes (ApduCommand, ApduError)
├── sdm_commands.py          # 11 command classes (BLOATED)
├── change_file_settings.py  # 1 command class
├── sun_commands.py          # 3 command classes
└── sdm_helpers.py           # Helper functions
```

### Commands in sdm_commands.py (11 classes)
1. `GetChipVersion` - Get chip version info
2. `SelectPiccApplication` - Select PICC app
3. `AuthenticateEV2First` - Auth phase 1
4. `AuthenticateEV2Second` - Auth phase 2
5. `ChangeKey` - Change cryptographic key
6. `GetFileIds` - List file IDs
7. `GetFileSettings` - Get file configuration
8. `GetKeyVersion` - Get key version
9. `WriteData` - Write to file
10. `ReadData` - Read from file
11. `GetFileCounters` - Get SDM counter (NEW)

### Commands in sun_commands.py (3 classes)
1. `WriteNdefMessage` - Write NDEF using ISO
2. `ReadNdefMessage` - Read NDEF using ISO
3. `ConfigureSunSettings` - Configure SUN (deprecated?)

### Commands in change_file_settings.py (1 class)
1. `ChangeFileSettings` - Change file settings with SDM

---

## Refactoring Strategy

### Principle: One Command Per File

**Benefits:**
- Easy to find specific command
- Clear what dataclasses belong to each command
- Easier to maintain and test
- Follows Single Responsibility Principle

### File Naming Convention
```
command_name.py         # Command class
    ├── CommandNameCommand class
    ├── CommandNameResponse dataclass (if needed)
    └── Related constants/enums (if command-specific)
```

---

## Proposed New Structure

```
src/ntag424_sdm_provisioner/commands/
├── __init__.py                    # Clean exports from all commands
├── base.py                        # ENHANCED: Common base classes, dataclasses, constants
│
├── # Chip Information Commands
├── get_chip_version.py           # GetChipVersion + Ntag424VersionInfo
├── get_key_version.py            # GetKeyVersion + KeyVersionResponse
│
├── # Application/File Selection
├── select_picc_application.py    # SelectPiccApplication
├── get_file_ids.py               # GetFileIds
├── get_file_settings.py          # GetFileSettings + FileSettingsResponse
│
├── # Authentication
├── authenticate_ev2_first.py     # AuthenticateEV2First + AuthenticationChallengeResponse
├── authenticate_ev2_second.py    # AuthenticateEV2Second (if needed separately)
│
├── # File Operations
├── read_data.py                  # ReadData + ReadDataResponse
├── write_data.py                 # WriteData
├── change_key.py                 # ChangeKey
│
├── # SDM/SUN Specific
├── get_file_counters.py          # GetFileCounters (NEW)
├── change_file_settings.py       # ChangeFileSettings (EXISTS) + SDMConfiguration
├── write_ndef_message.py         # WriteNdefMessage (from sun_commands)
├── read_ndef_message.py          # ReadNdefMessage (from sun_commands)
│
└── # Helpers
    ├── sdm_helpers.py            # SDM calculation helpers (keep as-is)
    └── ndef_helpers.py           # NDEF building helpers (extract from sdm_helpers)
```

---

## What Goes in base.py

### Current base.py
- `ApduCommand` - Base class for all commands
- `ApduError` - Exception class

### To ADD to base.py (Common Dataclasses/Types)
```python
# Success response (used by many commands)
@dataclass
class SuccessResponse:
    message: str

# Status word tuples (used everywhere)
SW_OK = (0x90, 0x00)
SW_OK_ALTERNATIVE = (0x91, 0x00)
# ... etc

# Common imports that every command needs
from ntag424_sdm_provisioner.hal import NTag424CardConnection, hexb
```

### Command-Specific Dataclasses (Stay with Command)
- `Ntag424VersionInfo` → with GetChipVersion
- `FileSettingsResponse` → with GetFileSettings
- `KeyVersionResponse` → with GetKeyVersion
- `ReadDataResponse` → with ReadData
- `SDMConfiguration` → with ChangeFileSettings

---

## Migration Steps

### Step 1: Create Refactoring Branch (Safety)
```bash
# Not doing actual git operations, but documenting approach
# Create backup of current state
```

### Step 2: Extract One Command (Test Pattern)
**Start with simplest:** GetFileCounters
1. Create `commands/get_file_counters.py`
2. Move GetFileCounters class
3. Import in `__init__.py`
4. Run tests to verify
5. If works, continue with others

### Step 3: Extract Remaining Commands (Batch)
**Group by category:**
- Chip info commands (2 files)
- File operation commands (4 files)
- Auth commands (2 files)
- SDM commands (4 files)

### Step 4: Clean Up
- Remove empty/obsolete files
- Update all imports
- Consolidate helpers

### Step 5: Verify
- Run all examples
- Run all tests
- Check imports work

---

## Testing Strategy

### Before Each Move
```python
# Test that command works
from ntag424_sdm_provisioner.commands import CommandName
cmd = CommandName(...)
assert cmd is not None
```

### After Each Move
```python
# Test that command still works from new location
from ntag424_sdm_provisioner.commands import CommandName
cmd = CommandName(...)
assert cmd is not None
```

### Final Verification
```bash
# Run all examples
python examples/20_get_file_counters.py
python examples/21_build_sdm_url.py
python examples/22_provision_game_coin.py

# Run all tests (if working)
pytest tests/ -v
```

---

## Files to Remove (Dead Code)

Based on investigation:
- `commands/sun_commands.py` - Merge into individual command files
- Obsolete investigation scripts (already in investigation/)
- Duplicate helper functions

---

## Risk Mitigation

### Low Risk Operations
✅ Creating new files
✅ Copying code to new location
✅ Testing imports

### Medium Risk Operations
⚠️ Removing old files (do last)
⚠️ Updating __init__.py (test thoroughly)

### High Risk Operations
❌ None - we're just reorganizing, not changing logic

---

## Timeline

**Estimated Time:** 2-3 hours

| Step | Duration | Risk |
|------|----------|------|
| 1. Plan | 15 min | Low |
| 2. Extract GetFileCounters | 10 min | Low |
| 3. Extract remaining commands | 60 min | Low |
| 4. Update imports | 30 min | Medium |
| 5. Test everything | 30 min | Low |
| 6. Clean up | 15 min | Low |

---

## Success Criteria

✅ Each command in its own file  
✅ Related dataclasses with command  
✅ Common base classes in base.py  
✅ All imports work  
✅ All examples run  
✅ All tests pass  
✅ No duplicate code  

---

## Example: GetFileCounters

**Before:**
```python
# In sdm_commands.py (428 lines with 10 other commands)
class GetFileCounters(ApduCommand):
    ...
```

**After:**
```python
# In commands/get_file_counters.py (50 lines, focused)
"""
GetFileCounters Command

Retrieves the SDM read counter for a specific file.
"""
from ntag424_sdm_provisioner.commands.base import ApduCommand, ApduError, SW_OK
from ntag424_sdm_provisioner.hal import NTag424CardConnection

class GetFileCounters(ApduCommand):
    """Get SDM read counter for a file."""
    ...
```

---

## Next Steps

1. ✅ **Review this plan** - Confirm approach
2. Start with GetFileCounters (simplest, newest)
3. Test after each extraction
4. Log any issues in LESSONS.md
5. Complete all extractions
6. Final verification

**Ready to proceed with refactoring?**

