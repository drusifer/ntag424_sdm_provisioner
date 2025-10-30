# Seritag NTAG424 DNA Investigation Analysis

**TLDR;**: Seritag tags use modified EV2 firmware. Phase 1 works, Phase 2 fails. Command 0x51 exists but requires authentication. Need to reverse-engineer Seritag's Phase 2 protocol or exploit 0x51 to reset tags.

---

## 🎯 Current Investigation Status

### ✅ **Confirmed Working**
- **Connection**: SelectPiccApplication works (SW=9000)
- **Version Info**: GetChipVersion works (returns HW 48.0, SW 1.2)
- **EV2 Phase 1**: AuthenticateEV2First works correctly (returns encrypted RndB)

### ❌ **Confirmed Failing**
- **EV2 Phase 2**: AuthenticateEV2Second fails with `91AE` (Authentication Error)
- **Full Authentication**: Cannot complete authentication to enable privileged commands
- **Standard Commands**: Most authenticated commands return `911C` (Command Not Supported)

### 🔍 **Partially Discovered**
- **Command 0x51**: Returns `91CA` (Wrong Session State) instead of `911C` (Unsupported)
  - Indicates command exists and requires authentication
  - Different parameters yield different error codes (`6A86`, `917E`, `91CA`)
  - May be Seritag-specific factory/recovery command

---

## 📊 Technical Findings

### **Seritag Hardware Identification**
- **Hardware Version**: 48.0 (vs. standard NXP 4.2)
- **Software Version**: 1.2
- **ATR**: 3B8180018080
- **UID**: 043F684A2F7080 (variable per tag)

### **Authentication Protocol Analysis**

#### **EV2 Phase 1 (Working)**
```
Reader → Tag: 90 71 00 00 02 [KeyNo] [LenCap]
Tag → Reader: [Encrypted RndB (16 bytes)] 91 AF
Reader: Decrypts RndB using factory key (all zeros)
```
**Status**: ✅ **STANDARD NXP BEHAVIOR** - Works correctly with factory key

#### **EV2 Phase 2 (Failing)**
```
Reader → Tag: 90 AF 00 00 20 [E(Kx, RndA || RndB') (32 bytes)] 00
Tag → Reader: 91 AE  (Authentication Error)
```
**Status**: ❌ **SERITAG MODIFICATION** - Expected protocol not accepted

**Hypothesis**: Seritag may use a different Phase 2 protocol:
- Different RndB rotation direction
- Different encryption mode/padding
- Different response format
- Requires intermediate command (0x51?) between phases

---

## 🔬 Command 0x51 Investigation

### **Error Code Analysis**
| Status Code | Meaning | Context |
|------------|---------|---------|
| `91CA` | Wrong Session State | Default response - command exists but requires auth |
| `6A86` | Incorrect P1-P2 | With certain parameter combinations |
| `917E` | Length Error | With certain data lengths |
| `911C` | Command Not Supported | Never returned (unlike other invalid commands) |

### **Parameter Testing Results**
- **Basic**: `90 51 00 00 00` → `91CA`
- **Key Number**: `90 51 00 00 01 [KeyNo] 00` → `91CA` or `6A86`
- **After Phase 1**: Still `91CA` (session state invalid)
- **Variations Tested**: 50+ combinations, no success yet

### **Speculation**
Command 0x51 might be:
- **Factory Reset**: Reset tag to standard NXP behavior
- **Key Recovery**: Unlock/change keys
- **Protocol Switch**: Switch between Seritag/NXP protocols
- **Diagnostic**: Internal Seritag diagnostic command

---

## 🛠️ Investigation Tools Created

### **Analysis Scripts**
1. **`seritag_phase2_analysis.py`**
   - Tests Phase 1 multiple times to analyze challenge patterns
   - Tries different Phase 2 variations (rotation directions, formats)
   - Tests command 0x51 immediately after Phase 1

2. **`seritag_0x51_exploit.py`**
   - Systematic 0x51 parameter brute force
   - Timing variations after Phase 1
   - Different key numbers
   - Command sequence testing

