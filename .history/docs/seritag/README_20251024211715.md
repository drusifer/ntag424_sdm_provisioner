# Seritag NTAG424 DNA Documentation

This directory contains Seritag-specific documentation and specifications for NTAG424 DNA NFC tags.

## Overview

Seritag produces NTAG424 DNA NFC tags with customized firmware and authentication protocols. These tags are designed for secure applications including product authentication and anti-counterfeiting.

## Key Differences from Standard NXP NTAG424 DNA

### Hardware Version
- **Standard NXP**: Hardware version 4.2
- **Seritag**: Hardware version 48.0 (observed in testing)

### Authentication Protocol
- **Standard NXP**: EV2 authentication with factory keys (all zeros)
- **Seritag**: May use modified EV2 or custom authentication protocol

### Key Management
- **Standard NXP**: Factory keys are all zeros (00000000000000000000000000000000)
- **Seritag**: May use different factory keys or key derivation

## Seritag NTAG424 DNA Features

### SUN (Secure Unique NFC) Message System
- Dynamic data addition to NDEF message on each scan
- Unique secure code generation
- Encrypted UID and scan counter
- Authentication without dedicated app

### Available Variants
- **Standard NTAG424 DNA**: Basic secure authentication
- **NTAG424 DNA TT**: Tag Tamper variant with tamper detection

### Physical Formats
- 40x25mm Wet Inlay NTAG424
- 48x78mm Clear NTAG424  
- 28mm Tamper Tag NTAG424
- 6mm On-Metal PCB NTAG424

## Authentication Flow

### Standard NXP Flow
1. Select PICC Application
2. Get Chip Version
3. AuthenticateEV2First (Phase 1)
4. AuthenticateEV2Second (Phase 2)
5. Derive session keys
6. Execute authenticated commands

### Seritag Flow (To Be Determined)
1. Select PICC Application ✓
2. Get Chip Version ✓ (returns HW 48.0)
3. Authentication method: **UNKNOWN** (EV2 fails with 0x917E)
4. Alternative protocols to investigate:
   - Modified EV2
   - EV1 authentication
   - Custom Seritag protocol
   - Different key management

## Testing Results

### Observed Behavior
- **ATR**: 3B8180018080
- **UID**: 043F684A2F7080
- **Hardware Version**: 48.0 (not 4.2)
- **Software Version**: 1.2
- **Authentication**: All EV2 attempts fail with 0x917E (SW_AUTH_FAILED)

### Commands That Work
- SelectPiccApplication: ✓ (SW=9000)
- GetChipVersion: ✓ (returns version info)

### Commands That Fail
- AuthenticateEV2First: ❌ (SW=917E for all keys 0-4)

## Next Steps

1. **Research Seritag Authentication**: Find official Seritag documentation
2. **Create Simulation**: Build Seritag HAL simulator for testing
3. **Test Alternative Protocols**: Try EV1, custom protocols
4. **Key Discovery**: Determine correct factory keys
5. **Protocol Implementation**: Implement working authentication

## References

- [Seritag NTAG424 DNA Products](https://seritag.com/nfc-tags/authentication)
- [Seritag News: New NTAG424 DNA NFC Tags](https://seritag.com/news/new-ntag424-dna-nfc-tags)
- NXP NTAG424 DNA Datasheet (for comparison)
