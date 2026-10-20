"""Phone-audio dropout reports for the device's Bugsink project, kept apart from Android Auto's.

Uses the Android Auto sender, DSN and bugsink.json switch, but reports as the ``phone_audio`` logger
with ``pa.*`` tags. Reads only the journal lines the relay chain already writes: BlueALSA missing-packet
warnings, PulseAudio underruns and, with ``audio_debug``, the relay's one-second timing summaries.
No audio, track names or phone identity is read; addresses are scrubbed by the shared sanitizer.
"""

from __future__ import annotations

import json
import re
import subprocess
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from openpilot.starpilot.soloist.paths import Layout

INTERVAL_S = 60.0
GAP_S = 10.0              # quiet time that ends one dropout window
MIN_LOST_PACKETS = 10     # a window needs this many missing packets, or MIN_UNDERRUNS, to be worth a report
MIN_UNDERRUNS = 3
MAX_REPORTS = 5           # per pass; the rest go in the next one
MAX_LINES = 20000
RTP = re.compile(r'Missing RTP packets \[\d+ != \d+\]: (\d+)')
UNDERRUN = 'Implicit underrun of'
HCI_UNKNOWN = 'ACL packet for unknown connection handle'
STATE_NAME = 'bugsink_report.json'
SCHEMA_TAGS = {'pa.schema': '1', 'component': 'phone_audio'}


def parse_line(line: str) -> tuple[float, str, str] | None:
  """(epoch, source, text) for one ``journalctl -o short-unix`` line, else None."""
  stamp, _, rest = line.partition(' ')
  try:
    when = float(stamp)
  except ValueError:
    return None
  _, _, text = rest.partition(': ')
  return when, rest.split('[', 1)[0].split(' ')[-1] if rest else '', text


def windows(lines: list[str]) -> list[dict]:
  """Group the journal into dropout windows separated by quiet gaps, with counts per signal."""
  found: list[dict] = []
  current: dict | None = None
  for line in lines:
    parsed = parse_line(line)
    if parsed is None:
      continue
    when, source, text = parsed
    lost = RTP.search(text)
    if lost:
      kind = 'rtp'
    elif UNDERRUN in text:
      kind = 'underrun'
    elif HCI_UNKNOWN in text:
      kind = 'hci'
    elif source == 'starpilot-phone-audio':
      kind = 'timing'
    else:
      continue
    if kind == 'timing':
      try:
        timing = json.loads(text)
      except ValueError:
        continue
      if not timing.get('reads_over_50ms') and not timing.get('writes_over_50ms'):
        continue
    if kind == 'hci':  # constant background noise: counted inside a window, never opens or extends one
      if current is not None and when - current['end'] <= GAP_S:
        current['hci_unknown_handle'] += 1
      continue
    if current is None or when - current['end'] > GAP_S:
      current = {'start': when, 'end': when, 'rtp_warnings': 0, 'lost_packets': 0, 'underruns': 0, 'hci_unknown_handle': 0,
                 'slow_reads': 0, 'slow_writes': 0, 'max_read_ms': 0.0, 'max_write_ms': 0.0, 'short_audio_seconds': 0}
      found.append(current)
    current['end'] = when
    if kind == 'rtp':
      current['rtp_warnings'] += 1
      current['lost_packets'] += int(lost[1])
    elif kind == 'underrun':
      current['underruns'] += 1
    else:
      current['slow_reads'] += int(timing.get('reads_over_50ms') or 0)
      current['slow_writes'] += int(timing.get('writes_over_50ms') or 0)
      current['max_read_ms'] = max(current['max_read_ms'], float(timing.get('max_read_ms') or 0))
      current['max_write_ms'] = max(current['max_write_ms'], float(timing.get('max_write_ms') or 0))
      interval = float(timing.get('interval_s') or 1)
      if float(timing.get('audio_ms') or 0) < 0.9 * interval * 1000:
        current['short_audio_seconds'] += 1
  return found


def significant(window: dict) -> bool:
  return window['lost_packets'] >= MIN_LOST_PACKETS or window['underruns'] >= MIN_UNDERRUNS


