# Static URL Provisioning Guide

**Date**: Current session  
**Status**: ✅ **WORKING** - Can provision static URLs without authentication!

---

## Summary

We can now provision Seritag NTAG424 DNA tags with **static URLs** without requiring EV2 authentication. This enables basic game coin functionality immediately, even though SDM/SUN configuration requires authentication.

---

## What Works ✅

### ✅ **NDEF Read/Write Without Authentication**
- **ISOReadBinary** (00 B0): Works after file selection
- **ISOUpdateBinary** (00 D6): Works after file selection
- **File Selection** (00 A4): Works with P1=0x02

### ✅ **Protocol Fixes Applied**
1. **CLA Byte**: ISO commands use CLA=00 (not 90)
2. **File Selection**: ISOSelectFile uses P1=0x02 (select EF under current DF)
3. **Command Format**: All APDU formats correct

---

## What Doesn't Work Yet ⚠️

### ❌ **SDM/SUN Configuration**
- **ChangeFileSettings** (90 5F): Requires Key 0 authentication
- **Current Access Rights**: Change access right = KEY_0 (requires auth)
- **Status**: Need EV2 Phase 2 authentication to enable SDM/SUN

### ❌ **EV2 Authentication Phase 2**
- **Phase 1**: ✅ Works (gets challenge)
- **Phase 2**: ❌ Fails (SW=91AE - Authentication Error)
- **Blocking**: SDM/SUN configuration

---

## Static URL Provisioning Process

### Prerequisites
- Seritag NTAG424 DNA tag (HW 48.0)
- NFC reader (ACR122U or equivalent)
- Python environment with project dependencies

### Step-by-Step Provisioning

#### **1. Select PICC Application**
```python
SelectPiccApplication().execute(card)
```

#### **2. Select NDEF File**
```python
# ISOSelectFile with P1=0x02 (select EF under current DF)
select_apdu = [0x00, 0xA4, 0x02, 0x00, 0x02, 0xE1, 0x04, 0x00]
_, sw1, sw2 = card.send_apdu(select_apdu, use_escape=True)
```

#### **3. Build NDEF URI Record**
```python
from ntag424_sdm_provisioner.commands.sun_commands import build_ndef_uri_record

base_url = "https://game-server.com/verify"
ndef_data = build_ndef_uri_record(base_url)
```

#### **4. Write NDEF to Tag**
```python
from ntag424_sdm_provisioner.commands.sun_commands import WriteNdefMessage

WriteNdefMessage(ndef_data).execute(card)
```

#### **5. Verify (Optional)**
```python
from ntag424_sdm_provisioner.commands.sun_commands import ReadNdefMessage

read_data = ReadNdefMessage(max_length=256).execute(card)
# Check if URL is readable
```

---

## Complete Example Script

```python
#!/usr/bin/env python3
"""Provision static URL to Seritag NTAG424 DNA tag."""

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from ntag424_sdm_provisioner.commands.sun_commands import (
    WriteNdefMessage, ReadNdefMessage, build_ndef_uri_record
)

def provision_static_url(url: str):
    """Provision a static URL to tag without authentication."""
    
    with CardManager(0) as card:
        # 1. Select PICC application
        SelectPiccApplication().execute(card)
        
        # 2. Select NDEF file
        select_apdu = [0x00, 0xA4, 0x02, 0x00, 0x02, 0xE1, 0x04, 0x00]
        _, sw1, sw2 = card.send_apdu(select_apdu, use_escape=True)
        if (sw1, sw2) != (0x90, 0x00):
            raise Exception(f"File selection failed: {sw1:02X}{sw2:02X}")
        
        # 3. Build and write NDEF
        ndef_data = build_ndef_uri_record(url)
        WriteNdefMessage(ndef_data).execute(card)
        
        # 4. Verify
        read_data = ReadNdefMessage(max_length=256).execute(card)
        print(f"Provisioned URL: {url}")
        print(f"NDEF data: {len(read_data)} bytes")
        
        return True

if __name__ == "__main__":
    url = "https://game-server.com/verify"
    provision_static_url(url)
```

---

## File Location

**Save to**: `examples/seritag/provision_static_url.py`

---

## Limitations

### ⚠️ **No Dynamic Authentication**
- Static URLs don't include UID, counter, or MAC
- Server cannot verify authenticity cryptographically
- Vulnerable to replay attacks

### ⚠️ **No SDK/SUN Features**
- Cannot use Secure Dynamic Messaging (SDM)
- Cannot use Secure Unique NFC (SUN)
- Limited to basic URL functionality

### ✅ **Suitable For**
- Development/testing
- Basic NFC tag functionality
- MVP game coin prototype (if authentication not critical)

---

## Next Steps for Full Solution

### **1. Solve EV2 Phase 2 Authentication**
- Current blocker: Phase 2 returns SW=91AE
- Required to enable SDM/SUN configuration
- Investigation ongoing

### **2. Enable SDM/SUN After Authentication**
Once authentication works:
```python
from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
from ntag424_sdm_provisioner.constants import SDMConfiguration, CommMode, AccessRight, AccessRights

config = SDMConfiguration(
    file_no=0x02,
    comm_mode=CommMode.PLAIN,
    access_rights=AccessRights(
        read=AccessRight.FREE,
        write=AccessRight.FREE,
        read_write=AccessRight.FREE,
        change=AccessRight.FREE
    ),
    enable_sdm=True,
    sdm_options=SDMOption.ENABLED | SDMOption.UID_MIRROR | SDMOption.READ_COUNTER,
    # ... offsets ...
)

ChangeFileSettings(config).execute(card, session=authenticated_session)
```

### **3. Full Provisioning Workflow**
1. Authenticate with factory key
2. Change all keys to unique values
3. Re-authenticate with new keys
4. Configure SDM/SUN
5. Write NDEF with placeholders
6. Tags will serve authenticated URLs!

---

## Testing

### **Test Static URL Provisioning**
```bash
python examples/seritag/provision_static_url.py
```

### **Verify with Phone**
1. Provision tag with static URL
2. Tap tag with NFC-enabled phone
3. Phone should open URL in browser
4. URL should be the static URL (no dynamic parameters)

---

## Related Files

- **Implementation**: `src/ntag424_sdm_provisioner/commands/sun_commands.py`
- **Test Script**: `examples/seritag/test_sun_configuration.py`
- **Comprehensive Test**: `examples/seritag/comprehensive_ndef_test.py`

---

## Status

**Current**: ✅ Static URL provisioning works  
**Next**: ⏳ Continue EV2 Phase 2 investigation for SDM/SUN support

