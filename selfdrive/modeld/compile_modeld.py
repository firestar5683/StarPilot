#!/usr/bin/env python3
import argparse
import atexit
import math
import os
import pickle
import shutil
import tempfile
import time
from collections import namedtuple
from functools import partial

import numpy as np


def _patch_tinygrad_fetch_fw():
  import hashlib
  import pathlib

  try:
    import zstandard
  except ImportError:
    return
  from tinygrad import helpers

  original_fetch_fw = getattr(helpers, "fetch_fw", None)
  if original_fetch_fw is None:
    return

  def fetch_fw(path, name, sha256):
    firmware_path = pathlib.Path(f"/lib/firmware/{path}/{name}.zst")
    if firmware_path.is_file():
      blob = zstandard.ZstdDecompressor().stream_reader(firmware_path.read_bytes()).read()
      if hashlib.sha256(blob).hexdigest() == sha256:
        return blob
    return original_fetch_fw(path, name, sha256)

  helpers.fetch_fw = fetch_fw


_patch_tinygrad_fetch_fw()

from tinygrad.device import Device
from tinygrad.engine.jit import TinyJit
from tinygrad.helpers import Context
from tinygrad.tensor import Tensor
from openpilot.selfdrive.modeld.helpers import dump_oob
from openpilot.selfdrive.modeld.usbgpu_link import wait_usbgpu_link


ARTIFACT_FORMAT_VERSION = 1
MODEL_TYPES = ("vision_policy", "vision_multi_policy", "supercombo")
NV12Frame = namedtuple("NV12Frame", ["width", "height", "stride", "y_height", "uv_height", "size"])
IMAGE_HISTORY_IN_WARP = "warp"
IMAGE_HISTORY_IN_POLICY = "policy"
IMAGE_HISTORY_PIPELINES = (IMAGE_HISTORY_IN_WARP, IMAGE_HISTORY_IN_POLICY)
LEGACY_WARP_INPUTS = ("img_q", "big_img_q", "tfm", "big_tfm")
FAST_WARP_INPUTS = ("tfm", "big_tfm")
BASE_POLICY_INPUTS = ("feat_q", "desire_q", "packed_npy_inputs")
FAST_POLICY_INPUTS = ("img_q", "big_img_q", *BASE_POLICY_INPUTS)
WARP_INPUTS = LEGACY_WARP_INPUTS
SPLIT_POLICY_INPUTS = BASE_POLICY_INPUTS
SUPERCOMBO_POLICY_INPUTS = BASE_POLICY_INPUTS
WARP_DEV = os.getenv("WARP_DEV")
OOB_PICKLE = False


def _detect_desire_key(input_shapes):
  return next((key for key in input_shapes if key.startswith("desire")), None)


def _detect_vision_keys(input_shapes):
  image_keys = sorted(key for key in input_shapes if "img" in key)
  road_key = next((key for key in image_keys if "big" not in key), None)
  wide_key = next((key for key in image_keys if "big" in key), None)
  if road_key is None or wide_key is None:
    raise ValueError(f"Cannot determine road/wide image keys from {list(input_shapes)}")
  return road_key, wide_key


def derive_frame_skip(input_shapes):
  features_shape = input_shapes.get("features_buffer")
  if features_shape is None:
    return 1
  return 1 if features_shape[1] >= 99 else 4


def make_random_images(keys, shape, device=None):
  return {key: Tensor.randint(shape, low=0, high=256, dtype="uint8", device=device).realize() for key in keys}


def make_random_blob_images(keys, size, device=None):
  keepalive: list[np.ndarray] = []

  def make_inputs():
    nonlocal keepalive
    keepalive = []
    tensors = {}
    for key in keys:
      frame = (32 * np.random.randn(size).astype(np.float32) + 128).clip(0, 255).astype(np.uint8)
      keepalive.append(frame)
      # Copy host bytes onto the target device instead of wrapping the host
      # pointer as a device buffer. Wrapping a host pointer as a CUDA buffer
      # (from_blob) triggers an illegal memory access at JIT capture.
      tensors[key] = Tensor(frame, device=device).realize()
    return tensors

  return make_inputs


