#!/usr/bin/env python3
"""Bounded, receive-only Cereal capture for EV9 preinit and handoff tests.

This intentionally imports no Panda APIs and opens no CAN device. It only
subscribes to messages already published by the running openpilot processes.
The output is a concatenated Cap'n Proto event stream readable by LogReader.
"""

import argparse
import json
import os
from pathlib import Path
import signal
import time

from cereal import log, messaging


DEFAULT_SERVICES = (
  "pandaStates",
  "can",
  "sendcan",
  "carState",
  "carParams",
  "carControl",
  "controlsState",
  "selfdriveState",
  "starpilotCarState",
  "longitudinalPlan",
  "onroadEvents",
  "deviceState",
  "peripheralState",
  "managerState",
)


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("output", type=Path)
  parser.add_argument("--duration", type=float, default=600.0)
  parser.add_argument("--services", nargs="+", default=DEFAULT_SERVICES)
  return parser.parse_args()


def main() -> int:
  args = parse_args()
  args.output.parent.mkdir(parents=True, exist_ok=True)
  metadata_path = args.output.with_suffix(args.output.suffix + ".metadata.json")
  stats_path = args.output.with_suffix(args.output.suffix + ".stats.json")
  markers_path = args.output.with_suffix(args.output.suffix + ".markers.jsonl")

  started_wall_ns = time.time_ns()
  started_mono_ns = time.monotonic_ns()
  metadata = {
    "format": "concatenated-cereal-events-v1",
    "receive_only": True,
    "started_wall_ns": started_wall_ns,
    "started_mono_ns": started_mono_ns,
    "duration_s": args.duration,
    "services": args.services,
    "pid": os.getpid(),
  }
  metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
  markers_path.write_text(json.dumps({
    "event": "capture_started",
    "wall_ns": started_wall_ns,
    "mono_ns": started_mono_ns,
  }) + "\n")

  running = True

  def stop(_signum: int, _frame: object) -> None:
    nonlocal running
    running = False

  signal.signal(signal.SIGINT, stop)
  signal.signal(signal.SIGTERM, stop)

  poller = messaging.Poller()
  sockets = []
  for service in args.services:
    sock = messaging.sub_sock(service, poller=poller, conflate=False)
    sockets.append(sock)

  counts = dict.fromkeys(args.services, 0)
  deadline_ns = started_mono_ns + int(args.duration * 1e9)
  last_flush_ns = started_mono_ns

  with args.output.open("wb", buffering=1024 * 1024) as output:
    while running and time.monotonic_ns() < deadline_ns:
      for sock in poller.poll(100):
        while True:
          event = sock.receive(non_blocking=True)
          if event is None:
            break
          output.write(event)
          with log.Event.from_bytes(event) as message:
            service = message.which()
          if service in counts:
            counts[service] += 1

      now_ns = time.monotonic_ns()
      if now_ns - last_flush_ns >= 1_000_000_000:
        output.flush()
        last_flush_ns = now_ns

    output.flush()
    os.fsync(output.fileno())

  finished_wall_ns = time.time_ns()
  finished_mono_ns = time.monotonic_ns()
  stats_path.write_text(json.dumps({
    **metadata,
    "finished_wall_ns": finished_wall_ns,
    "finished_mono_ns": finished_mono_ns,
    "elapsed_s": (finished_mono_ns - started_mono_ns) / 1e9,
    "bytes": args.output.stat().st_size,
    "counts": counts,
  }, indent=2) + "\n")
  with markers_path.open("a") as markers:
    markers.write(json.dumps({
      "event": "capture_finished",
      "wall_ns": finished_wall_ns,
      "mono_ns": finished_mono_ns,
    }) + "\n")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
