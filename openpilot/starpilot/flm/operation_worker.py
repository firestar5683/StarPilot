"""Isolated, bounded local FLM analysis worker; never started by the desktop CLI."""

from dataclasses import asdict
import ctypes
import json
import logging
import os
from pathlib import Path
import resource
import signal
import sys
import threading
import time

from openpilot.starpilot.flm.local_logs import LocalLogUnavailable, read_closed_rlog
from openpilot.starpilot.flm.log_decode import LogDecodeError, decode_segment
from openpilot.starpilot.flm.offline import SegmentInput, analyze_segments
from openpilot.starpilot.galaxy.drive_history import SEGMENT_NAME


MAX_REQUEST_BYTES = 2048
MAX_REPORT_BYTES = 1024 * 1024
LINUX_ADDRESS_SPACE_BYTES = 2 * 1024**3
LINUX_CPU_SECONDS = 240


def _emit(value: dict) -> None:
  payload = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
  if len(payload) > MAX_REPORT_BYTES:
    raise ValueError('report_limit')
  sys.stdout.buffer.write(payload + b'\n')
  sys.stdout.buffer.flush()


def _limits() -> None:
  try:
    os.nice(10)
  except OSError:
    pass
  if sys.platform.startswith('linux'):
    for limit, ceiling in ((resource.RLIMIT_AS, LINUX_ADDRESS_SPACE_BYTES),
                           (resource.RLIMIT_CPU, LINUX_CPU_SECONDS)):
      soft, hard = resource.getrlimit(limit)
      bounded = min([ceiling, *(value for value in (soft, hard) if value >= 0)])
      resource.setrlimit(limit, (bounded, hard))


def _parent_lifeline(expected_pid: int) -> None:
  if type(expected_pid) is not int or expected_pid <= 1:
    raise ValueError('invalid parent')
  if sys.platform.startswith('linux'):
    # Set in the child, never in preexec_fn of a threaded parent. The PID
    # recheck closes the race where the parent exits before prctl completes.
    if ctypes.CDLL(None).prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
      raise OSError('parent-death signal unavailable')
  if os.getppid() != expected_pid:
    raise ValueError('parent changed')
  if not sys.platform.startswith('linux'):
    def watch_parent() -> None:
      while True:
        time.sleep(0.1)
        if os.getppid() != expected_pid:
          os._exit(125)
    threading.Thread(target=watch_parent, daemon=True).start()


def main() -> int:
  try:
    _limits()
    request = json.loads(sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1))
    root, names = request['root'], request['segments']
    _parent_lifeline(request['parentPid'])
    if (type(root) is not str or not Path(root).is_absolute() or type(names) is not list or
        not 1 <= len(names) <= 5 or any(type(name) is not str or len(name) > 180 or
                                     SEGMENT_NAME.fullmatch(name) is None for name in names) or
        len(set(names)) != len(names)):
      raise ValueError('invalid_request')
    selected_names = [name for name in names if type(name) is str]
    segments = []
    for index, name in enumerate(selected_names, 1):
      source = read_closed_rlog(Path(root), name, permitted=lambda: True)
      match = SEGMENT_NAME.fullmatch(name)
      if match is None:
        raise ValueError('invalid_request')
      events = decode_segment(source.compressed, source.codec)
      analysis = analyze_segments((SegmentInput(match.group('route'), int(match.group('number')), events),))
      segments.append({'source': {'segmentName': name, 'sha256': source.sha256,
                                  'compressedBytes': source.size, 'codec': source.codec},
                       'analysis': asdict(analysis.segments[0])})
      del source, events, analysis
      _emit({'kind': 'progress', 'processed': index})
    report = {'schemaVersion': 1, 'purpose': 'offline_tracking_diagnostics', 'segments': segments,
              'tuneRecommendation': None, 'vehicleQualification': False}
    _emit({'kind': 'result', 'report': report})
    return 0
  except LocalLogUnavailable:
    logging.exception('FLM recording admission failed')
    code = 'recording_unavailable'
  except LogDecodeError:
    logging.exception('FLM recording decode failed')
    code = 'decode_failed'
  except MemoryError:
    logging.exception('FLM worker memory limit exceeded')
    code = 'resource_limit'
  except Exception:
    logging.exception('FLM worker failed')
    code = 'process_failed'
  try:
    _emit({'kind': 'error', 'code': code})
  except Exception:
    pass
  return 1


if __name__ == '__main__':
  raise SystemExit(main())
