"""Shared screen preferences and wake policy for native UI and Galaxy.

The existing brightness value 101 continues to encode Auto for older clients.
Manual values and offsets are independent for the driving and parked screens.
"""
from contextlib import contextmanager
import fcntl
import math
import os
from pathlib import Path
from threading import RLock

from openpilot.common.params import UnknownKeyName

BRIGHTNESS_KEYS = ('ScreenBrightness', 'ScreenBrightnessOnroad')
SCREEN_INT_KEYS = frozenset(key + suffix for key in BRIGHTNESS_KEYS for suffix in ('', 'Manual', 'Offset'))
STANDBY_BUTTON_PRESS_PARAM = 'StandbyButtonPressTime'
SCREEN_WAKE_OPTIONS = (
  ('StandbyWakeTouch', 'Touch screen', True),
  ('StandbyWakeDriveState', 'Car drive state changed', True),
  ('StandbyWakeButton', 'Bluetooth or steering wheel button', False),
  ('StandbyWakeEngage', 'Engagement', True),
  ('StandbyWakeDisengage', 'Disengagement', True),
  ('StandbyWakeInfoAlert', 'Informational alerts', True),
  ('StandbyWakeWarningAlert', 'Warning alerts', True),
  ('StandbyWakeCriticalAlert', 'Critical / takeover alerts', True),
  ('StandbyWakeTurnSignal', 'Turn signals', False),
  ('StandbyWakeBrake', 'Brake pedal', False),
  ('StandbyWakeAccelerator', 'Accelerator pedal', False),
)
SCREEN_WAKE_DESCRIPTIONS = {
  'StandbyWakeTouch': 'Wake the screen from Standby when you touch it.',
  'StandbyWakeDriveState': 'Wake the screen from Standby when the gear, ignition or driving state changes.',
  'StandbyWakeButton': 'Wake the screen from Standby when a connected Bluetooth or USB controller, or a supported steering wheel button, is pressed.',
  'StandbyWakeEngage': 'Wake the screen from Standby when StarPilot engages.',
  'StandbyWakeDisengage': 'Wake the screen from Standby when StarPilot disengages.',
  'StandbyWakeInfoAlert': 'Wake the screen from Standby and keep it awake while an informational alert is displayed.',
  'StandbyWakeWarningAlert': 'Wake the screen from Standby and keep it awake while a warning alert is displayed.',
  'StandbyWakeCriticalAlert': 'Wake the screen from Standby and keep it awake while a critical or takeover alert is displayed.',
  'StandbyWakeTurnSignal': 'Wake the screen from Standby when a turn signal is activated or its direction changes.',
  'StandbyWakeBrake': 'Wake the screen from Standby when the brake pedal is pressed.',
  'StandbyWakeAccelerator': 'Wake the screen from Standby when the accelerator pedal is pressed.',
}
SCREEN_WAKE_KEYS = frozenset(key for key, _, _ in SCREEN_WAKE_OPTIONS)
SCREEN_SETTING_KEYS = SCREEN_INT_KEYS | SCREEN_WAKE_KEYS
_WRITE_LOCK = RLock()


def _raw(params, key):
  try:
    return params.get(key)
  except (UnknownKeyName, KeyError, TypeError, ValueError):
    # Older native registries may not yet know new settings during an update.
    return None


def _integer(params, key, default, minimum, maximum):
  try:
    value = float(_raw(params, key))
    if not math.isfinite(value):
      return default
    return min(maximum, max(minimum, round(value)))
  except (TypeError, ValueError, OverflowError):
    return default


def brightness_preferences(params, key):
  if key not in BRIGHTNESS_KEYS:
    raise ValueError('Unknown brightness setting')
  value = _integer(params, key, 101, 0, 101)
  return {
    'mode': 'auto' if value == 101 else 'manual',
    'manual': _integer(params, key + 'Manual', 100, 0, 100) if value == 101 else value,
    'offset': _integer(params, key + 'Offset', 0, -30, 30),
  }


def _boolean(raw, default=False):
  if raw is None:
    return default
  if isinstance(raw, bytes):
    return raw.strip().lower() in (b'1', b'true')
  if isinstance(raw, str):
    return raw.strip().lower() in ('1', 'true')
  return bool(raw)


def enabled_wake_keys(params):
  return {key for key, _, default in SCREEN_WAKE_OPTIONS if _boolean(_raw(params, key), default)}


@contextmanager
def _screen_write_transaction(params):
  # Keep the lock outside the key directory, where Params clearing cannot remove
  # it. Include the prefix so isolated Params stores do not block each other.
  directory = Path(params.get_param_path())
  lock_path = directory.parent / f'.screen_settings.{directory.name}.lock'
  with _WRITE_LOCK:
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_CLOEXEC, 0o660)
    try:
      # A competing save must report busy instead of blocking the UI thread.
      fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
      invalidate = getattr(params, 'invalidate', None)
      if invalidate is not None:
        invalidate()
      try:
        yield
      finally:
        # UIParamCache must not retain a pre-transaction value after success or
        # rollback; Galaxy writes may have changed it before we took the lock.
        if invalidate is not None:
          invalidate()
    finally:
      os.close(fd)


