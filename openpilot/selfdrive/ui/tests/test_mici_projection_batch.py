"""C4/Mici lane batching preserves the existing per-line projection."""

from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from openpilot.selfdrive.ui.mici.onroad.model_renderer import ModelRenderer
from openpilot.selfdrive.ui.onroad.model_renderer import ModelRenderer as LargeModelRenderer


@pytest.fixture
def renderer():
  view = object.__new__(ModelRenderer)
  view._car_space_transform = np.array([[580, -480, 0], [400, 0, -480], [1, 0, 0]], dtype=np.float32)
  view._clip_region = SimpleNamespace(x=-500, y=-500, width=2160, height=1800)
  return view


@pytest.mark.parametrize('lengths', [(33,) * 6, (100,) * 6, (0, 1, 7, 33, 15, 100), (0,) * 6])
@pytest.mark.parametrize('max_idx', [-1, 0, 15, 32, 100])
def test_batch_matches_individual_lane_and_edge_geometry(renderer, lengths, max_idx):
  rng = np.random.default_rng(20260924)
  lines = [np.column_stack((np.linspace(-5, 110, length), rng.normal(0, 6, length),
                            rng.normal(0, 1, length))).astype(np.float32) for length in lengths]
  widths = [0.12, 0.16, 0.16, 0.16, 0.16, 0.16]
  actual = renderer._map_lines_to_polygons(lines, widths, max_idx)
  expected = [renderer._map_line_to_polygon(line, width, 0.0, max_idx)
              for line, width in zip(lines, widths, strict=True)]
  assert len(actual) == len(expected)
  for polygon, reference in zip(actual, expected, strict=True):
    assert polygon.shape == reference.shape
    assert polygon.dtype == np.float32
    np.testing.assert_allclose(polygon, reference, rtol=0, atol=1e-4)


def test_batch_clips_each_line_independently_and_path_hill_filter_is_unchanged(renderer):
  renderer._car_space_transform = np.eye(3, dtype=np.float32)
  renderer._clip_region = SimpleNamespace(x=0, y=0, width=100, height=100)
  lines = [np.array([[0, 0, 0], [20, 50, 1], [30, 99, 1]], dtype=np.float32),
           np.empty((0, 3), dtype=np.float32),
           np.array([[-1, 10, 1], [40, 80, 1], [50, 10, 1]], dtype=np.float32)]
  with np.errstate(divide='raise', invalid='raise'):
    polygons = renderer._map_lines_to_polygons(lines, [2, 1, 15], 100)
  np.testing.assert_array_equal(polygons[0], [[20, 48], [20, 52]])
  assert polygons[1].shape == (0, 2)
  np.testing.assert_array_equal(polygons[2], [[40, 65], [40, 95]])

  hill = np.array([[10, 50, 1], [20, 40, 1], [30, 45, 1], [40, 30, 1]], dtype=np.float32)
  path = renderer._map_line_to_polygon(hill, 2, 0, len(hill), allow_invert=False)
  np.testing.assert_array_equal(path[:len(path) // 2], [[10, 48], [20, 38], [40, 28]])


@pytest.mark.parametrize("dirty", [False, True])
@pytest.mark.parametrize("renderer_class", [ModelRenderer, LargeModelRenderer])
def test_equal_float32_transform_preserves_pending_projection(renderer, dirty, renderer_class):
  renderer.set_transform = renderer_class.set_transform.__get__(renderer)
  renderer._transform_dirty = dirty
  original = renderer._car_space_transform
  incoming = original.astype(np.float64)
  incoming[0, 0] += 1e-7  # Distinct input, identical matrix at projection precision.
  renderer.set_transform(incoming)
  assert renderer._car_space_transform is original
  assert renderer._transform_dirty is dirty


@pytest.mark.parametrize("value", [581, np.nan])
@pytest.mark.parametrize("renderer_class", [ModelRenderer, LargeModelRenderer])
def test_changed_or_nan_transform_remains_dirty_and_owned(renderer, value, renderer_class):
  renderer.set_transform = renderer_class.set_transform.__get__(renderer)
  renderer._transform_dirty = False
  incoming = renderer._car_space_transform.astype(np.float64)
  incoming[0, 0] = value
  renderer.set_transform(incoming)
  assert renderer._transform_dirty
  assert renderer._car_space_transform.dtype == np.float32
  assert not np.shares_memory(renderer._car_space_transform, incoming)
  renderer._transform_dirty = False
  renderer.set_transform(incoming)
  assert renderer._transform_dirty == bool(np.isnan(value))


def test_transform_guard_preserves_render_projection_updates(renderer, monkeypatch):
  from openpilot.selfdrive.ui.mici.onroad import model_renderer

  class Messages(dict):
    recv_frame = {"extrinsicsCalibration": 1, "modelV2": 1}
    updated = {"carParams": False, "modelV2": False, "radarState": False}
    valid = {"radarState": False}

  sm = Messages(carOutput=SimpleNamespace(actuatorsOutput=SimpleNamespace(torque=0)),
                selfdriveState=SimpleNamespace(experimentalMode=False),
                extrinsicsCalibration=SimpleNamespace(height=[]), modelV2=object())
  monkeypatch.setattr(model_renderer, "ui_state", SimpleNamespace(sm=sm, started_frame=0))
  renderer._torque_filter = Mock()
  renderer._path = SimpleNamespace(raw_points=np.array([[10, 0, 0]], dtype=np.float32))
  renderer._lead_indicator_enabled = False
  renderer._visual_status = lambda: model_renderer.UIStatus.DISENGAGED
  renderer._update_model = Mock()
  renderer._update_raw_points = Mock()
  renderer._transform_dirty = True

  renderer._render(renderer._clip_region)
  assert renderer._update_model.call_count == 1
  assert not renderer._transform_dirty
  renderer.set_transform(renderer._car_space_transform.copy())
  renderer._render(renderer._clip_region)
  assert renderer._update_model.call_count == 1
  changed = renderer._car_space_transform.copy()
  changed[0, 0] += 1
  renderer.set_transform(changed)
  renderer._render(renderer._clip_region)
  assert renderer._update_model.call_count == 2
  for service in ("modelV2", "radarState"):
    sm.updated[service] = True
    renderer._render(renderer._clip_region)
    sm.updated[service] = False
  assert renderer._update_model.call_count == 4
  renderer._update_raw_points.assert_called_once_with(sm["modelV2"])
