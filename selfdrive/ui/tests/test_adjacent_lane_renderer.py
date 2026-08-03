from types import SimpleNamespace

import numpy as np
import pytest

import openpilot.selfdrive.ui.onroad.model_renderer as model_renderer


class _FakeSubMaster:
  def __init__(self, plan):
    self.recv_frame = {"starpilotPlan": 1}
    self._plan = plan

  def __getitem__(self, key):
    assert key == "starpilotPlan"
    return self._plan


@pytest.mark.parametrize(
  ("lane_width_left", "lane_width_right", "expected_side"),
  [
    (3.5, 0.0, 0),
    (0.0, 3.5, 1),
  ],
)
def test_adjacent_path_keeps_a_single_valid_side(monkeypatch, lane_width_left, lane_width_right, expected_side):
  fake_ui_state = SimpleNamespace(
    sm=_FakeSubMaster(SimpleNamespace(laneWidthLeft=lane_width_left, laneWidthRight=lane_width_right)),
    started_frame=0,
  )
  monkeypatch.setattr(model_renderer, "ui_state", fake_ui_state)

  renderer = object.__new__(model_renderer.ModelRenderer)
  left_outer = np.ones((2, 3), dtype=np.float32)
  left_inner = np.ones((2, 3), dtype=np.float32)
  right_inner = np.ones((2, 3), dtype=np.float32)
  right_outer = np.ones((2, 3), dtype=np.float32)
  renderer._lane_lines = [
    SimpleNamespace(raw_points=left_outer),
    SimpleNamespace(raw_points=left_inner),
    SimpleNamespace(raw_points=right_inner),
    SimpleNamespace(raw_points=right_outer),
  ]
  renderer._adjacent_path_vertices = [
    np.ones((4, 2), dtype=np.float32),
    np.ones((4, 2), dtype=np.float32),
  ]

  def fake_get_adjacent_path_polygon(line1, *_args):
    side = 0 if line1 is left_outer else 1
    return np.array([[side, 0], [side, 1], [side + 0.5, 1], [side + 0.5, 0]], dtype=np.float32)

  monkeypatch.setattr(renderer, "_get_adjacent_path_polygon", fake_get_adjacent_path_polygon)

  renderer._update_adjacent_paths(max_idx=1, max_distance=10.0)

  assert renderer._adjacent_path_vertices[expected_side].size >= 4
  assert renderer._adjacent_path_vertices[1 - expected_side].size == 0
