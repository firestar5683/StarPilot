#!/usr/bin/env python3
"""Build the aligned EV9 stock BSM CAN/label dataset from stock rlogs.

The output schema is the input contract of ``analyze_ev9_bsm_fusion.py`` and
``extract_ev9_model_geometry.py``. It samples at every native 0x1BA update and
stores the latest retained payload for each selected CAN address.

Example:

  .venv/bin/python tools/ev9_longitudinal/extract_ev9_bsm_can_labels.py \
    --rlog-root /Users/brenrid/Code/EV9-Route-References/stock-rlogs \
    --output /tmp/ev9_bsm_stock.npz
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np

from opendbc.can import CANParser
from openpilot.tools.lib.logreader import LogReader


ROUTE_DIRECTORY_RE = re.compile(r"(?P<route>[^-]+)--.+--(?P<segment>\d+)$")
LABEL_MESSAGE = "BLINDSPOTS_REAR_CORNERS"
LABEL_ADDRESS = 0x1BA
LABEL_BUS = 1
LABEL_SIGNALS = (
  "BCW_Sta", "BCW_OnOffEquipSta", "BCW_LtIndSta", "BCW_RtIndSta",
  "BCW_LtSndWrngSta", "BCW_RtSndWrngSta", "FL_INDICATOR", "FR_INDICATOR",
  "BCW_SnstvtyModRetVal", "BCW_IndSta", "BCA_OnOffEquip2Sta", "BCA_Sta",
  "BCA_OnOffEquipSta", "BCA_DRV_WarnSta", "BCA_Plus_Deccel_Req",
  "BCA_Plus_BrkCmdSta", "BCA_Plus_LtWrngSta", "BCA_Plus_RtWrngSta",
  "BCA_Plus_FuncStat", "BCA_Plus_Sta", "Brake_Control_RL", "Brake_Control_RR",
  "OSMrrLamp_LtIndSta", "OSMrrLamp_RtIndSta",
)


@dataclass(frozen=True)
class PayloadGroup:
  name: str
  bus: int
  addresses: range
  byte_indexes: range
  expected_length: int


# Bytes 0..2 are transport integrity/counter fields and were deliberately
# omitted from the original mining dataset. The remaining bytes are retained
# verbatim; signal decoding happens in analyze_ev9_bsm_fusion.py.
PAYLOAD_GROUPS = (
  PayloadGroup("corner", 2, range(0x235, 0x249), range(3, 32), 32),
  PayloadGroup("mrr35", 0, range(0x3A5, 0x3C5), range(3, 24), 24),
  PayloadGroup("front1", 1, range(0x1E5, 0x1E6), range(3, 16), 16),
  PayloadGroup("front2", 1, range(0x36A, 0x36B), range(3, 16), 16),
)


def feature_names() -> np.ndarray:
  return np.asarray([
    f"{group.name}:b{group.bus}:0x{address:x}:byte{byte_index}"
    for group in PAYLOAD_GROUPS
    for address in group.addresses
    for byte_index in group.byte_indexes
  ])


def payload_names() -> np.ndarray:
  return np.asarray([
    f"{group.name}:b{group.bus}:0x{address:x}"
    for group in PAYLOAD_GROUPS
    for address in group.addresses
  ])


def discover_rlogs(root: Path) -> tuple[list[str], list[tuple[int, int, Path]]]:
  """Return lexicographically ordered route directories and stable indices.

  Directory ordering intentionally remains lexical (0, 1, 10, ..., 2, ...),
  matching ``sorted(Path.rglob())`` and the original analysis artifact. Segment
  boundaries make ordering irrelevant to temporal features, but stable ordering
  makes regenerated arrays directly comparable.
  """
  found: list[tuple[str, int, Path]] = []
  for rlog in sorted(root.glob("*/rlog.zst")):
    match = ROUTE_DIRECTORY_RE.fullmatch(rlog.parent.name)
    if match is None:
      continue
    found.append((match.group("route"), int(match.group("segment")), rlog))
  if not found:
    raise RuntimeError(f"no route directories containing rlog.zst found below {root}")
  route_names = sorted({route for route, _, _ in found})
  route_index = {route: index for index, route in enumerate(route_names)}
  return route_names, [(route_index[route], segment, path) for route, segment, path in found]


def snapshot_payloads(latest: dict[tuple[int, int], bytes]) -> bytearray:
  row = bytearray()
  for group in PAYLOAD_GROUPS:
    zero = bytes(group.expected_length)
    for address in group.addresses:
      payload = latest.get((group.bus, address), zero)
      # Malformed/truncated frames are not allowed to shift the fixed schema.
      if len(payload) < group.expected_length:
        payload = payload + bytes(group.expected_length - len(payload))
      row.extend(payload[index] for index in group.byte_indexes)
  return row


def car_state_values(car_state) -> tuple[float, ...]:
  if car_state is None:
    return (0.0,) * 8
  return (
    float(car_state.vEgo),
    float(car_state.aEgo),
    float(car_state.steeringAngleDeg),
    float(car_state.steeringRateDeg),
    float(car_state.steeringTorque),
    float(car_state.yawRate),
    float(car_state.leftBlinker),
    float(car_state.rightBlinker),
  )


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("--rlog-root", type=Path, required=True)
  parser.add_argument("--output", type=Path, required=True)
  parser.add_argument("--expected-rlogs", type=int, default=72,
                      help="fail if the discovered corpus size differs; use 0 to disable")
  args = parser.parse_args()

  route_names, rlogs = discover_rlogs(args.rlog_root)
  if args.expected_rlogs and len(rlogs) != args.expected_rlogs:
    raise RuntimeError(f"expected {args.expected_rlogs} rlogs, found {len(rlogs)}")

  rows: list[bytearray] = []
  labels: list[tuple[int, int]] = []
  route_indices: list[int] = []
  segments: list[int] = []
  times: list[int] = []
  vehicle_states: list[tuple[float, ...]] = []
  boundaries: list[bool] = []
  label_values: list[tuple[int, ...]] = []
  label_payloads: list[bytes] = []
  payload_presence: list[tuple[bool, ...]] = []
  car_state_valid: list[bool] = []

  target_keys = {
    (group.bus, address)
    for group in PAYLOAD_GROUPS
    for address in group.addresses
  }

  for route_index, segment, rlog in rlogs:
    # Logs are independently decodable. Resetting prevents a payload or parsed
    # label from a lexically previous segment leaking across a boundary.
    latest: dict[tuple[int, int], bytes] = {}
    label_parser = CANParser("hyundai_canfd_generated", [(LABEL_MESSAGE, 0)], LABEL_BUS)
    current_car_state = None
    segment_rows = 0

    for event in LogReader(str(rlog), sort_by_time=False):
      which = event.which()
      if which == "carState":
        current_car_state = event.carState
        continue
      if which != "can":
        continue

      now = int(event.logMonoTime)
      frames: list[tuple[int, bytes, int]] = []
      label_payload: bytes | None = None
      for frame in event.can:
        bus = int(frame.src)
        # Returned Panda frames have src >= 128 and are not vehicle receive
        # traffic. Including them could overwrite an OEM payload with our TX.
        if bus >= 128:
          continue
        address = int(frame.address)
        payload = bytes(frame.dat)
        frames.append((address, payload, bus))
        if bus == LABEL_BUS and address == LABEL_ADDRESS:
          label_payload = payload
        if (bus, address) in target_keys:
          latest[(bus, address)] = payload

      if LABEL_ADDRESS not in label_parser.update([now, frames]):
        continue
      values = label_parser.vl[LABEL_MESSAGE]
      rows.append(snapshot_payloads(latest))
      payload_presence.append(tuple(
        (group.bus, address) in latest
        for group in PAYLOAD_GROUPS
        for address in group.addresses
      ))
      labels.append((int(values["BCW_LtIndSta"] in (1, 2)),
                     int(values["BCW_RtIndSta"] in (1, 2))))
      label_values.append(tuple(int(values[name]) for name in LABEL_SIGNALS))
      payload = label_payload or bytes(24)
      label_payloads.append((payload + bytes(24))[:24])
      route_indices.append(route_index)
      segments.append(segment)
      times.append(now)
      vehicle_states.append(car_state_values(current_car_state))
      car_state_valid.append(current_car_state is not None)
      boundaries.append(segment_rows == 0)
      segment_rows += 1

    print(f"{route_names[route_index]} segment {segment:02d}: {segment_rows} samples")

  names = feature_names()
  x = np.asarray(rows, dtype=np.uint8)
  if x.ndim != 2 or x.shape[1] != len(names):
    raise RuntimeError(f"payload schema mismatch: data {x.shape}, names {names.shape}")

  np.savez_compressed(
    args.output,
    X=x,
    Y=np.asarray(labels, dtype=np.uint8),
    routes=np.asarray(route_indices, dtype=np.uint8),
    segs=np.asarray(segments, dtype=np.uint8),
    times=np.asarray(times, dtype=np.int64),
    car=np.asarray(vehicle_states, dtype=np.float32),
    boundaries=np.asarray(boundaries, dtype=bool),
    features=names,
    route_names=np.asarray(route_names),
    label_values=np.asarray(label_values, dtype=np.uint16),
    label_features=np.asarray(LABEL_SIGNALS),
    label_raw=np.asarray([list(payload) for payload in label_payloads], dtype=np.uint8),
    payload_presence=np.asarray(payload_presence, dtype=bool),
    payload_names=payload_names(),
    car_state_valid=np.asarray(car_state_valid, dtype=bool),
  )
  summary = f"wrote {args.output}: X={x.shape}, left={sum(y[0] for y in labels)}, "
  summary += f"right={sum(y[1] for y in labels)}, routes={len(route_names)}, rlogs={len(rlogs)}"
  print(summary)


if __name__ == "__main__":
  main()
