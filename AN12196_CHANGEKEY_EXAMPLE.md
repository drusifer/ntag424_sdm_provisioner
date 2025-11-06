# AN12196 ChangeKey Example Analysis

## Source
AN12196 Application Note, Table 26 - Example for Cmd.ChangeKey (Case 2: Changing Key 0 while authenticated with Key 0)

## Example Values

```
Old Key (KeyNo 0x00)     = 00000000000000000000000000000000
New Key (KeyNo 0x00)     = 5004BF991F408672B1EF00F08F9E8647
Version (new key)        = 01
KSesAuthMACKey          = 5529860B2FC5FB6154B7F28361D30BF9
KSesAuthENCKey          = 4CF3CB41A22583A61E89B158D252FC53
TI                      = 7614281A
CmdCtr                  = 0300 (little-endian = counter value 3)
```

## Step-by-Step Breakdown

### Step 11: Plaintext Input
```
NewKey || KeyVer || Padding
= 5004BF991F408672B1EF00F08F9E8647 || 01 || 800000000000000000000000000000
= 5004BF991F408672B1EF00F08F9E864701800000000000000000000000000000
  [----------16 bytes-----------]  [1] [--------14 bytes padding-------]
  Total: 32 bytes ✓ Matches our implementation
```

### Step 12: IVc Calculation
```
Current IV = A55A7614281A03000000000000000000
            = A5 5A || TI(7614281A) || CmdCtr(0300) || zeros(8)
            
IVc = E(KSesAuthENC, zero_iv, Current IV)
    = 01602D579423B2797BE8B478B0B4D27B
```

**CRITICAL:** The "Current IV" is the **plaintext IV**, and IVc is the **encrypted IV**!
This matches our implementation ✓

### Step 13: Encrypt Key Data
```
E(KSesAuthENC, IVc, Plaintext Input)
= C0EB4DEEFEDDF0B513A03A95A75491818580503190D4D05053FF75668A01D6FD
  [---------------------------32 bytes encrypted--------------------------]
```

### Step 14: MAC Input
```
Cmd || CmdCtr || TI || CmdHeader || E(KSesAuthEnc, CmdData)
= C4 || 0300 || 7614281A || 00 || C0EB4DEE...
  [1]  [2]     [4]        [1]     [32]
  Total: 40 bytes ✓ Matches our structure
```

### Step 15-16: CMAC
```
CMAC  = B7A60161F202EC3489BD4BEDEF64BB32 (16 bytes)
CMACt = A6610234BDED6432 (8 bytes truncated - even bytes only!)
```

**CRITICAL FINDING:** "MAC Truncation from 16 to 8 byte **by use of the even-numbered bytes**"

This is NOT just taking first 8 bytes - it's taking **even-numbered bytes**!

### Step 17: Final C-APDU
```
90 C4 00 00 29 00 C0EB4DEE...FD A6610234BDED6432 00
[-------] [Lc] [KeyNo][Encrypted 32][CMAC 8]   [Le]
```

## Key Discoveries

1. ✅ **Padding correct:** 0x80 + zeros to 32 bytes
2. ✅ **IV calculation correct:** Encrypt plaintext IV to get actual IV
3. ✅ **MAC input structure correct:** Cmd || CmdCtr || TI || KeyNo || Encrypted
4. ❌ **CMAC TRUNCATION WRONG!** We're taking first 8 bytes, should take **even-numbered bytes**!

## The Bug

**Our code:**
```python
mac = cmac_obj.digest()[:8]  # Take first 8 bytes
```

**Should be:**
```python
mac_full = cmac_obj.digest()  # 16 bytes
mac = bytes([mac_full[i] for i in range(1, 16, 2)])  # Even-numbered bytes: [1,3,5,7,9,11,13,15]
```

This explains why we get INTEGRITY_ERROR - our CMAC is completely wrong!

