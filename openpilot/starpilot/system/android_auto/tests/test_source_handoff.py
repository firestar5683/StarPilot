from unittest.mock import Mock
import pytest

from openpilot.starpilot.galaxy.android_auto_source import GalaxySourceRegistry
from openpilot.starpilot.system.android_auto import daemon


def test_source_registry_rejects_expiry_and_session_revoke():
  now = [10.0]
  valid = {('galaxy', '1')}
  registry = GalaxySourceRegistry(lambda identity: identity in valid, clock=lambda: now[0])
  source = registry.mint(('galaxy', '1'))
  assert registry.valid(source)
  assert registry.current(('galaxy', '1')) == source
  assert not registry.valid('bad')
  valid.clear()
  assert not registry.valid(source)
  assert registry.current(('galaxy', '1')) is None
  valid.add(('galaxy', '1'))
  next_source = registry.mint(('galaxy', '1'))
  now[0] += registry.LIFETIME + 1
  assert not registry.valid(next_source)
  assert registry.current(('galaxy', '1')) is None


def test_daemon_requires_galaxy_source_for_pairing_and_other_mutations(monkeypatch):
  from openpilot.common import params

  class Params:
    def get_bool(self, key):
      return key == 'AndroidAutoEnabled'

  monkeypatch.setattr(params, 'Params', Params)
  monkeypatch.setattr(daemon, '_offroad', lambda: True)
  source = 'a' * 64

  class Verifier:
    def valid(self, candidate):
      return candidate == source

  class Supervisor:
    def __init__(self):
      self.calls = []

    def bind_source_session(self, session):
      self.calls.append(('bind', session))

    def prepare_pairing(self):
      self.calls.append(('pair',))

    def status(self):
      return {'state': 'idle'}

    def user_stop(self):
      self.calls.append(('stop',))

  obj = Supervisor()
  for command in ('prepare_pairing', 'pair_device', 'start', 'devices', 'select_receiver'):
    with pytest.raises(RuntimeError, match='Authenticated Galaxy'):
      daemon.handle(Mock(wraps=obj), {'command': command}, Mock(wraps=Verifier()))
  assert daemon.handle(Mock(wraps=obj), {'command': 'prepare_pairing', 'source': source}, Mock(wraps=Verifier())) == {}
  assert obj.calls == [('bind', ('galaxy', source)), ('pair',)]
  assert daemon.handle(Mock(wraps=obj), {'command': 'status'}) == {'status': {'state': 'idle'}}
  assert daemon.handle(Mock(wraps=obj), {'command': 'stop'}) == {}


def test_daemon_park_gate_still_prevents_pairing(monkeypatch):
  from openpilot.common import params

  class Params:
    def get_bool(self, key):
      return True

  monkeypatch.setattr(params, 'Params', Params)
  monkeypatch.setattr(daemon, '_offroad', lambda: False)

  class Verifier:
    def valid(self, source):
      return True

  class Supervisor:
    def bind_source_session(self, session):
      pass

    def prepare_pairing(self):
      raise AssertionError('pairing should not start')

  with pytest.raises(RuntimeError, match='Park before pairing'):
    daemon.handle(Mock(wraps=Supervisor()), {'command': 'prepare_pairing', 'source': 'a' * 64}, Mock(wraps=Verifier()))


def test_pairing_prompt_commands_require_live_source_and_park(monkeypatch):
  from openpilot.common import params

  class Params:
    def get_bool(self, key):
      return key == 'AndroidAutoEnabled'

  monkeypatch.setattr(params, 'Params', Params)
  parked = [True]
  monkeypatch.setattr(daemon, '_offroad', lambda: parked[0])
  source = 'a' * 64

  class Verifier:
    def valid(self, value):
      return value == source

  class Supervisor:
    def __init__(self):
      self.calls = []

    def bind_source_session(self, session):
      self.calls.append(('bind', session))

    def pairing_status(self):
      return {'active': True, 'prompt': {'id': 'p'}}

    def pairing_response(self, prompt_id, accepted, value):
      self.calls.append(('response', prompt_id, accepted, value))

    def cancel_pairing(self):
      self.calls.append(('cancel',))

  obj = Supervisor()
  for command in ('pairing_status', 'pairing_response', 'cancel_pairing'):
    with pytest.raises(RuntimeError, match='Authenticated Galaxy'):
      daemon.handle(Mock(wraps=obj), {'command': command})
  assert daemon.handle(Mock(wraps=obj), {'command': 'pairing_status', 'source': source}, Mock(wraps=Verifier()))['pairing']['active']
  daemon.handle(Mock(wraps=obj), {'command': 'pairing_response', 'source': source, 'prompt_id': 'p', 'accepted': False, 'value': ''}, Mock(wraps=Verifier()))
  assert ('response', 'p', False, '') in obj.calls
  parked[0] = False
  with pytest.raises(RuntimeError, match='Park before pairing'):
    daemon.handle(Mock(wraps=obj), {'command': 'cancel_pairing', 'source': source}, Mock(wraps=Verifier()))
  assert ('cancel',) not in obj.calls


