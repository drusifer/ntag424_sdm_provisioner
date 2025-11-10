# AN12343 ChangeKey Analysis

## Source
AN12343 (MIFARE DESFire Light Features and Hints) - More detailed than AN12196

## Key Sections

### CMAC Truncation (Line 976)
> "The 16 byte MAC is truncated to an 8 byte MAC, using only the **even bytes in most significant order**"

**Applies to:** ALL AES Secure Messaging in DESFire/NTAG424

### Encryption Padding (Line 987)
> "Padding is done according to Padding Method 2 (**0x80 followed by zero bytes**) of ISO/IEC 9797-1"

**Note:** "if the original data is already a multiple of 16 bytes, another additional padding block (16 bytes) is added"
**Exception:** "The only exception is during the authentication itself, where no padding is applied at all"

### IV Calculation (Lines 993-999)
```
IV for CmdData  = E(KSesAuthENC, 0xA5 || 0x5A || TI || CmdCtr || 0x0000000000000000)
IV for RespData = E(KSesAuthENC, 0x5A || 0xA5 || TI || CmdCtr || 0x0000000000000000)
```

"The CmdCtr to be used for the IV calculation always represents the **current value**"

## Table 40: ChangeKey Case 2 (Key 0 while auth with Key 0)

### Input Values
```
KeyNo          = 00
Old KeyValue   = 00000000000000000000000000000000
New KeyValue   = 01234567890123456789012345678901
New KeyVersion = 00
TI             = 94297F4D
CmdCounter     = 0000 (after auth)
SesAuthENCKey  = E156C8522F7C8DC82B0C99BA847DE723
SesAuthMACKey  = 45D50C1570000D2F173DF949288E3CAD
```

### Encryption (Rows 16-20)
```
IV_Input      = A55A || 94297F4D || 0000 || 0000000000000000
IV            = 00000000000000000000000000000000 (zero IV for encrypting IV_Input)
IV for CmdData = E(KSesAuthENC, IV_Input) = BF4A2FB89311ED58E9DCBE56FC17794C

Data          = NewKeyValue || NewKeyVersion || Padding
              = 01234567890123456789012345678901 || 00 || 800000000000000000000000000000
              = 0123456789012345678901234567890100800000000000000000000000000000

Encrypted     = E(KSesAuthENC, IV_for_CmdData, Data)
              = BF5400DC97A1FBD65BE870716D6F11F8161BB4CA472856DB94AB94B2EC1A13E6
```

### CMAC (Rows 21-23)
```
IV            = 00000000000000000000000000000000
MAC_Input     = Ins || CmdCounter || TI || CmdHeader || Encrypted Data
              = C4 || 0000 || 94297F4D || 00 || BF5400DC97A1FBD65BE870716D6F11F8161BB4CA472856DB94AB94B2EC1A13E6
              
MAC (full 16) = CMAC(KSesAuthMAC, MAC_Input)
              = (not shown - but truncated to:)
              
MAC (truncated 8) = 27CE07CF56C11091
```

### Final APDU (Row 24-31)
```
Data = CmdHeader || Encrypted Data || MAC
     = 00 || BF5400DC...E6 || 27CE07CF56C11091
     = 1 + 32 + 8 = 41 bytes

C-APDU = 90 C4 00 00 29 00BF5400DC...E627CE07CF56C1109100
        [CLA][Ins][P1][P2][Lc][----------41 bytes Data---------][Le]
```

## Comparison with Our Implementation

### What Matches ✓
- Padding: 0x80 + zeros ✓
- IV calculation: E(zero_iv, A5 5A || TI || CmdCtr || zeros) ✓
- MAC input structure: Ins || CmdCtr || TI || KeyNo || Encrypted ✓
- Counter: 0000 after auth ✓
- Even-numbered truncation ✓

### Potential Differences to Check

1. **Padding for 17-byte data (Key 0):**
   - Spec says: "if already multiple of 16, add ANOTHER 16-byte block"
   - 17 bytes → NOT multiple of 16 → add 0x80 + 14 zeros = 32 bytes ✓
   - But what if they mean something different?

2. **CRC32 for non-zero keys:**
   - AN12343 Table 39 row 19 shows CRC32 = A0A60868
   - We're inverting - is this correct?

3. **Counter management:**
   - When exactly is it incremented?
   - Are we using the right value for IV vs CMAC?

4. **Session key derivation:**
   - Are our session keys correct?
   - Should verify with known test vectors

## Next Steps

1. Compare our session keys with AN12343 examples
2. Verify CRC32 calculation matches
3. Check if padding logic correct for 17-byte input
4. Create test with exact values from Table 40 to isolate issue