def warp_perspective_tinygrad(src_flat, matrix_inverse, dst_shape, src_shape, stride_pad, border_fill_val=None):
  width_dst, height_dst = dst_shape
  height_src, width_src = src_shape

  x = Tensor.arange(width_dst).reshape(1, width_dst).expand(height_dst, width_dst).reshape(-1)
  y = Tensor.arange(height_dst).reshape(height_dst, 1).expand(height_dst, width_dst).reshape(-1)

  src_x = matrix_inverse[0, 0] * x + matrix_inverse[0, 1] * y + matrix_inverse[0, 2]
  src_y = matrix_inverse[1, 0] * x + matrix_inverse[1, 1] * y + matrix_inverse[1, 2]
  src_w = matrix_inverse[2, 0] * x + matrix_inverse[2, 1] * y + matrix_inverse[2, 2]
  src_x = src_x / src_w
  src_y = src_y / src_w

  x_round = Tensor.round(src_x)
  y_round = Tensor.round(src_y)
  x_nn_clipped = x_round.clip(0, width_src - 1).cast("int")
  y_nn_clipped = y_round.clip(0, height_src - 1).cast("int")
  sampled = src_flat[y_nn_clipped * (width_src + stride_pad) + x_nn_clipped]

  if border_fill_val is None:
    return sampled

  in_bounds = ((x_round >= 0) & (x_round <= width_src - 1) &
               (y_round >= 0) & (y_round <= height_src - 1)).cast(sampled.dtype)
  return sampled * in_bounds + Tensor(border_fill_val, dtype=sampled.dtype) * (1 - in_bounds)