3. **`seritag_cmd_51_investigation.py`**
   - Reconnaissance on command 0x51 variations
   - Nearby command probing
   - Error code analysis

4. **`seritag_recovery_attempts.py`**
   - Factory key variations
   - FORMAT_PICC attempts
   - Alternative authentication protocols

### **Test Infrastructure**
- **`examples/seritag/03_authenticate_seritag.py`**: Authentication diagnostics
- **`tests/ntag424_sdm_provisioner/test_seritag_ev2_compliance.py`**: EV2 compliance testing

---

## 📚 Reference Documentation

### **NXP NTAG424 DNA Specification**
- Standard EV2 authentication protocol (Pages 45-49)
- Status word definitions (Page 45)
- Command structure (Page 17)

### **Seritag Authentication Documentation**
- Located in `investigation_ref/seritag_investigation_reference.md`
- SVG pages showing Seritag-specific implementation
- Authentication flow diagrams

### **Key Status Words**
```
9000  - Success
91AF  - Additional frame expected
91AE  - Authentication error (Phase 2 failure)
91CA  - Wrong session state (0x51 needs auth)
911C  - Command not supported
917E  - Length error
6A86  - Incorrect parameters P1-P2
```

---

## 🎯 Next Steps & Strategy

### **Phase A: Reverse Engineer Phase 2**
1. **Document Analysis**: Deep dive into Seritag SVG authentication pages
2. **Protocol Variations**: Test all possible Phase 2 formats:
   - Different RndB rotation (left/right, different byte counts)
   - Different padding schemes
   - Different encryption modes
   - Multi-frame responses
3. **Timing Analysis**: Check if there's a required delay between Phase 1 and Phase 2

### **Phase B: Exploit Command 0x51**
1. **Complete Authentication**: If we can succeed at Phase 2, try 0x51 authenticated
2. **Parameter Space**: Exhaustive search of P1/P2/Lc/Data combinations
3. **Documentation Research**: Search Seritag docs for 0x51 reference
4. **Reverse Engineering**: If we can capture Seritag's own tool traffic, analyze 0x51 usage

### **Phase C: Alternative Approaches**
1. **EV1 Authentication**: Try legacy EV1 protocol instead of EV2
2. **Factory Keys**: Brute force different factory key values
3. **Hardware Reset**: Physical/power cycling might reset to factory state
4. **Direct Communication**: Bypass reader abstraction, try low-level APDUs

---

## 💡 Key Insights

1. **Seritag Uses Standard Hardware**: Chip is NTAG424 DNA, only firmware is modified
2. **Phase 1 Compatibility**: Seritag maintains standard Phase 1 for backward compatibility
3. **Phase 2 Lockdown**: Modified Phase 2 prevents standard authentication
4. **Command 0x51 Exists**: Confirms Seritag has custom commands
5. **Recovery Possible**: Command 0x51 might enable factory reset or protocol switching

---

## 🚨 Risks & Warnings

- **FORMAT_PICC**: Will permanently erase tag if successful (one-way operation)
- **Key Changes**: Changing keys without proper backup permanently locks tag
- **Brute Force**: Too many authentication attempts may trigger security delays
- **Hardware Damage**: Low-level manipulation could physically damage tag

---

## 📋 Test Execution Plan

### **Immediate Next Steps**
1. ✅ Activate venv (done)
2. Run `seritag_phase2_analysis.py` with real tag
3. Analyze Seritag authentication SVG pages in detail
4. Test Phase 2 with all rotation/padding variations
5. Document exact error codes and timing

### **Short-term Goals**
- Identify exact Phase 2 protocol difference
- Complete authentication with modified protocol
- Successfully execute command 0x51 after authentication
- Document recovery procedure

### **Long-term Goals**
- Build Seritag-aware authentication handler
- Implement automatic protocol detection (HW 48.0 = Seritag)
- Create recovery tool for locked Seritag tags
- Document full Seritag protocol modifications

---

**Last Updated**: Current session  
**Status**: Active Investigation  
**Priority**: High (blocks SDM provisioning for Seritag tags)
