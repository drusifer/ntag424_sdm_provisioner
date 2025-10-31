# Changelog

## 2025-10-30 - Authentication Fixed & API Refactored

### ✅ Fixed
- **Authentication**: Fixed CBC mode encryption (was using ECB mode) - Authentication now working ✅
- **Status Word Handling**: Accept `SW_OK_ALTERNATIVE` (0x9100) as success status

### ✅ Added
- **Full Chip Diagnostic**: `examples/19_full_chip_diagnostic.py` - Canonical API usage example
- **Command Classes**: `GetFileIds`, `GetFileSettings`, `GetKeyVersion` moved to `sdm_commands.py`
- **Dataclasses**: `FileSettingsResponse`, `KeyVersionResponse` with `__str__` methods
- **Helpers**: `parse_file_settings()`, `parse_key_version()` in `sdm_helpers.py`

### ✅ Improved
- **API Organization**: Parsing/formatting moved to helpers and dataclasses
- **Fresh Tag Handling**: Graceful handling of missing files on fresh tags
- **Documentation**: Updated to reflect authentication success

### 🗂️ Archived
- Investigation scripts moved to `examples/seritag/investigation/`
- Historical investigation docs marked appropriately

---

## Previous Work
- Registry key fix (EscapeCommandEnable)
- Static URL NDEF provisioning (works without authentication)
- Comprehensive Phase 2 protocol investigation
- See `SERITAG_INVESTIGATION_COMPLETE.md` for full history

