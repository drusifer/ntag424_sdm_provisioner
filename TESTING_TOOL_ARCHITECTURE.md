# Testing Tool Architecture - Guide

**Goal**: Validate the new tool-based architecture works with real hardware

---

## What We're Testing

### Current Implementation:
- ✅ ToolRunner (main loop with connect/disconnect per operation)
- ✅ TagState assessment (reads UID, database, NDEF, backups)
- ✅ Tool filtering by preconditions
- ✅ DiagnosticsTool (displays complete tag info)

### What Should Work:
1. **Connection Management**: Connect → operation → disconnect → repeat
2. **Tag Detection**: Assess tag state automatically
3. **Menu Display**: Show available tools (just Diagnostics for now)
4. **Diagnostics Execution**: Display chip info, keys, NDEF
5. **Tag Swapping**: Should work between operations
6. **Error Recovery**: Should handle rate limits, connection issues

---

## Test Script

**Location**: `examples/tag_tool_demo.py`

**What It Does**:
```
1. Connects to reader (waits for tag)
2. Assesses tag state (UID, database status, NDEF, backups)
3. Shows menu: [1. Show Diagnostics | q. Quit]
4. Executes tool
5. Disconnects
6. Waits for next operation (can swap tags here)
7. Repeat
```

---

## How to Run

### Step 1: Place Tag on Reader

```powershell
cd examples
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe tag_tool_demo.py
```

### Step 2: Expected Output

```
======================================================================
NTAG424 Tag Tool (Demo Version)
======================================================================

Available tools:
  - Diagnostics Tool (show complete tag information)

Coming soon:
  - Provision Factory Tool
  - Restore Backup Tool
  - Update URL Tool
  - And more...

======================================================================
NTAG424 Tag Tool
======================================================================
Place tag on reader to begin

Press Enter when ready...
```

### Step 3: Press Enter (Tag Should Be On Reader)

Expected:
```
INFO:ntag424_sdm_provisioner.tools.runner:Connecting to tag...
INFO:ntag424_sdm_provisioner.tools.runner:Connected to tag
INFO:ntag424_sdm_provisioner.tools.runner:Assessing tag state for UID: 04XXXXXX [XX-XXXX]

======================================================================
NTAG424 Tag Tool Menu
======================================================================
Tag: XX-XXXX (UID: 04XXXXXX)
Database: <status>
======================================================================
Available tools:

  1. Show Diagnostics
     Display complete tag information (chip, keys, NDEF)

  q. Quit
======================================================================
Select tool:
```

### Step 4: Select "1" for Diagnostics

Expected:
- Complete chip information display
- Key versions
- NDEF content
- Database/backup status

### Step 5: After Tool Completes

```
======================================================================
Press Enter for next operation (or 'q' to quit):
```

**At this point you can:**
- Press Enter to run another operation on same tag
- Remove tag, place different tag, press Enter (tests tag swapping!)
- Press 'q' to quit

---

## Test Cases

### Test 1: Basic Operation ✓ / ✗
- [ ] Script starts without errors
- [ ] Connects to tag
- [ ] Shows menu with tag info
- [ ] Diagnostics tool runs successfully
- [ ] Disconnects cleanly
- [ ] Returns to menu

### Test 2: Tag Swapping ✓ / ✗
- [ ] Run diagnostics on Tag A
- [ ] Remove Tag A
- [ ] Place Tag B on reader
- [ ] Press Enter
- [ ] Connects to Tag B (different UID detected)
- [ ] Diagnostics shows Tag B info

### Test 3: Error Recovery ✓ / ✗
- [ ] Remove tag while at menu
- [ ] Select diagnostics
- [ ] Should error gracefully
- [ ] Should return to menu prompt
- [ ] Place tag back on reader
- [ ] Press Enter
- [ ] Should connect and work

### Test 4: Multiple Operations ✓ / ✗
- [ ] Run diagnostics 3 times in a row
- [ ] Each operation connects/disconnects
- [ ] No connection issues or stale state

---

## Expected Behavior

### ✅ Success Criteria:
1. No crashes or exceptions
2. Clean connect/disconnect cycles
3. Accurate tag state detection
4. Complete diagnostics display
5. Can swap tags between operations
6. Graceful error handling

### ❌ Known Limitations:
1. Only one tool available (Diagnostics)
2. No provisioning capability yet
3. No backup restore yet
4. Cannot modify tag (read-only operations)

---

## Troubleshooting

### "No reader found"
- Check reader is connected via USB
- Check reader drivers installed
- Try specifying reader: modify `tag_tool_demo.py` line with reader name

### "Connection timeout"
- Ensure tag is on reader before pressing Enter
- Try removing and replacing tag
- Check reader LED (should show tag present)

### "Rate limit (0x91AE)"
- This shouldn't happen with Diagnostics (no auth)
- If it does, wait 60s and try again

### Script hangs
- Ctrl+C to interrupt
- Check if tag is still on reader
- Restart script

---

## Next Steps After Testing

### If Architecture Works Well:
✅ Continue building remaining tools:
- provision_factory_tool.py
- restore_backup_tool.py  
- update_url_tool.py
- factory_reset_tool.py

### If Issues Found:
❌ Fix architecture issues before proceeding:
- Connection management bugs
- State detection problems
- Menu/UI issues
- Error handling gaps

---

## Feedback Checklist

After testing, note:
- [ ] Does connect/disconnect per operation work well?
- [ ] Is tag state detection accurate?
- [ ] Is the menu clear and usable?
- [ ] Does tag swapping work?
- [ ] Any unexpected errors or behaviors?
- [ ] UX improvements needed?
- [ ] Ready to add more tools?

---

**Ready to test!** 🚀

Place a tag on the reader and run the command above.

