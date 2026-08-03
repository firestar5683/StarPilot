import math

import numpy as np
import pytest

from openpilot.selfdrive.ui.onroad.radar_tracks import project_radar_points


def _scalar_reference(d_rel, in_y, path_x, path_z, transform, path_offset_z, clip_bounds, rect_bounds):
  clip_x, clip_y, clip_xmax, clip_ymax = clip_bounds
  rect_x, rect_y, rect_xmax, rect_ymax = rect_bounds
  result = []

  for d, y in zip(d_rel, in_y, strict=True):
    d = float(d)
    y = float(y)
    if not math.isfinite(d) or not math.isfinite(y):
      continue

    idx = np.searchsorted(path_x, d, side="right") - 1
    idx = int(idx) if idx >= 0 else 0
    z = float(path_z[idx]) if idx < len(path_z) else 0.0
    in_z = z + float(path_offset_z)

    point_w = (
      float(transform[2, 0]) * d
      + float(transform[2, 1]) * y
      + float(transform[2, 2]) * in_z
    )
    if abs(point_w) < 1e-6:
      continue

    x = (
      float(transform[0, 0]) * d
      + float(transform[0, 1]) * y
      + float(transform[0, 2]) * in_z
    ) / point_w
    screen_y = (
      float(transform[1, 0]) * d
      + float(transform[1, 1]) * y
      + float(transform[1, 2]) * in_z
    ) / point_w

    if not (clip_x <= x <= clip_xmax and clip_y <= screen_y <= clip_ymax):
      continue

    result.append((
      max(rect_x, min(x, rect_xmax)),
      max(rect_y, min(screen_y, rect_ymax)),
    ))

  return np.asarray(result, dtype=np.float64).reshape(-1, 2)


def _projection_inputs(count=65):
  d_rel = np.asarray([4.0 + i * 2.4 for i in range(count)], dtype=np.float64)
  in_y = np.asarray([((i % 9) - 4) * 0.45 for i in range(count)], dtype=np.float64)
  path_x = np.linspace(0.0, 192.0, 33, dtype=np.float32)
  path_z = (0.15 * np.sin(path_x / 30.0)).astype(np.float32)
  transform = np.asarray([
    [18.0, 0.25, 960.0],
    [0.1, -16.0, 820.0],
    [0.045, 0.001, 1.0],
  ], dtype=np.float32)
  clip_bounds = (-500.0, -500.0, 2420.0, 1580.0)
  rect_bounds = (0.0, 0.0, 1920.0, 1080.0)
  return d_rel, in_y, path_x, path_z, transform, clip_bounds, rect_bounds


@pytest.mark.parametrize("count", [0, 1, 10, 20, 65])
def test_vectorized_projection_matches_scalar_reference(count):
  d_rel, in_y, path_x, path_z, transform, clip_bounds, rect_bounds = _projection_inputs(count)
  expected = _scalar_reference(d_rel, in_y, path_x, path_z, transform, 1.22, clip_bounds, rect_bounds)

  actual = project_radar_points(
    d_rel, in_y, path_x, path_z, transform, 1.22, clip_bounds, rect_bounds,
  )

  assert actual.shape == expected.shape
  np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-10)


def test_vectorized_projection_preserves_order_duplicates_and_invalid_values():
  _, _, path_x, path_z, transform, clip_bounds, rect_bounds = _projection_inputs(0)
  d_rel = np.asarray([20.0, np.nan, 8.0, 20.0, np.inf, 12.0], dtype=np.float64)
  in_y = np.asarray([1.0, 2.0, -1.0, 1.0, 3.0, -2.0], dtype=np.float64)

  expected = _scalar_reference(d_rel, in_y, path_x, path_z, transform, 1.22, clip_bounds, rect_bounds)
  actual = project_radar_points(
    d_rel, in_y, path_x, path_z, transform, 1.22, clip_bounds, rect_bounds,
  )

  np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-10)
  assert actual.shape[0] == 4
  np.testing.assert_allclose(actual[0], actual[2], rtol=0.0, atol=1e-10)


def test_vectorized_projection_clips_and_clamps_like_scalar_reference():
  d_rel, in_y, path_x, path_z, transform, _, _ = _projection_inputs(3)
  clip_bounds = (0.0, 0.0, 1000.0, 1000.0)
  rect_bounds = (100.0, 200.0, 900.0, 800.0)

  expected = _scalar_reference(d_rel, in_y, path_x, path_z, transform, 1.22, clip_bounds, rect_bounds)
  actual = project_radar_points(
    d_rel, in_y, path_x, path_z, transform, 1.22, clip_bounds, rect_bounds,
  )

  np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-10)
  assert np.all(actual[:, 0] >= rect_bounds[0])
  assert np.all(actual[:, 0] <= rect_bounds[2])
  assert np.all(actual[:, 1] >= rect_bounds[1])
  assert np.all(actual[:, 1] <= rect_bounds[3])


def test_vectorized_projection_handles_path_edges_and_points_beyond_path():
  d_rel = np.asarray([-5.0, 0.0, 5.0, 25.0], dtype=np.float64)
  in_y = np.asarray([0.0, 0.0, 0.0, 0.0], dtype=np.float64)
  path_x = np.asarray([0.0, 10.0], dtype=np.float32)
  path_z = np.asarray([1.0, 2.0], dtype=np.float32)
  transform = np.eye(3, dtype=np.float32)
  clip_bounds = (-100.0, -100.0, 100.0, 100.0)
  rect_bounds = (-10.0, -10.0, 10.0, 10.0)

  expected = _scalar_reference(d_rel, in_y, path_x, path_z, transform, 1.0, clip_bounds, rect_bounds)
  actual = project_radar_points(
    d_rel, in_y, path_x, path_z, transform, 1.0, clip_bounds, rect_bounds,
  )

  np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-10)


def test_vectorized_projection_rejects_focal_plane_points():
  d_rel = np.asarray([1.0, 2.0], dtype=np.float64)
  in_y = np.asarray([0.0, 0.0], dtype=np.float64)
  path_x = np.asarray([0.0, 10.0], dtype=np.float32)
  path_z = np.zeros(2, dtype=np.float32)
  transform = np.eye(3, dtype=np.float32)
  bounds = (-100.0, -100.0, 100.0, 100.0)

  actual = project_radar_points(d_rel, in_y, path_x, path_z, transform, 0.0, bounds, bounds)

  assert actual.shape == (0, 2)
