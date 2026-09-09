import ast
import math
import re
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest

from openpilot.selfdrive.ui.onroad.starpilot.developer_metrics import build_developer_metric_parts, external_gpu_temperature_metric, external_gpu_memory_metric


ONROAD_VIEW = Path("selfdrive/ui/onroad/starpilot/starpilot_onroad_view.py")


def test_comma4_developer_metrics_use_published_temperatures_and_real_memory_capacity():
  parts = build_developer_metric_parts(
    show_fps=True,
    show_cpu=True,
    show_gpu=True,
    show_temp=True,
    show_memory=True,
    fps=20.4,
    min_fps=18.2,
    max_fps=21.1,
    avg_fps=19.8,
    cpu_usage_percent=[20, 24, 2, 44, 0, 0, 0, 0],
    cpu_temp_c=[58.4, 58.4, 58.8, 59.4, 57.8, 58.1, 57.8, 58.1],
    gpu_usage_percent=0,
    gpu_temp_c=[57.1, 57.8],
    max_temp_c=59.5,
    memory_usage_percent=32,
    memory_total_gib=3.52,
  )

  assert parts == [
    "CPU: 11% / 59°C",
    "GPU: 0% / 58°C",
    "TEMP: 60°C",
    "RAM: 1.1/3.5 GiB (32%)",
    "FPS: 20",
    "Min: 18",
    "Max: 21",
    "Avg: 20",
  ]


def test_onroad_view_uses_the_device_agnostic_metric_formatter():
  source = ONROAD_VIEW.read_text()

  assert "self._memory_total_gib = system_memory_total_gib()" in source
  assert "cpu_temps = list(device_state.cpuTempC)" in source
  assert "gpu_temps = list(device_state.gpuTempC)" in source
  assert "parts = build_developer_metric_parts(" in source
  assert "if math.isfinite(fps) and fps > 0:" in source
  assert "int(device_state.gpuUsagePercent)" not in source
  assert "int(device_state.memoryUsagePercent)" not in source
  assert "float(device_state.maxTempC)" not in source
  assert "mem_gb = 8.0 * mem_val / 100.0" not in source


def test_nonfinite_usage_values_fall_back_without_crashing_the_ui():
  parts = build_developer_metric_parts(
    show_fps=True,
    show_cpu=True,
    show_gpu=True,
    show_temp=True,
    show_memory=True,
    fps=math.inf,
    min_fps=-math.inf,
    max_fps=math.nan,
    avg_fps=math.inf,
    cpu_usage_percent=cast(list[int], [math.inf, -math.inf, math.nan]),
    cpu_temp_c=[],
    gpu_usage_percent=cast(int, math.inf),
    gpu_temp_c=[],
    max_temp_c=math.nan,
    memory_usage_percent=cast(int, math.nan),
    memory_total_gib=math.inf,
  )

  assert parts == [
    "CPU: 0%",
    "GPU: 0%",
    "TEMP: --",
    "RAM: 0%",
    "FPS: --",
    "Min: --",
    "Max: --",
    "Avg: --",
  ]


