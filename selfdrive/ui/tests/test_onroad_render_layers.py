import importlib
import sys
from types import ModuleType, SimpleNamespace


def _load_augmented_road_view(monkeypatch):
  def stub_module(name, **attributes):
    module = ModuleType(name)
    for key, value in attributes.items():
      setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)

  class CameraView:
    def _render(self, _rect):
      self.events.append("camera")

  class UIStatus:
    DISENGAGED = 0
    OVERRIDE = 1
    ENGAGED = 2

  stub_module(
    "openpilot.selfdrive.ui.ui_state",
    ui_state=SimpleNamespace(started=True, sm=SimpleNamespace()),
    UIStatus=UIStatus,
  )
  stub_module("openpilot.selfdrive.ui.lib.starpilot_visuals", get_border_width=lambda *_args: 0)
  stub_module("openpilot.selfdrive.ui.lib.starpilot_status", get_screen_edge_color=lambda *_args: None)
  stub_module("openpilot.selfdrive.ui.onroad.alert_renderer", AlertRenderer=object)
  stub_module("openpilot.selfdrive.ui.onroad.driver_state", DriverStateRenderer=object)
  stub_module("openpilot.selfdrive.ui.onroad.hud_renderer", HudRenderer=object)
  stub_module("openpilot.selfdrive.ui.onroad.model_renderer", ModelRenderer=object)
  stub_module("openpilot.selfdrive.ui.onroad.cameraview", CameraView=CameraView)
  stub_module("openpilot.system.ui.lib.application", gui_app=SimpleNamespace(target_fps=20))

  module_name = "openpilot.selfdrive.ui.onroad.augmented_road_view"
  monkeypatch.delitem(sys.modules, module_name, raising=False)
  return importlib.import_module(module_name)


def _load_starpilot_onroad_view(monkeypatch):
  def stub_module(name, **attributes):
    module = ModuleType(name)
    for key, value in attributes.items():
      setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)

  class AugmentedRoadView:
    pass

  dummy_widget = type("DummyWidget", (), {})
  color = SimpleNamespace(r=0, g=0, b=0, a=255)

  stub_module("openpilot.selfdrive.ui.onroad.augmented_road_view", AugmentedRoadView=AugmentedRoadView)
  stub_module(
    "openpilot.selfdrive.ui.onroad.starpilot.starpilot_border",
    render_behind=lambda *_args: None,
    render_overlay=lambda *_args: None,
    render_background_effects=lambda *_args: None,
  )
  stub_module(
    "openpilot.selfdrive.ui.onroad.starpilot.path",
    render_adjacent_lanes=lambda *_args: None,
    render_path_edges=lambda *_args: None,
  )
  stub_module("openpilot.selfdrive.ui.ui_state", ui_state=SimpleNamespace())
  stub_module("openpilot.selfdrive.ui.onroad.starpilot.torque_bar", TorqueBar=dummy_widget)
  stub_module("openpilot.selfdrive.ui.onroad.starpilot.widget_layout_manager", WidgetLayoutManager=dummy_widget)
  stub_module(
    "openpilot.selfdrive.ui.onroad.starpilot.widgets",
    SetSpeedWidget=dummy_widget,
    SpeedLimitWidget=dummy_widget,
    PedalIconsWidget=dummy_widget,
    AetherGaugeWidget=dummy_widget,
    PersonalityButtonWidget=dummy_widget,
    DriverMonitorWidget=dummy_widget,
    SteeringWheelWidget=dummy_widget,
    StoppedTimerWidget=dummy_widget,
  )
  stub_module(
    "openpilot.selfdrive.ui.onroad.starpilot.stopping_point",
    render_stopping_point=lambda *_args: None,
  )
  stub_module(
    "openpilot.selfdrive.ui.onroad.starpilot.pause_indicators",
    render_lateral_paused=lambda *_args: None,
    render_longitudinal_paused=lambda *_args: None,
  )
  stub_module("openpilot.selfdrive.ui.onroad.starpilot.weather_icon", render_weather_icon=lambda *_args: None)
  stub_module(
    "openpilot.selfdrive.ui.lib.starpilot_status",
    get_screen_edge_color=lambda *_args: color,
    ENGAGED_COLOR=color,
    EXPERIMENTAL_COLOR=color,
    TRAFFIC_COLOR=color,
  )
  stub_module(
    "openpilot.system.ui.lib.application",
    MousePos=object,
    gui_app=SimpleNamespace(font=lambda *_args: None),
    FontWeight=SimpleNamespace(BOLD=0, MEDIUM=1),
  )
  stub_module(
    "openpilot.system.ui.lib.text_measure",
    draw_text_with_shadow=lambda *_args: None,
    measure_text_cached=lambda *_args: SimpleNamespace(x=0, y=0),
  )

  module_name = "openpilot.selfdrive.ui.onroad.starpilot.starpilot_onroad_view"
  monkeypatch.delitem(sys.modules, module_name, raising=False)
  return importlib.import_module(module_name)