def frames_to_tensor(frames):
  height = (frames.shape[0] * 2) // 3
  width = frames.shape[1]
  return Tensor.cat(
    frames[0:height:2, 0::2],
    frames[1:height:2, 0::2],
    frames[0:height:2, 1::2],
    frames[1:height:2, 1::2],
    frames[height:height + height // 4].reshape((height // 2, width // 2)),
    frames[height + height // 4:height + height // 2].reshape((height // 2, width // 2)),
    dim=0,
  ).reshape((6, height // 2, width // 2))


def make_frame_prepare(nv12: NV12Frame, model_w, model_h):
  cam_w, cam_h, stride, y_height, uv_height, _ = nv12
  uv_offset = stride * y_height
  stride_pad = stride - cam_w

  def frame_prepare(input_frame, matrix_inverse):
    matrix_inverse_uv = matrix_inverse * Tensor(
      [[1.0, 1.0, 0.5], [1.0, 1.0, 0.5], [2.0, 2.0, 1.0]],
      device=WARP_DEV,
    )
    uv = input_frame[uv_offset:uv_offset + uv_height * stride].reshape(uv_height, stride)
    with Context(SPLIT_REDUCEOP=0):
      y = warp_perspective_tinygrad(
        input_frame[:cam_h * stride], matrix_inverse, (model_w, model_h), (cam_h, cam_w), stride_pad,
      ).realize()
      u = warp_perspective_tinygrad(
        uv[:cam_h // 2, :cam_w:2].flatten(), matrix_inverse_uv,
        (model_w // 2, model_h // 2), (cam_h // 2, cam_w // 2), 0,
      ).realize()
      v = warp_perspective_tinygrad(
        uv[:cam_h // 2, 1:cam_w:2].flatten(), matrix_inverse_uv,
        (model_w // 2, model_h // 2), (cam_h // 2, cam_w // 2), 0,
      ).realize()
    return frames_to_tensor(y.cat(u).cat(v).reshape((model_h * 3 // 2, model_w)))

  return frame_prepare


def make_warp_input_queues(vision_input_shapes, frame_skip, device):
  road_key, _ = _detect_vision_keys(vision_input_shapes)
  image_shape = vision_input_shapes[road_key]
  frame_count = image_shape[1] // 6
  image_buffer_shape = (frame_skip * (frame_count - 1) + 1, 6, image_shape[2], image_shape[3])

  npy = {
    "tfm": np.zeros((3, 3), dtype=np.float32),
    "big_tfm": np.zeros((3, 3), dtype=np.float32),
  }
  queues = {
    "img_q": Tensor(np.zeros(image_buffer_shape, dtype=np.uint8), device=device).contiguous().realize(),
    "big_img_q": Tensor(np.zeros(image_buffer_shape, dtype=np.uint8), device=device).contiguous().realize(),
    **{key: Tensor(value, device="NPY").realize() for key, value in npy.items()},
  }
  return queues, npy


def _packed_policy_shapes(input_shapes, include_prev_feature=False):
  desire_key = _detect_desire_key(input_shapes)
  if desire_key is None:
    raise ValueError(f"No desire input found in {list(input_shapes)}")

  shapes = {"desire": (input_shapes[desire_key][2],)}
  for key, shape in input_shapes.items():
    if key in ("features_buffer", desire_key) or "img" in key:
      continue
    shapes[key] = tuple(shape)
  if include_prev_feature:
    features_shape = input_shapes["features_buffer"]
    shapes["prev_feat"] = (features_shape[0], math.prod(features_shape[2:]))
  return shapes, [math.prod(shape) for shape in shapes.values()]


def make_split_input_queues(vision_input_shapes, policy_input_shapes, frame_skip, device):
  queues, npy = make_warp_input_queues(vision_input_shapes, frame_skip, device)
  features_shape = policy_input_shapes["features_buffer"]
  feature_dim = math.prod(features_shape[2:])
  desire_key = _detect_desire_key(policy_input_shapes)
  desire_shape = policy_input_shapes[desire_key]
  packed_shapes, packed_sizes = _packed_policy_shapes(policy_input_shapes)

  packed_inputs = np.zeros(sum(packed_sizes), dtype=np.float32)
  npy.update({
    key: value.reshape(shape)
    for (key, shape), value in zip(
      packed_shapes.items(), np.split(packed_inputs, np.cumsum(packed_sizes[:-1])), strict=True,
    )
  })
  queues.update({
    "feat_q": Tensor(
      np.zeros((frame_skip * (features_shape[1] - 1) + 1, features_shape[0], feature_dim), dtype=np.float32),
      device=device,
    ).contiguous().realize(),
    "desire_q": Tensor(
      np.zeros((frame_skip * desire_shape[1], desire_shape[0], desire_shape[2]), dtype=np.float32),
      device=device,
    ).contiguous().realize(),
    "packed_npy_inputs": Tensor(packed_inputs, device="NPY").realize(),
  })
  return queues, npy


def make_supercombo_input_queues(input_shapes, frame_skip, device):
  queues, npy = make_warp_input_queues(input_shapes, frame_skip, device)
  features_shape = input_shapes["features_buffer"]
  feature_dim = math.prod(features_shape[2:])
  desire_key = _detect_desire_key(input_shapes)
  desire_shape = input_shapes[desire_key]
  packed_shapes, packed_sizes = _packed_policy_shapes(input_shapes, include_prev_feature=True)

  packed_inputs = np.zeros(sum(packed_sizes), dtype=np.float32)
  npy.update({
    key: value.reshape(shape)
    for (key, shape), value in zip(
      packed_shapes.items(), np.split(packed_inputs, np.cumsum(packed_sizes[:-1])), strict=True,
    )
  })
  queues.update({
    "feat_q": Tensor(
      np.zeros((frame_skip * features_shape[1], features_shape[0], feature_dim), dtype=np.float32),
      device=device,
    ).contiguous().realize(),
    "desire_q": Tensor(
      np.zeros((frame_skip * desire_shape[1], desire_shape[0], desire_shape[2]), dtype=np.float32),
      device=device,
    ).contiguous().realize(),
    "packed_npy_inputs": Tensor(packed_inputs, device="NPY").realize(),
  })
  return queues, npy


def shift_and_sample(buffer, new_value, sample_fn):
  buffer.assign(buffer[1:].cat(new_value, dim=0).contiguous())
  return sample_fn(buffer)


def sample_skip(buffer, frame_skip):
  return buffer[::frame_skip].contiguous().flatten(0, 1).unsqueeze(0)


def sample_desire(buffer, frame_skip):
  return buffer.reshape(-1, frame_skip, *buffer.shape[1:]).max(1).flatten(0, 1).unsqueeze(0)


def make_warp(nv12, model_w, model_h, frame_skip, image_history_pipeline=IMAGE_HISTORY_IN_POLICY):
  frame_prepare = make_frame_prepare(nv12, model_w, model_h)

  if image_history_pipeline == IMAGE_HISTORY_IN_POLICY:
    def warp(tfm, big_tfm, frame, big_frame):
      tfm = tfm.to(WARP_DEV)
      big_tfm = big_tfm.to(WARP_DEV)
      Tensor.realize(tfm, big_tfm)

      return Tensor.cat(
        frame_prepare(frame, tfm).unsqueeze(0),
        frame_prepare(big_frame, big_tfm).unsqueeze(0),
      )

    return warp

  sample_skip_fn = partial(sample_skip, frame_skip=frame_skip)

  def warp_enqueue(img_q, big_img_q, tfm, big_tfm, frame, big_frame):
    tfm = tfm.to(WARP_DEV)
    big_tfm = big_tfm.to(WARP_DEV)
    Tensor.realize(tfm, big_tfm)

    warped = Tensor.cat(
      frame_prepare(frame, tfm).unsqueeze(0),
      frame_prepare(big_frame, big_tfm).unsqueeze(0),
    ).to(Device.DEFAULT)
    img = shift_and_sample(img_q, warped[0:1], sample_skip_fn)
    big_img = shift_and_sample(big_img_q, warped[1:2], sample_skip_fn)
    return img, big_img

  return warp_enqueue


def make_run_split_policy(vision_runner, policy_runners, metadata, policy_order, frame_skip,
                          image_history_pipeline=IMAGE_HISTORY_IN_POLICY):
  sample_desire_fn = partial(sample_desire, frame_skip=frame_skip)
  sample_skip_fn = partial(sample_skip, frame_skip=frame_skip)
  vision_metadata = metadata["vision"]
  policy_metadata = metadata[policy_order[0]]
  vision_features_slice = vision_metadata["output_slices"]["hidden_state"]
  desire_key = _detect_desire_key(policy_metadata["input_shapes"])
  packed_shapes, packed_sizes = _packed_policy_shapes(policy_metadata["input_shapes"])
  road_key, wide_key = _detect_vision_keys(vision_metadata["input_shapes"])

  def run_model(img, big_img, feat_q, desire_q, packed_npy_inputs):
    unpacked = {
      key: tensor.reshape(shape)
      for (key, shape), tensor in zip(
        packed_shapes.items(), packed_npy_inputs.split(packed_sizes), strict=True,
      )
    }
    desire_buffer = shift_and_sample(
      desire_q, unpacked.pop("desire").reshape(1, 1, -1), sample_desire_fn,
    )
    vision_output = next(iter(vision_runner({road_key: img, wide_key: big_img}).values())).cast("float32")
    new_feature = vision_output[:, vision_features_slice].reshape(1, -1).unsqueeze(0)
    features_buffer = shift_and_sample(feat_q, new_feature, sample_skip_fn)
    features_buffer = features_buffer.reshape(policy_metadata["input_shapes"]["features_buffer"])

    policy_inputs = {
      "features_buffer": features_buffer,
      desire_key: desire_buffer,
      **unpacked,
    }
    policy_outputs = [
      next(iter(policy_runners[key](policy_inputs).values())).cast("float32")
      for key in policy_order
    ]
    return (vision_output, *policy_outputs)

  if image_history_pipeline == IMAGE_HISTORY_IN_POLICY:
    def run_policy(warped, img_q, big_img_q, feat_q, desire_q, packed_npy_inputs):
      packed_npy_inputs = packed_npy_inputs.to(Device.DEFAULT)
      warped = warped.to(Device.DEFAULT)
      Tensor.realize(packed_npy_inputs, warped)
      img = shift_and_sample(img_q, warped[0:1], sample_skip_fn)
      big_img = shift_and_sample(big_img_q, warped[1:2], sample_skip_fn)
      return run_model(img, big_img, feat_q, desire_q, packed_npy_inputs)

    return run_policy

  def run_policy(img, big_img, feat_q, desire_q, packed_npy_inputs):
    packed_npy_inputs = packed_npy_inputs.to(Device.DEFAULT).realize()
    return run_model(img, big_img, feat_q, desire_q, packed_npy_inputs)

  return run_policy


def make_run_supercombo(model_runner, metadata, frame_skip, image_history_pipeline=IMAGE_HISTORY_IN_POLICY):
  input_shapes = metadata["model"]["input_shapes"]
  output_slices = metadata["model"]["output_slices"]
  sample_desire_fn = partial(sample_desire, frame_skip=frame_skip)
  sample_skip_fn = partial(sample_skip, frame_skip=frame_skip)
  desire_key = _detect_desire_key(input_shapes)
  packed_shapes, packed_sizes = _packed_policy_shapes(input_shapes, include_prev_feature=True)
  road_key, wide_key = _detect_vision_keys(input_shapes)

  def run_model(img, big_img, feat_q, desire_q, packed_npy_inputs):
    unpacked = {
      key: tensor.reshape(shape)
      for (key, shape), tensor in zip(
        packed_shapes.items(), packed_npy_inputs.split(packed_sizes), strict=True,
      )
    }
    desire_buffer = shift_and_sample(
      desire_q, unpacked.pop("desire").reshape(1, 1, -1), sample_desire_fn,
    )
    previous_feature = unpacked.pop("prev_feat")
    features_buffer = shift_and_sample(
      feat_q, previous_feature.reshape(1, 1, -1), sample_skip_fn,
    )
    features_buffer = features_buffer.reshape(input_shapes["features_buffer"])
    model_inputs = {
      road_key: img,
      wide_key: big_img,
      "features_buffer": features_buffer,
      desire_key: desire_buffer,
      **unpacked,
    }
    model_output = next(iter(model_runner(model_inputs).values())).cast("float32")
    return model_output,

  if image_history_pipeline == IMAGE_HISTORY_IN_POLICY:
    def run_policy(warped, img_q, big_img_q, feat_q, desire_q, packed_npy_inputs):
      packed_npy_inputs = packed_npy_inputs.to(Device.DEFAULT)
      warped = warped.to(Device.DEFAULT)
      Tensor.realize(packed_npy_inputs, warped)
      img = shift_and_sample(img_q, warped[0:1], sample_skip_fn)
      big_img = shift_and_sample(big_img_q, warped[1:2], sample_skip_fn)
      return run_model(img, big_img, feat_q, desire_q, packed_npy_inputs)

    return run_policy

  def run_policy(img, big_img, feat_q, desire_q, packed_npy_inputs):
    packed_npy_inputs = packed_npy_inputs.to(Device.DEFAULT).realize()
    return run_model(img, big_img, feat_q, desire_q, packed_npy_inputs)

  return run_policy


def compile_jit(jit, make_random_inputs, input_keys, make_queues):
  seed = 42

  def random_inputs_run(fn, current_seed, test_values=None, test_buffers=None, expect_match=True):
    input_queues, npy = make_queues(Device.DEFAULT)
    np.random.seed(current_seed)
    Tensor.manual_seed(current_seed)
    testing = test_values is not None or test_buffers is not None
    run_count = 1 if testing else 3

    for index in range(run_count):
      for value in npy.values():
        value[:] = np.random.randn(*value.shape).astype(value.dtype)
      Device.default.synchronize()
      random_inputs = make_random_inputs()
      start = time.perf_counter()
      outputs = fn(**{key: input_queues[key] for key in input_keys}, **random_inputs)
      mid = time.perf_counter()
      Device.default.synchronize()
      end = time.perf_counter()
      print(f"  [{index + 1}/{run_count}] enqueue {(mid - start) * 1e3:6.2f} ms -- total {(end - start) * 1e3:6.2f} ms")

      if index == 0:
        values = [np.copy(value.numpy()) for value in outputs]
        buffers = [np.copy(value.numpy()) for value in input_queues.values()]
        if not all(np.isfinite(value).all() for value in values):
          raise ValueError("Compiled JIT produced non-finite outputs")

    if test_values is not None:
      match = all(np.array_equal(lhs, rhs) for lhs, rhs in zip(values, test_values, strict=True))
      assert match == expect_match, f"outputs {'differ from' if expect_match else 'match'} baseline (seed={current_seed})"
    if test_buffers is not None:
      match = all(np.array_equal(lhs, rhs) for lhs, rhs in zip(buffers, test_buffers, strict=True))
      assert match == expect_match, f"buffers {'differ from' if expect_match else 'match'} baseline (seed={current_seed})"
    return values, buffers

  print("capture + replay")
  test_values, test_buffers = random_inputs_run(jit, seed)
  # The pickle round-trip below is normally a serialization sanity check, but in
  # this tinygrad build it rewrites the compiled device/target refs inside the
  # JIT to the comma-device default (QCOM), producing an artifact that cannot run
  # on a PC CUDA host. Skip it by default so the captured PC kernels survive.
  if os.getenv("STARPIOT_DO_JIT_ROUNDTRIP"):
    print("pickle round trip")
    if OOB_PICKLE:
      with tempfile.TemporaryFile(dir=".") as artifact_file:
        dump_oob(jit, artifact_file)
        artifact_file.seek(0)
        from openpilot.selfdrive.modeld.helpers import load_oob
        jit = load_oob(artifact_file)
    else:
      jit = pickle.loads(pickle.dumps(jit))
  else:
    print("skipping pickle round trip")
  random_inputs_run(jit, seed, test_values, test_buffers, expect_match=True)
  random_inputs_run(jit, seed + 1, test_values, test_buffers, expect_match=False)
  return jit


def _parse_size(value):
  width, height = value.lower().split("x")
  return int(width), int(height)


def read_file_chunked_to_disk(path):
  from openpilot.common.file_chunker import open_file_chunked

  if os.path.isfile(path):
    return os.fspath(path)

  temporary_path = f"{path}.unchunked"
  try:
    with open(temporary_path, "wb") as output, open_file_chunked(path) as source:
      shutil.copyfileobj(source, output)
  except Exception:
    if os.path.exists(temporary_path):
      os.remove(temporary_path)
    raise
  atexit.register(lambda: os.path.exists(temporary_path) and os.remove(temporary_path))
  return temporary_path


def validate_metadata(metadata):
  output_shapes = metadata.get("output_shapes", {})
  output_shape = output_shapes.get("outputs")
  if not output_shape or len(output_shape) < 2:
    raise ValueError(f"Invalid model output shape metadata: {output_shapes}")
  output_size = output_shape[-1]
  for name, output_slice in metadata.get("output_slices", {}).items():
    start, stop, step = output_slice.indices(output_size)
    if step != 1 or start < 0 or stop < start or stop > output_size:
      raise ValueError(f"Invalid output slice {name}={output_slice} for output size {output_size}")


def build_supercombo_artifact(supercombo_onnx, model_size, camera_resolutions, behavior_version=None,
                              frame_skip=None, image_history_pipeline=IMAGE_HISTORY_IN_POLICY):
  """Trace a supercombo ONNX into a live, in-memory artifact (no pickling).

  Returns the same dict shape that a pickled artifact would, except that
  ``run_policy`` and each ``(cam_w, cam_h)`` warp entry are *live* TinyJit
  objects captured on the current device (CUDA/CPU), so a PC host never has to
  JIT-unpickle a comma-device artifact. This is the reliable path on a host GPU.
  """
  from tinygrad.nn.onnx import OnnxRunner

  from openpilot.selfdrive.modeld.get_model_metadata import make_metadata_dict
  from openpilot.system.camerad.cameras.nv12_info import get_nv12_info

  output = {
    "format_version": ARTIFACT_FORMAT_VERSION,
    "model_type": "supercombo",
    "metadata": {},
    "image_history_pipeline": image_history_pipeline,
  }
  if behavior_version:
    output["behavior_version"] = behavior_version

  model_path = read_file_chunked_to_disk(supercombo_onnx)
  model_runner = OnnxRunner(model_path)
  output["metadata"]["model"] = make_metadata_dict(model_path)
  validate_metadata(output["metadata"]["model"])
  policy_shapes = output["metadata"]["model"]["input_shapes"]
  frame_skip = frame_skip or derive_frame_skip(policy_shapes)
  make_policy_queues = partial(make_supercombo_input_queues, policy_shapes, frame_skip)
  run_policy = make_run_supercombo(model_runner, output["metadata"], frame_skip, image_history_pipeline)
  image_shapes = policy_shapes
  policy_input_keys = FAST_POLICY_INPUTS if image_history_pipeline == IMAGE_HISTORY_IN_POLICY else SUPERCOMBO_POLICY_INPUTS

  output["frame_skip"] = frame_skip
  output["policy_input_keys"] = policy_input_keys
  warp_input_keys = FAST_WARP_INPUTS if image_history_pipeline == IMAGE_HISTORY_IN_POLICY else LEGACY_WARP_INPUTS
  output["warp_input_keys"] = warp_input_keys
  run_policy_jit = TinyJit(run_policy, prune=True)
  road_key, wide_key = _detect_vision_keys(image_shapes)
  if image_history_pipeline == IMAGE_HISTORY_IN_POLICY:
    make_random_model_inputs = partial(
      make_random_images,
      keys=["warped"],
      shape=(2, 6, *image_shapes[road_key][2:]),
      device=WARP_DEV,
    )
  else:
    make_random_model_inputs = partial(
      make_random_images,
      keys=[road_key, wide_key],
      shape=image_shapes[road_key],
    )
  output["run_policy"] = compile_jit(
    run_policy_jit, make_random_model_inputs, policy_input_keys, make_policy_queues,
  )

  model_w, model_h = model_size
  for cam_w, cam_h in camera_resolutions:
    nv12 = NV12Frame(cam_w, cam_h, *get_nv12_info(cam_w, cam_h))
    warp_enqueue = TinyJit(
      make_warp(nv12, model_w, model_h, frame_skip, image_history_pipeline),
      prune=True,
    )
    make_random_warp_inputs = make_random_blob_images(
      keys=["frame", "big_frame"], size=nv12.size, device=WARP_DEV,
    )
    make_warp_queues = partial(make_warp_input_queues, image_shapes, frame_skip)
    output[(cam_w, cam_h)] = compile_jit(
      warp_enqueue, make_random_warp_inputs, warp_input_keys, make_warp_queues,
    )
  return output


def main():
  global OOB_PICKLE
  from tinygrad.nn.onnx import OnnxRunner

  from openpilot.selfdrive.modeld.get_model_metadata import make_metadata_dict
  from openpilot.system.camerad.cameras.nv12_info import get_nv12_info

  parser = argparse.ArgumentParser()
  parser.add_argument("--model-type", choices=MODEL_TYPES, required=True)
  parser.add_argument("--model-size", type=_parse_size, required=True)
  parser.add_argument("--camera-resolutions", type=_parse_size, nargs="+", required=True)
  parser.add_argument("--frame-skip", type=int)
  parser.add_argument("--behavior-version")
  parser.add_argument("--output", required=True)
  parser.add_argument("--out-of-band", action="store_true", help="Stream model weights outside pickle opcodes for large artifacts.")
  parser.add_argument("--vision-onnx")
  parser.add_argument("--policy-onnx")
  parser.add_argument("--off-policy-onnx")
  parser.add_argument("--on-policy-onnx")
  parser.add_argument("--supercombo-onnx")
  parser.add_argument(
    "--image-history-pipeline",
    choices=IMAGE_HISTORY_PIPELINES,
    default=IMAGE_HISTORY_IN_POLICY,
    help="Where img/big_img history queues are updated. 'policy' is the newer faster ABI; 'warp' reproduces legacy v22 artifacts.",
  )
  args = parser.parse_args()
  OOB_PICKLE = args.out_of_band
  if "USB+AMD" in os.environ.get("DEV", ""):
    wait_usbgpu_link()

  output = {
    "format_version": ARTIFACT_FORMAT_VERSION,
    "model_type": args.model_type,
    "metadata": {},
    "image_history_pipeline": args.image_history_pipeline,
  }
  if args.behavior_version:
    output["behavior_version"] = args.behavior_version

  if args.model_type == "supercombo":
    if not args.supercombo_onnx:
      parser.error("--supercombo-onnx is required for supercombo")
    output = build_supercombo_artifact(
      args.supercombo_onnx,
      args.model_size,
      args.camera_resolutions,
      behavior_version=args.behavior_version,
      frame_skip=args.frame_skip,
      image_history_pipeline=args.image_history_pipeline,
    )
  else:
    if not args.vision_onnx:
      parser.error("--vision-onnx is required for split models")
    policy_paths = {}
    if args.policy_onnx:
      policy_paths["policy"] = args.policy_onnx
    if args.off_policy_onnx:
      policy_paths["off_policy"] = args.off_policy_onnx
    if args.on_policy_onnx:
      policy_paths["on_policy"] = args.on_policy_onnx
    if args.model_type == "vision_policy" and set(policy_paths) != {"policy"}:
      parser.error("vision_policy requires --policy-onnx")
    if args.model_type == "vision_multi_policy" and not policy_paths:
      parser.error("vision_multi_policy requires at least one policy ONNX")

    vision_path = read_file_chunked_to_disk(args.vision_onnx)
    resolved_policy_paths = {key: read_file_chunked_to_disk(path) for key, path in policy_paths.items()}
    vision_runner = OnnxRunner(vision_path)
    policy_runners = {key: OnnxRunner(path) for key, path in resolved_policy_paths.items()}
    output["metadata"]["vision"] = make_metadata_dict(vision_path)
    validate_metadata(output["metadata"]["vision"])
    for key, path in resolved_policy_paths.items():
      output["metadata"][key] = make_metadata_dict(path)
      validate_metadata(output["metadata"][key])

    policy_order = [key for key in ("on_policy", "off_policy", "policy") if key in policy_runners]
    output["policy_order"] = policy_order
    first_policy_shapes = output["metadata"][policy_order[0]]["input_shapes"]
    for key in policy_order[1:]:
      if output["metadata"][key]["input_shapes"] != first_policy_shapes:
        raise ValueError(f"Policy input shapes differ between {policy_order[0]} and {key}")
    frame_skip = args.frame_skip or derive_frame_skip(first_policy_shapes)
    make_policy_queues = partial(
      make_split_input_queues,
      output["metadata"]["vision"]["input_shapes"],
      first_policy_shapes,
      frame_skip,
    )
    run_policy = make_run_split_policy(
      vision_runner, policy_runners, output["metadata"], policy_order, frame_skip,
      args.image_history_pipeline,
    )
    image_shapes = output["metadata"]["vision"]["input_shapes"]
    policy_input_keys = FAST_POLICY_INPUTS if args.image_history_pipeline == IMAGE_HISTORY_IN_POLICY else SPLIT_POLICY_INPUTS

    output["frame_skip"] = frame_skip
    output["policy_input_keys"] = policy_input_keys
    warp_input_keys = FAST_WARP_INPUTS if args.image_history_pipeline == IMAGE_HISTORY_IN_POLICY else LEGACY_WARP_INPUTS
    output["warp_input_keys"] = warp_input_keys
    run_policy_jit = TinyJit(run_policy, prune=True)
    road_key, wide_key = _detect_vision_keys(image_shapes)
    if args.image_history_pipeline == IMAGE_HISTORY_IN_POLICY:
      make_random_model_inputs = partial(
        make_random_images,
        keys=["warped"],
        shape=(2, 6, *image_shapes[road_key][2:]),
        device=WARP_DEV,
      )
    else:
      make_random_model_inputs = partial(
        make_random_images,
        keys=[road_key, wide_key],
        shape=image_shapes[road_key],
      )
    output["run_policy"] = compile_jit(
      run_policy_jit, make_random_model_inputs, policy_input_keys, make_policy_queues,
    )

    model_w, model_h = args.model_size
    for cam_w, cam_h in args.camera_resolutions:
      nv12 = NV12Frame(cam_w, cam_h, *get_nv12_info(cam_w, cam_h))
      warp_enqueue = TinyJit(
        make_warp(nv12, model_w, model_h, frame_skip, args.image_history_pipeline),
        prune=True,
      )
      make_random_warp_inputs = make_random_blob_images(
        keys=["frame", "big_frame"], size=nv12.size, device=WARP_DEV,
      )
      make_warp_queues = partial(make_warp_input_queues, image_shapes, frame_skip)
      output[(cam_w, cam_h)] = compile_jit(
        warp_enqueue, make_random_warp_inputs, warp_input_keys, make_warp_queues,
      )

  with open(args.output, "wb") as artifact_file:
    if args.out_of_band:
      dump_oob(output, artifact_file)
    else:
      pickle.dump(output, artifact_file)
  print(f"Saved JITs to {args.output} ({os.path.getsize(args.output) / 1e6:.2f} MB)")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
