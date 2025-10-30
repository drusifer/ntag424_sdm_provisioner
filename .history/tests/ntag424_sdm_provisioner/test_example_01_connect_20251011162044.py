import ast
from pathlib import Path

import pytest

@pytest.fixture
def hal_instance():
    from ntag424_sdm_provisioner.hal import Hal
    return Hal()

def test_connect(