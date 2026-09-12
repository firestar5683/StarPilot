import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest


def screen():
  return importlib.import_module('openpilot.starpilot.common.screen_settings')


class Params:
  def __init__(self, values=None):
    self.values = dict(values or {})
    self.fail_key = None
    self.directory = TemporaryDirectory(prefix='screen-settings-test-')

  def get_param_path(self):
    return str(Path(self.directory.name) / 'd')

  def get(self, key):
    return self.values.get(key)

  def put_int(self, key, value):
    if key == self.fail_key:
      raise OSError('simulated write failure')
    self.values[key] = value

  def put_bool(self, key, value):
    self.put_int(key, value)

  def remove(self, key):
    self.values.pop(key, None)


@pytest.mark.parametrize('key', ['ScreenBrightness', 'ScreenBrightnessOnroad'])
def test_new_defaults_auto_zero_offset_and_remembered_manual(key):
  assert screen().brightness_preferences(Params(), key) == {'mode': 'auto', 'manual': 100, 'offset': 0}


def test_mode_switches_preserve_each_manual_level_independently():
  params = Params({'ScreenBrightness': 21, 'ScreenBrightnessOnroad': 76})
  screen().set_brightness_mode(params, 'ScreenBrightness', 'auto')
  screen().set_brightness_mode(params, 'ScreenBrightnessOnroad', 'auto')
  assert params.values['ScreenBrightness'] == 101
  assert params.values['ScreenBrightnessOnroad'] == 101
  screen().set_brightness_mode(params, 'ScreenBrightness', 'manual')
  screen().set_brightness_mode(params, 'ScreenBrightnessOnroad', 'manual')
  assert params.values['ScreenBrightness'] == 21
  assert params.values['ScreenBrightnessOnroad'] == 76


def test_manual_zero_is_remembered_and_auto_offset_is_retained():
  params = Params({'ScreenBrightness': 101, 'ScreenBrightnessOffset': -12})
  screen().write_screen_setting(params, 'ScreenBrightness', 0)
  screen().set_brightness_mode(params, 'ScreenBrightness', 'auto')
  assert screen().brightness_preferences(params, 'ScreenBrightness') == {'mode': 'auto', 'manual': 0, 'offset': -12}
  screen().set_brightness_mode(params, 'ScreenBrightness', 'manual')
  assert params.values['ScreenBrightness'] == 0


@pytest.mark.parametrize('key,value', [
  ('ScreenBrightness', -1), ('ScreenBrightness', 102), ('ScreenBrightness', True),
  ('ScreenBrightness', 3.5), ('ScreenBrightnessOffset', -31), ('ScreenBrightnessOffset', float('nan')),
  ('ScreenBrightnessOnroadOffset', 31), ('ScreenBrightnessManual', 101),
  ('StandbyWakeCriticalAlert', 'false'), ('StandbyWakeBrake', 1), ('StandbyWakeUnknown', True),
])
def test_invalid_values_are_rejected_without_any_writes(key, value):
  params = Params({'ScreenBrightness': 101})
  with pytest.raises(ValueError):
    screen().write_screen_setting(params, key, value)
  assert params.values == {'ScreenBrightness': 101}


def test_failed_primary_write_does_not_change_display_mode():
  params = Params({'ScreenBrightness': 25, 'ScreenBrightnessManual': 80})
  params.fail_key = 'ScreenBrightness'
  with pytest.raises(OSError):
    screen().set_brightness_mode(params, 'ScreenBrightness', 'auto')
  assert params.values['ScreenBrightness'] == 25


@pytest.mark.parametrize('automatic,manual,offset,expected', [
  (65, 101, 10, 72), (50, 101, -15, 42), (95, 101, 25, 100), (30, 101, -40, 21),
  (40, 101, -30, 28), (0, 101, -30, 5), (2, 101, 30, 5),
  (80, 23, 50, 23), (80, 0, -40, 0), (20, 100, 100, 100),
])
def test_offset_only_affects_auto_and_output_is_bounded(automatic, manual, offset, expected):
  assert screen().calculate_screen_brightness(automatic, manual, offset) == expected


