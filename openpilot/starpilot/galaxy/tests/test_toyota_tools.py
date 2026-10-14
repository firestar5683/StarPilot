"""Toyota tools use the registered factory context and exact guarded saved sources."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR
from openpilot.starpilot.car.toyota.security_key import decode_key
from openpilot.starpilot.galaxy.toyota_tools import ToyotaTools, ToyotaToolsChanged


class SavedParams:
  def __init__(self, root):
    self.root = root / 'd'
    self.root.mkdir()

  def get_param_path(self, key):
    return str(self.root / key)


@pytest.fixture
def tools(tmp_path):
  params = SavedParams(tmp_path)
  cp = CarInterface.get_non_essential_params(CAR.TOYOTA_RAV4_PRIME)
  assert cp.secOcRequired and cp.brand == 'toyota'
  current = SimpleNamespace(cp=cp, cp_raw=cp.to_bytes(), parked=True)
  context = SimpleNamespace(sample=lambda: current, close=lambda: None)
  return ToyotaTools(params, context, clock=lambda: 10), params, current


def action(owner, action_name, **fields):
  page = owner.page('session', b'generation')
  return owner.action(dict(view=page['view'], action=action_name, confirmed=True, **fields), 'session', b'generation')


@pytest.mark.parametrize('raw', [None, '', 'x' * 32, 'a' * 31, 'a' * 33, 'aa aa' * 6, b'\xff' * 32, 123])
def test_malformed_secoc_key_is_unavailable_without_decode_exception(raw):
  assert decode_key(raw) is None


def test_valid_key_uses_exact_sixteen_bytes():
  assert decode_key('AB' * 16) == bytes([171] * 16)
  assert decode_key(('ab' * 16).encode()) == bytes([171] * 16)


def test_key_library_use_delete_never_discloses_value(tools):
  owner, params, _ = tools
  assert action(owner, 'save_key', name='My Toyota', value='ab' * 16)['saved']
  page = owner.page('session', b'generation')
  assert page['keys'] == [{'name': 'My Toyota', 'active': False}]
  assert 'ab' * 16 not in json.dumps(page)
  assert action(owner, 'use_key', name='My Toyota')['nextStartup']
  assert Path(params.get_param_path('SecOCKey')).read_bytes() == b'ab' * 16
  assert owner.page('session', b'generation')['keys'][0]['active']
  assert action(owner, 'delete_key', name='My Toyota')['saved']
  assert owner.page('session', b'generation')['keys'] == []
  assert Path(params.get_param_path('SecOCKey')).read_bytes() == b'ab' * 16


@pytest.mark.parametrize('revoke', ['session', 'generation', 'parked', 'context', 'source', 'vehicle'])
def test_changed_authority_or_exact_source_cannot_write(tools, revoke):
  owner, params, current = tools
  page = owner.page('session', b'generation')
  if revoke == 'parked':
    current.parked = False
  elif revoke == 'context':
    current.cp_raw = b'changed'
  elif revoke == 'source':
    Path(params.get_param_path('LockDoors')).write_bytes(b'1')
  elif revoke == 'vehicle':
    current.cp.brand = 'honda'
  with pytest.raises(ToyotaToolsChanged):
    owner.action({'view': page['view'], 'action': 'save_key', 'name': 'test', 'value': 'ab' * 16, 'confirmed': True},
                 'other' if revoke == 'session' else 'session', b'other' if revoke == 'generation' else b'generation')
  assert not Path(params.get_param_path('SecOCKeys')).exists()


def test_non_toyota_hidden_and_non_secoc_key_actions_denied(tools):
  owner, _, current = tools
  current.cp.brand = 'hyundai'
  assert not owner.page('session', b'generation')['visible']
  current.cp = CarInterface.get_non_essential_params(CAR.TOYOTA_COROLLA_TSS2)
  current.cp_raw = current.cp.to_bytes()
  page = owner.page('session', b'generation')
  assert page['visible'] and not page['security']
  with pytest.raises(ValueError):
    owner.action({'view': page['view'], 'action': 'save_key', 'name': 'test', 'value': 'ab' * 16, 'confirmed': True},
                 'session', b'generation')


def test_door_preferences_default_off_and_verified_at_next_start(tools):
  owner, params, _ = tools
  page = owner.page('session', b'generation')
  assert not page['lock'] and not page['unlock']
  assert action(owner, 'lock', value=True)['nextStartup']
  assert Path(params.get_param_path('LockDoors')).read_bytes() == b'1'
  assert action(owner, 'unlock', value=True)['saved']
  assert Path(params.get_param_path('UnlockDoors')).read_bytes() == b'1'


def test_malformed_library_never_becomes_empty_or_discloses_credentials(tools):
  owner, params, _ = tools
  invalid = b'["private-invalid-value"]'
  Path(params.get_param_path('SecOCKeys')).write_bytes(invalid)
  page = owner.page('session', b'generation')
  assert not page['readable'] and page['view'] is None and page['keys'] == []
  assert invalid.decode() not in json.dumps(page)
  assert Path(params.get_param_path('SecOCKeys')).read_bytes() == invalid
