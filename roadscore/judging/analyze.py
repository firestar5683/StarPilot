"""Offline technical characterization only. Never imported by the composer."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

from prepare import digest, write_json

REQUIRED = ('carState', 'modelV2', 'roadCameraState')


def summarize(events, start_s=0, end_s=None):
  counts, valid_counts, first, last, gaps = Counter(), Counter(), {}, {}, {}
  speeds, steering, signals, navigation = [], [], 0, 0
  origin = None
  turns, stops, prior_signal, prior_stopped = 0, 0, False, False
  maneuvers = Counter()
  previous = None
  reversals = 0
  for event in events:
    ns, kind, valid, data = event
    if origin is None:
      origin = ns
    t = (ns - origin) / 1e9
    if previous is not None and ns < previous:
      reversals += 1
    previous = ns
    if t < start_s or (end_s is not None and t >= end_s):
      continue
    counts[kind] += 1
    valid_counts[kind] += bool(valid)
    if kind in last:
      gaps[kind] = max(gaps.get(kind, 0), t - last[kind])
    first.setdefault(kind, t)
    last[kind] = t
    if not valid:
      continue
    if kind == 'carState':
      for field, values in [('vEgo', speeds), ('steeringAngleDeg', steering)]:
        value = data.get(field)
        if isinstance(value, (float, int)) and math.isfinite(value):
          values.append(float(value))
      signal = bool(data.get('leftBlinker') or data.get('rightBlinker'))
      stopped = bool(data.get('standstill'))
      turns += signal and not prior_signal
      stops += stopped and not prior_stopped
      prior_signal, prior_stopped = signal, stopped
      signals += signal
    if kind == 'navInstruction':
      navigation += 1
      maneuvers[str(data.get('maneuverType', 'unspecified'))] += 1
  def stats(values):
    if not values:
      return None
    values = sorted(values)
    return {'min': values[0], 'median': values[len(values) // 2], 'max': values[-1], 'samples': len(values)}
  coverage = {k: {'count': counts[k], 'valid_count': valid_counts[k], 'first_s': first[k], 'last_s': last[k],
                  'max_gap_s': gaps.get(k), 'mean_hz': (counts[k] - 1) / (last[k] - first[k]) if last[k] > first[k] else None}
              for k in sorted(counts)}
  return {'message_coverage': coverage, 'required_valid_messages_present': all(valid_counts[k] > 0 for k in REQUIRED),
          'timestamp_reversals': reversals, 'speed_m_s': stats(speeds), 'steering_degrees': stats(steering),
          'blinker_active_samples': signals, 'blinker_activation_edges': turns,
          'standstill_entry_edges': stops, 'nav_maneuver_sample_counts': dict(maneuvers), 'valid_navigation_messages': navigation,
          'observed_span_s': max(last.values()) - min(first.values()) if last else 0,
          'limitations': ['Offline characterization only; never feed future annotations into runtime.',
                         'Presence is not camera decode, navigation accuracy, musical acceptance, or replay timing validation.',
                         'Blinker counts are samples, not distinct turns; steering is a proxy, not ground truth.',
                         'Origin is first decoded log message; segment numbering is only nominal 60s.']}


def read_events(paths):
  from openpilot.tools.lib.logreader import _LogFileReader
  for path in paths:
    for event in _LogFileReader(str(path), sort_by_time=False):
      kind = event.which()
      data = getattr(event, kind).to_dict() if kind in ('carState', 'navInstruction') else {}
      yield event.logMonoTime, kind, event.valid, data


def analyze(manifest):
  batch = json.loads(manifest.read_text())
  for row in batch['routes']:
    cache = row.get('cache', {})
    paths = {}
    try:
      for asset in cache.get('files', []):
        path = manifest.parent / asset['path']
        if path.name.startswith(('rlog', 'qlog')):
          if not path.is_file() or digest(path) != asset['sha256']:
            raise ValueError('Original log cache checksum mismatch')
          paths.setdefault(asset['segment'], path)
      if not paths:
        raise ValueError('No full logs available')
      selection = row['selection']
      first_segment = min(paths)
      # Time selections need segment zero to establish actual route-relative origin.
      if selection['segments'] is None and first_segment != 0:
        raise ValueError('Time/full-route selection needs segment zero to establish its clock origin')
      report = summarize(read_events([paths[s] for s in sorted(paths)]), selection['start_s'], selection['end_s'])
      report['segments'] = sorted(paths)
      report['selection'] = selection
      report['complete_selected_logs'] = all(s in paths and paths[s].name.startswith('rlog') for s in cache.get('selected_segments', []))
      report['qlog_fallback_segments'] = [s for s in sorted(paths) if paths[s].name.startswith('qlog')]
      report['clock_reference_is_full_log'] = paths[first_segment].name.startswith('rlog')
      report['clock_scope'] = 'selected first log' if selection['segments'] is not None else 'route first log'
      row['analysis_status'] = 'characterized' if report['required_valid_messages_present'] and report['complete_selected_logs'] else 'incomplete'
    except Exception as e:
      row['analysis_status'] = 'blocked'
      report = {'status': 'blocked', 'reason_type': type(e).__name__, 'reason': str(e), 'note': 'Check cache coverage and local logreader dependencies. No generation attempted.'}
    write_json(manifest.parent / 'analysis' / (row['label'] + '.private.json'), report)
    print(row['label'], row['analysis_status'], flush=True)
  write_json(manifest, batch)


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--manifest', type=Path, required=True)
  analyze(parser.parse_args().manifest)
