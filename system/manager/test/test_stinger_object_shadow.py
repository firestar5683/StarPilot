import ast
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from openpilot.starpilot.system.stinger_object_shadow import LOG_INTERVAL_NS, MAX_OBJECT_AGE_NS, PLATFORM, StingerObjectShadow
from openpilot.starpilot.system.stinger_object_tracks import (
  MAX_EGO_AGE_NS, MAX_TRIPLET_SPAN_NS, SLOT_COUNT, START_ADDRESS, StingerObjectDecoder, decode_triplet,
)


ROOT = Path(__file__).resolve().parents[3]
RUNTIME_FILES = ("starpilot/system/stinger_object_shadow.py", "starpilot/system/stinger_object_tracks.py")
DEPARTING = tuple(bytes.fromhex(dat) for dat in ("06ca7fcb8379f530", "8fc973d946180b18", "89504654ffe604e8"))
FOLLOWING = tuple(bytes.fromhex(dat) for dat in ("0f82804b8ea5ed30", "4fb978814578ff98", "49604825ffe604e8"))
LANE_EXIT = tuple(bytes.fromhex(dat) for dat in ("15f2843b9a71f62e", "106c7fc94608ff97", "19f446f7ffe5c4e8"))
STOPPED = tuple(bytes.fromhex(dat) for dat in ("01f27fdb7d09f412", "90746b3b45d80009", "8978473573024538"))
T = 1_000_000_000


def triplet(collector, timestamp=T, slot=0, payloads=DEPARTING):
  for part, dat in enumerate(payloads):
    collector.update_can(timestamp, START_ADDRESS + slot * 3 + part, dat, 1)


@pytest.mark.parametrize("slot,payloads,object_id,distance,lateral,speed", [
  (0, DEPARTING, 24, 10.85, -0.2, 5.15),
  (0, FOLLOWING, 24, 24.8, 0.2, 14.1),
  (1, LANE_EXIT, 23, 35.1, 3.35, 23.55),
  (9, STOPPED, 9, 3.1, -0.15, 0.0),
])
def test_logged_triplets(slot, payloads, object_id, distance, lateral, speed):
  obj = decode_triplet(slot, payloads)
  assert obj is not None
  assert obj.slot == slot
  assert obj.object_id == object_id
  assert obj.distance == pytest.approx(distance)
  assert obj.lateral_raw == pytest.approx(lateral)
  assert obj.absolute_speed == pytest.approx(speed)


def test_speed_is_absolute_and_requires_finite_ego_speed():
  assert decode_triplet(0, FOLLOWING).relative_speed(14.0) == pytest.approx(0.1)
  assert decode_triplet(0, STOPPED).relative_speed(12.0) == pytest.approx(-12.0)
  for invalid in (math.nan, math.inf, -math.inf):
    with pytest.raises(ValueError, match="finite"):
      decode_triplet(0, FOLLOWING).relative_speed(invalid)


@pytest.mark.parametrize("part,byte,mask", [(1, 0, 64), (2, 0, 64), (1, 7, 1), (2, 6, 64)])
def test_mixed_cycle_or_object_id_is_rejected(part, byte, mask):
  payloads = list(DEPARTING)
  changed = bytearray(payloads[part])
  changed[byte] ^= mask
  payloads[part] = bytes(changed)
  assert decode_triplet(0, tuple(payloads)) is None


@pytest.mark.parametrize("slot,payloads", [
  (-1, DEPARTING), (SLOT_COUNT, DEPARTING), (0, DEPARTING[:2]),
  (0, (b"", *DEPARTING[1:])), (0, (bytes(8),) * 3),
])
def test_invalid_or_empty_triplets_are_rejected(slot, payloads):
  assert decode_triplet(slot, payloads) is None


@pytest.mark.parametrize("bus", [0, 2, 128, 129, 130])
def test_other_buses_and_transmit_echoes_are_ignored(bus):
  decoder = StingerObjectDecoder()
  for part, dat in enumerate(DEPARTING):
    assert decoder.update(T, START_ADDRESS + part, dat, bus) is None
  assert decoder.frames == {}


def test_complete_fresh_triplets_are_consumed_once():
  decoder = StingerObjectDecoder()
  assert decoder.update(T, START_ADDRESS, DEPARTING[0], 1) is None
  assert decoder.update(T + 1, START_ADDRESS + 1, DEPARTING[1], 1) is None
  assert decoder.update(T + 2, START_ADDRESS + 2, DEPARTING[2], 1).object_id == 24
  assert decoder.frames == {}
  assert decoder.update(T + 3, START_ADDRESS + 2, DEPARTING[2], 1) is None
  assert decoder.update(T + 3, START_ADDRESS + 30, DEPARTING[0], 1) is None
  assert decoder.update(T + 3, START_ADDRESS, b"", 1) is None


