#!/usr/bin/env python3
"""
Example demonstrating the trace utilities for debugging.
"""

import logging

# Setup logging to see trace output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s [%(name)s] %(message)s'
)

from ntag424_sdm_provisioner.trace_util import (
    trace_calls,
    trace_block,
    trace_apdu,
    trace_crypto
)


# Example 1: Trace function calls
@trace_calls
def calculate_session_keys(rnda: bytes, rndb: bytes, key: bytes):
    """Example function with tracing."""
    import time
    time.sleep(0.01)  # Simulate work
    return rnda[:8], rndb[:8]  # Fake session keys


# Example 2: Trace code blocks
def example_with_blocks():
    """Example using trace_block context manager."""
    
    with trace_block("Authentication Phase 1"):
        rndb_encrypted = bytes([0x12, 0x34, 0x56, 0x78] * 4)
        print(f"Received encrypted RndB: {rndb_encrypted.hex()}")
    
    with trace_block("Authentication Phase 2"):
        rnda = bytes([0xAA, 0xBB, 0xCC, 0xDD] * 4)
        rndb = bytes([0x11, 0x22, 0x33, 0x44] * 4)
        
        # This will show the crypto operation
        trace_crypto("Session Key Derivation",
                    rnda=rnda,
                    rndb=rndb,
                    result=rnda[:8])


# Example 3: Trace APDUs
def example_apdu_tracing():
    """Example of APDU tracing."""
    
    # Command APDU
    select_apdu = [0x00, 0xA4, 0x04, 0x00, 0x07, 
                   0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
    trace_apdu(select_apdu, direction=">>", label="Select PICC Application")
    
    # Response APDU
    response = [0x90, 0x00]
    trace_apdu(response, direction="<<", label="Success")
    
    # Long APDU (will be wrapped)
    long_apdu = [0x90, 0xC4, 0x00, 0x00, 0x29, 0x00] + [0xAB] * 40 + [0x00]
    trace_apdu(long_apdu, direction=">>", label="ChangeKey")


# Example 4: Nested tracing
@trace_calls
def outer_function(data: bytes):
    """Example of nested function tracing."""
    with trace_block("Processing data"):
        result = inner_function(data)
    return result


@trace_calls
def inner_function(data: bytes):
    """Inner function that's also traced."""
    return data[:4]


if __name__ == '__main__':
    print("="*70)
    print("TRACE UTILITY EXAMPLES")
    print("="*70)
    print()
    
    print("Example 1: Function call tracing")
    print("-" * 70)
    rnda = bytes([0x10] * 16)
    rndb = bytes([0x20] * 16)
    key = bytes([0x00] * 16)
    enc_key, mac_key = calculate_session_keys(rnda, rndb, key)
    print()
    
    print("Example 2: Block tracing with crypto")
    print("-" * 70)
    example_with_blocks()
    print()
    
    print("Example 3: APDU tracing")
    print("-" * 70)
    example_apdu_tracing()
    print()
    
    print("Example 4: Nested tracing")
    print("-" * 70)
    data = bytes([0xFF] * 32)
    result = outer_function(data)
    print()
    
    print("="*70)
    print("All examples completed!")
    print("="*70)

