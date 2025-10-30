import ast
from pathlib import Path
from .mock_hal import MockCardManager
import pytest

@pytest.fixture
def card_manager_instance():
    from ntag424_sdm_provisioner.hal import has_readers, CardManager

    if has_readers():
        return CardManager
    else:
        return MockCardManager
    
    

def test_connect(card_manager_instance):
    with card_manager_instance(0) as conn:
        assert conn is not None