@pytest.fixture
def mici_metrics_view():
  """Exercise actual MICI render/metrics bodies without target-only native imports."""
  source_path = Path("selfdrive/ui/mici/onroad/augmented_road_view.py")
  source = ast.parse(source_path.read_text())
  view_class = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == "AugmentedRoadView")
  methods: list[ast.stmt] = [node for node in view_class.body if isinstance(node, ast.FunctionDef) and node.name in {"_render", "_render_developer_metrics"}]

  class CameraView:
    def _render(self, _rect):
      pass

  def rectangle(x, y, width, height):
    return SimpleNamespace(x=x, y=y, width=width, height=height)

  draw_text = Mock()
  raylib = Mock()
  raylib.Rectangle = rectangle
  raylib.Vector2 = lambda x, y: SimpleNamespace(x=x, y=y)
  raylib.draw_text_ex = draw_text
  raylib.get_fps.return_value = 20
  enabled_params = {"DeveloperUI", "DeveloperMetrics", "ShowGPU"}
  params = SimpleNamespace(get_bool=lambda key, **_kwargs: key in enabled_params)

  class SubMaster(dict):
    valid = {"deviceState": True}
    alive = {"deviceState": True}

  sm = SubMaster(deviceState=SimpleNamespace(
    cpuUsagePercent=[20, 24, 2, 44, 0, 0, 0, 0], cpuTempC=[58.4, 59.4],
    gpuUsagePercent=0, gpuTempC=[57.1, 57.8], maxTempC=59.5, memoryUsagePercent=32,
  ))
  state = SimpleNamespace(
    started=True, is_onroad=lambda: True, sm=sm, ui_params=params,
    starpilot_toggles={"developer_ui": True, "debug_mode": False, "gpu_metrics": True},
  )
  # Use shipped Inter glyph advances and MICI FONT_SCALE, not guessed widths.
  font_lines = Path("selfdrive/assets/fonts/Inter-Medium.fnt").read_text().splitlines()
  advances = {}
  for line in font_lines:
    if line.startswith("char id="):
      fields = dict(re.findall(r"(\w+)=(-?\d+)", line))
      advances[int(fields["id"])] = int(fields["xadvance"])

  def measure_text(_font, text, size):
    return SimpleNamespace(x=sum(advances.get(ord(char), advances[63]) for char in text) * size * 1.16 / 200)

  namespace = {
    "CameraView": CameraView, "rl": raylib, "ui_state": state,
    "time": SimpleNamespace(monotonic=lambda: 1.0), "gui_app": Mock(),
    "messaging": Mock(), "SIDE_PANEL_WIDTH": 60,
    "CAMERA_VIEW_NONE": 4, "DRIVER_CAM": 2,
    "build_developer_metric_parts": build_developer_metric_parts,
    "external_gpu_temperature_metric": external_gpu_temperature_metric,
    "external_gpu_memory_metric": external_gpu_memory_metric,
    "measure_text_cached": measure_text,
  }
  # Compile the production methods unchanged. Mock only unrelated camera,
  # widget and graphics boundaries, not the metrics dispatch under test.
  isolated_class = ast.ClassDef(
    name="AugmentedRoadView", bases=[ast.Name(id="CameraView", ctx=ast.Load())],
    keywords=[], body=methods, decorator_list=[],
  )
  tree = ast.fix_missing_locations(ast.Module(body=[isolated_class], type_ignores=[]))
  exec(compile(tree, str(source_path), "exec"), namespace)
  view = namespace["AugmentedRoadView"]()
  view.rect = view._rect = rectangle(0, 0, 536, 240)
  view.stream_type = 0
  view._camera_view = lambda: 2
  view._controls_ready = lambda: True
  view._is_in_reverse = lambda: False
  view._get_border_width = lambda: 8
  for name in (
    "_switch_stream_if_needed", "_update_calibration", "_hud_renderer",
    "_model_renderer", "_driver_state_renderer", "_standstill_timer",
    "_min_steer_speed_banner", "_sidebar_widgets", "_confidence_ball",
    "_favorite_slots", "_pip_sidecam", "_draw_border", "_bookmark_icon", "_pm",
  ):
    setattr(view, name, Mock())
  view._alert_renderer = SimpleNamespace(will_render=lambda: (None, True), render=Mock())
  view._fade_texture = object()
  view._offroad_label = Mock()
  view._metrics_font = object()
  view._memory_total_gib = 3.52
  return SimpleNamespace(view=view, state=state, raylib=raylib, params=enabled_params, measure_text=measure_text)


def test_comma4_onroad_render_emits_enabled_gpu_metric(mici_metrics_view):
  fixture = mici_metrics_view
  fixture.view._render(fixture.view.rect)
  texts = [call.args[1] for call in fixture.raylib.draw_text_ex.call_args_list]
  assert " | ".join(texts) == "GPU: 0% / 58°C | eGPU: -- | eGPU RAM: --", "Enabled GPU metrics were never drawn by MICI on-road renderer"


@pytest.mark.parametrize("gate", ["DeveloperUI", "DeveloperMetrics", "ShowGPU", "resolved_gpu", "resolved_ui"])
def test_mici_metrics_respect_master_and_individual_toggles(mici_metrics_view, gate):
  f = mici_metrics_view
  if gate.startswith("resolved_"):
    f.state.starpilot_toggles["gpu_metrics" if gate == "resolved_gpu" else "developer_ui"] = False
  else:
    f.state.starpilot_toggles.clear()
    f.params.remove(gate)
  f.view._render(f.view.rect)
  f.raylib.draw_text_ex.assert_not_called()


@pytest.mark.parametrize("mode", ["alert", "alert_fading", "offroad", "waiting", "reverse", "driver", "camera_none"])
def test_mici_metrics_yield_to_alerts_and_nonroad_views(mici_metrics_view, mode):
  f = mici_metrics_view
  if mode in {"alert", "alert_fading"}:
    f.view._alert_renderer.will_render = lambda: (SimpleNamespace(visual_alert=0), mode == "alert")
    f.view._render.__globals__["car"] = Mock()
  elif mode == "offroad":
    f.state.started = False
  elif mode == "waiting":
    f.view._controls_ready = lambda: False
  elif mode == "reverse":
    f.view._is_in_reverse = lambda: True
  elif mode == "driver":
    f.view.stream_type = 2
  else:
    f.view._camera_view = lambda: 4
  f.view._render(f.view.rect)
  f.raylib.draw_text_ex.assert_not_called()


