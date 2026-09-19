import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from composition_launch import configure

SESSION = {'seed_origin': 'random-session'}

def run(env, **kwargs):
    return configure(SESSION, False, 'ace', native=True, transport_only=False,
                     environ=env, root=Path('/unused'), **kwargs)

def test_native_bank_validated_and_network_credentials_removed(tmp_path):
    calls = []
    env = {'ROADSCORE_PLAN_BANK': str(tmp_path), 'ROADSCORE_ACE_PROFILE': 'prism',
           'ROADSCORE_PLANNER_URL': 'http://host', 'ROADSCORE_PLANNER_TOKEN': 'token'}
    with patch.dict(sys.modules, cached_composition=SimpleNamespace(validate_bank=lambda path, **kw: calls.append((path,kw)))):
        assert run(env) == 'hook-cache-v1'
    assert calls == [(tmp_path, {'profile': 'prism'})]
    assert 'ROADSCORE_PLANNER_URL' not in env and 'ROADSCORE_PLANNER_TOKEN' not in env

def test_invalid_native_bank_never_falls_back():
    def reject(*args, **kwargs): raise ValueError('missing current plan bank')
    with patch.dict(sys.modules, cached_composition=SimpleNamespace(validate_bank=reject)):
        with pytest.raises(ValueError, match='missing current plan bank'): run({})

@pytest.mark.parametrize('replay,session,transport', [(True, None, False), (False, {'seed_origin':'judging-route'}, False), (False, SESSION, True)])
def test_frozen_and_non_generation_do_not_require_bank(replay, session, transport):
    assert configure(session, replay, 'ace', native=True, transport_only=transport, environ={}, root=Path('/unused')) == 'prepared-v1'

def test_mac_fresh_path_unchanged():
    assert configure(SESSION, False, 'ace', native=False, transport_only=False, environ={}, root=Path('/unused')) == 'hook-v2'
