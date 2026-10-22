"""Whether comma can take a phone's Bluetooth pairing right now, so companion apps wait instead of failing."""
from collections.abc import Callable

# Short-lived states a phone may wait out; the others need someone to do something on comma.
TRANSIENT = frozenset(('starting', 'bridge_starting'))
BOOT_GRACE_SECONDS = 45.0


def system_uptime() -> float:
  try:
    with open('/proc/uptime') as stream:
      return float(stream.read().split()[0])
  except (OSError, ValueError, IndexError):
    return BOOT_GRACE_SECONDS  # no grace where the uptime cannot be read (not a comma)


def bridge_state() -> tuple[str, str]:
  """The phone bridge's (state, message); 'pending' whenever it cannot be read."""
  try:
    from openpilot.starpilot.galaxy_bluetooth.bootstrap import setup_state
    return setup_state()
  except Exception:
    return 'pending', 'Bridge startup pending'


def pairing_readiness(*, parked: Callable[[], bool], snapshot: Callable[[], dict],
                      bridge: Callable[[], tuple[str, str]], uptime: Callable[[], float] = system_uptime) -> dict:
  """{'ready': bool, 'code': str, 'message': str}; checked in the order a person would fix them."""
  def answer(ready: bool, code: str, message: str) -> dict:
    return {'schema': 1, 'ready': ready, 'code': code, 'message': message}

  if uptime() < BOOT_GRACE_SECONDS:
    return answer(False, 'starting', 'Comma just started and Bluetooth is still getting ready.')
  try:
    is_parked = parked()
    state = snapshot() if is_parked else {}
  except Exception:  # a readiness question must always get an answer, never an error
    return answer(False, 'bluetooth_unavailable', 'Comma’s Bluetooth service is not responding.')
  if not is_parked:
    return answer(False, 'park_required', 'Park the car or turn it off to pair a phone.')
  if state.get('errorCode') or not state.get('available', True):
    return answer(False, 'bluetooth_unavailable', 'Comma’s Bluetooth adapter is not available.')
  if not state.get('powered'):
    return answer(False, 'bluetooth_off', 'Bluetooth is off on comma. Turn it on in Settings > Bluetooth.')
  try:
    bridge_state, bridge_message = bridge()
  except Exception:
    bridge_state, bridge_message = 'pending', ''
  if bridge_state != 'ready':
    return answer(False, 'bridge_starting', bridge_message or 'The phone Bluetooth bridge is starting.')
  return answer(True, 'ready', 'Ready to pair.')
