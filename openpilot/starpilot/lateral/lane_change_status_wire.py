"""Bounded typed status for optional lane-change alert wording.

This status is presentation evidence, never engagement authority.
"""

from dataclasses import dataclass
from enum import IntEnum
import struct

import capnp

from openpilot.cereal import custom


SERVICE = "laneChangeAssistWire"
KIND = 3
VERSION = 1
MAX_BYTES = 512
MAX_WORDS = (MAX_BYTES - 8) // 8


class Phase(IntEnum):
  MANUAL_REQUIRED = 0
  WAITING_FOR_DELAY = 1
  LANE_UNAVAILABLE = 2
  BLINDSPOT_BLOCKED = 3


class Direction(IntEnum):
  NONE = 0
  LEFT = 1
  RIGHT = 2


@dataclass(frozen=True)
class LaneChangeStatus:
  producer_session_id: str
  sequence: int
  model_frame_id: int
  model_timestamp_eof_ns: int
  observed_mono_time_ns: int
  valid_until_mono_time_ns: int
  phase: Phase
  direction: Direction
  auto_configured: bool
  engaged: bool


def _valid(value: LaneChangeStatus) -> bool:
  return (type(value.producer_session_id) is str and 1 <= len(value.producer_session_id.encode("utf-8")) <= 96 and
          0 <= value.sequence < 2**64 and 0 <= value.model_frame_id < 2**32 and
          0 < value.model_timestamp_eof_ns < 2**64 and
          0 < value.observed_mono_time_ns <= value.valid_until_mono_time_ns < 2**64 and
          type(value.phase) is Phase and type(value.direction) is Direction and
          type(value.auto_configured) is bool and type(value.engaged) is bool)


def encode(value: LaneChangeStatus) -> bytes:
  if not _valid(value):
    raise ValueError("invalid lane-change status")
  msg = custom.AolAxisState.LaneChangeStatusWire.new_message(
    kind=KIND, version=VERSION, producerSessionId=value.producer_session_id,
    sequence=value.sequence, modelFrameId=value.model_frame_id,
    modelTimestampEofNs=value.model_timestamp_eof_ns,
    observedMonoTimeNs=value.observed_mono_time_ns, validUntilMonoTimeNs=value.valid_until_mono_time_ns,
    phase=int(value.phase), direction=int(value.direction),
    autoConfigured=value.auto_configured, engaged=value.engaged)
  raw = msg.to_bytes()
  if len(raw) > MAX_BYTES:
    raise ValueError("lane-change status exceeds wire bound")
  return raw


def encode_optional(value: LaneChangeStatus) -> bytes | None:
  """Bad optional camera metadata must not interrupt model publication."""
  try:
    return encode(value)
  except (ValueError, OverflowError, RuntimeError, capnp.KjException):
    return None


def decode(raw_value: bytes) -> LaneChangeStatus | None:
  if not isinstance(raw_value, (bytes, bytearray, memoryview)):
    return None
  raw = bytes(raw_value)
  if not 16 <= len(raw) <= MAX_BYTES or len(raw) % 8:
    return None
  try:
    segments, words = struct.unpack_from("<II", raw)
    if segments != 0 or words > MAX_WORDS or len(raw) != 8 + 8 * words:
      return None
    with custom.AolAxisState.LaneChangeStatusWire.from_bytes(raw, traversal_limit_in_words=MAX_WORDS, nesting_limit=4) as msg:
      if msg.kind != KIND or msg.version != VERSION:
        return None
      result = LaneChangeStatus(str(msg.producerSessionId), int(msg.sequence), int(msg.modelFrameId),
                                int(msg.modelTimestampEofNs), int(msg.observedMonoTimeNs),
                                int(msg.validUntilMonoTimeNs), Phase(int(msg.phase.raw)), Direction(int(msg.direction.raw)),
                                bool(msg.autoConfigured), bool(msg.engaged))
      return result if _valid(result) else None
  except (ValueError, OverflowError, RuntimeError, UnicodeDecodeError, capnp.KjException):
    return None


def fresh_for_model(status: LaneChangeStatus | None, model, now_mono_ns: int, recv_mono_ns: int,
                    last_sequence: int = -1, last_session: str = "", message_mono_ns: int | None = None) -> bool:
  if status is None or (status.phase != Phase.MANUAL_REQUIRED and not status.engaged) or not 0 <= now_mono_ns - status.observed_mono_time_ns <= 100_000_000:
    return False
  if not 0 <= now_mono_ns - recv_mono_ns <= 100_000_000 or now_mono_ns > status.valid_until_mono_time_ns:
    return False
  if message_mono_ns is not None and not 0 <= now_mono_ns - message_mono_ns <= 100_000_000:
    return False
  if status.producer_session_id == last_session and status.sequence < last_sequence:
    return False
  try:
    return (int(model.frameId) == status.model_frame_id and
            int(model.timestampEof) == status.model_timestamp_eof_ns and
            ((status.direction == Direction.LEFT and str(model.meta.laneChangeDirection) == "left") or
             (status.direction == Direction.RIGHT and str(model.meta.laneChangeDirection) == "right")))
  except (AttributeError, TypeError, ValueError):
    return False


def alert_wording(status: LaneChangeStatus | None, model, now_mono_ns: int, recv_mono_ns: int,
                  last_sequence: int = -1, last_session: str = "", message_mono_ns: int | None = None) -> tuple[str, str] | None:
  """None preserves stock manual copy only when a fresh status proves that path."""
  if not fresh_for_model(status, model, now_mono_ns, recv_mono_ns, last_sequence, last_session, message_mono_ns):
    return "Lane Change Pending", "Check surroundings"
  assert status is not None
  return {Phase.MANUAL_REQUIRED: None,
          Phase.WAITING_FOR_DELAY: ("Automatic Lane Change Pending", "Check surroundings; steer to confirm now"),
          Phase.LANE_UNAVAILABLE: ("Automatic Change Unavailable", "Steer to confirm when safe"),
          Phase.BLINDSPOT_BLOCKED: ("Car Detected in Blindspot", "")}[status.phase]
