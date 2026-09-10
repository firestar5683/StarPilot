from types import SimpleNamespace
import pytest
from openpilot.selfdrive.ui.tests.test_personality_selection import methods, Params

PATH = "selfdrive/ui/layouts/settings/starpilot/vehicle.py"


def controller(onroad=False, supported=True, firmware_available=True):
  params = Params(IsOnroad=onroad, TeslaWakeOnCAN=False)
  dialogs, launches = [], []
  def preflight(*_):
    if not firmware_available:
      raise RuntimeError("Tesla firmware is missing")
  env = {
    "validate_tesla_can_wake_firmware": preflight,
    "tr": lambda s: s, "supports_tesla_can_wake": lambda _: supported,
    "starpilot_state": SimpleNamespace(update=lambda **_: None),
    "gui_app": SimpleNamespace(push_widget=dialogs.append),
    "ConfirmDialog": lambda *args, **kw: SimpleNamespace(callback=kw["callback"]),
    "alert_dialog": lambda text: text,
    "DialogResult": SimpleNamespace(CONFIRM=True),
    "threading": SimpleNamespace(Thread=lambda **kw: SimpleNamespace(start=lambda: launches.append(True))),
  }
  cls = methods(PATH, "StarPilotVehicleSettingsLayout", {"_on_panda_firmware_toggle"}, env)
  obj = cls()
  obj._params = params
  obj._manager_view = SimpleNamespace(_rebuild_toggle_grid=lambda: None)
  return obj, params, dialogs, launches


@pytest.mark.parametrize("onroad,supported", [(True, True), (False, False)])
def test_native_rejects_onroad_or_unsupported_tesla_toggle(onroad, supported):
  obj, params, dialogs, launches = controller(onroad, supported)
  obj._on_panda_firmware_toggle("TeslaWakeOnCAN", "Flash")
  assert not any(hasattr(d, "callback") for d in dialogs)
  assert not params.writes and not launches


def test_native_rechecks_onroad_after_confirmation_opens():
  obj, params, dialogs, launches = controller()
  obj._on_panda_firmware_toggle("TeslaWakeOnCAN", "Flash")
  params.values["IsOnroad"] = True
  dialogs[0].callback(True)
  assert not params.writes and not launches


def test_native_offroad_confirmation_saves_and_starts_flash():
  obj, params, dialogs, launches = controller()
  obj._on_panda_firmware_toggle("TeslaWakeOnCAN", "Flash")
  dialogs[0].callback(True)
  assert params.values["TeslaWakeOnCAN"] is True
  assert launches == [True]


def test_missing_native_tesla_firmware_keeps_saved_setting():
  obj, params, dialogs, launches = controller(firmware_available=False)
  obj._on_panda_firmware_toggle("TeslaWakeOnCAN", "Flash")
  assert not any(hasattr(d, "callback") for d in dialogs)
  assert any("missing" in d for d in dialogs)
  assert not params.writes and not launches


@pytest.mark.parametrize("supported", [False, True])
def test_native_vehicle_row_visibility_and_off_default(supported):
  car_state = SimpleNamespace(**{key: False for key in (
    "isGM", "hasPedal", "canUsePedal", "hasOpenpilotLongitudinal", "isVolt", "hasSNG",
    "isJeep", "isSubaru", "isToyota", "isBolt", "isHKGCanFd",
  )})
  params = Params()
  cls = methods(PATH, "VehicleSettingsManagerView", {"_build_driving_toggles"}, {
    "tr": lambda s: s, "starpilot_state": SimpleNamespace(car_state=car_state),
    "supports_tesla_can_wake": lambda _: supported,
  })
  view = cls()
  view._controller = SimpleNamespace(_params=params)
  rows = [row for row in view._build_driving_toggles() if row["title"] == "Wake on CAN"]
  assert len(rows) == int(supported)
  if supported:
    assert rows[0]["get_state"]() is False
