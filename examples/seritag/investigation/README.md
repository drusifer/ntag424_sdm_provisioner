# Investigation Scripts Archive

This directory contains investigation and debugging scripts from the authentication troubleshooting phase.

**Status**: These scripts were used during the investigation phase and led to the CBC mode fix. They are preserved for historical reference but are no longer needed for active development.

## Archive Contents

### Main Examples Directory
- `15_auth_flow_detailed.py` - Detailed auth flow logging
- `16_reader_mode_comparison.py` - Reader hardware comparison
- `17_auth_flow_comparison.py` - Auth flow comparison (led to CBC fix)
- `18_test_cbc_mode.py` - CBC mode verification test
- `10_ndef_investigation.py` - NDEF investigation script
- `12_test_keys.py` - Key testing script

### Seritag Investigation Scripts
- `test_phase1_*.py` - Phase 1 authentication investigation scripts
- `test_phase2_*.py` - Phase 2 authentication investigation scripts
- `test_authentication_delay.py` - Authentication delay investigation
- `test_ev2_*.py` - EV2 authentication variant tests
- `test_factory_key_variations.py` - Factory key testing (all variations tested)
- `test_lrp_and_alternatives.py` - Alternative authentication methods
- `test_0x51_detailed.py` - Command 0x51 investigation
- `test_command_0x77.py` - Command 0x77 investigation
- `test_ev2_then_nonfirst.py` - Auth sequence testing

## Key Findings from These Scripts

1. **CBC Mode Fix**: The comparison scripts (`17_auth_flow_comparison.py`) led to identifying that authentication should use CBC mode with zero IV, not ECB mode.

2. **Protocol Verification**: All Phase 1 and Phase 2 investigation scripts confirmed the protocol implementation matches the NXP specification.

3. **Key Testing**: Factory key variations were all tested and ruled out as the cause of authentication failures.

4. **Hardware Ruled Out**: Reader comparison scripts confirmed the issue was not hardware-related.

## Current Status

✅ **Authentication is now working** (CBC mode fix implemented)  
✅ **API refactored** with clean command classes and dataclasses  
✅ **Full chip diagnostic example** created (`examples/19_full_chip_diagnostic.py`)

These scripts can be referenced if needed for historical context, but active development should use the canonical examples in the main `examples/` directory.

