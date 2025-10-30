# ACR122U Registry Settings

## Problem

The ACR122U reader requires a registry key to enable PC/SC Escape Commands. Without this key, escape mode operations (using `control()` instead of `transmit()`) may not work correctly, which can cause Phase 2 authentication failures.

## Solution

### Automatic Setup (Recommended)

Run the PowerShell script as Administrator:

```powershell
# Right-click PowerShell -> "Run as Administrator"
cd examples\seritag
.\enable_escape_command.ps1
```

### Manual Setup

1. Open Registry Editor (`regedit.exe`) as Administrator
2. Navigate to:
   ```
   HKLM\SYSTEM\CurrentControlSet\Enum\USB\VID_072F&PID_2200\Device Parameters
   ```
   
   (Or search for your ACR122U device under `HKLM\SYSTEM\CurrentControlSet\Enum\USB`)
   
3. If "Device Parameters" doesn't exist, create it:
   - Right-click the device key → New → Key
   - Name it: `Device Parameters`
   
4. Create the DWORD value:
   - Right-click "Device Parameters" → New → DWORD (32-bit) Value
   - Name it: `EscapeCommandEnable`
   - Double-click it
   - Set Value data to: `1`
   - Base: `Hexadecimal`
   - Click OK

5. Restart:
   - Unplug and replug the ACR122U reader
   - Restart any applications using the reader

## Verify

Run the check script:

```powershell
python examples\seritag\check_reader_registry.py
```

You should see:
```
[OK] EscapeCommandEnable registry key is correctly set to 1
```

## Reference

- **Source**: ACR122U Application Programming Interface V2.04, Appendix A
- **Key Name**: `EscapeCommandEnable`
- **Type**: DWORD (32-bit)
- **Value**: `1` (Hexadecimal)
- **Location**: `HKLM\SYSTEM\CurrentControlSet\Enum\USB\VID_072F&PID_2200\Device Parameters`

## Impact on Phase 2 Authentication

Without this registry key:
- Escape mode commands may be handled incorrectly
- Phase 2 APDUs might be wrapped/unwrapped incorrectly
- Status words may be misinterpreted
- Authentication can fail with `SW=91AE` even if protocol is correct

With this registry key enabled:
- Escape mode (`control()`) works correctly
- APDUs are handled properly
- Phase 2 authentication should work if protocol is correct

## Testing After Setup

After enabling the registry key, test Phase 2 again:

```powershell
python examples\seritag\test_phase2_with_detailed_logging.py
```

If Phase 2 still fails, the issue is likely in the authentication protocol itself (e.g., Seritag-specific differences), not the reader configuration.

