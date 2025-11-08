# Examples Directory Cleanup Plan

## To DELETE - Obsolete/Investigation Files

### Debug Scripts (Obsolete)
- `debug_change_file_settings.py`
- `debug_changekey_detailed.py`
- `debug_changekey.py`

### Test Scripts in Wrong Location (Should be in tests/)
- `test_auth_with_cmac_fix.py`
- `test_change_file_settings_no_auth.py`
- `test_key_encoding.py`
- `test_simple_auth_command.py`

### Entire Seritag Investigation Folder (OLD)
- `seritag/` - Complete directory with 30+ old investigation scripts
  - All from failed auth attempts (now fixed)
  - investigation/ subfolder with 20+ scripts
  - All use old/experimental APIs

### Demo Scripts (Duplicate Functionality)
- `demo_provision_context_manager.py` - Covered by 22_provision_game_coin.py

### Utility (Optional - probably not needed)
- `decode_access_rights.py` - Single-use utility

## To KEEP - Core Examples

### Basic Operations
- ✅ `01_connect.py` - Basic connection
- ✅ `02_get_version.py` - Get chip version
- ✅ `04_authenticate.py` - Authentication demo

### Advanced Operations
- ✅ `10_auth_session.py` - Auth session usage
- ✅ `19_full_chip_diagnostic.py` - Full diagnostic
- ✅ `20_get_file_counters.py` - GetFileCounters
- ✅ `21_build_sdm_url.py` - SDM URL building
- ✅ `25_get_current_file_settings.py` - File settings
- ✅ `26_authenticated_connection_pattern.py` - Auth pattern

### Provisioning (MAIN SCRIPTS)
- ✅ `22_provision_game_coin.py` - **PRIMARY** - Full provisioning with CsvKeyManager
- ✅ `22a_provision_sdm_factory_keys.py` - Variant for factory keys
- ✅ `99_reset_to_factory.py` - Reset to factory

## Scripts to UPDATE

### 22_provision_game_coin.py
**Status:** Uses CsvKeyManager ✅  
**Needs:** Verify uses new ChangeKey import and AuthenticatedConnection pattern

### Other examples
Need to check if they use old APIs (session= parameter, old imports, etc.)

## Summary

**DELETE:** ~40+ obsolete files (debug, test, seritag investigation)  
**KEEP:** 11 core examples  
**UPDATE:** Verify examples use current APIs

