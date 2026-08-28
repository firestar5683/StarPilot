#!/usr/bin/env python3
import json
import signal
import subprocess
import time

from collections import defaultdict, deque
from pathlib import Path

from cereal import messaging
from openpilot.common.basedir import BASEDIR
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.starpilot.common.starpilot_variables import MAPS_PATH

MAPD_DIR = Path(BASEDIR) / "starpilot/navigation"
MAPD_BIN = MAPD_DIR / "mapd"
OFFLINE_ROOT = MAPS_PATH
RESTART_DELAY_S = 0.25
MISSING_TILE_BACKOFF_S = 30.0
FAILURE_WINDOW_S = 3.0
FAILURE_THRESHOLD = 3
MISSING_COVERAGE_EXIT_CODE = 3
WAIT_FOR_GPS_EXIT_CODE = 4
ROAD_STATE_POLL_S = 1.0


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


def is_null_island_tile(filename: str) -> bool:
  try:
    min_lat, min_lon, max_lat, max_lon = (float(value) for value in Path(filename).name.split("_"))
  except (TypeError, ValueError):
    return False

  return min_lat <= 0 <= max_lat and min_lon <= 0 <= max_lon


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

  if not tile_path.is_file():
    return None

  quarantined = tile_path.with_name(f"{tile_path.name}.corrupt.{time.monotonic_ns()}")
  try:
    tile_path.rename(quarantined)
  except OSError:
    cloudlog.exception(f"mapd_wrapper failed to quarantine offline data: {tile_path}")
    return None
  return quarantined


def terminate_child(proc: subprocess.Popen[str]) -> None:
  if proc.poll() is not None:
    return

  proc.terminate()
  try:
    proc.wait(timeout=2)
  except subprocess.TimeoutExpired:
    proc.kill()
    try:
      proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
      cloudlog.error(f"mapd_wrapper child did not exit after kill: pid={proc.pid}")


def run_mapd_once() -> int:
  try:
    OFFLINE_ROOT.mkdir(parents=True, exist_ok=True)
  except PermissionError:
    cloudlog.exception(f"mapd_wrapper cannot create offline directory: {OFFLINE_ROOT}")
    return 2
  except OSError:
    cloudlog.exception(f"mapd_wrapper failed to prepare offline directory: {OFFLINE_ROOT}")
    return 2

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

    # mapd reports an unmarshal failure even when no offline tile is installed.
    # Stop its resulting hot loop until the next onroad process cycle.
    missing_tile = monitor.current_filename
    if is_offline_read_error(line) and missing_tile is not None and not Path(missing_tile).is_file():
      if is_null_island_tile(missing_tile):
        cloudlog.info(f"mapd_wrapper received a location before GPS fix; waiting to restart mapd: {missing_tile}")
        terminate_child(proc)
        return WAIT_FOR_GPS_EXIT_CODE

      cloudlog.info(f"mapd_wrapper has no offline tile for {missing_tile}; stopping mapd until the next drive")
      terminate_child(proc)
      return MISSING_COVERAGE_EXIT_CODE

    if bad_tile is None:
      continue

    quarantined = quarantine_offline_tile(bad_tile)
    if quarantined is None:
      if not OFFLINE_ROOT.exists():
        cloudlog.warning(f"mapd_wrapper detected repeated offline read failures for {bad_tile}, but {OFFLINE_ROOT} does not exist; backing off mapd restarts")
        terminate_child(proc)
        return 2

      cloudlog.warning(f"mapd_wrapper detected repeated offline read failures for {bad_tile}, but could not quarantine it")
    else:
      message = f"mapd_wrapper quarantined corrupt offline tile: {bad_tile} -> {quarantined}"
      print(message, flush=True)
      cloudlog.warning(message)

    terminate_child(proc)
    return 1 if quarantined is not None else 2

  return proc.wait()


def wait_for_road_state_change(params: Params) -> None:
  initial_onroad = params.get_bool("IsOnroad")
  while params.get_bool("IsOnroad") == initial_onroad:
    time.sleep(ROAD_STATE_POLL_S)


def wait_for_gps_fix_or_road_state_change(params: Params, sm=None) -> None:
  initial_onroad = params.get_bool("IsOnroad")
  sm = sm or messaging.SubMaster(["gpsLocationExternal"])

  while params.get_bool("IsOnroad") == initial_onroad:
    sm.update(1000)
    if sm.updated["gpsLocationExternal"] and sm["gpsLocationExternal"].hasFix:
      return


def main() -> None:
  params = Params()
  while True:
    exit_code = run_mapd_once()
    if exit_code == 1:
      time.sleep(RESTART_DELAY_S)
      continue
    if exit_code == 2:
      time.sleep(MISSING_TILE_BACKOFF_S)
      continue
    if exit_code == MISSING_COVERAGE_EXIT_CODE:
      wait_for_road_state_change(params)
      continue
    if exit_code == WAIT_FOR_GPS_EXIT_CODE:
      wait_for_gps_fix_or_road_state_change(params)
      continue
    raise SystemExit(exit_code)


if __name__ == "__main__":
  main()
