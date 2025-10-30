"""
Seritag NTAG424 DNA Connection Test

This script tests basic connection to a Seritag NTAG424 DNA tag.
It uses the Seritag simulator to test the connection flow.
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

def test_seritag_connection():
    """Test connection to Seritag NTAG424 DNA tag."""
    
    print("🔌 Seritag NTAG424 DNA Connection Test")
    print("=" * 50)
    
    try:
        with SeritagCardManager(0) as card:
            print("✅ Successfully connected to Seritag NTAG424 DNA tag")
            print("✅ Connection test passed")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = test_seritag_connection()
    if success:
        print("\n🎉 Seritag connection test completed successfully!")
    else:
        print("\n💥 Seritag connection test failed!")
        sys.exit(1)
