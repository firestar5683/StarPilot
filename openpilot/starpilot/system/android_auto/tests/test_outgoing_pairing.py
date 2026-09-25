"""Exercise imported owner, real PairingSession and supervisor with fake BlueZ I/O."""
import threading
import time

import pytest

from openpilot.starpilot.bluetooth.owner import BluetoothRejected, PairingSession
from openpilot.starpilot.system.android_auto.tests.test_bluetooth_bridge import FakeBlueZ, Phone, owner
from openpilot.starpilot.system.android_auto.supervisor import Supervisor


class OutgoingBlueZ(FakeBlueZ):
  def __init__(self, *, paired=False):
    super().__init__()
    self.paired[0].update(paired=paired, android_auto=False)
    self.operations = []
    self.pair_calls = []
    self.trust_calls = []
    self.prompt_entered = threading.Event()
    self.prompt_finished = threading.Event()
    self.stop_scan_error = False

  def operation(self, operation, address=None):
    self.operations.append((operation, address))
    if operation == 'stop_scan' and self.stop_scan_error:
      raise RuntimeError('scan cleanup failure')
    super().operation(operation, address)

  def pair(self, address, expected_path, session):
    assert isinstance(session, PairingSession)
    self.pair_calls.append((address, expected_path))
    try:
      self.prompt_entered.set()
      accepted, _value = session.ask('confirmation', expected_path, '123456')
      if accepted:
        self.paired[0]['paired'] = True
      return accepted
    finally:
      session.close_callbacks()
      self.prompt_finished.set()

  def cancel_pair(self, path):
    assert path == self.paired[0]['path']


class OutgoingPhone(Phone):
  def __init__(self, bluez):
    super().__init__()
    self.bluez = bluez
    self.connections = []
    self.connected = threading.Event()
    self.before_device = None

  def devices(self):
    return [dict(item) for item in self.bluez.paired]

  def device(self, address):
    if self.before_device is not None:
      callback, self.before_device = self.before_device, None
      callback()
    return next((item for item in self.devices() if item['address'] == address), None)

  def connect_device(self, address):
    self.connections.append(address)
    self.bluez.paired[0]['connected'] = True
    self.connected.set()


def setup(tmp_path, *, paired=False):
  state = {'parked': True, 'session': ('galaxy', 'outgoing')}
  bluez = OutgoingBlueZ(paired=paired)
  phone = OutgoingPhone(bluez)
  shared = owner(tmp_path, state, bluez)
  lease = shared.acquire_phone_role(state['session'], phone)
  return state, bluez, phone, shared, lease


def wait_for(predicate):
  deadline = time.monotonic() + 3
  while not predicate():
    assert time.monotonic() < deadline, 'background operation did not settle'
    time.sleep(.005)


def prompt(lease):
  assert lease.outgoing is not None
  with lease.outgoing.condition:
    assert lease.outgoing.condition.wait_for(lambda: lease.outgoing.prompt is not None, timeout=3)
    return dict(lease.outgoing.prompt)


def test_discovery_owned_and_cancellation_restores(tmp_path):
  state, bluez, phone, shared, lease = setup(tmp_path)
  try:
    status = shared.incoming_status(state['session'])
    assert status['discovering'] and status['devices'][0]['name'] == 'Car'
    with pytest.raises(BluetoothRejected):
      shared.request('scan', session=state['session'])
    lease.release()
    assert bluez.operations == [('scan', None), ('stop_scan', None)]
    assert bluez.agent_closed == 1 and phone.released == 1
    assert not shared.journal_path.exists()
  finally:
    shared.close()


def test_scan_cleanup_error_still_closes_agent_profile_and_lock(tmp_path):
  _state, bluez, phone, shared, lease = setup(tmp_path)
  bluez.stop_scan_error = True
  with pytest.raises(RuntimeError, match='scan cleanup'):
    lease.release()
  assert bluez.agent_closed == 1 and phone.released == 1
  assert lease.process_lock.closed and shared.phone_lease is None
  assert bluez.writes[-1] == (False, False)
  shared.close()