@pytest.mark.parametrize('manual,offset', [(0, 0)])
def test_zero_brightness_can_temporarily_be_seen_after_waking(manual, offset):
  assert screen().calculate_screen_brightness(30, manual, offset, interactive=True) == 5
  assert screen().calculate_screen_brightness(30, manual, offset, interactive=False) == 0


def test_sleep_and_standby_override_positive_offsets():
  assert screen().calculate_screen_brightness(65, 101, 100, awake=False, interactive=True) == 0
  assert screen().calculate_screen_brightness(65, 101, 100, standby_timed_out=True) == 0


@pytest.mark.parametrize('status,size,expected', [
  ('normal', 'none', None), ('normal', 'small', 'StandbyWakeInfoAlert'),
  ('userPrompt', 'small', 'StandbyWakeWarningAlert'), ('critical', 'full', 'StandbyWakeCriticalAlert'),
  ('critical', 'none', None),
])
def test_alerts_are_classified_by_priority(status, size, expected):
  assert screen().alert_wake_key(SimpleNamespace(alertStatus=status, alertSize=size)) == expected


def test_defaults_preserve_alert_and_engagement_waking_only():
  enabled = screen().enabled_wake_keys(Params())
  assert enabled == {'StandbyWakeEngage', 'StandbyWakeDisengage', 'StandbyWakeInfoAlert', 'StandbyWakeWarningAlert',
                     'StandbyWakeCriticalAlert', 'StandbyWakeTouch', 'StandbyWakeDriveState'}
  assert 'StandbyWakeCriticalAlert' not in screen().enabled_wake_keys(Params({'StandbyWakeCriticalAlert': False}))


def test_vehicle_triggers_are_edges_not_continuous_pedal_or_signal_states():
  tracker = screen().StandbyWakeTracker()
  assert tracker.update(engaged=False, turn_signal=0, brake=False, accelerator=False) == set()
  assert tracker.update(engaged=True, turn_signal=1, brake=True, accelerator=True) == {
    'StandbyWakeEngage', 'StandbyWakeTurnSignal', 'StandbyWakeBrake', 'StandbyWakeAccelerator'}
  assert tracker.update(engaged=True, turn_signal=1, brake=True, accelerator=True) == set()
  assert tracker.update(engaged=False, turn_signal=2, brake=False, accelerator=False) == {'StandbyWakeDisengage', 'StandbyWakeTurnSignal'}


def test_stale_vehicle_data_does_not_create_wake_events_when_it_returns():
  tracker = screen().StandbyWakeTracker()
  tracker.update(engaged=False, turn_signal=0, brake=False, accelerator=False)
  assert tracker.update() == set()
  assert tracker.update(engaged=True, turn_signal=1, brake=True, accelerator=True) == set()


@pytest.mark.parametrize('key', ['ScreenBrightness', 'ScreenBrightnessOnroad'])
@pytest.mark.parametrize('stored,expected', [(-100, -30), (100, 30), (-30, -30), (30, 30)])
def test_saved_offsets_are_limited_without_rewriting_preferences(key, stored, expected):
  params = Params({key + 'Offset': stored})
  assert screen().brightness_preferences(params, key)['offset'] == expected
  assert params.values[key + 'Offset'] == stored


@pytest.mark.parametrize('offset', [-30, 30])
def test_offset_limits_can_be_saved_in_both_contexts(offset):
  params = Params()
  for key in ('ScreenBrightnessOffset', 'ScreenBrightnessOnroadOffset'):
    assert screen().write_screen_setting(params, key, offset) == {key: offset}


def test_legacy_excessive_offset_is_clamped_in_brightness_calculation():
  assert screen().calculate_screen_brightness(65, 101, -100) == 46
