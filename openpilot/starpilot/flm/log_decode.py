"""Bounded, all-or-nothing decode of an already admitted local log segment."""

import bz2
import io
from collections.abc import Callable
from typing import Any

import zstandard as zstd

from openpilot.cereal import log


MAX_COMPRESSED_BYTES = 32 * 1024 * 1024
MAX_EXPANDED_BYTES = 64 * 1024 * 1024
MAX_MESSAGES = 250_000
EVENT_TRAVERSAL_WORDS = 1_000_000
CHUNK_BYTES = 64 * 1024


class LogDecodeError(ValueError):
  """The whole segment is unavailable; callers must discard every event."""


def _not_cancelled(cancelled: Callable[[], bool]) -> None:
  try:
    if cancelled():
      raise LogDecodeError("segment decode cancelled")
  except LogDecodeError:
    raise
  except Exception as error:
    raise LogDecodeError("segment cancellation check unavailable") from error


def _bounded_read(reader: Any, cancelled: Callable[[], bool]) -> bytes:
  chunks: list[bytes] = []
  total = 0
  while True:
    _not_cancelled(cancelled)
    chunk = reader.read(min(CHUNK_BYTES, MAX_EXPANDED_BYTES + 1 - total))
    if not chunk:
      break
    total += len(chunk)
    if total > MAX_EXPANDED_BYTES:
      raise LogDecodeError("expanded segment exceeds 64 MiB")
    chunks.append(chunk)
  return b"".join(chunks)


def _expand(data: bytes, codec: str, cancelled: Callable[[], bool]) -> bytes:
  try:
    if codec == "zst":
      with zstd.ZstdDecompressor(max_window_size=MAX_EXPANDED_BYTES).stream_reader(io.BytesIO(data)) as reader:
        expanded = _bounded_read(reader, cancelled)
      # stream_reader in pinned zstandard 0.25 returns short data for a
      # truncated frame. Validate the complete frame after proving its output
      # fits our bound, and reject a concatenated/trailing second frame.
      decoder = zstd.ZstdDecompressor(max_window_size=MAX_EXPANDED_BYTES).decompressobj()
      verified = decoder.decompress(data)
      if not decoder.eof or decoder.unused_data or verified != expanded:
        raise LogDecodeError("incomplete or trailing zstd frame")
    elif codec == "bz2":
      with bz2.BZ2File(io.BytesIO(data), "rb") as reader:
        expanded = _bounded_read(reader, cancelled)
      decoder = bz2.BZ2Decompressor()
      verified = decoder.decompress(data)
      if not decoder.eof or decoder.unused_data or verified != expanded:
        raise LogDecodeError("incomplete or trailing bzip2 stream")
    else:
      raise LogDecodeError("unsupported segment compression")
    _not_cancelled(cancelled)
    return expanded
  except LogDecodeError:
    raise
  except (OSError, EOFError, ValueError, zstd.ZstdError) as error:
    raise LogDecodeError("corrupt or incomplete compressed segment") from error


def decode_segment(data: bytes, codec: str, *, cancelled: Callable[[], bool] = lambda: False,
                   retain: frozenset[str] | None = None) -> tuple[Any, ...]:
  """Return all complete Event readers, or reject the entire segment."""
  if type(data) is not bytes or len(data) > MAX_COMPRESSED_BYTES or type(codec) is not str or \
     codec not in ("zst", "bz2"):
    raise LogDecodeError("unsupported or oversized compressed segment")
  _not_cancelled(cancelled)
  expanded = _expand(data, codec, cancelled)
  events: list[Any] = []
  try:
    for count, event in enumerate(log.Event.read_multiple_bytes(expanded, traversal_limit_in_words=EVENT_TRAVERSAL_WORDS)):
      _not_cancelled(cancelled)
      if count >= MAX_MESSAGES:
        raise LogDecodeError("segment message count exceeded")
      # Force envelope and union decoding before a reader can escape; a later
      # malformed record invalidates the entire segment, never a prefix.
      int(event.logMonoTime)
      kind = event.which()
      if retain is None or kind in retain:
        events.append(event)
  except LogDecodeError:
    raise
  except Exception as error:
    raise LogDecodeError("corrupt Cereal Event segment") from error
  _not_cancelled(cancelled)
  return tuple(events)
