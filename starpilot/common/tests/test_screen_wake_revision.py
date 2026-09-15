"""Requested standby contract, exercised through the actual Device class."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from openpilot.starpilot.common import screen_settings as screen
from test_screen_device_runtime import make_device


EXPECTED = {
  'StandbyWakeEngage', 'StandbyWakeDisengage', 'StandbyWakeInfoAlert',
  'StandbyWakeWarningAlert', 'StandbyWakeCriticalAlert', 'StandbyWakeTurnSignal',
}


def disabled():
  return dict.fromkeys(EXPECTED, False)


def test_only_requested_wake_options_are_exposed():
  assert screen.SCREEN_WAKE_KEYS == EXPECTED
  root = Path(__file__).resolve().parents[3]
  layout = json.loads((root / 'starpilot/common/assets/device_settings_layout.json').read_text())
  keys = {p['key'] for section in layout for p in section['params'] if p['key'].startswith('StandbyWake')}
  assert keys == EXPECTED


@pytest.mark.parametrize('source', ['touch', 'button'])
def test_touch_and_unassigned_button_always_wake_even_with_old_disabled_settings(source):
  device, state, app = make_device(**disabled(), StandbyWakeTouch=False, StandbyWakeButton=False)
  device._update_wakefulness()
  if source == 'touch':
    app.mouse_events = [SimpleNamespace(left_down=True)]
  else:
    state.params_memory.values['StandbyButtonPressTime'] = 99_500_000_000
  device._update_wakefulness()
  assert device.awake
  assert device._calculate_brightness() > 0


@pytest.mark.parametrize('field,value,old_key', [
  ('brakePressed', True, 'StandbyWakeBrake'),
  ('gasPressed', True, 'StandbyWakeAccelerator'),
  ('gearShifter', 'reverse', 'StandbyWakeDriveState'),
])
def test_removed_driver_triggers_do_not_wake_even_with_old_enabled_settings(field, value, old_key):
  device, state, _ = make_device(**disabled(), **{old_key: True})
  device._update_wakefulness()
  setattr(state.sm['carState'], field, value)
  device._update_wakefulness()
  assert device._calculate_brightness() == 0


@pytest.mark.parametrize('target,key', [('ENGAGED', 'StandbyWakeEngage'), ('DISENGAGED', 'StandbyWakeDisengage')])
@pytest.mark.parametrize('selected', [False, True])
def test_dom_status_transition_out_of_override_obeys_corresponding_toggle(target, key, selected):
  device, state, _ = make_device(**{**disabled(), key: selected})
  state.status = type(state.status).OVERRIDE
  device._update_wakefulness()
  assert device._calculate_brightness() == 0
  state.status = getattr(type(state.status), target)
  device._update_wakefulness()
  assert (device._calculate_brightness() > 0) is selected


@pytest.mark.parametrize('status,key', [('userPrompt', 'StandbyWakeWarningAlert'), ('critical', 'StandbyWakeCriticalAlert')])
def test_dom_non_normal_alert_status_wakes_even_without_alert_size(status, key):
  device, state, _ = make_device(**{**disabled(), key: True})
  state.sm['selfdriveState'].alertStatus = status
  device._update_wakefulness()
  assert device._calculate_brightness() > 0


def test_dom_standby_powers_display_down_until_touch():
  device, _, app = make_device(**disabled())
  device._update_wakefulness()
  assert not device.awake
  app.mouse_events = [SimpleNamespace(left_down=True)]
  device._update_wakefulness()
  assert device.awake


@pytest.mark.parametrize('event', ['engage', 'alert'])
def test_dom_manual_zero_suppresses_automatic_status_and_alert_wakes(event):
  device, state, app = make_device(ScreenBrightnessOnroad=0)
  if event == 'engage':
    state.status = type(state.status).ENGAGED
    state.sm['selfdriveState'].enabled = True
  else:
    state.sm['selfdriveState'].alertStatus = 'critical'
    state.sm['selfdriveState'].alertSize = 'full'
  device._update_wakefulness()
  assert device._calculate_brightness() == 0
  app.mouse_events = [SimpleNamespace(left_down=True)]
  device._update_wakefulness()
  assert device._calculate_brightness() == 5


def test_dom_ignition_transition_remains_unconditional():
  device, state, _ = make_device(**disabled(), StandbyWakeDriveState=False)
  state.ignition = False
  device._update_wakefulness()
  assert device._calculate_brightness() > 0