def stamp(epoch: float) -> str:
  return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec='seconds')


def dropout_event(window: dict, *, output: str = 'unknown') -> dict:
  seconds = round(window['end'] - window['start'], 1)
  detail = {key: round(value, 1) if isinstance(value, float) else value for key, value in window.items() if key not in ('start', 'end')}
  summary = (f'{window["lost_packets"]} Bluetooth packets lost, {window["underruns"]} underruns over {seconds} s')
  return {
    'message': f'Phone audio dropout: {summary}',
    'level': 'warning',
    'fingerprint': ['phone-audio', 'dropout'],
    'tags': {**SCHEMA_TAGS, 'pa.report': 'dropout', 'pa.output': output,
             'pa.cause_hint': 'bluetooth_input' if window['lost_packets'] >= MIN_LOST_PACKETS else 'relay_or_output'},
    'contexts': {'phone_audio': {'started': stamp(window['start']), 'duration_s': seconds, **detail}},
  }


def journal(since: float, run=subprocess.run) -> list[str]:
  """Relay-chain journal lines since ``since``; the BlueALSA, PulseAudio, relay and kernel-Bluetooth sources only."""
  base = ['journalctl', '--no-pager', '-q', '-o', 'short-unix', '--since', f'@{int(since)}', '-n', str(MAX_LINES)]
  lines: list[str] = []
  for selector in (['-u', 'bluealsa'], ['_COMM=pulseaudio'], ['-t', 'starpilot-phone-audio'], ['-k', '--grep', 'hci0']):
    reply = run([*base, *selector], capture_output=True, text=True, timeout=10, check=False)
    if reply.returncode == 0:
      lines += reply.stdout.splitlines()
  return sorted(lines)


def _state(path: Path) -> float | None:
  try:
    value = json.loads(path.read_text()).get('since')
    return float(value) if isinstance(value, (int, float)) else None
  except (OSError, ValueError, AttributeError):
    return None


def send_reports(capture: Callable[..., bool], layout: Layout | None = None, *, now: float | None = None,
                 read: Callable[[float], list[str]] = journal, output: str = 'unknown') -> int:
  """Send windows that have gone quiet since the last pass; returns how many reports were accepted."""
  layout = layout or Layout.default()
  now = time.time() if now is None else now
  path = layout.root / STATE_NAME
  since = _state(path)
  if since is None:
    since = now - 3600  # first pass: look back an hour, not the whole journal
  everything = windows(read(since))
  found = [w for w in everything if now - w['end'] > GAP_S]  # a window still in progress waits for the next pass
  pending = [w for w in everything if now - w['end'] <= GAP_S]
  sent, cursor = 0, since
  for window in found:
    if significant(window):
      if sent >= MAX_REPORTS or not capture(**dropout_event(window, output=output)):
        break
      sent += 1
    cursor = window['end']
  else:
    cursor = max(cursor, pending[0]['start'] - 0.001 if pending else now - GAP_S)
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps({'since': cursor + 0.001}))
  return sent


class Reporter:
  """Background thread in the music supervisor: every minute, while parked, sends what is new."""

  def __init__(self, parked: Callable[[], bool], output: Callable[[], str] = lambda: 'unknown', interval: float = INTERVAL_S):
    self._parked, self._output, self._interval = parked, output, interval
    self._stop = threading.Event()

  def start(self) -> Reporter:
    threading.Thread(target=self._run, name='phone_audio_bugsink', daemon=True).start()
    return self

  def close(self) -> None:
    self._stop.set()

  def _run(self) -> None:
    from openpilot.starpilot.system.android_auto.bugsink_transport import configured_sender
    while not self._stop.wait(self._interval):
      try:
        if self._parked():
          capture = configured_sender(active=lambda: not self._stop.is_set() and self._parked(), logger='phone_audio',
                                      client='starpilot-pa/1', schema_tags=SCHEMA_TAGS)
          if capture is not None:
            send_reports(capture, output=self._output())
      except Exception as error:
        print(json.dumps({'event': 'phone_audio_report_failed', 'error_kind': type(error).__name__}), flush=True)
