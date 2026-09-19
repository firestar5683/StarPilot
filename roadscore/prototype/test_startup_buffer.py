import pytest
from startup_buffer import initial_target

def test_default_and_explicit_current_bank_candidate():
    assert initial_target({},'hook-cache-v1')==112
    assert initial_target({'ROADSCORE_INITIAL_BUFFER_SECONDS':'80'},'hook-cache-v1')==80

@pytest.mark.parametrize('value',['0','79','113','nan','inf'])
def test_unsupported_reserve_rejected(value):
    with pytest.raises(ValueError):initial_target({'ROADSCORE_INITIAL_BUFFER_SECONDS':value},'hook-cache-v1')

def test_frozen_policy_unchanged_and_rejects_override():
    assert initial_target({},'prepared-v1')==112
    with pytest.raises(ValueError):initial_target({'ROADSCORE_INITIAL_BUFFER_SECONDS':'80'},'prepared-v1')
