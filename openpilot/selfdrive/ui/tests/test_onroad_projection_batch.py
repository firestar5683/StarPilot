"""The on-road lane batch keeps line clipping and path projection separate."""

from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np

from openpilot.selfdrive.ui.onroad.model_renderer import ModelPoints, ModelRenderer


class CountedTransform:
  def __init__(self):
    self.calls = 0

  def __matmul__(self, points):
    self.calls += 1
    return np.eye(3, dtype=np.float32) @ points


def renderer():
  view = object.__new__(ModelRenderer)
  view._car_space_transform = CountedTransform()
  view._clip_region = SimpleNamespace(x=0, y=0, width=30, height=30)
  return view


def test_six_line_batch_clips_each_polygon_with_one_transform():
  view = renderer()
  lines = [
    np.array([[10, 10, 1], [20, 10, 1], [40, 10, 1]], dtype=np.float32),
    np.empty((0, 3), dtype=np.float32),
    np.array([[10, 50, 1], [20, 5, 1], [40, 5, 1]], dtype=np.float32),
    np.array([[10, 10, 0], [20, 10, 0], [40, 10, 0]], dtype=np.float32),
    np.array([[-10, 10, 1], [-5, 10, 1], [0, 10, 1]], dtype=np.float32),
    np.array([[10, 29, 1], [20, 29, 1], [40, 29, 1]], dtype=np.float32),
  ]
  with np.errstate(divide='raise', invalid='raise'):
    polygons = view._map_lines_to_polygons(lines, [2] * 6, 0.0, 1, 35.0)
  assert view._car_space_transform.calls == 1
  np.testing.assert_array_equal(polygons[0], [[10, 8], [20, 8], [20, 12], [10, 12]])
  np.testing.assert_array_equal(polygons[2], [[20, 3], [20, 7]])
  assert all(polygon.shape == (0, 2) for polygon in (polygons[1], polygons[3], polygons[4], polygons[5]))


def test_model_update_batches_lanes_and_edges_but_keeps_path_separate():
  view = renderer()
  points = np.array([[10, 10, 1], [20, 10, 1], [30, 10, 1]], dtype=np.float32)
  view._path = ModelPoints(raw_points=points.copy())
  view._lane_lines = [ModelPoints(raw_points=points.copy()) for _ in range(4)]
  view._road_edges = [ModelPoints(raw_points=points.copy()) for _ in range(2)]
  view._lane_line_probs = np.ones(4, dtype=np.float32)
  view._path_offset_z = 0.0
  view._update_experimental_gradient = Mock()

  view._update_model(None, points[:, 0])

  assert view._car_space_transform.calls == 2  # one lane/edge batch, one path
  assert all(line.projected_points.size for line in [*view._lane_lines, *view._road_edges])
  assert view._path.projected_points.size
  view._update_experimental_gradient.assert_called_once_with()
