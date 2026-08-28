import numpy as np
import os

from msgq.visionipc import VisionIpcServer, VisionStreamType
from cereal import messaging

from openpilot.common.basedir import BASEDIR
from openpilot.tools.sim.lib.common import W, H

class Camerad:
  """Simulates the camerad daemon"""
  def __init__(self, dual_camera):
    self.pm = messaging.PubMaster(['roadCameraState', 'wideRoadCameraState'])

    self.frame_road_id = 0
    self.frame_wide_id = 0
    self.vipc_server = VisionIpcServer("camerad")

    self.vipc_server.create_buffers(VisionStreamType.VISION_STREAM_ROAD, 5, W, H)
    if dual_camera:
      self.vipc_server.create_buffers(VisionStreamType.VISION_STREAM_WIDE_ROAD, 5, W, H)

    self.vipc_server.start_listener()

    # GPU-accelerated rgb->nv12 via pyopencl when an OpenCL platform exists,
    # otherwise fall back to a CPU numpy conversion (e.g. laptops without an
    # OpenCL ICD, such as NVIDIA-only hosts).
    self.ctx = None
    try:
      import pyopencl as cl
      import pyopencl.array as cl_array
      self._cl_array = cl_array
      self.ctx = cl.create_some_context()
      self.queue = cl.CommandQueue(self.ctx)
      cl_arg = f" -DHEIGHT={H} -DWIDTH={W} -DRGB_STRIDE={W * 3} -DUV_WIDTH={W // 2} -DUV_HEIGHT={H // 2} -DRGB_SIZE={W * H} -DCL_DEBUG "
      kernel_fn = os.path.join(BASEDIR, "tools/sim/rgb_to_nv12.cl")
      with open(kernel_fn) as f:
        prg = cl.Program(self.ctx, f.read()).build(cl_arg)
        self.krnl = prg.rgb_to_nv12
      self.Wdiv4 = W // 4 if (W % 4 == 0) else (W + (4 - W % 4)) // 4
      self.Hdiv4 = H // 4 if (H % 4 == 0) else (H + (4 - H % 4)) // 4
    except Exception:
      self.ctx = None

  def cam_send_yuv_road(self, yuv):
    self._send_yuv(yuv, self.frame_road_id, 'roadCameraState', VisionStreamType.VISION_STREAM_ROAD)
    self.frame_road_id += 1

  def cam_send_yuv_wide_road(self, yuv):
    self._send_yuv(yuv, self.frame_wide_id, 'wideRoadCameraState', VisionStreamType.VISION_STREAM_WIDE_ROAD)
    self.frame_wide_id += 1

  # Returns: yuv bytes
  def rgb_to_yuv(self, rgb):
    assert rgb.shape == (H, W, 3), f"{rgb.shape}"
    assert rgb.dtype == np.uint8

    if self.ctx is not None:
      rgb_cl = self._cl_array.to_device(self.queue, rgb)
      yuv_cl = self._cl_array.empty_like(rgb_cl)
      self.krnl(self.queue, (self.Wdiv4, self.Hdiv4), None, rgb_cl.data, yuv_cl.data).wait()
      yuv = np.resize(yuv_cl.get(), rgb.size // 2)
      return yuv.data.tobytes()
    return self.rgb_to_yuv_cpu(rgb).tobytes()

  @staticmethod
  def rgb_to_yuv_cpu(rgb):
    """Numpy NV12 conversion mirroring tools/sim/rgb_to_nv12.cl (BT.601 limited)."""
    r = rgb[:, :, 0].astype(np.int32)
    g = rgb[:, :, 1].astype(np.int32)
    b = rgb[:, :, 2].astype(np.int32)

    y = ((b * 13 + g * 65 + r * 33 + 64) >> 7) + 16
    y = np.clip(y, 0, 255).astype(np.uint8)

    def avg2(ch):
      return (ch[0::2, 0::2] + ch[0::2, 1::2] + ch[1::2, 0::2] + ch[1::2, 1::2] + 1) >> 1

    r2, g2, b2 = avg2(r), avg2(g), avg2(b)
    u = ((b2 * 56 - g2 * 37 - r2 * 19 + 0x8080) >> 8) & 0xFF
    v = ((r2 * 56 - g2 * 47 - b2 * 9 + 0x8080) >> 8) & 0xFF

    uv = np.empty((H // 2, W), dtype=np.uint8)
    uv[:, 0::2] = u.astype(np.uint8)
    uv[:, 1::2] = v.astype(np.uint8)
    return np.concatenate([y.ravel(), uv.ravel()]).astype(np.uint8)

  def _send_yuv(self, yuv, frame_id, pub_type, yuv_type):
    eof = int(frame_id * 0.05 * 1e9)
    self.vipc_server.send(yuv_type, yuv, frame_id, eof, eof)

    dat = messaging.new_message(pub_type, valid=True)
    msg = {
      "frameId": frame_id,
      "transform": [1.0, 0.0, 0.0,
                    0.0, 1.0, 0.0,
                    0.0, 0.0, 1.0]
    }
    setattr(dat, pub_type, msg)
    self.pm.send(pub_type, dat)
