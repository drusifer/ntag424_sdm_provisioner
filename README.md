# **NTAG424 SDM Provisioner**

TLDR; **Type-Safe Architecture COMPLETE** ✅ - 72/74 tests passing. Commands type-enforce auth (`ApduCommand` vs `AuthApduCommand`). No if/else branches. Crypto validated vs NXP spec (11 tests). DNA_Calc → test package (reference). ChangeKey + ChangeFileSettings refactored. Coverage 56%. Production ready. See `TYPE_SAFE_ARCHITECTURE.md`, `ARCH.md`, `HOW_TO_RUN.md`.

This project provides a Python-based toolkit for provisioning NXP NTAG424 DNA NFC tags for Secure Dynamic Messaging (SDM). It offers a modular, command-oriented framework for interacting with the tag at a low level, enabling developers to perform a full provisioning sequence from a factory-default state.

## **Recent Updates (2025-11-06)**

### Type-Safe Architecture Implementation ✅

**Design Principles:**
- **Type Safety**: Commands declare auth requirements via method signatures
  - `ApduCommand.execute(connection: NTag424CardConnection)` - No auth
  - `AuthApduCommand.execute(auth_conn: AuthenticatedConnection)` - Auth required
  - Type checkers (mypy, IDE) catch errors at development time
  
- **Single Source of Truth**: All crypto operations in `AuthenticatedConnection`
  - `encrypt_and_mac()` - For CommMode.FULL (encryption + CMAC)
  - `apply_mac_only()` - For CommMode.MAC (CMAC only)
  - Zero crypto code duplication
  
- **Clean Separation**: Commands build data, connections handle crypto
  - Commands: Data builders (what to send)
  - Connections: Crypto operations (how to protect)
  
- **Explicit Scope**: Context managers for authentication lifetime
  - Authentication scope clearly defined by `with` blocks
  - Auto-cleanup when exiting context
  - No leaked session keys

**Test Coverage:** 10/12 tests passing for new architecture

### Example - Type-Safe Usage:
```python
# Type-safe authenticated command flow
with CardManager() as card:  # card: NTag424CardConnection
    
    # Unauthenticated commands (type-safe)
    SelectPiccApplication().execute(card)  # ✅ Takes NTag424CardConnection
    version = GetChipVersion().execute(card)

    # Authenticated session (context manager)
    with AuthenticateEV2(FACTORY_KEY, 0).execute(card) as auth_conn:
        # auth_conn: AuthenticatedConnection
        
        # Authenticated commands (type-safe)
        ChangeKey(0, new, old).execute(auth_conn)  # ✅ Takes AuthenticatedConnection
        ChangeFileSettings(config).execute(auth_conn)
    
    # Auth session closed, keys wiped
```

### Type Safety Example:
```python
# ❌ Type checker catches this error:
with CardManager() as card:
    ChangeKey(0, new, old).execute(card)
    # ERROR: Argument 1 has incompatible type "NTag424CardConnection"
    #        expected "AuthenticatedConnection"
```

## **Features**

* **Hardware Abstraction Layer (HAL):** Clean interface for PC/SC compliant NFC readers via pyscard.  
* **Command Architecture:** Each NTAG424 command as distinct class with automatic error handling and multi-frame support.  
* **Authenticated Session Management:** Context manager pattern for EV2 authentication with automatic CMAC application.  
* **Enum Constants:** Self-documenting enums with auto-formatting (e.g., `CommMode.PLAIN (0x00)`).  
* **Type-Safe API:** Dataclass-based configuration, commands work with both regular and authenticated connections.
* **Encapsulated Encoding:** High-level classes handle byte encoding internally (no manual `.to_bytes()` calls).
* **Specific Exceptions:** Descriptive exception classes for different error conditions (polymorphic error handling).
* **SDM Support:** Commands for GetFileCounters, ChangeFileSettings, NDEF building with placeholders.
* **Examples:** 10 working examples including authenticated connection pattern, provisioning workflow, chip diagnostics.

## **Prerequisites**

* **Python 3.8+**  
* **PC/SC Compliant NFC Reader:** A generic USB reader (e.g., ACR122U, ACR1252U) with the appropriate drivers installed.  
* **NXP NTAG424 DNA Tag:** The target NFC tag for provisioning.

## **Installation**

1. **Clone the repository:**  
   git clone \<repository-url\>  
   cd ntag424-sdm-provisioner

2. **Create a virtual environment:**  
   python \-m venv venv  
   source venv/bin/activate  \# On Windows, use \`venv\\Scripts\\activate\`

3. **Install dependencies from pyproject.toml:**  
   pip install \-e .

   This will install pyscard and pycryptodome.

## **Project Structure**

.  
├── examples/             \# Standalone scripts demonstrating functionality  
│   ├── 01\_connect.py  
│   ├── 02\_get\_version.py  
│   ├── 03\_authenticate.py  
│   ├── 04\_change\_key.py  
│   └── 05\_provision\_sdm.py   \# The main provisioning script  
├── src/                    \# Source code for the library  
│   ├── commands/           \# Individual APDU command classes  
│   ├── hal.py              \# Hardware Abstraction Layer (PC/SC)  
│   └── session.py          \# Session management and authentication  
└── pyproject.toml        \# Project definition and dependencies

