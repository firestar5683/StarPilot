"""Device state for an Android Auto bug report, gathered when the log bundle is downloaded.

A session log says what StarPilot saw; this says what the rest of the device was doing at the time:
NetworkManager, wpa_supplicant and bluetoothd journals, kernel messages (Wi-Fi and Bluetooth drivers),
the running build, CPU and memory pressure, and the Wi-Fi link. Every command starts at once and the
whole collection has one deadline, so a hung journal or D-Bus tool costs at most that long and is
recorded as timed out instead of failing the download. Hardware addresses are masked to their last
byte, which still tells devices apart without identifying them.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

DEADLINE_SECONDS = 8.0
OUTPUT_LIMIT = 2 << 20       # the tail of each command's output kept in the bundle
JOURNAL_LINES = 20000
DEFAULT_WINDOW_SECONDS = 3 * 3600
MAX_WINDOW_SECONDS = 24 * 3600
WINDOW_MARGIN_SECONDS = 10 * 60

_MAC = re.compile(r"(?<![0-9A-Fa-f])((?:[0-9A-Fa-f]{2}[:_-]){5})([0-9A-Fa-f]{2})(?![0-9A-Fa-f])")
_PROC_FILES = ("/proc/uptime", "/proc/loadavg", "/proc/meminfo", "/proc/pressure/cpu", "/proc/pressure/memory",
               "/proc/pressure/io", "/proc/net/wireless")


def redact(data: bytes) -> bytes:
  """Mask hardware addresses (aa:bb:..., dev_AA_BB_..., aa-bb-...) to their last byte."""
  text = data.decode("utf-8", errors="replace")
  return _MAC.sub(lambda match: re.sub(r"[0-9A-Fa-f]{2}", "xx", match.group(1)) + match.group(2), text).encode()


def window_start(starts: Sequence[str], now: float | None = None) -> float:
  """Journal start: a little before the oldest kept session, at most a day back."""
  now = datetime.now(UTC).timestamp() if now is None else now
  times = []
  for value in starts:
    try:
      times.append(datetime.fromisoformat(value).timestamp())
    except (TypeError, ValueError):
      continue
  start = min(times) - WINDOW_MARGIN_SECONDS if times else now - DEFAULT_WINDOW_SECONDS
  return max(start, now - MAX_WINDOW_SECONDS)


def _basedir() -> str:
  try:
    from openpilot.common.basedir import BASEDIR
    return BASEDIR
  except Exception:
    return os.getcwd()


def commands(since: float) -> dict[str, list[str]]:
  since_arg = f"@{int(since)}"
  journal = ["journalctl", "--no-pager", "-q", "-o", "short-iso-precise", "--since", since_arg, "-n", str(JOURNAL_LINES)]
  basedir = _basedir()
  return {
    "journal_network.log": [*journal, "-u", "NetworkManager", "-u", "wpa_supplicant"],
    "journal_bluetooth.log": [*journal, "-u", "bluetooth"],
    "journal_kernel.log": [*journal, "-k"],
    "dmesg.log": ["dmesg", "-T"],
    "processes.txt": ["ps", "-eo", "pid,psr,ni,pcpu,pmem,rss,etime,stat,comm", "--sort=-pcpu"],
    "wifi_link.txt": ["iw", "dev", "wlan0", "link"],
    "network_devices.txt": ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"],
    "disk.txt": ["df", "-h", "/data"],
    "build.txt": ["git", "-C", basedir, "log", "-1", "--format=%H%n%D%n%ci%n%s"],
    "build_changes.txt": ["git", "-C", basedir, "status", "--short", "--untracked-files=no"],
  }


def _proc_snapshot() -> bytes:
  lines = []
  for path in _PROC_FILES:
    try:
      with open(path, "rb") as handle:
        lines.append(f"==== {path}\n".encode() + handle.read(64 << 10))
    except OSError as error:
      lines.append(f"==== {path}: {error.strerror or error}\n".encode())
  return b"\n".join(lines)


def collect(since: float, deadline: float = DEADLINE_SECONDS, *, run: Callable | None = None,
            command_set: dict[str, list[str]] | None = None) -> dict[str, bytes]:
  """Run every command concurrently under one deadline; returns {file name: redacted bytes} plus a manifest."""
  spawn = run or subprocess.Popen
  started = time.monotonic()
  manifest: dict[str, dict] = {}
  running = {}
  for name, argv in (command_set if command_set is not None else commands(since)).items():
    try:
      running[name] = spawn(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                            env={**os.environ, "LC_ALL": "C", "SYSTEMD_PAGER": ""})
      manifest[name] = {"command": " ".join(argv)}
    except OSError as error:
      manifest[name] = {"command": " ".join(argv), "error": error.strerror or str(error)}

  outputs: dict[str, bytes] = {}

  def drain(name: str, process) -> None:
    # Each pipe is read on its own thread so one chatty command cannot stall another behind a full pipe.
    entry = manifest[name]
    try:
      output, _ = process.communicate(timeout=deadline)
      entry["exit"] = process.returncode
    except subprocess.TimeoutExpired:
      process.kill()
      try:
        output, _ = process.communicate(timeout=1.0)
      except subprocess.TimeoutExpired:
        output = b""
      entry["error"] = f"timed out after {deadline:.0f} s"
    except Exception as error:  # reported in the manifest; never fails the bundle
      output = b""
      entry["error"] = str(error) or type(error).__name__
    entry["seconds"] = round(time.monotonic() - started, 2)
    outputs[name] = output or b""

  readers = [threading.Thread(target=drain, args=item, name=f"aa_snapshot_{item[0]}", daemon=True) for item in running.items()]
  for reader in readers:
    reader.start()
  for reader in readers:
    reader.join(timeout=max(0.0, deadline + 2.0 - (time.monotonic() - started)))

  files: dict[str, bytes] = {}
  for name in running:
    entry = manifest[name]
    if name not in outputs:
      entry["error"] = "did not finish"
      continue
    output = outputs[name]
    if len(output) > OUTPUT_LIMIT:
      entry["truncated_bytes"] = len(output) - OUTPUT_LIMIT
      output = output[-OUTPUT_LIMIT:]
    if output:
      files[name] = redact(output)

  files["proc.txt"] = redact(_proc_snapshot())
  files["manifest.json"] = json.dumps({
    "collected": datetime.now(UTC).isoformat(timespec="seconds"),
    "journal_since": datetime.fromtimestamp(since, UTC).isoformat(timespec="seconds"),
    "commands": manifest,
  }, indent=2).encode()
  return files
