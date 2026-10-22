from openpilot.starpilot.galaxy.pairing_ready import BOOT_GRACE_SECONDS, TRANSIENT, pairing_readiness

GOOD = {'available': True, 'powered': True, 'errorCode': None}


def ask(*, uptime=600., parked=True, state=None, bridge=('ready', 'Ready to pair')):
  def snapshot():
    if isinstance(state, Exception):
      raise state
    return GOOD if state is None else state
  return pairing_readiness(parked=lambda: parked, snapshot=snapshot, bridge=lambda: bridge, uptime=lambda: uptime)


def test_ready_only_when_everything_a_phone_needs_is_up():
  assert ask() == {'schema': 1, 'ready': True, 'code': 'ready', 'message': 'Ready to pair.'}


def test_each_blocker_has_its_own_code_in_the_order_a_person_would_fix_them():
  assert ask(uptime=BOOT_GRACE_SECONDS - 1)['code'] == 'starting'
  assert ask(parked=False)['code'] == 'park_required'
  assert ask(state={'available': True, 'powered': False})['code'] == 'bluetooth_off'
  assert ask(state={'available': True, 'powered': True, 'errorCode': 'adapter_unavailable'})['code'] == 'bluetooth_unavailable'
  assert ask(state=OSError('gone'))['code'] == 'bluetooth_unavailable'
  assert ask(bridge=('pending', 'Bridge startup pending')) == {
    'schema': 1, 'ready': False, 'code': 'bridge_starting', 'message': 'Bridge startup pending'}
  assert ask(uptime=1, parked=False)['code'] == 'starting', 'boot comes first'


def test_only_boot_and_bridge_start_are_worth_waiting_for():
  assert TRANSIENT == {'starting', 'bridge_starting'}
  assert ask(parked=False)['code'] not in TRANSIENT
  assert ask(state={'available': True, 'powered': False})['code'] not in TRANSIENT
