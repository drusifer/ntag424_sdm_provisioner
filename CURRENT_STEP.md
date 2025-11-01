# Current Step: Fix SDM Configuration for Game Coin Provisioning

TLDR; Refactoring complete ✅. Auth + NDEF write working ✅. Blocking issue: ChangeFileSettings returns 0x917E (length error). Goal: Debug and fix SDM configuration to enable tap-unique URLs.

---

## Step Goal

Fix ChangeFileSettings command to successfully enable SDM on NDEF file, allowing game coins to generate tap-unique authenticated URLs.

---

## Context

### What's Working ✅
1. **Authentication** - Full EV2 auth with factory keys
2. **NDEF Write** - Can write 87-byte URLs using ISOUpdateBinary
3. **URL Building** - Proper NDEF structure with placeholders
4. **KeyManager** - SimpleKeyManager provides keys

### What's Blocked ❌
**SDM Configuration fails with 0x917E (NTAG_LENGTH_ERROR)**
- Command: ChangeFileSettings
- Error: Length error on Seritag NTAG424 DNA
- Impact: Placeholders won't be replaced (not dynamic)

---

## User Story

**As a developer**, I want to enable SDM on the NDEF file, so that the tag generates tap-unique URLs with UID, counter, and CMAC authentication.

**Acceptance Criteria:**
- [x] Can authenticate with tag
- [x] Can build SDM configuration
- [ ] ChangeFileSettings succeeds (SW=9000)
- [ ] GetFileCounters returns counter (not 0x911C)
- [ ] Tag fills placeholders when tapped

---

## Investigation Plan

### Step 1: Debug ChangeFileSettings Payload
1. Log exact APDU bytes being sent
2. Compare with NXP specification
3. Check build_sdm_settings_payload() output
4. Identify length mismatch

### Step 2: Test Simpler SDM Configuration
1. Try minimal SDM config (just enable, no options)
2. Test without CMAC mirroring
3. Test with just UID mirroring
4. Find what works

### Step 3: Research Seritag-Specific Requirements
1. Check if Seritag SDM differs from standard
2. Review NT4H2421Gx.md for ChangeFileSettings spec
3. Look for byte-level examples

### Step 4: Fix and Verify
1. Implement fix based on findings
2. Test with real chip
3. Verify GetFileCounters works after config
4. Tap coin and verify dynamic URL

---

## Implementation Plan

### Phase 1: Add Detailed Logging
Create diagnostic script to see exact bytes:

```python
def debug_sdm_config():
    # Build SDM config
    config = SDMConfiguration(...)
    
    # Log payload
    payload = build_sdm_settings_payload(config)
    print(f"Payload: {payload.hex()}")
    print(f"Payload length: {len(payload)}")
    
    # Build full APDU
    apdu = build_change_file_settings_apdu(config)
    print(f"APDU: {' '.join(f'{b:02X}' for b in apdu)}")
    print(f"APDU length: {len(apdu)}")
```

### Phase 2: Test Minimal Config
Try absolute simplest SDM configuration:

```python
# Minimal: Just enable SDM, no mirroring
config = SDMConfiguration(
    file_no=0x02,
    comm_mode=CommMode.PLAIN,
    access_rights=b'\xEE\xEE',  # All free
    enable_sdm=False,  # Start with SDM disabled
)
# If this works, add features one by one
```

### Phase 3: Compare with Working Example
Check if any existing examples successfully use ChangeFileSettings.

### Phase 4: Implement Fix
Based on findings, fix:
- Payload length calculation
- SDM options byte encoding
- Offset encoding (3 bytes LSB-first)
- Access rights format

---

## Acceptance Tests

**Test 1: ChangeFileSettings Succeeds**
```python
def test_change_file_settings_minimal():
    """ChangeFileSettings with minimal config succeeds"""
    # Authenticate
    # Configure SDM (minimal)
    # Expect: SW=9000
```

**Test 2: GetFileCounters Works After SDM**
```python
def test_file_counters_after_sdm():
    """GetFileCounters returns counter after SDM enabled"""
    # Configure SDM
    # Read counter
    # Expect: Integer 0-16777215 (not error)
```

**Test 3: Tag Fills Placeholders**
```python
def test_tap_generates_dynamic_url():
    """Tapping tag generates URL with real values"""
    # Configure SDM
    # Write NDEF with placeholders
    # Read back (simulates tap)
    # Expect: Real UID, not 00000000000000
```

---

## Expected Outcome

After this step:
- ✅ ChangeFileSettings succeeds
- ✅ SDM enabled on NDEF file
- ✅ GetFileCounters returns actual counter
- ✅ Tag generates tap-unique URLs
- ✅ Ready for server-side validation (Phase 4)

---

## Progress Tracking

### Completed
- [x] Identified blocking issue (ChangeFileSettings length error)
- [x] Authentication pipeline working
- [x] NDEF write pipeline working
- [x] URL building working

### In Progress
- [ ] Debug ChangeFileSettings payload
- [ ] Test simpler SDM configurations
- [ ] Fix length error
- [ ] Verify SDM works

### Pending
- [ ] CMAC validation (Phase 4)
- [ ] Server endpoint examples (Phase 4)
- [ ] Mock HAL SDM simulation (Phase 5)

---

**Status:** Starting debug of ChangeFileSettings  
**Estimated Duration:** 1-2 hours  
**Blockers:** None - have all tools and access to chip  
**Next:** Create debug script for ChangeFileSettings
