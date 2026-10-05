"""Current-frame NV12 warp supplied to Jetlink's build API."""

CAMERA_SIZES = ((1928, 1208), (1344, 760))
MODEL_SIZES = ((512, 256), (1024, 512))


def make_warp(cam_w, cam_h, model_w, model_h):
  from examples.openpilot.compile_warp import NV12Frame, make_frame_prepare
  from tinygrad import Tensor
  from openpilot.system.camerad.cameras.nv12_info import get_nv12_info

  if (cam_w, cam_h) not in CAMERA_SIZES or (model_w, model_h) not in MODEL_SIZES:
    raise ValueError("unsupported Jetlink warp geometry")
  layout = get_nv12_info(cam_w, cam_h)
  prepare = make_frame_prepare(NV12Frame(cam_w, cam_h, *layout), model_w, model_h)

  def warp(tfm, big_tfm, frame, big_frame):
    return Tensor.stack(prepare(frame, tfm), prepare(big_frame, big_tfm))
  return warp, layout[3]


def adapter():
  from types import SimpleNamespace
  return SimpleNamespace(make_warp=make_warp)
