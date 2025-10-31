"""
Compare EV2 Phase 2 with escape vs no-escape transmit paths.

Runs AuthenticateEV2First/Second twice:
  1) Forced escape (control())
  2) Forced no-escape (transmit())

Prints status words and basic outcomes for both runs.
"""
import os
import time
import sys

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    AuthenticateEV2First,
    AuthenticateEV2Second,
)
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession


FACTORY_KEY = bytes(16)


def run_once(force_escape: bool | None):
    if force_escape is True:
        os.environ['FORCE_ESCAPE'] = '1'
        os.environ.pop('FORCE_NO_ESCAPE', None)
        mode = 'escape'
    elif force_escape is False:
        os.environ['FORCE_NO_ESCAPE'] = '1'
        os.environ.pop('FORCE_ESCAPE', None)
        mode = 'no-escape'
    else:
        os.environ.pop('FORCE_ESCAPE', None)
        os.environ.pop('FORCE_NO_ESCAPE', None)
        mode = 'default'

    print("=" * 60)
    print(f"EV2 Phase 2 Test ({mode})")
    print("=" * 60)

    try:
        with CardManager(0, timeout_seconds=15) as card:
            # Select PICC
            try:
                SelectPiccApplication().execute(card)
            except Exception as e:
                print(f"[WARN] Select PICC failed: {e}")

            # Phase 1
            try:
                ch = AuthenticateEV2First(0x00).execute(card)
            except Exception as e:
                print(f"[FAIL] Phase 1 failed: {e}")
                return

            # Process Phase 1, build Phase 2
            sess = Ntag424AuthSession(key=FACTORY_KEY)
            try:
                # Will internally send Phase 2 and parse response
                sess._phase2_authenticate(card, ch.challenge)
                print("[OK] Phase 2 completed (9000)")
            except Exception as e:
                print(f"[RESULT] Phase 2 error: {e}")
    except Exception as outer:
        print(f"[ERROR] Card session error: {outer}")


def main():
    # Run with forced escape
    run_once(force_escape=True)
    # Small delay to avoid immediate re-auth penalty
    time.sleep(0.6)
    # Run with forced no-escape
    run_once(force_escape=False)


if __name__ == "__main__":
    main()


