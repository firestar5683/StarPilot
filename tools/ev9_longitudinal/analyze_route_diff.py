#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from openpilot.tools.lib.logreader import LogReader


WATCH_ADDRESSES = {
  0x100, 0x110, 0x12A, 0x160, 0x161, 0x162, 0x1A0, 0x1B5, 0x1BA,
  0x1DA, 0x1EA, 0x200, 0x345, 0x362, 0x730,
}
CCNC_FAULTS = (
  "FAULT_FSS", "FAULT_FCA", "FAULT_LSS", "FAULT_SLA", "FAULT_DAW", "FAULT_HBA",
  "FAULT_SCC", "FAULT_LFA", "FAULT_HDA", "FAULT_LCA", "FAULT_HDP", "FAULT_DAS", "FAULT_ESS",
)


@dataclass
class MessageSummary:
  address: int
  bus: int
  size: int
  count: int = 0
  first_nanos: int = 0
  last_nanos: int = 0

  @property
  def frequency_hz(self) -> float:
    duration = (self.last_nanos - self.first_nanos) * 1e-9
    return (self.count - 1) / duration if duration > 0 and self.count > 1 else 0.0


@dataclass
class RouteSummary:
  path: str
  messages: dict[str, MessageSummary]
  ccnc_fault_samples: dict[str, int]
  mrr35_track_frames: int
  mrr35_track_addresses: int


def resolve_log(path: Path) -> Path:
  if path.is_file():
    return path
  for name in ("rlog.zst", "rlog.bz2", "rlog", "qlog.zst", "qlog.bz2", "qlog"):
    candidate = path / name
    if candidate.exists():
      return candidate
  raise FileNotFoundError(f"no log found under {path}")


def summarize(path: Path, include_returned: bool = False) -> RouteSummary:
  log_path = resolve_log(path)
  summaries: dict[tuple[int, int, int], MessageSummary] = {}
  ccnc_fault_samples = Counter()
  mrr35_addresses: set[int] = set()
  mrr35_track_frames = 0

  from opendbc.can.parser import CANParser
  ccnc = CANParser("hyundai_canfd_generated", [("CCNC_0x162", 20)], 1)

  for event in LogReader(str(log_path), sort_by_time=False):
    if event.which() != "can":
      continue

    frames = []
    for can in event.can:
      address, bus, data = int(can.address), int(can.src), bytes(can.dat)
      if not include_returned and bus >= 128:
        continue
      frames.append((address, data, bus))

      key = (address, bus, len(data))
      if key not in summaries:
        summaries[key] = MessageSummary(address, bus, len(data), first_nanos=int(event.logMonoTime))
      summary = summaries[key]
      summary.count += 1
      summary.last_nanos = int(event.logMonoTime)

      if bus == 0 and 0x3A5 <= address <= 0x3C4 and len(data) == 24:
        mrr35_track_frames += 1
        mrr35_addresses.add(address)

    if 0x162 in ccnc.update([int(event.logMonoTime), frames]):
      values = ccnc.vl["CCNC_0x162"]
      for fault in CCNC_FAULTS:
        if values[fault] != 0:
          ccnc_fault_samples[fault] += 1

  keyed = {f"0x{s.address:03X}/bus{s.bus}/{s.size}": s for s in summaries.values()}
  return RouteSummary(str(log_path), keyed, dict(ccnc_fault_samples), mrr35_track_frames, len(mrr35_addresses))


def print_summary(label: str, summary: RouteSummary) -> None:
  print(f"{label}: {summary.path}")
  if Path(summary.path).name.startswith("qlog"):
    print("  WARNING: qlog is downsampled; use rlog for message-rate and MRR35 coverage decisions")
  print(f"  MRR35: {summary.mrr35_track_addresses}/32 addresses, {summary.mrr35_track_frames} frames")
  print(f"  CCNC faults: {summary.ccnc_fault_samples or 'none'}")
  for item in sorted(summary.messages.values(), key=lambda value: (value.bus, value.address)):
    if item.address in WATCH_ADDRESSES or 0x3A5 <= item.address <= 0x3C4:
      print(f"  0x{item.address:03X} bus={item.bus} len={item.size} count={item.count} hz={item.frequency_hz:.1f}")


def print_diff(before: RouteSummary, after: RouteSummary) -> None:
  print("changed/disappeared messages:")
  for key in sorted(set(before.messages) | set(after.messages)):
    left = before.messages.get(key)
    right = after.messages.get(key)
    left_hz = left.frequency_hz if left else 0.0
    right_hz = right.frequency_hz if right else 0.0
    ratio = right_hz / left_hz if left_hz > 0 else float("inf")
    address = (left or right).address
    if address in WATCH_ADDRESSES or ratio < 0.8 or ratio > 1.2:
      print(f"  {key}: {left_hz:.1f} Hz -> {right_hz:.1f} Hz")


def to_json(summary: RouteSummary) -> dict:
  data = asdict(summary)
  for key, message in summary.messages.items():
    data["messages"][key]["frequency_hz"] = message.frequency_hz
  return data


def main() -> None:
  parser = argparse.ArgumentParser(description="Compare EV9 CAN traffic before and after ADAS_DRV transmit-disable.")
  parser.add_argument("before", type=Path, help="Baseline rlog/qlog file or segment directory")
  parser.add_argument("after", type=Path, nargs="?", help="Post-disable rlog/qlog file or segment directory")
  parser.add_argument("--include-returned", action="store_true", help="Include Panda returned/forwarded buses (>=128)")
  parser.add_argument("--json", action="store_true")
  args = parser.parse_args()

  before = summarize(args.before, args.include_returned)
  after = summarize(args.after, args.include_returned) if args.after else None
  if args.json:
    print(json.dumps({"before": to_json(before), "after": to_json(after) if after else None}, indent=2))
    return

  print_summary("before", before)
  if after:
    print_summary("after", after)
    print_diff(before, after)


if __name__ == "__main__":
  main()
