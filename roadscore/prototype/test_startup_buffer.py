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

def test_short_startup_requires_explicit_test_policy():
    from startup_buffer import session_target
    with pytest.raises(ValueError):initial_target({'ROADSCORE_INITIAL_BUFFER_SECONDS':'40'},'hook-cache-v1')
    assert initial_target({'ROADSCORE_INITIAL_BUFFER_SECONDS':'40','ROADSCORE_TEST_SHORT_STARTUP':'1'},'hook-cache-v1')==40
    request={'session_protocol':2,'initial_buffer_target_seconds':40,'startup_policy':'short-startup-test-v1'}
    assert session_target(request,'hook-cache-v1')==40
    with pytest.raises(ValueError):session_target({**request,'initial_buffer_target_seconds':30},'hook-cache-v1')
    with pytest.raises(ValueError):session_target({**request,'session_protocol':1},'hook-cache-v1')


def test_old_worker_same_target_compatible_changed_target_requires_restart():
    from prepared_session import requested_buffer
    metadata={'initial_buffer_target_seconds':100}
    env={'ROADSCORE_INITIAL_BUFFER_SECONDS':'100','ROADSCORE_COMPOSITION_POLICY':'hook-cache-v1'}
    assert requested_buffer(metadata,env) is None
    with pytest.raises(RuntimeError,match='restart it once'):
        requested_buffer(metadata,{**env,'ROADSCORE_INITIAL_BUFFER_SECONDS':'40','ROADSCORE_TEST_SHORT_STARTUP':'1'})
    assert requested_buffer({**metadata,'resident_session_protocol':2},env)==100
