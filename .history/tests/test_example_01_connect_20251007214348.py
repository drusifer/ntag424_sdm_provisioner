import importlib.util
import sys
import pytest


def test_example_01_list_readers_runs():
    """Import and run the examples/01_connect.py list_readers function.

    This test intentionally does not mock hardware. It will be skipped if the
    `smartcard` (pyscard) package is not installed in the test environment.
    """
    try:
        import smartcard  # type: ignore
    except Exception:
        pytest.skip("pyscard not installed; skipping hardware discovery test")

    spec = importlib.util.spec_from_file_location(
        "example_01",
        "examples/01_connect.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore

    # Call the function; it should return a list (possibly empty) and not raise
    readers = module.list_readers()
    assert isinstance(readers, list)
