"""
Check ACR122U Registry Settings for Escape Command Enable

According to ACR122U API v2.04 Appendix A, escape commands must be enabled
via a registry key. This script checks if the key exists and is set correctly.
"""
import sys
import platform

def check_registry_key():
    """Check if EscapeCommandEnable registry key is set."""
    
    print("=" * 80)
    print("ACR122U Registry Settings Check")
    print("=" * 80)
    print("\nChecking if PC/SC Escape Command is enabled...")
    
    if platform.system() != "Windows":
        print("\n[INFO] Registry keys are Windows-specific.")
        print("This check only applies to Windows systems.")
        return False
    
    try:
        import winreg
    except ImportError:
        print("\n[ERROR] Could not import winreg module.")
        print("This script requires Windows to check registry keys.")
        return False
    
    # Registry paths to check (from ACR122U spec Appendix A)
    registry_paths = [
        r"SYSTEM\CurrentControlSet\Enum\USB\VID_072F&PID_2200\Device Parameters",
        r"SYSTEM\CurrentControlSet\Enum\USB\VID_072F&PID_90CC\Device Parameters",
        # Also try without VID/PID prefix for direct lookup
    ]
    
    # Also try searching through USB devices
    usb_base = r"SYSTEM\CurrentControlSet\Enum\USB"
    
    print("\nRegistry Paths to Check:")
    for path in registry_paths:
        print(f"  HKLM\\{path}")
    
    found = False
    enabled = False
    
    try:
        # Try to open the USB enumeration key
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, usb_base) as usb_key:
            print(f"\nSearching USB devices...")
            
            # Iterate through subkeys looking for ACR122U devices
            i = 0
            while True:
                try:
                    device_key_name = winreg.EnumKey(usb_key, i)
                    
                    # Check if this looks like an ACR122U device
                    if "VID_072F" in device_key_name.upper() and "PID_2200" in device_key_name.upper():
                        print(f"\n[FOUND] ACR122U device: {device_key_name}")
                        
                        try:
                            device_params_path = f"{usb_base}\\{device_key_name}\\Device Parameters"
                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, device_params_path) as params_key:
                                try:
                                    value, reg_type = winreg.QueryValueEx(params_key, "EscapeCommandEnable")
                                    found = True
                                    print(f"  [FOUND] EscapeCommandEnable = {value} (type: {reg_type})")
                                    if value == 1:
                                        enabled = True
                                        print(f"  [OK] Escape command is ENABLED")
                                    else:
                                        print(f"  [WARN] Escape command is DISABLED (value = {value})")
                                        print(f"        Should be 1 to enable escape commands")
                                except FileNotFoundError:
                                    print(f"  [NOT FOUND] EscapeCommandEnable key does not exist")
                                except Exception as e:
                                    print(f"  [ERROR] Could not read key: {e}")
                        except FileNotFoundError:
                            print(f"  [WARN] Device Parameters subkey not found")
                        except Exception as e:
                            print(f"  [ERROR] Could not access device parameters: {e}")
                    
                    i += 1
                except OSError:
                    break
                    
    except FileNotFoundError:
        print(f"\n[ERROR] Could not find USB enumeration key: HKLM\\{usb_base}")
        print("         Reader may not be connected or drivers not installed")
    except Exception as e:
        print(f"\n[ERROR] Registry access failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Try direct paths
    if not found:
        print("\nTrying direct registry paths...")
        for path in registry_paths:
            try:
                full_path = path
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, full_path) as params_key:
                    try:
                        value, reg_type = winreg.QueryValueEx(params_key, "EscapeCommandEnable")
                        found = True
                        print(f"\n[FOUND] EscapeCommandEnable in HKLM\\{full_path}")
                        print(f"  Value: {value} (type: {reg_type})")
                        if value == 1:
                            enabled = True
                            print(f"  [OK] Escape command is ENABLED")
                        else:
                            print(f"  [WARN] Escape command is DISABLED (value = {value})")
                            print(f"        Should be 1 to enable escape commands")
                    except FileNotFoundError:
                        print(f"  [NOT FOUND] EscapeCommandEnable key does not exist in {full_path}")
            except FileNotFoundError:
                print(f"  [NOT FOUND] Registry path does not exist: HKLM\\{full_path}")
            except Exception as e:
                print(f"  [ERROR] Could not access {full_path}: {e}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if not found:
        print("\n[ISSUE] EscapeCommandEnable registry key not found!")
        print("\nTo enable PC/SC Escape Command (required for escape mode):")
        print("\n1. Open Registry Editor (regedit.exe)")
        print("2. Navigate to:")
        print("   HKLM\\SYSTEM\\CurrentControlSet\\Enum\\USB\\VID_072F&PID_2200\\Device Parameters")
        print("   (Or search for your ACR122U device)")
        print("3. Right-click 'Device Parameters' -> New -> DWORD (32-bit) Value")
        print("4. Name it: EscapeCommandEnable")
        print("5. Double-click it, set Value data to: 1")
        print("6. Base: Hexadecimal")
        print("7. Click OK")
        print("8. Restart the application (may need to unplug/replug reader)")
        print("\n[NOTE] This enables the PC/SC Escape Command which is required")
        print("       for escape mode (control() vs transmit()) operations.")
        return False
    elif not enabled:
        print("\n[ISSUE] EscapeCommandEnable is set but value is not 1!")
        print("\nTo fix:")
        print("1. Open Registry Editor (regedit.exe)")
        print("2. Navigate to the Device Parameters key found above")
        print("3. Double-click EscapeCommandEnable")
        print("4. Set Value data to: 1 (Hexadecimal)")
        print("5. Restart the application")
        return False
    else:
        print("\n[OK] EscapeCommandEnable registry key is correctly set to 1")
        print("     PC/SC Escape Command should be enabled")
        return True


if __name__ == "__main__":
    try:
        result = check_registry_key()
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED]")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

