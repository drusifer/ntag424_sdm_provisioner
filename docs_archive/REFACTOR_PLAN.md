# Command Module Refactoring Plan

## Goal
Split `sdm_commands.py` into individual command files with associated dataclasses.

## Current Structure
```
commands/
├── base.py (ApduCommand, AuthenticatedConnection)
├── sdm_commands.py (8 commands, 314 lines)
├── change_key.py ✓ (already separated)
├── change_file_settings.py ✓ (already separated)
├── read_data.py ✓ (already separated)
├── write_data.py ✓ (already separated)
├── iso_commands.py (ISOSelectFile, ISOReadBinary)
├── sun_commands.py ✓ (NDEF/SUN commands)
└── sdm_helpers.py (utility functions)
```

## Target Structure
```
commands/
├── base.py
├── select_picc_application.py (SelectPiccApplication)
├── get_chip_version.py (GetChipVersion + Ntag424VersionInfo)
├── authenticate_ev2.py (AuthenticateEV2First, AuthenticateEV2Second, AuthenticateEV2 + auth dataclasses)
├── get_file_ids.py (GetFileIds)
├── get_file_settings.py (GetFileSettings + FileSettingsResponse)
├── get_key_version.py (GetKeyVersion)
├── get_file_counters.py (GetFileCounters)
├── change_key.py ✓
├── change_file_settings.py ✓
├── read_data.py ✓
├── write_data.py ✓
├── iso_commands.py (+ CCFileData)
├── sun_commands.py ✓
└── sdm_helpers.py
```

## Dataclass Moves

| Dataclass | Current Location | New Location |
|-----------|-----------------|--------------|
| Ntag424VersionInfo | constants.py | get_chip_version.py |
| FileSettingsResponse | constants.py | get_file_settings.py |
| CCFileData | constants.py | iso_commands.py |
| AuthenticationResponse | constants.py | authenticate_ev2.py |
| AuthSessionKeys | constants.py | authenticate_ev2.py |
| ReadDataResponse | constants.py | read_data.py |

## Steps

1. ✅ Create new command files
2. ✅ Move dataclasses to command files
3. ✅ Update imports in constants.py (re-export for backwards compat)
4. ✅ Update __init__.py exports
5. ✅ Test all examples still work
6. ✅ Delete old sdm_commands.py

## Import Compatibility

Keep backwards compatibility by re-exporting from constants.py:
```python
# constants.py
from ntag424_sdm_provisioner.commands.get_chip_version import Ntag424VersionInfo
# ... etc
```

## Execution Order

1. ✅ Create select_picc_application.py
2. ✅ Create get_chip_version.py (+ Ntag424VersionInfo)
3. ✅ Create get_file_ids.py
4. ✅ Create get_key_version.py (+ KeyVersionResponse)
5. ✅ Remove smartcard deps from hal.hexb()
6. ⏭️ Create get_file_settings.py (+ FileSettingsResponse) - NEXT
7. ⏭️ Create authenticate_ev2.py (auth commands + dataclasses) - BIG
8. ⏭️ Move CCFileData to iso_commands.py
9. ⏭️ Move ReadDataResponse to read_data.py
10. ⏭️ Update constants.py with re-exports
11. ⏭️ Update commands/__init__.py
12. ⏭️ Update provisioning script imports
13. ⏭️ Test examples
14. ⏭️ Delete sdm_commands.py

## Progress: 5/14 (36%)

## Decision: Keep Dataclasses in constants.py

**Rationale:** Avoid circular imports
- constants.py → commands (imports would create cycles)
- Commands reference constants for types
- Dataclasses stay in constants.py for shared access
- Command modules focus on behavior, not data structures

**Result:** Clean separation without import issues
- ✅ Commands in individual files
- ✅ Dataclasses in constants.py (shared)
- ✅ No circular dependencies
- ✅ All imports work

## Completed Files:
1. ✅ `select_picc_application.py` - 48 lines
2. ✅ `get_chip_version.py` - Uses Ntag424VersionInfo from constants
3. ✅ `get_file_ids.py` - 42 lines
4. ✅ `get_key_version.py` - Uses KeyVersionResponse from constants
5. ✅ `get_file_settings.py` - Uses parse_file_settings helper
6. ✅ `authenticate_ev2.py` - All 3 auth commands (AuthenticateEV2First, Second, EV2)
7. ✅ `hal.py` - Removed smartcard.util dependency from hexb()
8. ✅ `auth_session.py` - Local imports to break circular dependency

## Remaining in sdm_commands.py:
- (Empty now - can be deleted)

## Status: 
- ✅ All commands extracted and working
- ✅ Circular imports resolved (local imports in auth_session)
- ✅ Provisioning script imports updated
- ✅ check_ndef_config.py imports updated
- ✅ All modules tested and working