@pytest.mark.parametrize("first,last", [(T, T + MAX_TRIPLET_SPAN_NS + 1), (T + 1, T)])
def test_wrapped_counter_cannot_reuse_stale_or_future_frames(first, last):
  decoder = StingerObjectDecoder()
  assert decoder.update(first, START_ADDRESS, DEPARTING[0], 1) is None
  assert decoder.update(first, START_ADDRESS + 1, DEPARTING[1], 1) is None
  assert decoder.update(last, START_ADDRESS + 2, DEPARTING[2], 1) is None


def test_shadow_uses_fresh_ego_speed_and_logs_raw_payload_fields():
  collector = StingerObjectShadow(False)
  collector.update_ego(T, 5.0, True, False, 1.0)
  triplet(collector)
  snapshot = collector.snapshot(T)
  assert snapshot["platform"] == PLATFORM
  assert snapshot["shadow_only"]
  obj = snapshot["objects"][0]
  assert obj["object_id"] == 24
  assert obj["ego_timestamp_ns"] == T
  assert obj["relative_speed"] == pytest.approx(0.15)
  json.dumps(snapshot, allow_nan=False)


@pytest.mark.parametrize("ego_timestamp", [None, T - MAX_EGO_AGE_NS - 1, T + 1])
def test_missing_stale_or_future_ego_speed_is_not_guessed(ego_timestamp):
  collector = StingerObjectShadow(False)
  if ego_timestamp is not None:
    collector.update_ego(ego_timestamp, 15.0, True, False, 0.0)
  triplet(collector)
  obj = collector.snapshot(T)["objects"][0]
  assert obj["ego_speed"] is None
  assert obj["relative_speed"] is None


@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_invalid_ego_samples_are_not_logged(invalid):
  collector = StingerObjectShadow(False)
  collector.update_ego(T, invalid, True, False, 0.0)
  collector.update_ego(T, 0.0, True, False, invalid)
  assert collector.snapshot(T)["car_state"] is None


def test_shadow_is_rate_limited_and_expires_objects():
  collector = StingerObjectShadow(False)
  collector.update_ego(T, 5.0, True, False, 0.0)
  triplet(collector)
  assert collector.snapshot(T)["objects"]
  assert collector.snapshot(T + MAX_OBJECT_AGE_NS) is None
  snapshot = collector.snapshot(T + LOG_INTERVAL_NS)
  assert snapshot["objects"] == []
  assert snapshot["car_state"] is None


@pytest.mark.parametrize("alpha_long", [False, True])
def test_self_generated_scc_is_not_an_independent_reference(alpha_long):
  collector = StingerObjectShadow(alpha_long)
  raw = 29_908_004_774_150_145
  collector.update_can(T, 0x420, raw.to_bytes(8, "little"), 0)
  snapshot = collector.snapshot(T)
  assert snapshot["scc11"]["distance"] == pytest.approx(15.0)
  assert snapshot["scc11"]["relative_speed"] == pytest.approx(0.0)
  assert snapshot["scc11_independent_reference"] is not alpha_long


def test_logger_imports_from_git_export_without_tools_or_cached_bytecode(tmp_path):
  runtime = tmp_path / "openpilot"
  for filename in RUNTIME_FILES:
    source = subprocess.check_output(["git", "show", f":{filename}"], cwd=ROOT)
    target = runtime / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source)
  code = """
import sys
sys.path.insert(0, sys.argv[1])
from openpilot.starpilot.system.stinger_object_shadow import StingerObjectShadow
assert StingerObjectShadow(False).snapshot(0)['shadow_only']
assert not any(name.startswith('openpilot.tools') for name in sys.modules)
"""
  subprocess.run([sys.executable, "-I", "-B", "-c", code, str(tmp_path)], cwd=tmp_path,
                 check=True, capture_output=True, text=True)
  assert not list(tmp_path.rglob("*.pyc"))


def test_logger_cannot_publish_control_or_radar_messages():
  for filename in RUNTIME_FILES:
    tree = ast.parse((ROOT / filename).read_text())
    assert not any(isinstance(node, ast.Attribute) and node.attr in ("PubMaster", "pub_sock", "make_can_msg", "send")
                   for node in ast.walk(tree))