def test_extra_road_overlays_render_between_model_and_hud_and_alerts_last(monkeypatch):
  augmented_road_view = _load_augmented_road_view(monkeypatch)
  events = []

  class LayeredRoadView(augmented_road_view.AugmentedRoadView):
    def _render_extra_road_overlays(self, _rect):
      events.append("road_overlays")

  class Renderer:
    def __init__(self, name):
      self.name = name

    def render(self, _rect):
      events.append(self.name)

  view = object.__new__(LayeredRoadView)
  view.events = events
  view.stream_type = augmented_road_view.ROAD_CAM
  view._camera_view = lambda: augmented_road_view.CAMERA_VIEW_STANDARD
  view._switch_stream_if_needed = lambda *_args: None
  view._is_in_reverse = lambda: False
  view._update_calibration = lambda: None
  view._get_border_width = lambda: 0
  view._draw_border = lambda _rect: events.append("border")
  view.model_renderer = Renderer("model")
  view._hud_renderer = Renderer("hud")
  view.driver_state_renderer = Renderer("driver_state")
  view.alert_renderer = Renderer("alert")
  view._draw_driver_state = True
  view._pm = SimpleNamespace(send=lambda *_args: events.append("publish"))

  monkeypatch.setattr(augmented_road_view.rl, "begin_scissor_mode", lambda *_args: events.append("scissor_begin"))
  monkeypatch.setattr(augmented_road_view.rl, "end_scissor_mode", lambda: events.append("scissor_end"))
  monkeypatch.setattr(
    augmented_road_view.messaging,
    "new_message",
    lambda *_args: SimpleNamespace(uiDebug=SimpleNamespace(drawTimeMillis=0.0)),
  )

  view._render(augmented_road_view.rl.Rectangle(0, 0, 100, 50))

  assert events == [
    "scissor_begin",
    "camera",
    "model",
    "road_overlays",
    "hud",
    "driver_state",
    "alert",
    "scissor_end",
    "border",
    "publish",
  ]


def test_full_alert_detection_uses_the_alert_size(monkeypatch):
  starpilot_onroad_view = _load_starpilot_onroad_view(monkeypatch)
  view = object.__new__(starpilot_onroad_view.StarPilotOnroadView)

  view.alert_renderer = SimpleNamespace(
    will_render=lambda: (SimpleNamespace(size=starpilot_onroad_view.AlertSize.full), False),
  )
  assert view._full_alert_showing()

  view.alert_renderer = SimpleNamespace(
    will_render=lambda: (SimpleNamespace(size=starpilot_onroad_view.AlertSize.mid), False),
  )
  assert not view._full_alert_showing()

  view.alert_renderer = SimpleNamespace(will_render=lambda: (None, True))
  assert not view._full_alert_showing()


def test_starpilot_road_overlays_use_the_parent_scissor(monkeypatch):
  starpilot_onroad_view = _load_starpilot_onroad_view(monkeypatch)
  events = []
  view = object.__new__(starpilot_onroad_view.StarPilotOnroadView)
  view.model_renderer = SimpleNamespace(
    _path=SimpleNamespace(projected_points=SimpleNamespace(size=1)),
    _track_edge_vertices=SimpleNamespace(size=4),
  )
  view._font_bold = object()

  monkeypatch.setattr(starpilot_onroad_view, "render_path_edges", lambda *_args: events.append("path_edges"))
  monkeypatch.setattr(starpilot_onroad_view, "render_adjacent_lanes", lambda *_args: events.append("adjacent_lanes"))
  monkeypatch.setattr(starpilot_onroad_view, "render_stopping_point", lambda *_args: events.append("stopping_point"))

  def fail_scissor(*_args):
    raise AssertionError("road overlay changed the parent scissor")

  monkeypatch.setattr(starpilot_onroad_view.rl, "begin_scissor_mode", fail_scissor)
  monkeypatch.setattr(starpilot_onroad_view.rl, "end_scissor_mode", fail_scissor)

  view._render_extra_road_overlays(object())

  assert events == ["path_edges", "adjacent_lanes", "stopping_point"]
