# NTAG424 SDM Provisioner

**Status**: ✅ Production Ready | End-to-End Provisioning Working | Type-Safe Architecture

A Python library for provisioning NXP NTAG424 DNA NFC tags with unique keys and Secure Dynamic Messaging (SDM) capabilities.

---

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd ntag424_sdm_provisioner

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install in editable mode
pip install -e .
```

### Basic Provisioning

```bash
# Connect tag to reader, then run:
python examples/22_provision_game_coin.py
```

This will:
1. Read tag UID and chip info
2. Generate unique random keys
3. Change all keys (0, 1, 3) using two-session protocol
4. Write NDEF message with SDM placeholders
5. Save keys to `tag_keys.csv`

**⚠️ WARNING**: This changes cryptographic keys permanently. Save the generated keys!

---

## Features

✅ **End-to-End Provisioning** - Complete workflow from factory to provisioned  
✅ **Type-Safe Commands** - Compile-time safety for authenticated commands  
✅ **EV2 Authentication** - Full two-phase authentication protocol  
✅ **Key Management** - CSV-based storage with two-phase commit  
✅ **Factory Reset** - Reset tags to factory defaults  
✅ **Clean Architecture** - SOLID principles, DRY, testable  
✅ **Crypto Validated** - All crypto verified vs NXP specifications  
✅ **Production Ready** - Proven working (see SUCCESSFUL_PROVISION_FLOW.md)

---

## Architecture

### Command Pattern (Inverted Control)

```python
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.authenticate_ev2 import AuthenticateEV2
from ntag424_sdm_provisioner.commands.change_key import ChangeKey

# New pattern: connection executes command
with CardManager() as card:
    # Unauthenticated commands
    card.send(SelectPiccApplication())
    version = card.send(GetChipVersion())
    
    # Authenticated commands
    with AuthenticateEV2(key, key_no=0)(card) as auth_conn:
        auth_conn.send(ChangeKey(0, new_key, None))
```

### Type Safety

Commands are type-checked at compile time:

```python
# ✅ OK: Unauthenticated command with card connection
card.send(SelectPiccApplication())

# ✅ OK: Authenticated command with authenticated connection
auth_conn.send(ChangeKey(0, new_key, None))

# ❌ ERROR: Type checker catches this at development time
card.send(ChangeKey(0, new_key, None))
# Error: ChangeKey requires AuthenticatedConnection
```

---

## Key Concepts

### Two-Session Provisioning

Changing Key 0 (PICC Master Key) invalidates the current session. Must use two sessions:

```python
# SESSION 1: Change Key 0 only
with AuthenticateEV2(old_key, key_no=0)(card) as auth_conn:
    auth_conn.send(ChangeKey(0, new_key, None))
# Session 1 is now INVALID (Key 0 changed)

# SESSION 2: Change Keys 1 & 3 with NEW Key 0
with AuthenticateEV2(new_key, key_no=0)(card) as auth_conn:
    auth_conn.send(ChangeKey(1, new_key_1, None))
    auth_conn.send(ChangeKey(3, new_key_3, None))
```

### ChangeKey Requirements

**Key 0** (PICC Master Key):
```python
# Only new key needed
auth_conn.send(ChangeKey(0, new_key, None))
```

**Keys 1-4** (Application Keys):
```python
# Old key REQUIRED for XOR verification
auth_conn.send(ChangeKey(1, new_key, old_key))
```

### Key Management

```python
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager

key_mgr = CsvKeyManager()

# Two-phase commit (atomic provisioning)
with key_mgr.provision_tag(uid, url="https://...") as new_keys:
    # Keys generated and saved (status='pending')
    auth_conn.send(ChangeKey(0, new_keys.get_picc_master_key_bytes(), None))
    auth_conn.send(ChangeKey(1, new_keys.get_app_read_key_bytes(), None))
    auth_conn.send(ChangeKey(3, new_keys.get_sdm_mac_key_bytes(), None))
    # On success: status='provisioned'
    # On exception: status='failed', keys backed up

