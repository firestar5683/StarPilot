import threading
import time

from openpilot.starpilot.system.android_auto.incoming_pairing import IncomingPairing


ADDRESS = 'AA:BB:CC:DD:EE:FF'
PATH = '/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF'


def agent(state):
  return IncomingPairing(
    ('galaxy', 'source'), devices=lambda: state['devices'], live=lambda: state['parked'] and state['source'], clock=lambda: state['time'], deadline=180
  )


def prompt_for(agent, member, body):
  result = []
  worker = threading.Thread(target=lambda: result.append(agent.handle(member, body)), daemon=True)
  worker.start()
  deadline = time.monotonic() + 1
  while time.monotonic() < deadline and agent.status()['prompt'] is None and worker.is_alive():
    time.sleep(0.001)
  return worker, result, agent.status()['prompt']


def state():
  return {'time': 1.0, 'parked': True, 'source': True, 'devices': [{'path': PATH, 'address': ADDRESS, 'name': 'My car', 'paired': False}]}


def test_incoming_confirmation_requires_exact_session_and_explicit_acceptance():
  data = state()
  incoming = agent(data)
  assert incoming.handle('RequestAuthorization', ('/org/bluez/hci0/dev_00_00_00_00_00_00',))[0] is False
  worker, result, prompt = prompt_for(incoming, 'RequestConfirmation', (PATH, 1234))
  assert prompt['kind'] == 'confirmation' and prompt['value'] == '001234'
  assert incoming.status()['receiver'] == {'address': ADDRESS, 'name': 'My car'}
  assert not incoming.respond(('galaxy', 'other'), prompt['id'], True)
  assert not incoming.respond(('galaxy', 'source'), 'stale', True)
  assert incoming.respond(('galaxy', 'source'), prompt['id'], True)
  worker.join(timeout=1)
  assert result == [(True, None, ())] and incoming.status()['approved']
  assert incoming.approved_address == ADDRESS


def test_rejected_or_invalid_passkey_never_approves_and_second_car_cannot_take_over():
  data = state()
  incoming = agent(data)
  worker, result, prompt = prompt_for(incoming, 'RequestPasskey', (PATH,))
  assert prompt['kind'] == 'passkey'
  assert not incoming.respond(('galaxy', 'source'), prompt['id'], True, '1000000')
  assert incoming.respond(('galaxy', 'source'), prompt['id'], False)
  worker.join(timeout=1)
  assert result == [(False, None, ())] and not incoming.status()['approved']
  second = '/org/bluez/hci0/dev_11_22_33_44_55_66'
  data['devices'].append({'path': second, 'address': '11:22:33:44:55:66', 'name': 'Other', 'paired': False})
  assert incoming.handle('RequestAuthorization', (second,))[0] is False


def test_display_only_requires_prior_explicit_approval_and_park_source_ttl_revoke():
  data = state()
  incoming = agent(data)
  worker, result, prompt = prompt_for(incoming, 'DisplayPasskey', (PATH, 42, 0))
  assert prompt['kind'] == 'authorization'
  assert incoming.respond(('galaxy', 'source'), prompt['id'], True)
  worker.join(timeout=1)
  assert result == [(True, None, ())]
  assert incoming.status()['prompt']['kind'] == 'display_passkey'
  data['parked'] = False
  assert not incoming.status()['active']
  assert incoming.handle('RequestAuthorization', (PATH,))[0] is False
  data['parked'] = True
  data['source'] = False
  assert incoming.handle('RequestAuthorization', (PATH,))[0] is False
  data['source'] = True
  data['time'] = 180.0
  assert incoming.handle('RequestAuthorization', (PATH,))[0] is False


def test_bluez_cancel_closes_pending_prompt_and_cannot_reopen():
  data = state()
  incoming = agent(data)
  worker, result, prompt = prompt_for(incoming, 'RequestAuthorization', (PATH,))
  assert prompt is not None
  assert incoming.handle('Cancel', ()) == (True, None, ())
  worker.join(timeout=1)
  assert result == [(False, None, ())]
  assert not incoming.status()['active']
  assert incoming.handle('RequestAuthorization', (PATH,))[0] is False
