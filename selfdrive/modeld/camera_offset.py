from __future__ import annotations

import numpy as np


DEFAULT_CAMERA_HEIGHT = 1.22
CAMERA_OFFSET_SMOOTHING = 0.1


def _device_cameras():
  from openpilot.common.transformations.camera import DEVICE_CAMERAS

  return DEVICE_CAMERAS


class CameraOffset:
  def __init__(self) -> None:
    self.target_offset = 0.0
    self.offset = 0.0

  @staticmethod
  def apply(model_transform: np.ndarray, intrinsics: np.ndarray, camera_height: float, offset: float) -> np.ndarray:
    height = camera_height if camera_height > 0.0 else DEFAULT_CAMERA_HEIGHT
    cy = intrinsics[1, 2]
    shear = np.eye(3, dtype=np.float32)
    shear[0, 1] = offset / height
    shear[0, 2] = -offset / height * cy
    return (shear @ model_transform).astype(np.float32)

  def set_target(self, offset: float) -> None:
    self.target_offset = float(offset)

  def update(
    self,
    model_transform_main: np.ndarray,
    model_transform_extra: np.ndarray,
    device_type: str,
    camera_sensor: str,
    camera_height: float,
    main_wide_camera: bool,
    device_cameras: dict | None = None,
  ) -> tuple[np.ndarray, np.ndarray]:
    self.offset += (self.target_offset - self.offset) * CAMERA_OFFSET_SMOOTHING

    dc = (device_cameras or _device_cameras())[(device_type, camera_sensor)]
    main_intrinsics = dc.ecam.intrinsics if main_wide_camera else dc.fcam.intrinsics

    return (
      self.apply(model_transform_main, main_intrinsics, camera_height, self.offset),
      self.apply(model_transform_extra, dc.ecam.intrinsics, camera_height, self.offset),
    )