@pytest.mark.parametrize("status", ["valid", "alive"])
def test_mici_missing_or_stale_device_metrics_are_unavailable(mici_metrics_view, status):
  f = mici_metrics_view
  getattr(f.state.sm, status)["deviceState"] = False
  f.view._render(f.view.rect)
  assert " | ".join(call.args[1] for call in f.raylib.draw_text_ex.call_args_list) == "GPU: -- | eGPU: -- | eGPU RAM: --"


@pytest.mark.parametrize("border", [0, 8, 24])
def test_mici_all_metrics_fit_readably_inside_camera_bounds(mici_metrics_view, border):
  f = mici_metrics_view
  f.state.starpilot_toggles.clear()
  f.params.update({"ShowCPU", "NumericalTemp", "ShowMemoryUsage", "FPSCounter"})
  f.view._get_border_width = lambda: border
  f.view.rect.x, f.view.rect.y = 30, 12
  f.view._render(f.view.rect)
  calls = f.raylib.draw_text_ex.call_args_list
  text = " | ".join(call.args[1] for call in calls)
  for metric in ["CPU: 11% / 59°C", "GPU: 0% / 58°C", "TEMP: 60°C", "RAM: 1.1/3.5 GiB (32%)", "FPS: 20"]:
    assert metric in text
  assert "Min:" not in text
  panel = f.raylib.draw_rectangle_rec.call_args.args[0]
  content = f.view._content_rect
  assert panel.x >= content.x + max(border, 96)
  assert panel.x + panel.width <= content.x + content.width - max(border, 64)
  assert panel.y >= content.y + border
  assert panel.y + panel.height <= content.y + content.height - border
  for call in calls:
    font, line, pos, size = call.args[:4]
    assert size >= 16
    assert panel.x <= pos.x < pos.x + f.measure_text(font, line, size).x <= panel.x + panel.width
    assert panel.y <= pos.y < pos.y + size * 1.16 <= panel.y + panel.height


def test_mici_debug_mode_preserves_existing_overrides(mici_metrics_view):
  f = mici_metrics_view
  f.params.clear()
  f.state.starpilot_toggles = {"debug_mode": True, "gpu_metrics": False}
  f.view._render(f.view.rect)
  text = " | ".join(call.args[1] for call in f.raylib.draw_text_ex.call_args_list)
  for metric in ["CPU:", "TEMP:", "RAM:", "FPS:"]:
    assert metric in text
  assert "GPU:" not in text


def test_mici_metrics_are_drawn_below_safety_hud_and_previews(mici_metrics_view):
  f = mici_metrics_view
  order = Mock()
  order.attach_mock(f.raylib.draw_text_ex, "metrics")
  order.attach_mock(f.view._hud_renderer.render_background, "navigation")
  order.attach_mock(f.view._hud_renderer.render_foreground, "hud")
  order.attach_mock(f.view._pip_sidecam.render, "preview")
  f.view._render(f.view.rect)
  names = [call[0] for call in order.mock_calls]
  assert names.index("metrics") < names.index("navigation") < names.index("hud") < names.index("preview")


def test_comma4_selects_mici_metrics_renderer_and_initialises_resources():
  app = ast.parse(Path("system/ui/lib/application.py").read_text())
  cls = next(node for node in app.body if isinstance(node, ast.ClassDef) and node.name == "GuiApplication")
  method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "big_ui")
  method.decorator_list = []
  namespace = {"HARDWARE": SimpleNamespace(get_device_type=lambda: "mici"), "BIG_UI": False}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), "application.py", "exec"), namespace)
  assert namespace["big_ui"]() is False
  assert "from openpilot.selfdrive.ui.mici.layouts.main import MiciMainLayout" in Path("selfdrive/ui/ui.py").read_text()
  main = Path("selfdrive/ui/mici/layouts/main.py").read_text()
  assert "from openpilot.selfdrive.ui.mici.onroad.augmented_road_view import AugmentedRoadView" in main
  assert "self._onroad_layout = AugmentedRoadView(" in main
  view = ast.parse(Path("selfdrive/ui/mici/onroad/augmented_road_view.py").read_text())
  cls = next(node for node in view.body if isinstance(node, ast.ClassDef) and node.name == "AugmentedRoadView")
  init = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "__init__")
  source = ast.unparse(init)
  assert "self._memory_total_gib = system_memory_total_gib()" in source
  assert "self._metrics_font = gui_app.font(FontWeight.MEDIUM)" in source
