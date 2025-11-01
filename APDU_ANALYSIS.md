# ChangeFileSettings APDU Analysis

**Actual APDU Sent:**
```
90 5F 00 00 0A 02 40 E0 EE C0 EF 0E 2F 00 00 00
```

## Byte-by-Byte Breakdown

| Byte(s) | Hex | Decimal | Field | Value |
|---------|-----|---------|-------|-------|
| 0 | 90 | 144 | CLA | DESFire/NTAG424 |
| 1 | 5F | 95 | INS | ChangeFileSettings |
| 2 | 00 | 0 | P1 | (none) |
| 3 | 00 | 0 | P2 | (none) |
| 4 | 0A | 10 | Lc | 10 bytes of data |
| 5 | 02 | 2 | FileNo | NDEF file |
| 6 | 40 | 64 | FileOption | Bit 6 set (SDM enabled), CommMode=PLAIN |
| 7-8 | E0 EE | | AccessRights | RW/Change=E, Read/Write=E (free) |
| 9 | C0 | 192 | SDMOptions | Bit 7 (UID_MIRROR) + Bit 6 (enabled) |
| 10-11 | EF 0E | | SDMAccessRights | CtrRet=E, FileRead=F, MetaRead=E |
| 12-14 | 2F 00 00 | 47 | UIDOffset | Position 47 (LSB-first) |
| 15 | 00 | 0 | Le | Expect response |

**Total:** 16 bytes (APDU header + data + Le)

---

## Problem Analysis

**SDMOptions = 0xC0 = Binary 11000000**
- Bit 7 = 1 (UID_MIRROR enabled) ✓
- Bit 6 = 1 (??? - this should be READ_COUNTER, not SDM enable)
- Bit 5 = 0 (READ_COUNTER limit not set)
- ...

**WAIT!** I think I found the bug!

Looking at FileOption constants:
- SDM_ENABLED = 0x40 (this goes in FileOption byte, not SDMOptions!)
- UID_MIRROR = 0x80 (this goes in SDMOptions)
- READ_COUNTER = 0x20 (this goes in SDMOptions)

**Our SDMOptions byte:**
- We're setting: `SDM_ENABLED | UID_MIRROR` = 0x40 | 0x80 = 0xC0
- But SDM_ENABLED (0x40) should NOT be in SDMOptions!
- It should ONLY be in FileOption!

**Correct values:**
- FileOption = 0x40 (SDM enabled) ✓ We have this
- SDMOptions = 0x80 (just UID_MIRROR) ← We have 0xC0 (wrong!)

---

## The Bug

We're combining `FileOption.SDM_ENABLED` into SDMOptions, but SDM_ENABLED (0x40) belongs in FileOption, NOT SDMOptions!

**Wrong:**
```python
sdm_options = FileOption.SDM_ENABLED | FileOption.UID_MIRROR  # 0xC0
```

**Correct:**
```python
sdm_options = FileOption.UID_MIRROR  # 0x80 (no SDM_ENABLED flag here!)
```

The SDM_ENABLED flag is already set in FileOption byte (bit 6). Don't duplicate it in SDMOptions!

---

## Fix

In examples, use:
```python
sdm_options=FileOption.UID_MIRROR | FileOption.READ_COUNTER  # NO SDM_ENABLED!
```

NOT:
```python
sdm_options=FileOption.SDM_ENABLED | FileOption.UID_MIRROR  # Wrong!
```

---

**Root Cause:** Using SDM_ENABLED constant in wrong field  
**Fix:** Remove SDM_ENABLED from sdm_options (it belongs in FileOption only)

