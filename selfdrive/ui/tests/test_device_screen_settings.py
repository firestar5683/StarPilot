from types import SimpleNamespace

from openpilot.selfdrive.ui import ui_state as ui_state_module


class FakeParams:
  def __init__(self, **values):
    self.values = values

  def get_bool(self, key, **_kwargs):
    return bool(self.values.get(key, False))

  def get_int(self, key, **_kwargs):
    return int(self.values.get(key, 0))


class PassthroughFilter:
  def update(self, value):
    return value


def make_device(monkeypatch, **overrides):
  values = {
    "ScreenManagement": True,
    "ScreenBrightness": 35,
    "ScreenBrightnessOnroad": 45,
    "ScreenTimeout": 30,
    "ScreenTimeoutOnroad": 10,
    "StandbyMode": False,
  }
  values.update(overrides)
  state = SimpleNamespace(
    ui_params=FakeParams(**values),
    status=ui_state_module.UIStatus.DISENGAGED,
    started=False,
    ignition=False,
    light_sensor=-1.0,
    sm={},
  )
  monkeypatch.setattr(ui_state_module, "ui_state", state)
  monkeypatch.setattr(ui_state_module.gui_app, "big_ui", lambda: False)
  monkeypatch.setattr(ui_state_module.gui_app, "_mouse_events", [])
  device = ui_state_module.Device()
  device._brightness_filter = PassthroughFilter()
  return device, state


def test_manual_brightness_applies_to_current_device_state(monkeypatch):
  device, state = make_device(monkeypatch)

  assert device._calculate_brightness() == 35

  state.started = True
  assert device._calculate_brightness() == 45


def test_auto_brightness_preserves_existing_behavior(monkeypatch):
  device, state = make_device(monkeypatch, ScreenBrightness=101, ScreenBrightnessOnroad=101)

  assert device._calculate_brightness() == ui_state_module.BACKLIGHT_OFFROAD

  state.started = True
  state.light_sensor = -1.0
  assert device._calculate_brightness() == ui_state_module.BACKLIGHT_OFFROAD


def test_screen_management_off_ignores_custom_values(monkeypatch):
  device, state = make_device(monkeypatch, ScreenManagement=False, ScreenBrightness=10, ScreenBrightnessOnroad=20,
                              StandbyMode=True)

  assert device._calculate_brightness() == ui_state_module.BACKLIGHT_OFFROAD

  state.started = True
  device._interaction_time = 0
  assert device._calculate_brightness() == ui_state_module.BACKLIGHT_OFFROAD
  assert device.interactive_timeout == 30


def test_screen_settings_refresh_after_external_param_change(monkeypatch):
  now = 100.0
  monkeypatch.setattr(ui_state_module.time, "monotonic", lambda: now)
  device, state = make_device(monkeypatch)
  state.started = True
  state.ignition = True
  device._ignition = True
  device._interaction_time = now + 10

  state.ui_params.values["ScreenBrightnessOnroad"] = 72
  state.ui_params.values["ScreenTimeoutOnroad"] = 25
  now += device.SCREEN_SETTINGS_REFRESH_INTERVAL
  device._refresh_screen_settings()

  assert device._calculate_brightness() == 72
  assert device.interactive_timeout == 25
  assert device._interaction_time == now + 25


def test_standby_blanks_after_timeout_and_touch_wakes(monkeypatch):
  now = 100.0
  monkeypatch.setattr(ui_state_module.time, "monotonic", lambda: now)
  device, state = make_device(monkeypatch, StandbyMode=True)
  state.started = True
  state.ignition = True
  device._ignition = True
  device._interaction_time = now - 1

  assert device._calculate_brightness() == 0

  monkeypatch.setattr(ui_state_module.gui_app, "_mouse_events", [SimpleNamespace(left_down=True)])
  device._update_wakefulness()

  assert device._interaction_time == now + 10
  assert device._calculate_brightness() == 45


def test_hide_ui_blanks_after_timeout_and_touch_wakes(monkeypatch):
  now = 100.0
  monkeypatch.setattr(ui_state_module.time, "monotonic", lambda: now)
  device, state = make_device(monkeypatch, ScreenBrightnessOnroad=0)
  state.started = True
  state.ignition = True
  device._ignition = True
  device._interaction_time = now - 1

  assert device._calculate_brightness() == 0

  monkeypatch.setattr(ui_state_module.gui_app, "_mouse_events", [SimpleNamespace(left_down=True)])
  device._update_wakefulness()

  assert device._interaction_time == now + 10
  assert device._calculate_brightness() == 5


def test_standby_wakes_for_visible_alert(monkeypatch):
  now = 100.0
  monkeypatch.setattr(ui_state_module.time, "monotonic", lambda: now)
  device, state = make_device(monkeypatch, StandbyMode=True)
  state.started = True
  state.ignition = True
  device._ignition = True
  device._interaction_time = now - 1
  device._visible_onroad_alert = lambda: True

  device._update_wakefulness()

  assert device._interaction_time == now + 10
  assert device._calculate_brightness() == 45
