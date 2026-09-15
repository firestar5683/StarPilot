import importlib.util
from enum import IntFlag
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

from cereal import car


MODULE_PATH = Path(__file__).resolve().parents[1] / "onroad" / "starpilot" / "rivian_lateral_mode.py"
EXP_BUTTON_PATH = Path(__file__).resolve().parents[1] / "onroad" / "exp_button.py"


LateralControlMode = car.CarControl.Actuators.LateralControlMode


class FakeColor:
  def __init__(self, r, g, b, a):
    self.r = r
    self.g = g
    self.b = b
    self.a = a


class FakeRectangle:
  def __init__(self, x, y, width, height):
    self.x = x
    self.y = y
    self.width = width
    self.height = height


class FakeTexture:
  def __init__(self, name, width, height):
    self.name = name
    self.width = width
    self.height = height


class FakeSubMaster(dict):
  def __init__(self, *, lateral_mode, steering_pressed=False, lat_active=True):
    super().__init__({
      "carControl": SimpleNamespace(latActive=lat_active),
      "carState": SimpleNamespace(steeringPressed=steering_pressed),
      "carOutput": SimpleNamespace(
        actuatorsOutput=SimpleNamespace(lateralControlMode=lateral_mode),
      ),
    })
    self.frame = 1
    self.recv_frame = {"carControl": 1, "carState": 1}


def load_lateral_mode(monkeypatch, *, brand="rivian", angle_harness=True, longitudinal_harness=False,
                      steering_pressed=False, lat_active=True, lateral_mode=LateralControlMode.inactive):
  class RivianFlags(IntFlag):
    ANGLE_HARNESS = 1
    LONGITUDINAL_HARNESS = 2

  fake_pyray = ModuleType("pyray")
  fake_pyray.Color = lambda *args: args
  monkeypatch.setitem(sys.modules, "pyray", fake_pyray)

  values_module = ModuleType("opendbc.car.rivian.values")
  values_module.RivianFlags = RivianFlags
  monkeypatch.setitem(sys.modules, "opendbc.car.rivian.values", values_module)

  flags = RivianFlags(0)
  if angle_harness:
    flags |= RivianFlags.ANGLE_HARNESS
  if longitudinal_harness:
    flags |= RivianFlags.LONGITUDINAL_HARNESS

  ui_state = SimpleNamespace(
    CP=SimpleNamespace(brand=brand, flags=flags),
    sm=FakeSubMaster(lateral_mode=lateral_mode, steering_pressed=steering_pressed, lat_active=lat_active),
    started_frame=0,
  )
  ui_state_module = ModuleType("openpilot.selfdrive.ui.ui_state")
  ui_state_module.ui_state = ui_state
  monkeypatch.setitem(sys.modules, "openpilot.selfdrive.ui.ui_state", ui_state_module)

  spec = importlib.util.spec_from_file_location("rivian_lateral_mode_under_test", MODULE_PATH)
  assert spec is not None and spec.loader is not None
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


