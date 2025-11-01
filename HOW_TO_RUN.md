# How to Run Scripts and Tests in This Project

**CRITICAL**: This project uses a Python virtual environment at `.venv`. ALL commands MUST use the venv Python.

---

## Base Python Command

```powershell
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe
```

**Always use the `&` operator and forward slashes in PowerShell!**

---

## Running Python Scripts

### Generic Script
```powershell
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe path/to/script.py
```

### Example Scripts
```powershell
# Run chip diagnostic
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe examples/seritag/comprehensive_chip_diagnostic.py

# Run authentication example
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe examples/04_authenticate.py

# Run full chip diagnostic
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe examples/19_full_chip_diagnostic.py
```

---

## Running Pytest Tests

### All Tests
```powershell
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe -m pytest tests/ -v
```

### Specific Test File
```powershell
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe -m pytest tests/ntag424_sdm_provisioner/test_key_manager.py -v
```

### Specific Test Class
```powershell
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe -m pytest tests/ntag424_sdm_provisioner/test_key_manager.py::TestKeyManager -v
```

### Specific Test Method
```powershell
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe -m pytest tests/ntag424_sdm_provisioner/test_key_manager.py::TestKeyManager::test_derive_keys -v
```

### With Mock HAL (no hardware)
```powershell
$env:USE_MOCK_HAL="1"
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe -m pytest tests/ -v
```

---

## Installing/Reinstalling Package

### After adding new Python modules
```powershell
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe -m pip install -e .
```

**Required when:**
- Adding new `.py` files to `src/ntag424_sdm_provisioner/`
- Adding new command modules
- Adding new dataclasses/constants files

**NOT required when:**
- Editing existing files (editable install picks up changes automatically)

---

## Quick Test Import

### Test if a module can be imported
```powershell
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe -c "import ntag424_sdm_provisioner.key_manager_interface; print('Success')"
```

---

## Common Mistakes to Avoid

❌ **WRONG** - Using `python` directly:
```powershell
python script.py  # Uses system Python, not venv!
```

❌ **WRONG** - Using backslashes:
```powershell
& c:\Users\drusi\...\python.exe  # PowerShell escaping issues
```

❌ **WRONG** - Using `cd /d`:
```powershell
cd /d C:\path  # That's CMD syntax, not PowerShell
```

❌ **WRONG** - Forgetting the `&` operator:
```powershell
c:/Users/.../python.exe  # Won't work in PowerShell
```

✅ **CORRECT**:
```powershell
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe script.py
```

---

## Shortcuts (Optional)

### Create a variable for the Python path
```powershell
$python = "c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe"

# Then use it:
& $python script.py
& $python -m pytest tests/ -v
& $python -m pip install -e .
```

---

## Activating Virtual Environment (Alternative)

If you prefer to activate the venv first:

```powershell
# Activate venv
.venv\Scripts\Activate.ps1

# Now you can use python directly
python script.py
python -m pytest tests/ -v

# Deactivate when done
deactivate
```

**Note:** The `&` method is more reliable for one-off commands.

---

## Project Structure Reference

```
ntag424_sdm_provisioner/
├── .venv/                          # Virtual environment
│   └── Scripts/
│       └── python.exe             # ← Use this Python!
├── src/
│   └── ntag424_sdm_provisioner/   # Main package
│       ├── commands/
│       ├── crypto/
│       └── *.py
├── tests/                         # Test files
│   └── ntag424_sdm_provisioner/
│       └── test_*.py
├── examples/                      # Example scripts
│   └── *.py
└── pyproject.toml                # Package config
```

---

**Last Updated:** 2025-11-01  
**Remember:** Always use the full path with `&` operator in PowerShell!