def test_only_explicitly_approved_paired_receiver_can_be_selected(tmp_path, monkeypatch):
  from openpilot.starpilot.system.android_auto import identity as identity_store, supervisor

  monkeypatch.setattr(identity_store, 'CONFIG_PATH', tmp_path / 'config.json')
  selected = []

  class Phone:
    def __init__(self):
      self.closed = False

    def devices(self):
      return [
        {'address': 'AA:BB:CC:DD:EE:FF', 'name': 'Approved', 'paired': True, 'android_auto': True},
        {'address': '11:22:33:44:55:66', 'name': 'Other', 'paired': True, 'android_auto': True},
      ]

    def close(self):
      self.closed = True

  phone = Phone()
  obj = supervisor.Supervisor(shared_bluetooth_owner=object())
  obj._bluez = phone
  obj._pairing_known = set()
  obj._pairing_until = 10**12
  approved = [False]
  monkeypatch.setattr(obj, 'pairing_status', lambda: {'active': True, 'approved': approved[0], 'receiver': {'address': 'AA:BB:CC:DD:EE:FF'}})
  monkeypatch.setattr(obj, 'select_receiver', lambda address, name: selected.append((address, name)))
  obj._select_new_car()
  assert selected == [] and not phone.closed
  approved[0] = True
  obj._select_new_car()
  assert selected == [('AA:BB:CC:DD:EE:FF', 'Approved')] and phone.closed
  assert obj._pairing_known is None


def test_hfp_pairing_window_accepts_only_approved_head_unit(tmp_path, monkeypatch):
  from openpilot.starpilot.system.android_auto import identity as identity_store, supervisor

  monkeypatch.setattr(identity_store, 'CONFIG_PATH', tmp_path / 'config.json')

  class Incoming:
    approved_address = ''

  incoming = Incoming()

  class Owner:
    phone_lease = type('Lease', (), {'incoming': incoming, 'released': False, 'receiver': ''})()

  obj = supervisor.Supervisor(shared_bluetooth_owner=Owner())
  obj._source_session = ('galaxy', 'source')
  obj._pairing_until = 10**12
  obj.config['receiver_address'] = '11:22:33:44:55:66'
  assert not obj._hfp_accepts('11:22:33:44:55:66')
  incoming.approved_address = 'AA:BB:CC:DD:EE:FF'
  assert obj._hfp_accepts('AA:BB:CC:DD:EE:FF')
  assert not obj._hfp_accepts('11:22:33:44:55:66')


def test_supervisor_revokes_phone_role_when_galaxy_source_expires(tmp_path, monkeypatch):
  from openpilot.starpilot.system.android_auto import identity as identity_store, supervisor

  monkeypatch.setattr(identity_store, 'CONFIG_PATH', tmp_path / 'config.json')
  state = {'valid': True, 'maintained': 0}

  class Owner:
    def session_valid(self, session):
      return state['valid'] and session == ('galaxy', 'a' * 64)

    def maintain_phone_role(self):
      state['maintained'] += 1

  obj = supervisor.Supervisor(shared_bluetooth_owner=Owner())
  monkeypatch.setattr(obj, '_auto_connect', lambda now: None)
  session = ('galaxy', 'a' * 64)
  obj.bind_source_session(session)

  class Phone:
    def __init__(self, binding):
      self.closed = False
      self.lease = type('Lease', (), {'session': binding, 'released': False})()

    def close(self):
      self.closed = True

  phone = Phone(session)
  obj._bluez = phone
  state['valid'] = False
  obj.maintain()
  assert state['maintained'] == 1 and phone.closed and obj._source_session is None
  state['valid'] = True
  obj.bind_source_session(session)
  projection = Phone(None)
  obj._bluez = projection
  state['valid'] = False
  obj.maintain()
  assert not projection.closed and obj._source_session is None


def test_projection_runtime_stops_when_disabled_or_receiver_identity_changes(tmp_path, monkeypatch):
  from openpilot.starpilot.system.android_auto import identity as identity_store, supervisor

  monkeypatch.setattr(identity_store, 'CONFIG_PATH', tmp_path / 'config.json')
  state = {'enabled': True, 'identity_changed': False}

  class Lease:
    session = None
    released = False

  class Phone:
    def __init__(self):
      self.lease = Lease()
      self.closed = False

    def close(self):
      self.closed = True

  class Owner:
    def maintain_phone_role(self):
      if state['identity_changed']:
        phone.lease.released = True

  obj = supervisor.Supervisor(shared_bluetooth_owner=Owner(), projection_enabled=lambda: state['enabled'])
  monkeypatch.setattr(obj, '_auto_connect', lambda now: None)
  phone = Phone()
  obj._bluez = phone
  state['identity_changed'] = True
  obj.maintain()
  assert phone.closed and obj._bluez is None
  assert 'receiver changed' in obj.status()['error']
  state['identity_changed'] = False
  phone = Phone()
  obj._bluez = phone
  state['enabled'] = False
  obj.maintain()
  assert phone.closed and obj._bluez is None
  assert 'disabled' in obj.status()['error']
