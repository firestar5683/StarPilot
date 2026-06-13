#!/usr/bin/env python3
import os
import time
import pickle
import numpy as np
from pathlib import Path
from tinygrad.tensor import Tensor
from tinygrad.helpers import Context
from tinygrad.device import Device
from tinygrad.engine.jit import TinyJit

from openpilot.system.camerad.cameras.nv12_info import get_nv12_info

MODELS_DIR = Path(__file__).parent / 'models'
WARP_COMPILE_ITERS = max(2, int(os.getenv("WARP_COMPILE_ITERS", "2")))

# Keep compile_warp standalone so it does not depend on common.transformations C extensions.
MEDMODEL_INPUT_SIZE = (512, 256)
DM_INPUT_SIZE = (1440, 960)

DEFAULT_CAMERA_CONFIGS = [
  (1928, 1208),  # tici / tizi
  (1344, 760),   # mici
]


def _parse_camera_configs_from_env() -> list[tuple[int, int]]:
  raw = os.getenv("SP_WARP_RESOLUTIONS", "").strip()
  if not raw:
    return DEFAULT_CAMERA_CONFIGS

  parsed: list[tuple[int, int]] = []
  for token in raw.replace(";", ",").split(","):
    token = token.strip().lower()
    if not token:
      continue
    try:
      w_str, h_str = token.split("x", 1)
      parsed.append((int(w_str), int(h_str)))
    except Exception as e:
      raise ValueError(f"Invalid SP_WARP_RESOLUTIONS token: {token!r}") from e

  # Keep first occurrence order, drop duplicates.
  deduped: list[tuple[int, int]] = []
  seen: set[tuple[int, int]] = set()
  for wh in parsed:
    if wh not in seen:
      seen.add(wh)
      deduped.append(wh)
  return deduped or DEFAULT_CAMERA_CONFIGS


CAMERA_CONFIGS = _parse_camera_configs_from_env()

UV_SCALE_MATRIX = np.array([[0.5, 0, 0], [0, 0.5, 0], [0, 0, 1]], dtype=np.float32)
UV_SCALE_MATRIX_INV = np.linalg.inv(UV_SCALE_MATRIX)

