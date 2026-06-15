from types import SimpleNamespace

import numpy as np

from openpilot.selfdrive.modeld.camera_offset import CameraOffset


def _camera_meta():
  fcam_intrinsics = np.array([
    [910.0, 0.0, 582.0],
    [0.0, 910.0, 437.0],
    [0.0, 0.0, 1.0],
  ], dtype=np.float32)
  ecam_intrinsics = np.array([
    [560.0, 0.0, 582.0],
    [0.0, 560.0, 437.0],
    [0.0, 0.0, 1.0],
  ], dtype=np.float32)
  return {
    ("mici", "os04c10"): SimpleNamespace(
      fcam=SimpleNamespace(intrinsics=fcam_intrinsics),
      ecam=SimpleNamespace(intrinsics=ecam_intrinsics),
    )
  }


def test_camera_offset_smoothing():
  camera_offset = CameraOffset()
  camera_offset.set_target(0.2)

  transform = np.eye(3, dtype=np.float32)
  camera_offset.update(transform, transform, "mici", "os04c10", 1.22, False, _camera_meta())
  np.testing.assert_almost_equal(camera_offset.offset, 0.02)

  camera_offset.update(transform, transform, "mici", "os04c10", 1.22, False, _camera_meta())
  np.testing.assert_almost_equal(camera_offset.offset, 0.038)


def test_camera_offset_apply():
  intrinsics = _camera_meta()[("mici", "os04c10")].fcam.intrinsics
  transform = np.eye(3, dtype=np.float32)
  height = 1.22
  offset = 0.1

  cy = intrinsics[1, 2]
  expected = np.eye(3, dtype=np.float32)
  expected[0, 1] = offset / height
  expected[0, 2] = -offset / height * cy

  result = CameraOffset.apply(transform, intrinsics, height, offset)
  np.testing.assert_array_almost_equal(result, expected)


def test_camera_offset_update_default_noop():
  camera_offset = CameraOffset()
  main_transform = np.eye(3, dtype=np.float32)
  extra_transform = np.eye(3, dtype=np.float32)

  main_out, extra_out = camera_offset.update(main_transform, extra_transform, "mici", "os04c10", 1.22, False, _camera_meta())

  np.testing.assert_array_equal(main_out, main_transform)
  np.testing.assert_array_equal(extra_out, extra_transform)


def test_camera_offset_update_changes_both_transforms():
  camera_offset = CameraOffset()
  camera_offset.set_target(0.2)
  main_transform = np.eye(3, dtype=np.float32)
  extra_transform = np.eye(3, dtype=np.float32)

  main_out, extra_out = camera_offset.update(main_transform, extra_transform, "mici", "os04c10", 1.22, False, _camera_meta())

  assert not np.array_equal(main_out, main_transform)
  assert not np.array_equal(extra_out, extra_transform)
  assert main_out[0, 1] != 0.0
  assert main_out[0, 2] != 0.0
