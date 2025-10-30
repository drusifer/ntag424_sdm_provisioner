"""
Seritag NTAG424 DNA Test Runner

This script runs all Seritag-specific tests in sequence.
"""
import sys
import subprocess
import os

def run_seritag_tests():
    """Run all Seritag NTAG424 DNA tests."""
    
    print("🧪 Seritag NTAG424 DNA Test Suite")
    print("=" * 50)
    
    # Get the examples directory
    examples_dir = os.path.join(os.path.dirname(__file__), 'examples', 'seritag')
    
    tests = [
        ("01_connect_seritag.py", "Connection Test"),
        ("02_get_version_seritag.py", "Version Information Test"), 
        ("03_authenticate_seritag.py", "Authentication Diagnostic")
    ]
    
    results = []
    
    for test_file, test_name in tests:
        print(f"\n🔬 Running {test_name}...")
        print("-" * 30)
        
        test_path = os.path.join(examples_dir, test_file)
        
        try:
            result = subprocess.run([sys.executable, test_path], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✅ {test_name} PASSED")
                results.append((test_name, True, result.stdout))
            else:
                print(f"❌ {test_name} FAILED")
                print(f"   Error: {result.stderr}")
                results.append((test_name, False, result.stderr))
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_name} TIMEOUT")
            results.append((test_name, False, "Timeout"))
        except Exception as e:
            print(f"💥 {test_name} ERROR: {e}")
            results.append((test_name, False, str(e)))
    
    # Summary
    print(f"\n📊 Test Results Summary")
    print("=" * 50)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, output in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Seritag tests passed!")
        return True
    else:
        print("💥 Some Seritag tests failed!")
        return False

if __name__ == "__main__":
    success = run_seritag_tests()
    sys.exit(0 if success else 1)
