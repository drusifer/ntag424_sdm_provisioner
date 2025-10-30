# Seritag Test Results - Critical Analysis

**Date**: Current session  
**Test Run**: `comprehensive_ndef_test.py` with Seritag tag (HW 48.0)

---

## 🔍 Analysis

### Key Finding: **SW=6985 is "Conditions of Use Not Satisfied"**

Per ISO 7816-4 spec, **SW=6985** for ISOReadBinary can mean:
1. **No file selected** ← **LIKELY CAUSE**
2. Targeted file is not StandardData type
3. Application holds a TransactionMAC file

This explains why ISOReadBinary with CLA=00 returns `6985` - **we haven't selected a file yet!**

### Error Code Pattern

| Test | Command | SW | Likely Cause |
|------|---------|----|--------------| 
| File Select | ISOSelectFile (00 A4) | **6A82** | File not found (wrong format?) |
| Read (offset) | ISOReadBinary (00 B0) | **6985** | No file selected (because selection failed) |
| Read (file_id) | ISOReadBinary (00 B0) | **6A82** | Cannot find file by ID |
| Read (CLA=90) | ReadBinary (90 B0) | **917E** | Wrong CLA (expected, confirms fix) |
| ReadData | ReadData (90 BD) | **91BE** | Wrong format used (fixed: was 0xAD, should be 0xBD) |

---

## 🎯 Root Cause Analysis

### The Issue Chain
1. **File Selection Fails** (SW=6A82)
   - ISOSelectFile not finding file E104h
   - Could be wrong format or wrong file ID encoding
   
2. **Read Commands Fail** (SW=6985)
   - Because no file selected
   - ISOReadBinary requires file selection first
   
3. **File ID Mode Fails** (SW=6A82)
   - P1[7]=1 with file ID bits also failing
   - Cannot find file by short file ID

---

## 💡 Key Insights

### 1. Commands ARE Recognized! ✅
- No `911C` (ILLEGAL_COMMAND_CODE) errors
- Command formats are **correct**
- Issue is **access/selection**, not protocol

### 2. File Selection is the Problem
- **Hypothesis**: ISOSelectFile format for file E104h might be wrong
- **Hypothesis**: File might need to be selected differently (by application first?)
- **Hypothesis**: Seritag might use different file ID encoding

### 3. SW=6985 Pattern
- Gets `6985` (conditions not satisfied) when no file selected
- This is **expected behavior** per ISO spec
- If we can fix file selection → reads should work

### 4. Progress Made
- **Before fix**: `911C` (command not supported) - format wrong
- **After fix**: `6985` (conditions not satisfied) - format correct, conditions wrong
- **We're closer!** ✅

---

## 🔧 Next Investigation: File Selection

### ISOSelectFile Format Check
From spec:
- **ISOSelectFile**: `00 A4 P1 P2 Lc [Data] Le`
- **For File ID**: P1=00/01/02, P2=00, Lc=02, Data=File ID (2 bytes), Le=00

Current code uses:
- P1=0x04 (select by DF Name) - **WRONG for file ID!**
- Should use P1=0x00, 0x01, or 0x02 for file ID selection

### Test Variations Needed
1. **P1=0x00** (select by file ID, first occurrence)
2. **P1=0x01** (select by file ID, next occurrence)
3. **P1=0x02** (select by file ID, child DF)

---

**Status**: Format bugs fixed. File selection format likely wrong. Need to fix ISOSelectFile P1 value!
