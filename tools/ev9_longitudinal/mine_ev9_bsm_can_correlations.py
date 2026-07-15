#!/usr/bin/env python3
"""Mine route-stable CAN bit correlations with native EV9 BSM lamps.

Unlike the focused BSM NPZ, this scans every received CAN address. Each bit
and its inverse are scored independently on every stock route. Candidates are
ranked by their weakest positive-route F1 and penalized for firing on routes
with no positive examples. A high score is evidence for further decoding, not
proof of causality; ADAS-originated messages must still be rejected if they
disappear after transmit suppression.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import sys

import numpy as np

from opendbc.can import CANParser
from openpilot.tools.lib.logreader import LogReader


ROUTE_DIRECTORY_RE = re.compile(r"(?P<route>[^-]+)--.+--(?P<segment>\d+)$")
LABEL_MESSAGE = "BLINDSPOTS_REAR_CORNERS"
LABEL_ADDRESS = 0x1BA
LABEL_BUS = 1


@dataclass
class AddressStats:
  length: int
  # Dimensions: side, truth state, byte, bit.
  ones: np.ndarray
  # Dimensions: side, truth state.
  present: np.ndarray

  @classmethod
  def create(cls, length: int) -> AddressStats:
    return cls(length, np.zeros((2, 2, length, 8), dtype=np.uint32),
               np.zeros((2, 2), dtype=np.uint32))


@dataclass(frozen=True)
class Candidate:
  bus: int
  address: int
  length: int
  byte: int
  bit: int
  value: int
  pooled_precision: float
  pooled_recall: float
  pooled_f1: float
  min_route_precision: float
  min_route_recall: float
  min_route_f1: float
  max_negative_route_on_fraction: float
  min_presence: float
  route_metrics: tuple[tuple[str, float, float, float, float], ...]


def discover_rlogs(root: Path) -> tuple[list[str], list[tuple[int, int, Path]]]:
  found: list[tuple[str, int, Path]] = []
  for rlog in sorted(root.glob("*/rlog.zst")):
    match = ROUTE_DIRECTORY_RE.fullmatch(rlog.parent.name)
    if match is not None:
      found.append((match.group("route"), int(match.group("segment")), rlog))
  if not found:
    raise RuntimeError(f"no stock rlogs below {root}")
  route_names = sorted({route for route, _, _ in found})
  route_index = {route: index for index, route in enumerate(route_names)}
  return route_names, [(route_index[route], segment, path) for route, segment, path in found]


def _f1(precision: float, recall: float) -> float:
  return 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0


def mine(root: Path) -> tuple[list[str], np.ndarray, list[dict[tuple[int, int], AddressStats]]]:
  route_names, rlogs = discover_rlogs(root)
  totals = np.zeros((len(route_names), 2, 2), dtype=np.uint32)
  route_stats: list[dict[tuple[int, int], AddressStats]] = [dict() for _ in route_names]

  for route_index, segment, rlog in rlogs:
    latest: dict[tuple[int, int], bytes] = {}
    label_parser = CANParser("hyundai_canfd_generated", [(LABEL_MESSAGE, 0)], LABEL_BUS)
    samples = 0
    for event in LogReader(str(rlog), sort_by_time=False):
      if event.which() != "can":
        continue
      now = int(event.logMonoTime)
      frames: list[tuple[int, bytes, int]] = []
      for frame in event.can:
        bus = int(frame.src)
        if bus >= 128:
          continue
        address = int(frame.address)
        payload = bytes(frame.dat)
        frames.append((address, payload, bus))
        latest[(bus, address)] = payload

      if LABEL_ADDRESS not in label_parser.update([now, frames]):
        continue
      values = label_parser.vl[LABEL_MESSAGE]
      truth = (int(values["BCW_LtIndSta"] in (1, 2)), int(values["BCW_RtIndSta"] in (1, 2)))
      for side in range(2):
        totals[route_index, side, truth[side]] += 1

      stats_for_route = route_stats[route_index]
      for key, payload in latest.items():
        stats = stats_for_route.get(key)
        if stats is None or stats.length != len(payload):
          # CAN-FD lengths are stable in the corpus. If a malformed frame has
          # a different length, retain the most common/longest representation.
          if stats is not None and stats.length > len(payload):
            continue
          stats = AddressStats.create(len(payload))
          stats_for_route[key] = stats
        bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8), bitorder="little").reshape(len(payload), 8)
        for side in range(2):
          state = truth[side]
          stats.present[side, state] += 1
          stats.ones[side, state] += bits
      samples += 1
    print(f"{route_names[route_index]} segment {segment:02d}: {samples} labels", file=sys.stderr)
  return route_names, totals, route_stats


def recurring_messages(root: Path, minimum_frames: int) -> set[tuple[int, int, int]]:
  """Return messages that recur after suppression, excluding boot-only traffic."""
  counts: Counter[tuple[int, int, int]] = Counter()
  for rlog in sorted(root.glob("*/rlog.zst")):
    for event in LogReader(str(rlog), sort_by_time=False):
      if event.which() != "can":
        continue
      for frame in event.can:
        bus = int(frame.src)
        if bus < 128:
          counts[(bus, int(frame.address), len(frame.dat))] += 1
  return {key for key, count in counts.items() if count >= minimum_frames}


def candidates_for_side(route_names: list[str], totals: np.ndarray,
                        route_stats: list[dict[tuple[int, int], AddressStats]], side: int,
                        min_presence: float,
                        recurring_after_suppression: set[tuple[int, int, int]] | None = None) -> list[Candidate]:
  keys = sorted(set().union(*(stats.keys() for stats in route_stats)))
  candidates: list[Candidate] = []
  for bus, address in keys:
    if (bus, address) == (LABEL_BUS, LABEL_ADDRESS):
      continue
    lengths = [stats[(bus, address)].length for stats in route_stats if (bus, address) in stats]
    if not lengths:
      continue
    length = max(set(lengths), key=lengths.count)
    if recurring_after_suppression is not None and (bus, address, length) not in recurring_after_suppression:
      continue
    for byte in range(length):
      for bit in range(8):
        for value in (0, 1):
          route_rows: list[tuple[str, float, float, float, float]] = []
          pooled_tp = pooled_fp = pooled_fn = 0
          positive_precision: list[float] = []
          positive_recall: list[float] = []
          positive_f1: list[float] = []
          negative_on: list[float] = []
          presence_fractions: list[float] = []
          valid = True
          for route_index, route_name in enumerate(route_names):
            stats = route_stats[route_index].get((bus, address))
            total_off, total_on = (int(v) for v in totals[route_index, side])
            total = total_off + total_on
            if stats is None or stats.length != length or total == 0:
              valid = False
              break
            present = int(stats.present[side].sum())
            presence = present / total
            presence_fractions.append(presence)
            if presence < min_presence:
              valid = False
              break
            ones_off = int(stats.ones[side, 0, byte, bit])
            ones_on = int(stats.ones[side, 1, byte, bit])
            if value:
              tp, fp = ones_on, ones_off
            else:
              tp = int(stats.present[side, 1]) - ones_on
              fp = int(stats.present[side, 0]) - ones_off
            fn = total_on - tp
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / total_on if total_on else 0.0
            f1 = _f1(precision, recall)
            on_fraction = fp / total_off if total_off else 0.0
            route_rows.append((route_name, precision, recall, f1, on_fraction))
            pooled_tp += tp
            pooled_fp += fp
            pooled_fn += fn
            if total_on:
              positive_precision.append(precision)
              positive_recall.append(recall)
              positive_f1.append(f1)
            else:
              negative_on.append(on_fraction)
          if not valid or not positive_f1:
            continue
          pooled_precision = pooled_tp / (pooled_tp + pooled_fp) if pooled_tp + pooled_fp else 0.0
          pooled_recall = pooled_tp / (pooled_tp + pooled_fn) if pooled_tp + pooled_fn else 0.0
          candidates.append(Candidate(
            bus, address, length, byte, bit, value,
            pooled_precision, pooled_recall, _f1(pooled_precision, pooled_recall),
            min(positive_precision), min(positive_recall), min(positive_f1),
            max(negative_on, default=0.0), min(presence_fractions), tuple(route_rows),
          ))
  return sorted(candidates, key=lambda item: (
    item.min_route_f1 - item.max_negative_route_on_fraction,
    item.min_route_f1, item.pooled_f1,
  ), reverse=True)


def print_candidates(candidates: list[Candidate], limit: int) -> None:
  print("bus addr   len byte bit=value  pooled P/R/F1   min-route P/R/F1  neg-route-on presence  per-route F1")
  for item in candidates[:limit]:
    pooled = f"{item.pooled_precision:.3f}/{item.pooled_recall:.3f}/{item.pooled_f1:.3f}"
    minimum = f"{item.min_route_precision:.3f}/{item.min_route_recall:.3f}/{item.min_route_f1:.3f}"
    routes = ",".join(f"{name}:{f1:.3f}" for name, _, _, f1, _ in item.route_metrics)
    row = f"{item.bus:3d} 0x{item.address:03x} {item.length:3d} {item.byte:4d} {item.bit}={item.value}   "
    row += f"{pooled:17s} {minimum:18s} {item.max_negative_route_on_fraction:12.4f} "
    row += f"{item.min_presence:8.4f}  {routes}"
    print(row)


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--rlog-root", type=Path, required=True)
  parser.add_argument("--side", choices=("left", "right", "both"), default="both")
  parser.add_argument("--limit", type=int, default=40)
  parser.add_argument("--min-presence", type=float, default=0.995)
  parser.add_argument("--availability-rlog-root", type=Path,
                      help="post-suppression rlogs; discard messages that do not recur there")
  parser.add_argument("--min-availability-frames", type=int, default=1000,
                      help="minimum post-suppression frames across the supplied corpus")
  args = parser.parse_args()

  route_names, totals, route_stats = mine(args.rlog_root)
  available = recurring_messages(args.availability_rlog_root, args.min_availability_frames) \
    if args.availability_rlog_root is not None else None
  if available is not None:
    print(f"\npost-suppression recurring message schemas: {len(available)}")
  sides = (0, 1) if args.side == "both" else (0 if args.side == "left" else 1,)
  for side in sides:
    print(f"\n=== {('left', 'right')[side]} ===")
    candidates = candidates_for_side(route_names, totals, route_stats, side, args.min_presence, available)
    print_candidates(candidates, args.limit)


if __name__ == "__main__":
  main()
