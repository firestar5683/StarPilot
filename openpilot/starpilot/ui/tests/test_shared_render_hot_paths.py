"""Hot-path shortcuts in shared UI renderers must draw exactly what the long way did."""

from types import SimpleNamespace

import numpy as np
import pytest


class TestShaderUniformCache:
  @pytest.fixture
  def state(self, monkeypatch):
    from openpilot.system.ui.lib import shader_polygon
    uploads = []
    monkeypatch.setattr(shader_polygon.rl, "set_shader_value", lambda shader, location, value, kind: uploads.append(location))
    monkeypatch.setattr(shader_polygon.rl, "set_shader_value_v",
                        lambda shader, location, value, kind, count: uploads.append(location))
    state = object.__new__(shader_polygon.ShaderState)  # the singleton's state without its GL shader
    state.shader = object()
    state.locations = {name: name for name in ("fillColor", "useGradient", "gradientStart", "gradientEnd",
                                               "gradientColors", "gradientStops", "gradientColorCount")}
    for name, ctype, size in (("fill_color_ptr", "float[]", 4), ("use_gradient_ptr", "int[]", 1), ("color_count_ptr", "int[]", 1),
                              ("gradient_colors_ptr", "float[]", shader_polygon.MAX_GRADIENT_COLORS * 4),
                              ("gradient_stops_ptr", "float[]", shader_polygon.MAX_GRADIENT_COLORS)):
      setattr(state, name, shader_polygon.rl.ffi.new(ctype, size))
    state.uniform_values = {}
    return shader_polygon, state, uploads

  def test_unchanged_color_is_uploaded_once(self, state):
    shader_polygon, state, uploads = state
    rect = shader_polygon.rl.Rectangle(0, 0, 100, 100)
    color = shader_polygon.rl.Color(10, 20, 30, 255)
    shader_polygon._configure_shader_color(state, color, None, rect)
    assert sorted(uploads) == ["fillColor", "useGradient"]
    shader_polygon._configure_shader_color(state, color, None, rect)
    assert len(uploads) == 2
    color.g = 21  # edited in place: the value changed, the object did not
    shader_polygon._configure_shader_color(state, color, None, rect)
    assert uploads[-1] == "fillColor" and len(uploads) == 3

  def test_gradient_uploads_only_what_changed(self, state):
    shader_polygon, state, uploads = state
    rl = shader_polygon.rl
    gradient = shader_polygon.Gradient(start=(0.0, 1.0), end=(0.0, 0.0),
                                       colors=[rl.Color(255, 0, 0, 255), rl.Color(0, 0, 255, 128)], stops=[0.0, 1.0])
    shader_polygon._configure_shader_color(state, None, gradient, rl.Rectangle(0, 0, 100, 100))
    first = len(uploads)
    assert first == 6
    shader_polygon._configure_shader_color(state, None, gradient, rl.Rectangle(0, 0, 100, 100))
    assert len(uploads) == first
    shader_polygon._configure_shader_color(state, None, gradient, rl.Rectangle(0, 10, 100, 100))
    assert sorted(uploads[first:]) == ["gradientEnd", "gradientStart"]
    np.testing.assert_allclose(list(state.gradient_colors_ptr[0:8]), [1, 0, 0, 1, 0, 0, 1, 128 / 255], rtol=1e-6)

  def test_reloading_the_shader_forgets_uploaded_values(self, state, monkeypatch):
    shader_polygon, state, uploads = state
    color = shader_polygon.rl.Color(1, 2, 3, 4)
    shader_polygon._configure_shader_color(state, color, None, shader_polygon.rl.Rectangle(0, 0, 1, 1))
    monkeypatch.setattr(shader_polygon.rl, "unload_shader", lambda shader: None)
    state.initialized = True
    state.cleanup()
    assert state.uniform_values == {}


class TestModelLineEndpoint:
  @pytest.fixture
  def renderer(self):
    from openpilot.selfdrive.ui.onroad.model_renderer import ModelRenderer
    renderer = object.__new__(ModelRenderer)
    renderer._car_space_transform = np.eye(3, dtype=np.float32)
    renderer._clip_region = SimpleNamespace(x=-500, y=-500, width=2000, height=2000)
    return renderer

  @pytest.mark.parametrize("dtype", [np.float32, np.float64])
  @pytest.mark.parametrize("endpoints", [(10, 20), (10, 10), (20, 10)])
  @pytest.mark.parametrize("distance", [5, 10, 15, 20, 25])
  def test_endpoint_matches_numpy_interp(self, renderer, dtype, endpoints, distance):
    line = np.array([[0, 0, 2], [endpoints[0], 2, 3], [endpoints[1], 6, 5], [30, 8, 7]], dtype=dtype)
    endpoint = [distance, np.interp(distance, line[1:3, 0], line[1:3, 1]), np.interp(distance, line[1:3, 0], line[1:3, 2])]
    expanded = np.concatenate((line[:2], np.array([endpoint], dtype=dtype)))
    expected = renderer._map_line_to_polygon(expanded, 0.9, 1.2, 2, distance)
    actual = renderer._map_line_to_polygon(line, 0.9, 1.2, 1, distance)
    np.testing.assert_allclose(actual, expected, rtol=1e-6, atol=1e-6)
