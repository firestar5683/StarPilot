#!/usr/bin/env python3
import json
import os
import signal
import subprocess
import sys
import time

from collections import defaultdict, deque
from pathlib import Path

from openpilot.common.basedir import BASEDIR
from openpilot.common.swaglog import cloudlog

MAPD_DIR = Path(BASEDIR) / "frogpilot/navigation"
MAPD_BIN = MAPD_DIR / "mapd"
OFFLINE_ROOT = Path("/data/media/0/osm/offline")
RESTART_DELAY_S = 0.25
FAILURE_WINDOW_S = 3.0
FAILURE_THRESHOLD = 3


def extract_bounds_filename(line: str) -> str | None:
  try:
    payload = json.loads(line)
  except json.JSONDecodeError:
    return None

  if payload.get("msg") != "Loading bounds file":
    return None

  filename = payload.get("filename")
  return filename if isinstance(filename, str) else None


def is_offline_read_error(line: str) -> bool:
  try:
    payload = json.loads(line)
  except json.JSONDecodeError:
    return False

  return payload.get("msg") == "could not unmarshal offline data"


class CorruptTileMonitor:
  def __init__(self, threshold: int = FAILURE_THRESHOLD, window_s: float = FAILURE_WINDOW_S):
    self.threshold = threshold
    self.window_s = window_s
    self.current_filename: str | None = None
    self.failures: dict[str, deque[float]] = defaultdict(deque)

  def observe(self, line: str, now: float | None = None) -> str | None:
    filename = extract_bounds_filename(line)
    if filename is not None:
      self.current_filename = filename
      return None

    if not is_offline_read_error(line) or self.current_filename is None:
      return None

    ts = time.monotonic() if now is None else now
    failures = self.failures[self.current_filename]
    failures.append(ts)

    cutoff = ts - self.window_s
    while failures and failures[0] < cutoff:
      failures.popleft()

    if len(failures) >= self.threshold:
      return self.current_filename
    return None


def quarantine_offline_tile(filename: str) -> Path | None:
  tile_path = Path(filename)
  try:
    tile_path.relative_to(OFFLINE_ROOT)
  except ValueError:
    cloudlog.warning(f"mapd_wrapper refusing to quarantine unexpected path: {filename}")
    return None

  if not tile_path.exists():
    return None

  quarantined = tile_path.with_name(f"{tile_path.name}.corrupt.{int(time.time())}")
  tile_path.rename(quarantined)
  return quarantined


def terminate_child(proc: subprocess.Popen[str]) -> None:
  if proc.poll() is not None:
    return

  proc.terminate()
  try:
    proc.wait(timeout=2)
  except subprocess.TimeoutExpired:
    proc.kill()
    proc.wait(timeout=2)


def run_mapd_once() -> int:
  proc = subprocess.Popen(
    [MAPD_BIN.as_posix()],
    cwd=MAPD_DIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
  )
  assert proc.stdout is not None

  def _handle_signal(signum, _frame):
    terminate_child(proc)
    raise SystemExit(128 + signum)

  signal.signal(signal.SIGTERM, _handle_signal)
  signal.signal(signal.SIGINT, _handle_signal)

  monitor = CorruptTileMonitor()

  for line in proc.stdout:
    print(line, end="")
    bad_tile = monitor.observe(line)
    if bad_tile is None:
      continue

    quarantined = quarantine_offline_tile(bad_tile)
    if quarantined is None:
      cloudlog.warning(f"mapd_wrapper detected repeated offline read failures for {bad_tile}, but could not quarantine it")
    else:
      message = f"mapd_wrapper quarantined corrupt offline tile: {bad_tile} -> {quarantined}"
      print(message, flush=True)
      cloudlog.warning(message)

    terminate_child(proc)
    return 1

  return proc.wait()


def main() -> None:
  while True:
    exit_code = run_mapd_once()
    if exit_code == 1:
      time.sleep(RESTART_DELAY_S)
      continue
    raise SystemExit(exit_code)


if __name__ == "__main__":
  main()
