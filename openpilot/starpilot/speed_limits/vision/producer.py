"""Opt-in onroad camera observation producer; no Params mailbox or control writes."""

from __future__ import annotations

import time
import uuid

import numpy as np

from openpilot.starpilot.speed_limits.vision.model import VisionModelCore, cv2
from openpilot.starpilot.speed_limits.vision.observation import MODEL_ID, MAX_FRAME_AGE_NS, MAX_PAIR_SKEW_NS, clock_pair_ns

UNAVAILABLE_RETRY_SECONDS = 1.0


def _camera_frame(client) -> tuple[np.ndarray, int, int] | None:
  buffer = client.recv(100)
  if buffer is None:
    return None
  eof_boot_ns, frame_id = int(client.timestamp_eof), int(client.frame_id)
  stride, width, height = int(client.stride), int(client.width), int(client.height)
  uv_offset = int(client.uv_offset)
  if (stride < width or width <= 0 or height <= 0 or width % 2 or height % 2 or
      uv_offset < stride * height or uv_offset % stride):
    return None
  # Copy before dropping VisionBuf: no old camerad allocation stays pinned.
  raw = np.frombuffer(buffer.data, dtype=np.uint8).copy()
  del buffer
  required = uv_offset + stride * (height // 2)
  if raw.size < required:
    return None
  y = raw[:stride * height].reshape((height, stride))[:, :width]
  uv = raw[uv_offset:required].reshape((height // 2, stride))[:, :width]
  nv12 = np.concatenate((y, uv), axis=0)
  frame = cv2.cvtColor(nv12, cv2.COLOR_YUV2BGR_NV12)
  return frame, eof_boot_ns, frame_id


def _send(pm, *, session: str, status: str, stream: str, observed_ns: int = 0,
          eof_boot_ns: int = 0, frame_id: int = 0, result: tuple[int, float, int, int] | None = None) -> None:
  from openpilot.cereal import messaging

  msg = messaging.new_message('slcVisionObservation', valid=True)
  event = msg.slcVisionObservation.init('vision')
  event.producerSessionId = session
  event.status = status
  event.modelId = MODEL_ID
  event.stream = stream
  event.observedMonoTime = observed_ns
  event.cameraFrameEofBootTime = eof_boot_ns
  event.frameId = frame_id
  if result is not None:
    mph, confidence, support, episode = result
    event.speedMps = mph * 0.44704
    event.confidence = confidence
    event.supportCount = support
    event.episode = episode
    event.validUntilMonoTime = observed_ns + MAX_FRAME_AGE_NS
  pm.send('slcVisionObservation', msg)


def main() -> None:
  import openpilot.cereal.messaging as messaging
  from openpilot.cereal.visionipc import VisionStreamType
  from msgq.visionipc import VisionIpcClient
  from openpilot.common.params import Params
  from openpilot.common.swaglog import cloudlog

  pm = messaging.PubMaster(['slcVisionObservation'])
  session = uuid.uuid4().hex
  stream = 'unknown'
  client = None
  core = None
  last_unavailable = 0.0
  try:
    if cv2 is not None:
      cv2.setNumThreads(2)
    core = VisionModelCore(is_metric=Params().get_bool('IsMetric'))
  except Exception as error:
    cloudlog.error('vision SLC model unavailable: %s', error)
  last_inference_ns = 0
  last_clock_offset_ns = None
  while True:
    if core is None:
      now = time.monotonic()
      if now - last_unavailable >= UNAVAILABLE_RETRY_SECONDS:
        _send(pm, session=session, status='unavailable', stream=stream)
        last_unavailable = now
      time.sleep(0.1)
      continue
    try:
      available = VisionIpcClient.available_streams('camerad', block=False)
      wanted = (VisionStreamType.VISION_STREAM_NARROW_ROAD if VisionStreamType.VISION_STREAM_NARROW_ROAD in available else
                VisionStreamType.VISION_STREAM_WIDE_ROAD if VisionStreamType.VISION_STREAM_WIDE_ROAD in available else None)
      if wanted is None:
        if client is not None:
          core.reset()
          session = uuid.uuid4().hex
        client = None
        stream = 'unknown'
        _send(pm, session=session, status='unavailable', stream='unknown')
        time.sleep(UNAVAILABLE_RETRY_SECONDS)
        continue
      new_stream = 'road' if wanted == VisionStreamType.VISION_STREAM_NARROW_ROAD else 'wideRoad'
      if client is None or stream != new_stream:
        core.reset()
        session = uuid.uuid4().hex
        client = VisionIpcClient('camerad', wanted, True)
        stream = new_stream
      if not client.is_connected():
        # Even a successful reconnect of the same client starts a new camera
        # session. Earlier sign support cannot confirm a new producer's frame.
        core.reset()
        session = uuid.uuid4().hex
        last_inference_ns = 0
        last_clock_offset_ns = None
        client.connect(False)
        if not client.is_connected():
          core.reset()
          client = None
          time.sleep(0.1)
          continue
      frame_info = _camera_frame(client)
      if frame_info is None:
        continue
      frame, eof_boot_ns, frame_id = frame_info
      pair = clock_pair_ns()
      if pair is None or eof_boot_ns <= 0 or not 0 <= pair[1] - eof_boot_ns <= MAX_FRAME_AGE_NS:
        _send(pm, session=session, status='stale', stream=stream, eof_boot_ns=eof_boot_ns, frame_id=frame_id)
        continue
      offset_ns = pair[1] - pair[0]
      if last_clock_offset_ns is not None and abs(offset_ns - last_clock_offset_ns) > MAX_PAIR_SKEW_NS:
        core.reset()
        session = uuid.uuid4().hex
        last_inference_ns = 0
      last_clock_offset_ns = offset_ns
      if pair[0] - last_inference_ns < 166_666_667:
        continue
      last_inference_ns = pair[0]
      try:
        result = core.observe(frame, now=pair[0] / 1e9)
      except Exception as error:
        cloudlog.error('vision SLC inference unavailable: %s', error)
        _send(pm, session=session, status='unavailable', stream=stream)
        client = None
        core = None
        continue
      observed_pair = clock_pair_ns()
      if (observed_pair is None or
          abs((observed_pair[1] - observed_pair[0]) - offset_ns) > MAX_PAIR_SKEW_NS or
          not 0 <= observed_pair[1] - eof_boot_ns <= MAX_FRAME_AGE_NS):
        core.reset()
        session = uuid.uuid4().hex
        last_clock_offset_ns = None
        _send(pm, session=session, status='stale', stream=stream, eof_boot_ns=eof_boot_ns, frame_id=frame_id)
        continue
      _send(pm, session=session, status='valid' if result is not None else 'unknown', stream=stream,
            observed_ns=observed_pair[0], eof_boot_ns=eof_boot_ns, frame_id=frame_id, result=result)
    except Exception as error:
      cloudlog.error('vision SLC camera unavailable: %s', error)
      _send(pm, session=session, status='unavailable', stream=stream)
      client = None
      core.reset()
      session = uuid.uuid4().hex
      last_clock_offset_ns = None
      time.sleep(0.1)
