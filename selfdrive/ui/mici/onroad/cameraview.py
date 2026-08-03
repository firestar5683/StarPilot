"""Mici CameraView using upstream's engaged color treatment."""

from openpilot.selfdrive.ui.onroad.cameraview import CameraView as SharedCameraView


class CameraView(SharedCameraView):
  _use_upstream_engaged_color = True


__all__ = ["CameraView"]
