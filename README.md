# **NTAG424 SDM Provisioner**

TLDR; Static URL NDEF provisioning works on Seritag tags without authentication; SDM/SUN is blocked by Phase 2 auth (Seritag-specific). Use `examples/seritag` for diagnostics and `tests/` with the mock HAL. Canonical docs: `SERITAG_INVESTIGATION_COMPLETE.md`, `Plan.md`, `ARCH.md`, `Requirements.md`, `CURRENT_STEP.md`.

This project provides a Python-based toolkit for provisioning NXP NTAG424 DNA NFC tags for Secure Dynamic Messaging (SDM). It offers a modular, command-oriented framework for interacting with the tag at a low level, enabling developers to perform a full provisioning sequence from a factory-default state.

## **Features**

* **Hardware Abstraction Layer (HAL):** A clean interface for communicating with PC/SC compliant NFC readers via pyscard.  
* **Command-Oriented Architecture:** Each NTAG424 command is implemented as a distinct, reusable class, promoting modularity and extensibility.  
* **Secure Session Management:** A high-level Ntag424Session class that handles the complex EV2 authentication handshake and session key derivation.  
* **Full Provisioning Workflow:** The included examples demonstrate the complete process:  
  1. Connecting to a tag.  
  2. Authenticating with factory keys.  
  3. Changing all 5 cryptographic keys to secure, random values.  
  4. Configuring NDEF file settings for SDM with UID and read counter mirroring.  
  5. Writing a dynamic NDEF URI for server-side verification.

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



