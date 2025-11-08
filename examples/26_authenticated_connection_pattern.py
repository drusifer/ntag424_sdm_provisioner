"""
Example: Using AuthenticatedConnection pattern for cleaner authenticated commands.

This demonstrates the new design where authentication returns a context manager
that wraps the connection, making authenticated commands cleaner and more explicit.
"""

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    AuthenticateEV2,
    GetChipVersion,
    GetFileSettings,
    GetKeyVersion,
)
from ntag424_sdm_provisioner.constants import FACTORY_KEY

def main():
    """Demonstrate authenticated connection pattern."""
    
    print("=" * 70)
    print("AUTHENTICATED CONNECTION PATTERN DEMO")
    print("=" * 70)
    print()
    
    # Step 1: Connect to card
    print("[1] Connecting to card...")
    with CardManager(reader_index=0, timeout_seconds=30) as connection:
        print(f"    Connected: {connection}")
        print()
        
        # Step 2: Select application (unauthenticated command)
        print("[2] Selecting PICC application...")
        SelectPiccApplication().execute(connection)
        print("    Application selected")
        print()
        
        # Step 3: Get chip version (unauthenticated command)
        print("[3] Reading chip version...")
        version = GetChipVersion().execute(connection)
        print(f"    Hardware: {version.hw_vendor_id}.{version.hw_type}.{version.hw_subtype} v{version.hw_major_version}.{version.hw_minor_version}")
        print(f"    UID: {version.uid.hex().upper()}")
        print()
        
        # Step 4: Check file settings (unauthenticated - file is CommMode.PLAIN)
        print("[4] Reading file settings (unauthenticated)...")
        settings = GetFileSettings(file_no=2).execute(connection)
        print(f"    File type: {settings.file_type}")
        print(f"    File option: 0x{settings.file_option:02X}")
        
        # Get CommMode using response method (no bitwise math!)
        comm_mode = settings.get_comm_mode()
        print(f"    Comm mode: {comm_mode}")  # Enum __str__ handles formatting
        print(f"    File size: {settings.file_size} bytes")
        
        # Check if authentication is needed
        needs_auth = settings.requires_authentication()
        print(f"    Needs authentication: {needs_auth}")
        print()
        
        # Step 5: Demonstrate authenticated context pattern
        print("[5] Authentication pattern (for files requiring CommMode.MAC)...")
        
        if needs_auth:
            print("    File REQUIRES authentication - using AuthenticateEV2...")
            try:
                with AuthenticateEV2(FACTORY_KEY, key_no=0)(connection) as auth_conn:
                    print(f"    Authenticated: {auth_conn}")
                    
                    # Commands that require CMAC would work here
                    # For this file (CommMode.PLAIN), auth not needed but still works
                    settings2 = GetFileSettings(file_no=2).execute(auth_conn)
                    print(f"    File settings (via auth_conn): {settings2.file_type}")
            except Exception as e:
                if "91AD" in str(e):
                    print("    [INFO] Authentication rate-limited (0x91AD - wait 5s between attempts)")
                else:
                    raise
        else:
            print("    File is CommMode.PLAIN - no authentication needed")
            print("    (Commands work directly without AuthenticatedConnection)")
        print()
        
        print("[6] Pattern complete")
        print()
    
    print("[7] Connection closed")
    print()
    print("=" * 70)
    print("PATTERN BENEFITS:")
    print("=" * 70)
    print("[+] Explicit authentication scope (context manager)")
    print("[+] No session parameters on commands")
    print("[+] Type-safe (AuthenticatedConnection type)")
    print("[+] CMAC handled automatically when needed")
    print("[+] Clean separation: auth vs non-auth")
    print("[+] Check CommMode first - only auth if file requires it")
    print("=" * 70)

if __name__ == "__main__":
    main()

