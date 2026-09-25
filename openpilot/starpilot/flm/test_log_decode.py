"""No partial FLM segment success after corrupt compression or Cereal data."""

import bz2
from unittest import mock

import pytest
import zstandard as zstd

from openpilot.cereal import messaging
from openpilot.starpilot.flm import log_decode


def _events() -> bytes:
  first = messaging.new_message("deviceState", valid=True)
  first.logMonoTime = 101
  first.deviceState.started = True
  second = messaging.new_message("carState", valid=False)
  second.logMonoTime = 202
  return first.to_bytes() + second.to_bytes()


def _compressed(raw: bytes, codec: str) -> bytes:
  return zstd.ZstdCompressor().compress(raw) if codec == "zst" else bz2.compress(raw)


@pytest.mark.parametrize("codec", ["zst", "bz2"])
def test_complete_segment_retains_all_event_envelopes_and_timestamps(codec):
  decoded = log_decode.decode_segment(_compressed(_events(), codec), codec)
  assert len(decoded) == 2
  assert [(event.which(), event.logMonoTime, event.valid) for event in decoded] == [
    ("deviceState", 101, True), ("carState", 202, False),
  ]
  assert decoded[0].deviceState.started


@pytest.mark.parametrize("codec", ["zst", "bz2"])
def test_truncated_trailing_and_wrong_codec_reject_entire_segment(codec):
  source = _compressed(_events(), codec)
  for candidate in (source[:-1], source + _compressed(_events(), codec), source + b"trailing"):
    with pytest.raises(log_decode.LogDecodeError):
      log_decode.decode_segment(candidate, codec)
  other = "bz2" if codec == "zst" else "zst"
  with pytest.raises(log_decode.LogDecodeError):
    log_decode.decode_segment(source, other)


def test_expansion_compressed_count_and_cereal_corruption_caps(monkeypatch):
  raw = _events()
  encoded = _compressed(raw, "zst")
  monkeypatch.setattr(log_decode, "MAX_COMPRESSED_BYTES", len(encoded) - 1)
  with pytest.raises(log_decode.LogDecodeError):
    log_decode.decode_segment(encoded, "zst")
  monkeypatch.setattr(log_decode, "MAX_COMPRESSED_BYTES", 32 * 1024 * 1024)
  monkeypatch.setattr(log_decode, "MAX_EXPANDED_BYTES", len(raw) - 1)
  with pytest.raises(log_decode.LogDecodeError):
    log_decode.decode_segment(encoded, "zst")
  monkeypatch.setattr(log_decode, "MAX_EXPANDED_BYTES", 64 * 1024 * 1024)
  monkeypatch.setattr(log_decode, "MAX_MESSAGES", 1)
  with pytest.raises(log_decode.LogDecodeError):
    log_decode.decode_segment(encoded, "zst")
  monkeypatch.setattr(log_decode, "MAX_MESSAGES", 250_000)
  with pytest.raises(log_decode.LogDecodeError):
    log_decode.decode_segment(_compressed(raw + b"not an Event", "zst"), "zst")


def test_cancelled_and_wrong_input_never_return_prefix(monkeypatch):
  encoded = _compressed(_events(), "zst")
  monkeypatch.setattr(log_decode, "CHUNK_BYTES", 8)
  calls = 0
  def cancel():
    nonlocal calls
    calls += 1
    return calls > 3
  with pytest.raises(log_decode.LogDecodeError, match="cancelled"):
    log_decode.decode_segment(encoded, "zst", cancelled=cancel)
  decode = mock.Mock(wraps=log_decode.decode_segment)
  with pytest.raises(log_decode.LogDecodeError):
    decode(bytearray(encoded), "zst")
  with pytest.raises(log_decode.LogDecodeError):
    log_decode.decode_segment(encoded, "raw")


def test_event_traversal_limit_rejects_whole_segment(monkeypatch):
  monkeypatch.setattr(log_decode, "EVENT_TRAVERSAL_WORDS", 1)
  with pytest.raises(log_decode.LogDecodeError, match="Cereal"):
    log_decode.decode_segment(_compressed(_events(), "zst"), "zst")


@pytest.mark.parametrize("codec", ["zst", "bz2"])
def test_filtered_retention_still_validates_entire_segment(codec):
  encoded = _compressed(_events(), codec)
  selected = log_decode.decode_segment(encoded, codec, retain=frozenset(("carState",)))
  assert [(event.which(), event.logMonoTime) for event in selected] == [("carState", 202)]
  with mock.patch.object(log_decode, "MAX_MESSAGES", 1), pytest.raises(log_decode.LogDecodeError, match="message count"):
    log_decode.decode_segment(encoded, codec, retain=frozenset())
  with pytest.raises(log_decode.LogDecodeError):
    log_decode.decode_segment(_compressed(_events() + b"not an Event", codec), codec, retain=frozenset())
