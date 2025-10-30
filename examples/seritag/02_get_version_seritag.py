"""
Seritag NTAG424 DNA Version Information Test

This script tests getting version information from a Seritag NTAG424 DNA tag.
It demonstrates the differences between Seritag and standard NXP tags.
"""
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

from ntag424_sdm_provisioner.seritag_simulator import SeritagCardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion

def test_seritag_version():
    """Test getting version information from Seritag NTAG424 DNA tag."""
    
    print("📋 Seritag NTAG424 DNA Version Information Test")
    print("=" * 60)
    
    try:
        with SeritagCardManager(0) as card:
            print("✅ Connected to Seritag NTAG424 DNA tag")
            
            # Select PICC application
            print("\n📱 Selecting PICC application...")
            SelectPiccApplication().execute(card)
            print("✅ PICC application selected")
            
            # Get chip version
            print("\n🔍 Getting chip version information...")
            version_info = GetChipVersion().execute(card)
            
            print(f"\n📊 Seritag NTAG424 DNA Version Information:")
            print(f"   UID: {version_info.uid.hex().upper()}")
            print(f"   Hardware Version: {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"   Software Version: {version_info.sw_major_version}.{version_info.sw_minor_version}")
            print(f"   Hardware Storage: {version_info.hw_storage_size} bytes")
            print(f"   Software Storage: {version_info.sw_storage_size} bytes")
            print(f"   Batch Number: {version_info.batch_no.hex().upper()}")
            print(f"   Fabrication: Week {version_info.fab_week}, Year {version_info.fab_year}")
            print(f"   Hardware Protocol: {version_info.hw_protocol}")
            print(f"   Software Protocol: {version_info.sw_protocol}")
            print(f"   Hardware Type: {version_info.hw_type}")
            print(f"   Software Type: {version_info.sw_type}")
            
            # Compare with standard NXP expectations
            print(f"\n🔍 Comparison with Standard NXP NTAG424 DNA:")
            print(f"   Expected HW Version: 4.2")
            print(f"   Actual HW Version: {version_info.hw_major_version}.{version_info.hw_minor_version}")
            
            if version_info.hw_major_version == 4 and version_info.hw_minor_version == 2:
                print("   ✅ Hardware version matches standard NXP")
            else:
                print("   ⚠️  Hardware version differs from standard NXP (Seritag variant)")
                
            print("\n✅ Version information retrieved successfully")
            
    except Exception as e:
        print(f"❌ Version test failed: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = test_seritag_version()
    if success:
        print("\n🎉 Seritag version test completed successfully!")
    else:
        print("\n💥 Seritag version test failed!")
        sys.exit(1)