def test_saved_bond_connects_without_pair_trust_or_removal(tmp_path):
  state, bluez, phone, shared, lease = setup(tmp_path, paired=True)
  try:
    shared.pair_device(state['session'], bluez.paired[0]['address'])
    assert phone.connected.wait(3)
    wait_for(lambda: lease.operation_state == 'connected')
    assert bluez.pair_calls == [] and bluez.trust_calls == []
    assert phone.connections == [bluez.paired[0]['address']]
    assert bluez.operations == [('scan', None), ('stop_scan', None)]
    assert shared.incoming_status(state['session'])['approved']
  finally:
    shared.close()


@pytest.mark.parametrize('accepted', [True, False])
def test_unpaired_real_session_prompt_accept_and_reject(tmp_path, accepted):
  state, bluez, phone, shared, lease = setup(tmp_path)
  try:
    shared.pair_device(state['session'], bluez.paired[0]['address'])
    request = prompt(lease)
    assert not shared.incoming_response(('stale',), request['id'], True)
    assert shared.incoming_response(state['session'], request['id'], accepted)
    assert bluez.prompt_finished.wait(3)
    wait_for(lambda: lease.operation_state in ('connected', 'failed'))
    assert bool(phone.connections) == accepted
    assert bluez.paired[0]['paired'] == accepted
    assert lease.outgoing.callbacks_closed
    assert bluez.agent_closed == 1
    assert shared.incoming_status(state['session'])['prompt'] is None
  finally:
    shared.close()


@pytest.mark.parametrize('reason', ['cancel', 'source', 'park', 'adapter'])
def test_cancel_and_authority_loss_end_waiting_callbacks(tmp_path, reason):
  state, bluez, phone, shared, lease = setup(tmp_path)
  try:
    shared.pair_device(state['session'], bluez.paired[0]['address'])
    request = prompt(lease)
    if reason == 'cancel':
      lease.release()
    elif reason == 'source':
      state['session'] = ('galaxy', 'revoked')
    elif reason == 'park':
      state['parked'] = False
    else:
      bluez.sender = ':replacement'
    shared.maintain_phone_role()
    assert bluez.prompt_finished.wait(3)
    assert lease.outgoing.done.wait(3)
    assert lease.released and lease.outgoing.callbacks_closed
    assert phone.connections == []
    assert not shared.incoming_response(('galaxy', 'outgoing'), request['id'], True)
  finally:
    shared.close()


def test_revoke_between_bond_lookup_and_connect_prevents_connect(tmp_path):
  state, bluez, phone, shared, lease = setup(tmp_path, paired=True)
  try:
    phone.before_device = lambda: state.update(session=('revoked',))
    shared.pair_device(state['session'], bluez.paired[0]['address'])
    wait_for(lambda: lease.released)
    assert phone.connections == []
  finally:
    shared.close()


def test_target_cannot_change_while_real_prompt_is_pending(tmp_path):
  state, bluez, _phone, shared, lease = setup(tmp_path)
  try:
    shared.pair_device(state['session'], bluez.paired[0]['address'])
    prompt(lease)
    with pytest.raises(BluetoothRejected, match='Finish or cancel'):
      shared.pair_device(state['session'], bluez.paired[0]['address'])
    with pytest.raises(BluetoothRejected):
      shared.request('pair', session=state['session'], address=bluez.paired[0]['address'])
  finally:
    shared.close()
    assert bluez.prompt_finished.wait(3)


@pytest.mark.parametrize('wireless_aa', [False, True])
def test_supervisor_never_selects_ordinary_hfp_as_projection_receiver(tmp_path, wireless_aa):
  state, bluez, phone, shared, lease = setup(tmp_path, paired=True)
  try:
    shared.pair_device(state['session'], bluez.paired[0]['address'])
    assert phone.connected.wait(3)
    wait_for(lambda: lease.operation_state == 'connected')
    bluez.paired[0]['android_auto'] = wireless_aa
    supervisor = Supervisor.__new__(Supervisor)
    supervisor._lock = threading.RLock()
    supervisor._source_session = state['session']
    supervisor._shared_bluetooth_owner = shared
    supervisor._pairing_known = {bluez.paired[0]['address']}
    supervisor._session_alive = lambda: False
    supervisor._phone = lambda: phone
    supervisor.log = lambda *args, **kwargs: None
    selected = []
    supervisor.cancel_pairing = lambda: None
    supervisor.select_receiver = lambda address, name: selected.append((address, name))
    supervisor._select_new_car()
    assert bool(selected) == wireless_aa
  finally:
    shared.close()
