"""Opt-in onroad camera observation producer; no Params mailbox or control writes."""

from __future__ import annotations

import math
import os
import time
import uuid

import numpy as np

from openpilot.starpilot.speed_limits.vision.model import VisionModelCore, cv2
from openpilot.starpilot.speed_limits.vision.observation import MODEL_ID, MAX_FRAME_AGE_NS, MAX_PAIR_SKEW_NS, clock_pair_ns

UNAVAILABLE_RETRY_SECONDS = 1.0
INFERENCE_INTERVAL_NS = 166_666_667
BUSY_INFERENCE_INTERVAL_NS = 1_500_000_000


def _configure_process() -> None:
  from openpilot.common.hardware import PC
  from openpilot.common.realtime import drop_realtime, set_core_affinity

  if PC:
    return
  for configure in (drop_realtime, lambda: set_core_affinity([0, 1, 2])):
    try:
      configure()
    except OSError:
      pass
  try:
    os.nice(max(0, 10 - os.getpriority(os.PRIO_PROCESS, 0)))
  except (AttributeError, OSError):
    pass


def _driving_model_ready(sm, now_ns: int) -> bool:
  service = 'drivingModelData'
  if not sm.seen[service] or not sm.valid[service]:
    return False
  stamp_ns = sm.logMonoTime[service]
  drop = float(sm[service].frameDropPerc)
  return (stamp_ns > 0 and 0 <= now_ns - stamp_ns <= MAX_FRAME_AGE_NS and
          math.isfinite(drop) and 0 <= drop <= 1)


def _camera_buffer(client):
  buffer = client.recv(100)
  if buffer is None:
    return None
  eof_boot_ns, frame_id = int(client.timestamp_eof), int(client.frame_id)
  stride, width, height = int(client.stride), int(client.width), int(client.height)
  uv_offset = int(client.uv_offset)
  if (stride < width or width <= 0 or height <= 0 or width % 2 or height % 2 or
      uv_offset < stride * height or uv_offset % stride):
    return None
  return buffer, eof_boot_ns, frame_id, stride, width, height, uv_offset


def _convert_camera_buffer(info) -> tuple[np.ndarray, int, int] | None:
  buffer, eof_boot_ns, frame_id, stride, width, height, uv_offset = info
  # VisionBuf borrows client-owned shared memory. Copy before another receive
  # or reconnect; only the owned array is used for conversion and inference.
  raw = np.frombuffer(buffer.data, dtype=np.uint8).copy()
  required = uv_offset + stride * (height // 2)
  if raw.size < required:
    return None
  y = raw[:stride * height].reshape((height, stride))[:, :width]
  uv = raw[uv_offset:required].reshape((height // 2, stride))[:, :width]
  nv12 = np.concatenate((y, uv), axis=0)
  frame = cv2.cvtColor(nv12, cv2.COLOR_YUV2BGR_NV12)
  return frame, eof_boot_ns, frame_id


def _camera_frame(client) -> tuple[np.ndarray, int, int] | None:
  info = _camera_buffer(client)
  return _convert_camera_buffer(info) if info is not None else None


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

  _configure_process()
  pm = messaging.PubMaster(['slcVisionObservation'])
  sm = messaging.SubMaster(['drivingModelData'])
  session = uuid.uuid4().hex
  stream = 'unknown'
  client = None
  core = None
  last_unavailable = 0.0
  try:
    if cv2 is not None:
      cv2.setNumThreads(1)
    core = VisionModelCore(is_metric=Params().get_bool('IsMetric'))
  except Exception as error:
    cloudlog.error('vision SLC model unavailable: %s', error)
  last_inference_ns = 0
  inference_interval_ns = INFERENCE_INTERVAL_NS
  last_clock_offset_ns = None
  model_paused = False
  while True:
    if core is None:
      now = time.monotonic()
      if now - last_unavailable >= UNAVAILABLE_RETRY_SECONDS:
        _send(pm, session=session, status='unavailable', stream=stream)
        last_unavailable = now
      time.sleep(0.1)
      continue
    try:
      sm.update(0)
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
        inference_interval_ns = INFERENCE_INTERVAL_NS
        last_clock_offset_ns = None
        client.connect(False)
        if not client.is_connected():
          core.reset()
          client = None
          time.sleep(0.1)
          continue
      buffer_info = _camera_buffer(client)
      if buffer_info is None:
        continue
      eof_boot_ns, frame_id = buffer_info[1:3]
      admission_pair = clock_pair_ns()
      if (admission_pair is None or eof_boot_ns <= 0 or
          not 0 <= admission_pair[1] - eof_boot_ns <= MAX_FRAME_AGE_NS):
        del buffer_info
        _send(pm, session=session, status='stale', stream=stream, eof_boot_ns=eof_boot_ns, frame_id=frame_id)
        continue
      if not _driving_model_ready(sm, admission_pair[0]):
        del buffer_info
        if not model_paused:
          core.reset()
          session = uuid.uuid4().hex
          _send(pm, session=session, status='unavailable', stream=stream)
          last_unavailable = admission_pair[0] / 1e9
        elif admission_pair[0] / 1e9 - last_unavailable >= UNAVAILABLE_RETRY_SECONDS:
          _send(pm, session=session, status='unavailable', stream=stream)
          last_unavailable = admission_pair[0] / 1e9
        model_paused = True
        time.sleep(0.1)
        continue
      model_paused = False
      admission_offset_ns = admission_pair[1] - admission_pair[0]
      offset_stable = (last_clock_offset_ns is None or
                       abs(admission_offset_ns - last_clock_offset_ns) <= MAX_PAIR_SKEW_NS)
      if offset_stable and admission_pair[0] - last_inference_ns < inference_interval_ns:
        del buffer_info
        continue
      try:
        frame_info = _convert_camera_buffer(buffer_info)
      finally:
        del buffer_info
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
        inference_interval_ns = INFERENCE_INTERVAL_NS
      last_clock_offset_ns = offset_ns
      if pair[0] - last_inference_ns < inference_interval_ns:
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
      sm.update(0)
      observed_pair = clock_pair_ns()
      if observed_pair is not None:
        processing_ns = observed_pair[0] - last_inference_ns
        if processing_ns >= 0:
          # Original Dom processing-cost cooldown: keep slow CPU inference from
          # immediately starting another pass, including after stale rejection.
          inference_interval_ns = max(INFERENCE_INTERVAL_NS,
                                      min(BUSY_INFERENCE_INTERVAL_NS, processing_ns * 5 // 2))
      if (observed_pair is None or
          abs((observed_pair[1] - observed_pair[0]) - offset_ns) > MAX_PAIR_SKEW_NS or
          not 0 <= observed_pair[1] - eof_boot_ns <= MAX_FRAME_AGE_NS):
        core.reset()
        session = uuid.uuid4().hex
        last_clock_offset_ns = None
        _send(pm, session=session, status='stale', stream=stream, eof_boot_ns=eof_boot_ns, frame_id=frame_id)
        continue
      if not _driving_model_ready(sm, observed_pair[0]):
        core.reset()
        session = uuid.uuid4().hex
        model_paused = True
        last_unavailable = observed_pair[0] / 1e9
        _send(pm, session=session, status='unavailable', stream=stream)
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