def load_exp_button(monkeypatch):
  draws = {"textures": [], "rings": []}
  fake_pyray = ModuleType("pyray")
  fake_pyray.Color = lambda *args: FakeColor(*args)
  fake_pyray.Rectangle = FakeRectangle
  fake_pyray.Texture = FakeTexture
  fake_pyray.Vector2 = lambda x, y: SimpleNamespace(x=x, y=y)
  fake_pyray.draw_circle = lambda *args: None
  fake_pyray.draw_ring = lambda *args: draws["rings"].append(args)
  fake_pyray.draw_texture_ex = lambda *args: draws["textures"].append(args)
  fake_pyray.draw_texture_pro = lambda *args: draws["textures"].append(args)
  monkeypatch.setitem(sys.modules, "pyray", fake_pyray)

  params_module = ModuleType("openpilot.common.params")
  params_module.Params = type("Params", (), {"get_bool": lambda self, *args, **kwargs: False})
  monkeypatch.setitem(sys.modules, "openpilot.common.params", params_module)

  fake_ui_state = SimpleNamespace(
    ui_params=SimpleNamespace(get_bool=lambda *args, **kwargs: False),
    sm={
      "selfdriveState": SimpleNamespace(experimentalMode=False, engageable=True, enabled=False),
      "carState": SimpleNamespace(steeringAngleDeg=0.0),
    },
    starpilot_toggles={},
    always_on_lateral_active=False,
    conditional_status=0,
    switchback_mode_enabled=False,
    traffic_mode_enabled=False,
    params_memory=SimpleNamespace(),
    has_longitudinal_control=False,
  )
  ui_state_module = ModuleType("openpilot.selfdrive.ui.ui_state")
  ui_state_module.ui_state = fake_ui_state
  monkeypatch.setitem(sys.modules, "openpilot.selfdrive.ui.ui_state", ui_state_module)

  class FakeGuiApp:
    target_fps = 60

    @staticmethod
    def texture(name, width, height):
      return FakeTexture(name, width, height)

  application_module = ModuleType("openpilot.system.ui.lib.application")
  application_module.gui_app = FakeGuiApp()
  monkeypatch.setitem(sys.modules, "openpilot.system.ui.lib.application", application_module)

  class FakeWidget:
    def __init__(self):
      self.is_pressed = False

    def set_visible(self, visible):
      self._visible = visible

    def _handle_mouse_release(self, _):
      pass

  widgets_module = ModuleType("openpilot.system.ui.widgets")
  widgets_module.Widget = FakeWidget
  monkeypatch.setitem(sys.modules, "openpilot.system.ui.widgets", widgets_module)

  class FakeFilter:
    def __init__(self, x, *args):
      self.x = x

    def update(self, x):
      self.x = x
      return x

  filter_module = ModuleType("openpilot.common.filter_simple")
  filter_module.FirstOrderFilter = FakeFilter
  monkeypatch.setitem(sys.modules, "openpilot.common.filter_simple", filter_module)

  experimental_module = ModuleType("openpilot.starpilot.common.experimental_state")
  experimental_module.CEStatus = {"OFF": 0}
  experimental_module.next_manual_ce_status = lambda *args: 0
  experimental_module.sync_manual_ce_state = lambda *args: None
  monkeypatch.setitem(sys.modules, "openpilot.starpilot.common.experimental_state", experimental_module)

  spec = importlib.util.spec_from_file_location("exp_button_under_test", EXP_BUTTON_PATH)
  assert spec is not None and spec.loader is not None
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module, draws


def test_angle_mode_uses_controller_report(monkeypatch):
  module = load_lateral_mode(monkeypatch, lateral_mode=LateralControlMode.angle)
  mode = module.RivianLateralMode()

  mode.update()

  assert mode.mode == "angle"
  assert mode.wheel_tint == module.ANGLE_COLOR


def test_zero_torque_at_standstill_stays_in_reported_torque_mode(monkeypatch):
  module = load_lateral_mode(monkeypatch, lateral_mode=LateralControlMode.torque)
  mode = module.RivianLateralMode()

  mode.update()

  assert mode.mode == "torque"
  assert mode.wheel_tint == module.TORQUE_COLOR


def test_torque_recovery_stays_blue(monkeypatch):
  module = load_lateral_mode(monkeypatch, lateral_mode=LateralControlMode.torqueRecovering)
  mode = module.RivianLateralMode()

  mode.update()

  assert mode.mode == "torque"
  assert mode.wheel_tint == module.TORQUE_COLOR


def test_basic_harness_rivian_uses_torque_color(monkeypatch):
  module = load_lateral_mode(monkeypatch, angle_harness=False, lateral_mode=LateralControlMode.torque)
  mode = module.RivianLateralMode()

  mode.update()

  assert mode.mode == "torque"
  assert mode.wheel_tint == module.TORQUE_COLOR


def test_longitudinal_harness_rivian_uses_torque_color(monkeypatch):
  module = load_lateral_mode(monkeypatch, angle_harness=False, longitudinal_harness=True,
                             lateral_mode=LateralControlMode.torque)
  mode = module.RivianLateralMode()

  mode.update()

  assert mode.mode == "torque"
  assert mode.wheel_tint == module.TORQUE_COLOR


@pytest.mark.parametrize(("angle_harness", "longitudinal_harness", "lateral_mode"), [
  (False, False, LateralControlMode.torque),
  (False, True, LateralControlMode.torque),
  (True, True, LateralControlMode.angle),
  (True, True, LateralControlMode.torque),
  (True, True, LateralControlMode.torqueRecovering),
])
def test_driver_steering_is_white_in_every_configuration(monkeypatch, angle_harness, longitudinal_harness, lateral_mode):
  module = load_lateral_mode(monkeypatch, angle_harness=angle_harness, longitudinal_harness=longitudinal_harness,
                             steering_pressed=True, lateral_mode=lateral_mode)
  mode = module.RivianLateralMode()

  mode.update()

  expected_mode = "angle" if lateral_mode == LateralControlMode.angle else "torque"
  assert mode.mode == expected_mode
  assert mode.driver_override
  assert mode.wheel_tint == module.DRIVER_OVERRIDE_COLOR