# Retrieve keys later
keys = key_mgr.get_tag_keys(uid)
picc_key = keys.get_picc_master_key_bytes()
```

---

## Examples

### Provisioning
- `22_provision_game_coin.py` - Complete provisioning workflow
- `22a_provision_sdm_factory_keys.py` - Provision without changing keys

### Utilities
- `99_reset_to_factory.py` - Reset tag to factory defaults
- `check_ndef_config.py` - Diagnostic for NDEF and CC files
- `print_asset_tags.py` - List asset tags from database

### Diagnostics
- `10_auth_session.py` - Test authentication
- `20_get_file_counters.py` - Read file counters
- `21_build_sdm_url.py` - Test URL building

---

## Project Structure

```
src/ntag424_sdm_provisioner/
├── commands/              # APDU commands
│   ├── base.py           # Base classes, AuthenticatedConnection
│   ├── authenticate_ev2.py  # EV2 authentication
│   ├── change_key.py     # ChangeKey command
│   ├── change_file_settings.py
│   ├── sun_commands.py   # NDEF read/write
│   ├── iso_commands.py   # ISO 7816 commands
│   ├── select_picc_application.py
│   ├── get_chip_version.py
│   ├── get_file_ids.py
│   ├── get_file_settings.py
│   ├── get_key_version.py
│   ├── get_file_counters.py
│   ├── read_data.py
│   ├── write_data.py
│   ├── sdm_helpers.py    # SDM utilities
│   └── sdm_commands.py   # Compatibility shim
├── crypto/
│   ├── auth_session.py   # Ntag424AuthSession
│   └── crypto_primitives.py  # Verified crypto functions
├── hal.py                # Hardware abstraction
├── csv_key_manager.py    # Key storage
├── constants.py          # Enums, dataclasses
├── uid_utils.py          # UID helpers
└── trace_util.py         # Debug tracing

examples/
├── 22_provision_game_coin.py  # Main provisioning (clean OOP)
├── 99_reset_to_factory.py     # Factory reset utility
└── check_ndef_config.py       # NDEF diagnostics

tests/
├── test_crypto_validation.py  # Crypto vs NXP specs
├── raw_changekey_test_fixed.py  # Raw pyscard test
└── test_production_auth.py    # Production auth test
```

---

## Documentation

- **MINDMAP.md** - Project overview and status
- **ARCH.md** - Detailed architecture diagrams
- **charts.md** - Sequence diagrams with actual flow
- **SUCCESSFUL_PROVISION_FLOW.md** - Captured trace of working provisioning
- **LESSONS.md** - Key learnings and best practices
- **HOW_TO_RUN.md** - Command reference for Windows

---

## Key Classes

### Commands

**`ApduCommand`** - Base for unauthenticated commands:
- `build_apdu()` - Build APDU bytes
- `parse_response()` - Parse response

**`AuthApduCommand`** - Base for authenticated commands:
- `get_command_byte()` - Command byte (e.g., 0xC4)
- `get_unencrypted_header()` - Unencrypted portion
- `build_command_data()` - Plaintext data
- `parse_response()` - Parse decrypted response

### Authentication

**`AuthenticateEV2`** - Protocol orchestrator (callable class):
```python
# Returns AuthenticatedConnection context manager
with AuthenticateEV2(key, key_no=0)(card) as auth_conn:
    # Authenticated operations
    auth_conn.send(ChangeKey(...))
```

**`AuthenticatedConnection`** - Context manager for authenticated operations:
- Transparently handles encryption, CMAC, IV calculation
- Manages session keys and counter
- Delegates to `crypto_primitives.py`

### HAL

**`CardManager`** - Context manager for reader:
```python
with CardManager(reader_index=0) as card:
    # card is NTag424CardConnection
    card.send(Command())
```

**`NTag424CardConnection`** - Card communication:
- `send_apdu()` - Low-level APDU
- `send()` - Execute command object
- `send_write_chunked()` - Multi-chunk writes

---

## Common Tasks

### Read Tag Info
```python
with CardManager() as card:
    card.send(SelectPiccApplication())
    version = card.send(GetChipVersion())
    print(f"UID: {version.uid.hex().upper()}")
    print(f"Asset Tag: {version.get_asset_tag()}")
```

### Authenticate
```python
factory_key = bytes(16)  # 0x00 * 16
with AuthenticateEV2(factory_key, key_no=0)(card) as auth_conn:
    # Authenticated operations
    pass