def write_screen_setting(params, key, value):
  if key not in SCREEN_SETTING_KEYS:
    raise ValueError('Unknown screen setting')
  if key in SCREEN_WAKE_KEYS:
    if type(value) is not bool:
      raise ValueError('Wake selections must be booleans')
  else:
    lo, hi = (-30, 30) if key.endswith('Offset') else (0, 101 if key in BRIGHTNESS_KEYS else 100)
    if type(value) not in (int, float) or not math.isfinite(value) or int(value) != value or not lo <= value <= hi:
      raise ValueError(f'{key} must be a whole number from {lo} to {hi}')
    value = int(value)

  with _screen_write_transaction(params):
    return _write_screen_setting(params, key, value)


def _write_screen_setting(params, key, value):
  changes = {}
  if key in BRIGHTNESS_KEYS:
    current = _integer(params, key, 101, 0, 101)
    if value != 101:
      changes[key + 'Manual'] = value
    elif current != 101:
      changes[key + 'Manual'] = current
  changes[key] = value
  before = {k: _raw(params, k) for k in changes}
  applied = []
  try:
    for changed_key, changed_value in changes.items():
      put = params.put_bool if changed_key in SCREEN_WAKE_KEYS else params.put_int
      put(changed_key, changed_value)
      applied.append(changed_key)
      actual = _raw(params, changed_key)
      if changed_key in SCREEN_WAKE_KEYS:
        matches = (changed_key in enabled_wake_keys(params)) == changed_value
      else:
        matches = actual is not None and _integer(params, changed_key, -999, -100, 101) == changed_value
      if not matches:
        raise OSError('Screen setting write did not persist')
  except Exception:
    for changed_key in reversed(applied):
      try:
        previous = before[changed_key]
        if previous is None:
          params.remove(changed_key)
        elif changed_key in SCREEN_WAKE_KEYS:
          params.put_bool(changed_key, _boolean(previous))
        else:
          params.put_int(changed_key, int(previous))
      except Exception:
        pass
    raise
  return changes


def set_brightness_mode(params, key, mode):
  if mode not in ('auto', 'manual'):
    raise ValueError('Brightness mode must be Auto or Manual')
  if key not in BRIGHTNESS_KEYS:
    raise ValueError('Unknown brightness setting')
  with _screen_write_transaction(params):
    preferences = brightness_preferences(params, key)
    return _write_screen_setting(params, key, 101 if mode == 'auto' else preferences['manual'])


def calculate_screen_brightness(automatic, manual, offset=0, *, interactive=False, awake=True, standby_timed_out=False):
  if not awake or standby_timed_out:
    return 0
  target = automatic * (1 + min(30, max(-30, offset)) / 100) if manual == 101 else manual
  target = min(100, max(0, round(target)))
  # A tap or selected wake event must make a deliberately dark screen usable.
  return max(5, target) if manual == 101 or interactive else target


def alert_wake_key(alert):
  status = str(getattr(alert, 'alertStatus', 'normal'))
  size = str(getattr(alert, 'alertSize', 'none'))
  if size in ('none', '0'):
    return None
  if status in ('critical', '2'):
    return 'StandbyWakeCriticalAlert'
  if status in ('userPrompt', '1'):
    return 'StandbyWakeWarningAlert'
  if size not in ('none', '0'):
    return 'StandbyWakeInfoAlert'
  return None


def standby_alert_wake_key(primary, secondary, *, now, started_time, started_frame, updated, recv_frame, recv_time,
                           primary_fresh, secondary_fresh, tici, mici, hide_alerts=False):
  """Resolve the current renderer alert without constructing a UI widget.

  Both renderers generate startup/unresponsive alerts before reading normal
  messages. C4 keeps the reboot alert critical; C3 renders it informational.
  Raw stale messages never wake Standby, even if still cached by the renderer.
  """
  waiting_for_startup = recv_frame < started_frame
  if not updated:
    if waiting_for_startup and now - started_time > 5:
      return 'StandbyWakeInfoAlert'
    missing = now - recv_time
    if tici and not waiting_for_startup and missing > 5:
      if getattr(primary, 'enabled', False) and missing - 5 < 10:
        return 'StandbyWakeCriticalAlert'
      return 'StandbyWakeCriticalAlert' if mici else 'StandbyWakeInfoAlert'

  if waiting_for_startup:
    return None
  # Primary alerts take display precedence, even when that category is disabled.
  if alert_wake_key(primary) is not None:
    alert = primary if primary_fresh else None
  else:
    alert = secondary if secondary_fresh else None
  if not mici and hide_alerts and str(getattr(alert, 'alertStatus', 'normal')) in ('normal', '0'):
    return None
  return alert_wake_key(alert)


class StandbyWakeTracker:
  """Detect new driver inputs; missing samples reset each input's history."""
  def __init__(self):
    self.previous = {}

  def update(self, *, engaged=None, turn_signal=None, brake=None, accelerator=None, drive_state=None):
    current = dict(engaged=engaged, turn_signal=turn_signal, brake=brake, accelerator=accelerator, drive_state=drive_state)
    events = set()
    for key, value in current.items():
      previous = self.previous.get(key)
      if value is not None and previous is not None and value != previous:
        if key == 'engaged':
          events.add('StandbyWakeEngage' if value else 'StandbyWakeDisengage')
        elif key == 'drive_state':
          events.add('StandbyWakeDriveState')
        elif value:
          events.add({'turn_signal': 'StandbyWakeTurnSignal', 'brake': 'StandbyWakeBrake', 'accelerator': 'StandbyWakeAccelerator'}[key])
    self.previous = current
    return events


def standby_button_press_time(params):
  try:
    return max(0, int(_raw(params, STANDBY_BUTTON_PRESS_PARAM) or 0))
  except (TypeError, ValueError, OverflowError):
    return 0
