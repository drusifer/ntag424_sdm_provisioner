"""
Example 02: Connect to an NTAG424, select the PICC, and get its version.
"""
from __future__ import print_function
import sys
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.get_version2 import GetVersion

# NTAG424 uses 0x3F3F as the PICC master application ID
PICC_APPLICATION_ID = 0x3F3F


def main():
    """Main execution function."""
    try:
        # Use the first available reader
        with CardManager(0) as card:
            print("--- Example 02: Get Version ---")
            print("INFO: Card detected. ATR:", card.wait_for_atr())

            get_version_command = GetVersion()
            version_info = get_version_command.execute(card)
            print("\n" + str(version_info))

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        raise e
    return 0


def test_snippet():
    # language: python
# Small ACR122 escape -> GET_VERSION example. Run in your venv; does not modify repo files.
    from smartcard.System import readers

    # IOCTL_CCID_ESCAPE = SCARD_CTL_CODE(3500)
    IOCTL_CCID_ESCAPE = (0x31 << 16) | (3500 << 2)

    def hexb(b):
        if isinstance(b, (list, tuple)):
            b = bytes(b)
        return b.hex().upper() if isinstance(b, (bytes, bytearray)) else str(b)

    rlist = readers()
    print("Readers:", [str(r) for r in rlist])
    if not rlist:
        raise SystemExit("No PC/SC readers found")

    r = rlist[0]
    conn = r.createConnection()
    conn.connect()  # may raise if another app has exclusive access
    print("Connected to:", str(r))

    # NXP proprietary APDU: 90 60 00 00 00
    apdu = bytes([0x90, 0x60, 0x00, 0x00, 0x00])

    # ACR122 escape wrapper:  FF 00 00 00 <Lc> <APDU bytes>
    payload = bytes([0xFF, 0x00, 0x00, 0x00, len(apdu)]) + apdu

    print("Sending escape payload:", hexb(payload))
    resp = conn.control(IOCTL_CCID_ESCAPE, payload)

    print("Raw response:", hexb(resp))
    # If response includes status bytes at end, print them separated:
    if isinstance(resp, (bytes, bytearray)) and len(resp) >= 2:
        print("Possible SW:", hexb(resp[-2:]), "Data:", hexb(resp[:-2]))

if __name__ == "__main__":
    sys.exit(main())