IMG_BUFFER_SHAPE = (30, MEDMODEL_INPUT_SIZE[1] // 2, MEDMODEL_INPUT_SIZE[0] // 2)


def warp_pkl_path(w, h):
  return MODELS_DIR / f'warp_{w}x{h}_tinygrad.pkl'


def dm_warp_pkl_path(w, h):
  return MODELS_DIR / f'dm_warp_{w}x{h}_tinygrad.pkl'


def warp_perspective_tinygrad(src_flat, M_inv, dst_shape, src_shape, stride_pad, border_fill_val=None):
  w_dst, h_dst = dst_shape
  h_src, w_src = src_shape

  x = Tensor.arange(w_dst).reshape(1, w_dst).expand(h_dst, w_dst).reshape(-1)
  y = Tensor.arange(h_dst).reshape(h_dst, 1).expand(h_dst, w_dst).reshape(-1)

  # inline 3x3 matmul as elementwise to avoid reduce op (enables fusion with gather)
  src_x = M_inv[0, 0] * x + M_inv[0, 1] * y + M_inv[0, 2]
  src_y = M_inv[1, 0] * x + M_inv[1, 1] * y + M_inv[1, 2]
  src_w = M_inv[2, 0] * x + M_inv[2, 1] * y + M_inv[2, 2]

  src_x = src_x / src_w
  src_y = src_y / src_w

  x_round = Tensor.round(src_x)
  y_round = Tensor.round(src_y)
  x_nn_clipped = x_round.clip(0, w_src - 1).cast('int')
  y_nn_clipped = y_round.clip(0, h_src - 1).cast('int')
  idx = y_nn_clipped * (w_src + stride_pad) + x_nn_clipped

  sampled = src_flat[idx]
  if border_fill_val is None:
    return sampled

  in_bounds = ((x_round >= 0) & (x_round <= w_src - 1) &
               (y_round >= 0) & (y_round <= h_src - 1)).cast(sampled.dtype)
  return sampled * in_bounds + Tensor(border_fill_val, dtype=sampled.dtype) * (1 - in_bounds)


def frames_to_tensor(frames, model_w, model_h):
  H = (frames.shape[0] * 2) // 3
  W = frames.shape[1]
  in_img1 = Tensor.cat(frames[0:H:2, 0::2],
                       frames[1:H:2, 0::2],
                       frames[0:H:2, 1::2],
                       frames[1:H:2, 1::2],
                       frames[H:H+H//4].reshape((H//2, W//2)),
                       frames[H+H//4:H+H//2].reshape((H//2, W//2)), dim=0).reshape((6, H//2, W//2))
  return in_img1


def make_frame_prepare(cam_w, cam_h, model_w, model_h):
  stride, y_height, uv_height, _ = get_nv12_info(cam_w, cam_h)
  uv_offset = stride * y_height
  stride_pad = stride - cam_w

  def frame_prepare_tinygrad(input_frame, M_inv):
    # UV_SCALE @ M_inv @ UV_SCALE_INV simplifies to elementwise scaling
    M_inv_uv = M_inv * Tensor([[1.0, 1.0, 0.5], [1.0, 1.0, 0.5], [2.0, 2.0, 1.0]])
    # deinterleave NV12 UV plane (UVUV... -> separate U, V)
    uv = input_frame[uv_offset:uv_offset + uv_height * stride].reshape(uv_height, stride)
    with Context(SPLIT_REDUCEOP=0):
      y = warp_perspective_tinygrad(input_frame[:cam_h*stride],
                                    M_inv, (model_w, model_h),
                                    (cam_h, cam_w), stride_pad).realize()
      u = warp_perspective_tinygrad(uv[:cam_h//2, :cam_w:2].flatten(),
                                    M_inv_uv, (model_w//2, model_h//2),
                                    (cam_h//2, cam_w//2), 0).realize()
      v = warp_perspective_tinygrad(uv[:cam_h//2, 1:cam_w:2].flatten(),
                                    M_inv_uv, (model_w//2, model_h//2),
                                    (cam_h//2, cam_w//2), 0).realize()
    yuv = y.cat(u).cat(v).reshape((model_h * 3 // 2, model_w))
    tensor = frames_to_tensor(yuv, model_w, model_h)
    return tensor
  return frame_prepare_tinygrad


def make_update_img_input(frame_prepare, model_w, model_h):
  def update_img_input_tinygrad(tensor, frame, M_inv):
    M_inv = M_inv.to(Device.DEFAULT)
    new_img = frame_prepare(frame, M_inv)
    full_buffer = tensor[6:].cat(new_img, dim=0).contiguous()
    return full_buffer, Tensor.cat(full_buffer[:6], full_buffer[-6:], dim=0).contiguous().reshape(1, 12, model_h//2, model_w//2)
  return update_img_input_tinygrad


def make_update_both_imgs(frame_prepare, model_w, model_h):
  update_img = make_update_img_input(frame_prepare, model_w, model_h)

  def update_both_imgs_tinygrad(calib_img_buffer, new_img, M_inv,
                                calib_big_img_buffer, new_big_img, M_inv_big):
    calib_img_buffer, calib_img_pair = update_img(calib_img_buffer, new_img, M_inv)
    calib_big_img_buffer, calib_big_img_pair = update_img(calib_big_img_buffer, new_big_img, M_inv_big)
    return calib_img_buffer, calib_img_pair, calib_big_img_buffer, calib_big_img_pair
  return update_both_imgs_tinygrad


def make_warp_dm(cam_w, cam_h, dm_w, dm_h):
  stride, y_height, _, _ = get_nv12_info(cam_w, cam_h)
  stride_pad = stride - cam_w

  def warp_dm(input_frame, M_inv):
    M_inv = M_inv.to(Device.DEFAULT)
    result = warp_perspective_tinygrad(
      input_frame[:cam_h*stride], M_inv, (dm_w, dm_h), (cam_h, cam_w), stride_pad, border_fill_val=16
    ).reshape(-1, dm_h * dm_w)
    return result
  return warp_dm


def compile_modeld_warp(cam_w, cam_h):
  model_w, model_h = MEDMODEL_INPUT_SIZE
  _, _, _, yuv_size = get_nv12_info(cam_w, cam_h)

  print(f"Compiling modeld warp for {cam_w}x{cam_h} ({WARP_COMPILE_ITERS} iters)...", flush=True)

  frame_prepare = make_frame_prepare(cam_w, cam_h, model_w, model_h)
  update_both_imgs = make_update_both_imgs(frame_prepare, model_w, model_h)
  update_img_jit = TinyJit(update_both_imgs, prune=True)

  full_buffer = Tensor.zeros(IMG_BUFFER_SHAPE, dtype='uint8').contiguous().realize()
  big_full_buffer = Tensor.zeros(IMG_BUFFER_SHAPE, dtype='uint8').contiguous().realize()
  full_buffer_np = np.zeros(IMG_BUFFER_SHAPE, dtype=np.uint8)
  big_full_buffer_np = np.zeros(IMG_BUFFER_SHAPE, dtype=np.uint8)

  for i in range(WARP_COMPILE_ITERS):
    new_frame_np = (32 * np.random.randn(yuv_size).astype(np.float32) + 128).clip(0, 255).astype(np.uint8)
    img_inputs = [full_buffer,
                  Tensor.from_blob(new_frame_np.ctypes.data, (yuv_size,), dtype='uint8').realize(),
                  Tensor(Tensor.randn(3, 3).mul(8).realize().numpy(), device='NPY')]
    new_big_frame_np = (32 * np.random.randn(yuv_size).astype(np.float32) + 128).clip(0, 255).astype(np.uint8)
    big_img_inputs = [big_full_buffer,
                      Tensor.from_blob(new_big_frame_np.ctypes.data, (yuv_size,), dtype='uint8').realize(),
                      Tensor(Tensor.randn(3, 3).mul(8).realize().numpy(), device='NPY')]
    inputs = img_inputs + big_img_inputs
    Device.default.synchronize()

    inputs_np = [x.numpy() for x in inputs]
    inputs_np[0] = full_buffer_np
    inputs_np[3] = big_full_buffer_np

    st = time.perf_counter()
    out = update_img_jit(*inputs)
    full_buffer = out[0].contiguous().realize().clone()
    big_full_buffer = out[2].contiguous().realize().clone()
    mt = time.perf_counter()
    Device.default.synchronize()
    et = time.perf_counter()
    print(f"  [{i+1}/{WARP_COMPILE_ITERS}] enqueue {(mt-st)*1e3:6.2f} ms -- total {(et-st)*1e3:6.2f} ms", flush=True)

  pkl_path = warp_pkl_path(cam_w, cam_h)
  with open(pkl_path, "wb") as f:
    pickle.dump(update_img_jit, f)
  print(f"  Saved to {pkl_path}", flush=True)

  jit = pickle.load(open(pkl_path, "rb"))
  jit(*inputs)


def compile_dm_warp(cam_w, cam_h):
  dm_w, dm_h = DM_INPUT_SIZE
  _, _, _, yuv_size = get_nv12_info(cam_w, cam_h)

  print(f"Compiling DM warp for {cam_w}x{cam_h} ({WARP_COMPILE_ITERS} iters)...", flush=True)

  warp_dm = make_warp_dm(cam_w, cam_h, dm_w, dm_h)
  warp_dm_jit = TinyJit(warp_dm, prune=True)

  for i in range(WARP_COMPILE_ITERS):
    inputs = [Tensor.from_blob((32 * Tensor.randn(yuv_size,) + 128).cast(dtype='uint8').realize().numpy().ctypes.data, (yuv_size,), dtype='uint8'),
              Tensor(Tensor.randn(3, 3).mul(8).realize().numpy(), device='NPY')]
    Device.default.synchronize()
    st = time.perf_counter()
    warp_dm_jit(*inputs)
    mt = time.perf_counter()
    Device.default.synchronize()
    et = time.perf_counter()
    print(f"  [{i+1}/{WARP_COMPILE_ITERS}] enqueue {(mt-st)*1e3:6.2f} ms -- total {(et-st)*1e3:6.2f} ms", flush=True)

  pkl_path = dm_warp_pkl_path(cam_w, cam_h)
  with open(pkl_path, "wb") as f:
    pickle.dump(warp_dm_jit, f)
  print(f"  Saved to {pkl_path}", flush=True)


def run_and_save_pickle():
  for cam_w, cam_h in CAMERA_CONFIGS:
    compile_modeld_warp(cam_w, cam_h)
    compile_dm_warp(cam_w, cam_h)


if __name__ == "__main__":
  run_and_save_pickle()