def test_releasing_wheel_restores_active_mode_color(monkeypatch):
  module = load_lateral_mode(monkeypatch, steering_pressed=True, lateral_mode=LateralControlMode.angle)
  mode = module.RivianLateralMode()
  mode.update()
  assert mode.wheel_tint == module.DRIVER_OVERRIDE_COLOR

  module.ui_state.sm["carState"].steeringPressed = False
  module.ui_state.sm.frame += 1
  mode.update()

  assert not mode.driver_override
  assert mode.wheel_tint == module.ANGLE_COLOR


def test_non_rivian_is_not_classified(monkeypatch):
  module = load_lateral_mode(monkeypatch, brand="toyota", steering_pressed=True,
                             lateral_mode=LateralControlMode.torque)
  mode = module.RivianLateralMode()

  mode.update()

  assert mode.mode is None
  assert not mode.driver_override
  assert mode.wheel_tint is None


def test_inactive_lateral_is_not_classified(monkeypatch):
  module = load_lateral_mode(monkeypatch, steering_pressed=True, lat_active=False,
                             lateral_mode=LateralControlMode.torque)
  mode = module.RivianLateralMode()

  mode.update()

  assert mode.mode is None
  assert not mode.driver_override
  assert mode.wheel_tint is None


def test_non_mici_wheel_icon_uses_rivian_tint(monkeypatch):
  module, draws = load_exp_button(monkeypatch)
  assert not isinstance(module.rl.Color, type)
  button = module.ExpButton(192, 144)
  button.wheel_tint = FakeColor(0x4D, 0x9D, 0xFF, 255)
  button._update_state()

  button._render(FakeRectangle(0, 0, 192, 192))

  assert len(draws["textures"]) == 1
  texture_color = draws["textures"][0][-1]
  assert (texture_color.r, texture_color.g, texture_color.b, texture_color.a) == (0x4D, 0x9D, 0xFF, 255)


def test_non_mici_wheel_icon_turns_red_when_brakes_are_pressed(monkeypatch):
  module, draws = load_exp_button(monkeypatch)
  button = module.ExpButton(192, 144)
  button.wheel_tint = FakeColor(0x4D, 0x9D, 0xFF, 255)
  module.ui_state.ui_params.get_bool = lambda key, *args, **kwargs: key == "ShowBrakeStatus"
  module.ui_state.sm["carState"].brakePressed = True
  button._update_state()

  button._render(FakeRectangle(0, 0, 192, 192))

  assert len(draws["textures"]) == 1
  texture_color = draws["textures"][0][-1]
  assert (texture_color.r, texture_color.g, texture_color.b, texture_color.a) == (255, 0, 0, 255)


def test_non_mici_wheel_icon_uses_reported_brake_lights(monkeypatch):
  module, draws = load_exp_button(monkeypatch)
  button = module.ExpButton(192, 144)
  button.wheel_tint = FakeColor(0x4D, 0x9D, 0xFF, 255)
  class FakeUiSubMaster(dict):
    pass

  module.ui_state.sm = FakeUiSubMaster(module.ui_state.sm)
  module.ui_state.sm.valid = {"starpilotCarState": True}
  module.ui_state.sm["starpilotCarState"] = SimpleNamespace(brakeLights=True)
  module.ui_state.ui_params.get_bool = lambda key, *args, **kwargs: key == "ShowBrakeStatus"
  button._update_state()

  button._render(FakeRectangle(0, 0, 192, 192))

  assert len(draws["textures"]) == 1
  texture_color = draws["textures"][0][-1]
  assert (texture_color.r, texture_color.g, texture_color.b, texture_color.a) == (255, 0, 0, 255)


def test_non_mici_wheel_icon_brake_tint_is_disabled_by_default(monkeypatch):
  module, draws = load_exp_button(monkeypatch)
  button = module.ExpButton(192, 144)
  button.wheel_tint = FakeColor(0x4D, 0x9D, 0xFF, 255)
  module.ui_state.sm["carState"].brakePressed = True
  button._update_state()

  button._render(FakeRectangle(0, 0, 192, 192))

  assert len(draws["textures"]) == 1
  texture_color = draws["textures"][0][-1]
  assert (texture_color.r, texture_color.g, texture_color.b, texture_color.a) == (0x4D, 0x9D, 0xFF, 255)