```

### Change Keys
```python
# Key 0 (no old key)
auth_conn.send(ChangeKey(0, new_key, None))

# Keys 1-4 (old key required)
auth_conn.send(ChangeKey(1, new_key, old_key))
```

### Factory Reset
```python
# Must know old keys for Keys 1 & 3
keys = key_mgr.get_tag_keys(uid)

# Session 1: Reset Key 0
with AuthenticateEV2(keys.get_picc_master_key_bytes(), key_no=0)(card) as auth:
    auth.send(ChangeKey(0, factory_key, None, 0x00))

# Session 2: Reset Keys 1 & 3
with AuthenticateEV2(factory_key, key_no=0)(card) as auth:
    auth.send(ChangeKey(1, factory_key, keys.get_app_read_key_bytes(), 0x00))
    auth.send(ChangeKey(3, factory_key, keys.get_sdm_mac_key_bytes(), 0x00))
```

---

## Troubleshooting

### Authentication Fails (91AE)
**Causes**:
- Wrong key (check database)
- Session invalid (changed Key 0 without re-auth)
- Rate limited (wait 60 seconds)

**Solution**: Check `tag_keys.csv` for status, use correct key

### Rate Limiting (91AD)
**Cause**: Too many failed auth attempts (3-5 limit)

**Solution**: 
- Wait 60+ seconds
- Use fresh tag
- Don't test auth upfront

### Integrity Error (911E)
**Causes**:
- Wrong old key for Keys 1-4 (XOR mismatch)
- CMAC verification failed

**Solution**: Verify old key in database is correct

### SDM Not Working (Placeholders Visible)
**Cause**: ChangeFileSettings returns 917E (LENGTH_ERROR)

**Status**: Known issue, under investigation. Doesn't block provisioning.

---

## Testing

### Run Tests
```bash
# All tests
pytest -v

# Specific test
pytest tests/test_crypto_validation.py -v

# With hardware (requires tag on reader)
pytest tests/test_production_auth.py -v
```

### Mock HAL
```bash
# Run tests without hardware
$env:USE_MOCK_HAL="1"
pytest -v
```

---

## Prerequisites

- **Python 3.8+**
- **PC/SC Compliant NFC Reader** (ACR122U recommended)
- **NXP NTAG424 DNA Tags**
- **Windows/Linux/Mac** with PC/SC drivers

### Dependencies
- `pyscard` - PC/SC interface
- `pycryptodome` - AES, CMAC cryptography

Installed automatically via `pip install -e .`

---

## Security Notes

### Key Storage
- Keys stored in `tag_keys.csv`
- **CRITICAL**: Secure this file (contains all tag keys)
- Automatic backups before changes

### Factory Defaults
- Factory key: `0x00` * 16 (all zeros)
- **NEVER use factory keys in production**
- Always change keys during provisioning

### Rate Limiting
- Tags block auth after 3-5 failed attempts
- Counter persists in non-volatile memory
- 60+ second lockout

---

## API Reference

### Core Classes

**CardManager** - Reader connection:
```python
with CardManager(reader_index=0) as card:
    # Use card
```

**AuthenticateEV2** - Authentication protocol:
```python
with AuthenticateEV2(key, key_no=0)(card) as auth_conn:
    # Authenticated operations
```

**CsvKeyManager** - Key storage:
```python
key_mgr = CsvKeyManager()
keys = key_mgr.get_tag_keys(uid)
with key_mgr.provision_tag(uid, url="...") as new_keys:
    # Provision with two-phase commit
```

### Main Commands

**Unauthenticated**:
- `SelectPiccApplication()` - Select PICC app
- `GetChipVersion()` - Read version + UID
- `GetFileIds()` - List files
- `GetFileSettings(file_no)` - Read file settings
- `GetKeyVersion(key_no)` - Read key version
- `ISOSelectFile(file_id)` - Select ISO file
- `ISOReadBinary(offset, length)` - Read data
- `ChangeFileSettings(config)` - Change file settings (PLAIN mode)

**Authenticated**:
- `ChangeKey(key_no, new_key, old_key)` - Change key
- `ChangeFileSettingsAuth(config)` - Change settings (MAC/FULL modes)

**Special**:
- `WriteNdefMessage(data)` - Write NDEF (chunked)
- `ReadNdefMessage()` - Read NDEF

---

## Examples

### Full Provisioning
```python
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.commands.authenticate_ev2 import AuthenticateEV2
from ntag424_sdm_provisioner.commands.change_key import ChangeKey
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion

key_mgr = CsvKeyManager()
factory_key = bytes(16)

with CardManager() as card:
    # Get UID
    card.send(SelectPiccApplication())
    version = card.send(GetChipVersion())
    uid = version.uid
    
    # Two-phase commit
    with key_mgr.provision_tag(uid, url="https://example.com") as new_keys:
        # Session 1: Change Key 0
        with AuthenticateEV2(factory_key, key_no=0)(card) as auth:
            auth.send(ChangeKey(0, new_keys.get_picc_master_key_bytes(), None))
        
        # Session 2: Change Keys 1 & 3
        with AuthenticateEV2(new_keys.get_picc_master_key_bytes(), key_no=0)(card) as auth:
            auth.send(ChangeKey(1, new_keys.get_app_read_key_bytes(), None))
            auth.send(ChangeKey(3, new_keys.get_sdm_mac_key_bytes(), None))
    
    # Keys automatically saved as 'provisioned'
```

### Read Tag
```python
with CardManager() as card:
    card.send(SelectPiccApplication())
    version = card.send(GetChipVersion())
    
    print(f"UID: {version.uid.hex().upper()}")
    print(f"Hardware: v{version.hardware_protocol}")
    print(f"Software: v{version.software_protocol}")
```

### Factory Reset
```python
keys = key_mgr.get_tag_keys(uid)
factory_key = bytes(16)

# Session 1: Reset Key 0
with AuthenticateEV2(keys.get_picc_master_key_bytes(), key_no=0)(card) as auth:
    auth.send(ChangeKey(0, factory_key, None, 0x00))

# Session 2: Reset Keys 1 & 3
with AuthenticateEV2(factory_key, key_no=0)(card) as auth:
    auth.send(ChangeKey(1, factory_key, keys.get_app_read_key_bytes(), 0x00))
    auth.send(ChangeKey(3, factory_key, keys.get_sdm_mac_key_bytes(), 0x00))

# Update database
key_mgr.save_tag_keys(uid, TagKeys.from_factory_keys(uid.hex().upper()))
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| **MINDMAP.md** | Project overview and current status |
| **ARCH.md** | Architecture diagrams and details |
| **charts.md** | Sequence diagrams |
| **SUCCESSFUL_PROVISION_FLOW.md** | Proven working trace |
| **LESSONS.md** | Key learnings and best practices |
| **HOW_TO_RUN.md** | Windows-specific command reference |

---

## Development

### Running Tests
```bash
# All tests
pytest -v

# Specific module
pytest tests/test_crypto_validation.py -v

# With coverage
pytest --cov=src --cov-report=html
```

### Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Trace Utilities
```python
from ntag424_sdm_provisioner.trace_util import trace_block, trace_apdu, trace_crypto

with trace_block("My Operation"):
    # Code here
    
trace_apdu("Command Name", apdu, response, sw1, sw2)
trace_crypto("Operation", key, input_data, output_data)
```

---

## References

- **NXP AN12196** - NTAG 424 DNA features and hints
- **NXP AN12343** - Session key derivation
- **NXP Datasheet** - NT4H2421Gx NTAG 424 DNA
- **ISO 7816-4** - APDU command structure

---

## Contributing

### Code Style
- Follow PEP 8
- Type hints for all functions
- Docstrings for public APIs
- Single Responsibility Principle
- DRY (Don't Repeat Yourself)

### Testing
- Add tests for new features
- Maintain >50% coverage
- Validate crypto against NXP specs

### Documentation
- Update relevant .md files
- Add examples for new features
- Keep charts.md diagrams current

---

## License

[Your License Here]

---

## Credits

- NXP Semiconductors - NTAG424 DNA chip and specifications
- pyscard project - PC/SC interface
- Crypto primitives verified against NXP official specifications

---

**Status**: ✅ Production Ready  
**Version**: 1.0 (Post-refactor)  
**Last Updated**: 2025-11-08
