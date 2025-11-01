# Arduino ChangeFileSettings Implementation Analysis

**Source:** MFRC522_NTAG424DNA library (C++)  
**Date:** 2025-11-01

---

## Key Findings

### 1. Field Order (from line 220-221 comment)

```
sendData = FileOption, AccessRights(2), [SDMOptions], [SMDAccessRights(2)], 
           [UIDOffset(3)], [SDMReadCtrOffset(3)], [PICCDataOffset(3)], 
           [SDMMACInputOFFset(3)], [SDMENCOffset(3)], [SDMENCLength(3)], 
           [SDMMACOffset(3)], [SDMReadCtrLimit(3)]
```

**CRITICAL:** Note the order!
- `UIDOffset` comes BEFORE `PICCDataOffset`
- `SDMReadCtrOffset` comes BEFORE `PICCDataOffset`

**Our Order:**
- We're sending: PICCDataOffset, MACInputOffset, MACOffset, ReadCtrOffset
- Missing: UIDOffset field!

### 2. Access Rights Encoding (lines 213-214)

```cpp
sendData[1] = (readWriteAccess << 4) | changeAccess;
sendData[2] = (readAccess << 4) | writeAccess;
```

**Format:** Nibble-packed (each byte = 2 access rights)
- Byte 1[7:4] = ReadWrite access, Byte 1[3:0] = Change access
- Byte 2[7:4] = Read access, Byte 2[3:0] = Write access

**Example:**
- Read=E, Write=E, ReadWrite=E, Change=0
- Byte 1 = (E << 4) | 0 = 0xE0
- Byte 2 = (E << 4) | E = 0xEE
- Result: `0xE0 0xEE` ✓ This matches what we're using!

### 3. SDM Not Implemented in Arduino Library

```cpp
if(SDMEnabled)
    return DNA_SDM_NOT_IMPLEMENTED_IN_LIB;
```

The Arduino library explicitly says "SDM IS NOT SUPPORTED!" (line 97, 207, 969)

**Implication:** We can't use this library as a working reference for SDM!
- It only handles non-SDM ChangeFileSettings
- SDM fields are documented but not implemented
- Need to rely on NXP spec, not this code

### 4. APDU Construction (lines 231-238)

```cpp
sendData2[0] = 0x90; // CLA
sendData2[1] = 0x5F; // CMD
sendData2[2] = 0x00; // P1
sendData2[3] = 0x00; // P2
sendData2[4] = sendDataLen + 1; // Lc (data + FileNo)
sendData2[5] = file; // FileNo
memcpy(&sendData2[6], sendData, sendDataLen);
sendData2[6 + sendDataLen] = 0x00; // Le
```

**Format:** FileNo is sent AFTER the Lc, as first byte of data!
- This matches our implementation ✓

---

## Critical Discovery: Missing UIDOffset!

Looking at the field order comment, when SDM Options includes UID mirroring:

**Required fields:**
1. FileOption
2. AccessRights (2 bytes)
3. SDMOptions
4. SDMAccessRights (2 bytes)
5. **UIDOffset (3 bytes)** ← WE'RE MISSING THIS!
6. SDMReadCtrOffset (3 bytes) - if counter enabled
7. PICCDataOffset (3 bytes) - if encrypted PICC data
8. SDMMACInputOffset (3 bytes) - if CMAC enabled
9. SDMENCOffset (3 bytes) - if encryption enabled
10. SDMENCLength (3 bytes) - if encryption enabled
11. SDMMACOffset (3 bytes) - if CMAC enabled
12. SDMReadCtrLimit (3 bytes) - if limit enabled

---

## What We're Doing Wrong

### Our Current Order:
```
FileOption, AccessRights, SDMOptions, SDMAccessRights,
PICCDataOffset, MACInputOffset, MACOffset, ReadCtrOffset
```

### Correct Order (per spec):
```
FileOption, AccessRights, SDMOptions, SDMAccessRights,
UIDOffset, SDMReadCtrOffset, PICCDataOffset, SDMMACInputOffset,
SDMENCOffset, SDMENCLength, SDMMACOffset, SDMReadCtrLimit
```

**We're missing UIDOffset** and the order is wrong!

---

## Field Presence Logic

From NXP spec and comment:

**UIDOffset (3 bytes):**
- Present if: `SDMOptions[Bit 7] = 1` (UID_MIRROR) AND `SDMMetaRead != Fh`

**SDMReadCtrOffset (3 bytes):**
- Present if: `SDMOptions[Bit 6] = 1` (READ_COUNTER) AND `SDMMetaRead != Fh`

**PICCDataOffset (3 bytes):**
- Present if: `SDMMetaRead = 0..4` (encrypted PICC data)

**SDMMACInputOffset (3 bytes):**
- Present if: `SDMFileRead != Fh` (CMAC enabled)

**SDMMACOffset (3 bytes):**
- Present if: `SDMFileRead != Fh` (CMAC enabled)

---

## Our Mistake

We're treating `PICCDataOffset` as the UID position, but:
- **UIDOffset** = where plain UID is mirrored
- **PICCDataOffset** = where encrypted PICC data (UID+counter) is mirrored

These are DIFFERENT fields!

For plain UID mirroring (what we want), we need **UIDOffset**, not PICCDataOffset!

---

## Correct Implementation

For plain UID + Counter mirroring:

```python
# SDMOptions: Enable + UID Mirror + Read Counter
sdm_options = 0xE0  # Bit 7 (UID), Bit 6 (Counter), Bit 5 (enabled)

# SDMAccessRights:
# Byte 1[7:4] = SDMCtrRet (E = free)
# Byte 1[3:0] = SDMFileRead (F = disabled, we don't want CMAC yet)
# Byte 2[7:4] = RFU (0)
# Byte 2[3:0] = SDMMetaRead (E = plain UID)
sdm_access_rights = [0xEF, 0x0E]

# Field order:
# 1. UIDOffset (3 bytes) - because UID_MIRROR set and SDMMetaRead=E
# 2. SDMReadCtrOffset (3 bytes) - because READ_COUNTER set and SDMMetaRead=E
# 3. NO PICCDataOffset - because SDMMetaRead=E (plain), not 0..4 (encrypted)
# 4. NO SDMMACInputOffset - because SDMFileRead=F (disabled)
# 5. NO SDMMACOffset - because SDMFileRead=F (disabled)
```

---

## Fix Needed

Update `build_sdm_settings_payload()` to:
1. Add UIDOffset field when UID_MIRROR enabled
2. Use correct field order
3. Only include PICCDataOffset if SDMMetaRead=0..4 (encrypted)
4. Only include CMAC offsets if SDMFileRead=0..4 (CMAC enabled)

For our simple case (plain UID + counter, no CMAC):
- Include: UIDOffset, SDMReadCtrOffset
- Exclude: PICCDataOffset, MACInputOffset, MACOffset

---

**Root Cause:** Mixing up UIDOffset vs PICCDataOffset  
**Fix:** Add UIDOffset field and use correct field presence logic  
**Next:** Implement fix in sdm_helpers.py