## **Usage**

The examples/ directory contains scripts that build upon each other. The most important script is 05\_provision\_sdm.py, which performs the full provisioning process.

To run the final provisioning script:

python examples/05\_provision\_sdm.py

Place a factory-default NTAG424 tag on the reader. The script will output the new, randomly generated keys and confirm each step of the process.

### **⚠️ CRITICAL WARNING: Key Management ⚠️**

Running examples/04\_change\_key.py or examples/05\_provision\_sdm.py will **permanently change the cryptographic keys** on your tag.

* The script will print the new keys to the console.  
* **You MUST save these new keys.**  
* If you lose these keys, you will **permanently lose administrative control** over the tag. It will be impossible to change its configuration or keys again.

Always handle keys securely and ensure you have a system for storing them before provisioning tags for production use.

---

## Quick Start (Seritag)

Static URL provisioning (works without authentication on Seritag):

```bash
python examples/13_working_ndef.py
```

Diagnostics and deep dive scripts:

```bash
python examples/seritag/test_phase2_deep_dive.py
python examples/seritag/test_sun_configuration_acceptance.py
```

Mock HAL for tests (no hardware):

```bash
$env:USE_MOCK_HAL="1"; pytest -q
```

# Diagrams
To illustrate the NTAG424 SDM Provisioning Protocol Flow, I'll create a sequence diagram that typically covers the core provisioning steps:

Start communication between the Provisioning Host (PC/Server), NFC Reader, and NTAG424 Tag.
Perform authentication (EV2).
Change master keys.
Set up NDEF file and SDM settings.
Write the initial NDEF message.
Below is the Mermaid sequence diagram code for this protocol flow.

Summary:
This sequence diagram shows the NTAG424 SDM Provisioning Protocol, where a provisioning host authenticates with an NTAG424 tag through an NFC reader, updates its master key, sets up a Secure Dynamic Messaging (SDM)-capable file, and writes the first dynamic NDEF message, preparing the tag for deployment

```mermaid
%%{init: {"theme":"dark"}}%%
sequenceDiagram
    participant Host as Provisioning Host
    participant Reader as NFC Reader
    participant Tag as NTAG424 Tag

    %% 1. Establish Communication
    Host->>Reader: Connect()
    Reader->>Tag: Power On / ATR
    Tag-->>Reader: ATR Response
    Reader-->>Host: Tag Detected

    %% 2. Authenticate (EV2)
    rect rgb(80,70,130)
    note over Host,Tag: Secure session is established with default keys
    Host->>Tag: AuthenticateEV2First [C-APDU]
    Tag-->>Host: Encrypted RndB + SW
    Host->>Tag: AuthenticateEV2Part2 (Enc. RndA, rotated RndB)
    Tag-->>Host: Encrypted RndA' + SW
    note over Host: Session keys derived (SesAuthMACKey, SesEncKey)
    end

    %% 3. Change PICC Master Key
    rect rgb(31,97,141)
    note over Host,Tag: Update master key to unique value
    Host->>Tag: ChangeKey (Encrypted)
    Tag-->>Host: Success (SW=91 00)
    end

    %% 4. Set up SDM File & Settings
    rect rgb(39,174,96)
    note over Host,Tag: Configure SDM-enabled NDEF File
    Host->>Tag: CreateFile (NDEF, Encrypted)
    Tag-->>Host: Success
    Host->>Tag: SetFileSettings (SDM, Encrypted)
    Tag-->>Host: Success
    end

    %% 5. Provision NDEF Message
    rect rgb(230,126,34)
    note over Host,Tag: Write initial SDM-enabled NDEF Message
    Host->>Tag: WriteData (NDEF, Encrypted)
    Tag-->>Host: Success
    end

    %% 6. SDM Tag ready for deployment
    note over Tag: Tag provisioned and SDM enabled
```

## Authententicate_ev2_first
```mermaid
packet-beta
title AuthenticateEV2First (C-APDU)
0-7: "CLA"
8-15: "INS (0x71)"
16-23: "P1"
24-31: "P2"
32-39: "Lc (length of Data)"
40-47: "KeyNo"
48-63: "Le (Expected length)"
```

## authenticate_ev2_part2

```mermaid
packet-beta
title AuthenticateEV2Part2 (C-APDU)
0-7: "CLA"
8-15: "INS (0xAF)"
16-23: "P1"
24-31: "P2"
32-39: "Lc"
40-71: "Encrypted RndA + rotated RndB (32B total, truncated as example)"
72-79: "Le"

```

## change_key
```mermaid
packet-beta
title ChangeKey Command Payload
0-7: "KeyNo"
8-135: "NewKey XOR OldKey (16B)"
136-167: "CRC32(NewKey) (4B)"
```


## set_file_settings
```mermaid
packet-beta
title ChangeKey Command Payload
0-7: "KeyNo"
8-135: "NewKey XOR OldKey (16B)"
136-167: "CRC32(NewKey) (4B)"
```



