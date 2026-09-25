#!/usr/bin/env python3
"""Bounded, read-only local runtime sampling and offline capture comparison."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
from itertools import islice
import math
import os
from pathlib import Path
import platform
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ('uiDebug', 'managerState', 'deviceState', 'modelV2', 'controlsState', 'selfdriveState')
MAX_PROCESSES = 64
MAX_INSTANCES = 256
FIELDS = {
  'uiDebug': {'reportedFrameIntervalMs': ('frameTimeMillis', 1), 'reportedPrePresentWallMs': ('cpuTimeMillis', 1)},
  'modelV2': {'reportedModelExecutionMs': ('modelExecutionTime', 1000), 'reportedFrameDropPercent': ('frameDropPerc', 1)},
  'deviceState': {name: (field, 1) for name, field in (
    ('reportedMemoryUsagePercent', 'memoryUsagePercent'), ('reportedGpuUsagePercent', 'gpuUsagePercent'),
    ('reportedMaxTemperatureC', 'maxTempC'), ('reportedPowerDrawW', 'powerDrawW'))},
}
CATEGORIES = {'deviceState': ('started', 'thermalStatus', 'deviceType', 'chestnutPresent'),
              'selfdriveState': ('enabled', 'active'), 'modelV2': ('big',)}
METRICS = {
  'reportedFrameIntervalMs': 'uiDebug.frameTimeMillis; Raylib reported frame interval, not measured present duration',
  'reportedPrePresentWallMs': 'uiDebug.cpuTimeMillis; publisher monotonic wall time for drawing/update before present, not thread CPU',
  'reportedModelExecutionMs': 'modelV2.modelExecutionTime * 1000; publisher execution interval, not sensor-to-actuator latency',
  'observedReceiveRateHz': 'fresh conflated messages observed / actual capture seconds; capped by collector polling, not publisher rate',
  'receiveAgeMs': 'time since this collector last received a message, sampled each poll after first receipt',
  'publicationAgeAtReceiveMs': 'collector monotonic time minus Event.logMonoTime at receipt; includes publication/transport/sampling delay',
  'cpuPercentOneCore': '100 * delta process(user+system ticks) / clock ticks per second / elapsed sample seconds; can exceed 100',
  'rssMiB': 'Linux /proc/PID/stat resident pages * page size / 1048576; excludes swapped/nonresident memory',
}


class Distribution:
  def __init__(self):
    self.values: list[float] = []
    self.missing: Counter[str] = Counter()

  def add(self, value, reason='missing_field'):
    if value is None:
      self.missing[reason] += 1
    elif not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
      self.missing['nonfinite_or_nonnumeric'] += 1
    else:
      self.values.append(float(value))

  def summary(self):
    values = sorted(self.values)
    result = {'status': 'observed' if values else 'no_samples', 'sampleCount': len(values), 'missingCounts': dict(self.missing)}
    if not values:
      return {**result, **dict.fromkeys(('min', 'mean', 'p50', 'p90', 'p95', 'p99', 'max'))}

    def percentile(q):
      index = (len(values) - 1) * q
      lo, hi = math.floor(index), math.ceil(index)
      return values[lo] + (values[hi] - values[lo]) * (index - lo)

    return {**result, 'min': values[0], 'mean': math.fsum(values) / len(values), 'max': values[-1],
            **{f'p{q}': percentile(q / 100) for q in (50, 90, 95, 99)}}


def field(body, name):
  try:
    return body.get(name) if isinstance(body, dict) else getattr(body, name)
  except (AttributeError, RuntimeError):
    return None


class MessageSamples:
  def __init__(self):
    self.count = 0
    self.invalid = 0
    self.last_received = None
    self.last_published = None
    self.timestamps = Counter()
    self.receive_age = Distribution()
    self.publication_age = Distribution()
    self.intervals = Distribution()
    self.metrics: dict[str, Distribution] = {}
    self.states: dict[str, Counter] = {}

  def observe(self, now, event):
    self.count += 1
    self.invalid += not event['valid']
    if self.last_received is not None:
      self.intervals.add((now - self.last_received) * 1000)
    self.last_received = now
    published = event['logMonoTime']
    if not isinstance(published, int) or published <= 0:
      self.publication_age.add(None, 'missing_or_zero_timestamp')
    elif published > now * 1e9:
      self.publication_age.add(None, 'future_timestamp_clock_mismatch')
    else:
      self.publication_age.add((now - published / 1e9) * 1000)
    if isinstance(published, int) and published > 0:
      if self.last_published is not None:
        if published == self.last_published:
          self.timestamps['repeated'] += 1
        elif published < self.last_published:
          self.timestamps['regressed'] += 1
      self.last_published = published

  def summary(self, duration, source_status):
    return {'status': 'observed' if self.count else ('no_messages' if source_status == 'available' else source_status),
            'observedMessages': self.count, 'invalidMessages': self.invalid,
            'observedReceiveRateHz': self.count / duration if duration > 0 and source_status == 'available' else None,
            'timestampDiscontinuities': dict(self.timestamps), 'receiveAgeMs': self.receive_age.summary(),
            'publicationAgeAtReceiveMs': self.publication_age.summary(), 'observedReceiveIntervalMs': self.intervals.summary(),
            'reportedStateCounts': {name: dict(value) for name, value in self.states.items()},
            'metrics': {name: value.summary() for name, value in self.metrics.items()}}


class LocalMessages:
  def __init__(self):
    self.status = 'available'
    self.error = None
    self.master = None
    self.expected_rates = {}
    self.module_path = None
    try:
      from openpilot.cereal import messaging
      from openpilot.cereal.services import SERVICE_LIST
      self.module_path = messaging.__file__
      self.master = messaging.SubMaster(list(SERVICES))
      self.expected_rates = {name: SERVICE_LIST[name].frequency for name in SERVICES}
    except Exception as error:
      self.status, self.error = 'unavailable', type(error).__name__

  def poll(self):
    if self.master is None:
      return {}
    try:
      self.master.update(0)
      return {name: {'body': self.master[name], 'valid': self.master.valid[name], 'logMonoTime': self.master.logMonoTime[name]}
              for name in SERVICES if self.master.updated[name]}
    except Exception as error:
      self.status, self.error, self.master = 'error', type(error).__name__, None
      return {}


class ProcReader:
  def __init__(self, root=Path('/proc'), ticks=None, page_size=None):
    self.root = root
    self.available = (root / 'self/stat').exists()
    self.ticks = ticks or (os.sysconf('SC_CLK_TCK') if self.available else None)
    self.page_size = page_size or (os.sysconf('SC_PAGE_SIZE') if self.available else None)

  def read(self, pid):
    if not self.available:
      return None, 'proc_unavailable'
    try:
      raw = (self.root / str(pid) / 'stat').read_text()
      begin, end = raw.index('('), raw.rindex(')')
      parts = raw[end + 2:].split()
      if int(raw[:begin].strip()) != pid:
        raise ValueError('PID mismatch')
      result = {'comm': raw[begin + 1:end], 'cpuTicks': int(parts[11]) + int(parts[12]),
                'startTicks': int(parts[19]), 'rssPages': int(parts[21])}
      if min(result['cpuTicks'], result['startTicks'], result['rssPages']) < 0:
        raise ValueError('negative stat')
      return result, None
    except FileNotFoundError:
      return None, 'process_gone'
    except PermissionError:
      return None, 'permission_denied'
    except (OSError, ValueError, IndexError):
      return None, 'unreadable_or_malformed_stat'


class ProcessSamples:
  def __init__(self, reader):
    self.reader = reader
    self.instances = {}
    self.previous = {}
    self.read_errors = Counter()
    self.pid_reuses = 0
    self.skipped_instances = 0
    self.skipped_targets = 0
    self.target_samples = 0

  def poll(self, now, targets):
    self.skipped_targets += max(0, len(targets) - MAX_PROCESSES)
    self.target_samples += min(MAX_PROCESSES, len(targets))
    for pid, name in sorted(targets.items())[:MAX_PROCESSES]:
      record, error = self.reader.read(pid)
      if error:
        self.read_errors[error] += 1
        previous = self.previous.pop(pid, None)
        if previous is not None:
          for metric in ('cpuPercentOneCore', 'rssMiB'):
            self.instances[previous[0]][metric].add(None, error)
        continue
      identity = (pid, record['startTicks'])
      if identity not in self.instances:
        if len(self.instances) >= MAX_INSTANCES:
          self.skipped_instances += 1
          continue
        self.instances[identity] = {'pid': pid, 'startTicks': record['startTicks'], 'requestedName': name, 'comm': record['comm'],
                                    'firstObservedMonotonic': now, 'lastObservedMonotonic': now,
                                    'cpuPercentOneCore': Distribution(), 'rssMiB': Distribution()}
      item = self.instances[identity]
      item['lastObservedMonotonic'] = now
      item['rssMiB'].add(record['rssPages'] * self.reader.page_size / 1048576)
      before = self.previous.get(pid)
      reason = None
      if before is None:
        reason = 'baseline_required'
      elif before[0] != identity:
        reason = 'pid_reused_or_restarted'
        self.pid_reuses += 1
      elif now <= before[1]:
        reason = 'nonpositive_sample_interval'
      elif record['cpuTicks'] < before[2]:
        reason = 'cpu_counter_regressed'
      if reason:
        item['cpuPercentOneCore'].add(None, reason)
      else:
        assert before is not None
        item['cpuPercentOneCore'].add(100 * (record['cpuTicks'] - before[2]) / self.reader.ticks / (now - before[1]))
      self.previous[pid] = (identity, now, record['cpuTicks'])
    self.previous = {pid: value for pid, value in self.previous.items() if pid in targets}

  def summary(self):
    names = Counter(item['requestedName'] for item in self.instances.values())
    return {'status': 'available' if self.reader.available else 'unavailable', 'readErrors': dict(self.read_errors),
            'samplingStatus': 'observed' if self.instances else ('no_targets' if not self.target_samples else 'no_readable_processes'),
            'requestedTargetSamples': self.target_samples,
            'clockTicksPerSecond': self.reader.ticks, 'pageSizeBytes': self.reader.page_size,
            'pidReuseOrRestartEvents': self.pid_reuses, 'skippedInstanceSamples': self.skipped_instances,
            'observedInstanceCountsByName': dict(names),
            'skippedTargetSamples': self.skipped_targets,
            'instances': [{name: value.summary() if isinstance(value, Distribution) else value for name, value in item.items()}
                          for item in self.instances.values()]}


def capture(duration=30, rate=20, *, messages=None, proc=None, pids=(), clock=time.monotonic, sleep=time.sleep):
  if not math.isfinite(duration) or not 0.1 <= duration <= 120 or not math.isfinite(rate) or not 1 <= rate <= 50:
    raise ValueError('duration must be 0.1..120 seconds and sample rate 1..50 Hz')
  if len(pids) > MAX_PROCESSES or any(type(pid) is not int or pid <= 0 for pid in pids):
    raise ValueError('at most 64 positive PIDs are supported')
  messages = messages if messages is not None else LocalMessages()
  processes = ProcessSamples(proc if proc is not None else ProcReader())
  samples = {name: MessageSamples() for name in SERVICES}
  for service, metrics in FIELDS.items():
    samples[service].metrics = {name: Distribution() for name in metrics}
  for name in ('reportedCpuUsageMeanPercent', 'reportedCpuUsageMaxPercent'):
    samples['deviceState'].metrics[name] = Distribution()
  explicit = {pid: f'explicit_pid_{pid}' for pid in pids}
  targets = {}
  manager_counts = Counter()
  polls, missed_slots = 0, 0
  poll_intervals = Distribution()
  started = clock()
  previous_poll = None
  scheduled = started
  while polls < math.ceil(duration * rate) and clock() < started + duration:
    if clock() < scheduled:
      sleep(min(scheduled, started + duration) - clock())
    if clock() >= started + duration:
      break
    events = messages.poll()
    now = clock()
    if previous_poll is not None:
      poll_intervals.add((now - previous_poll) * 1000)
    previous_poll = now
    for service, event in events.items():
      sample = samples[service]
      sample.observe(now, event)
      body = event['body']
      for name in CATEGORIES.get(service, ()):
        value = field(body, name)
        sample.states.setdefault(name, Counter())['missing' if value is None else str(value)[:128]] += 1
      for name, (source, scale) in FIELDS.get(service, {}).items():
        value = field(body, source)
        if isinstance(value, (int, float)) and value < 0:
          sample.metrics[name].add(None, 'negative_reported_value')
        else:
          sample.metrics[name].add(value * scale if isinstance(value, (int, float)) else value)
      if service == 'deviceState':
        values = field(body, 'cpuUsagePercent')
        values = list(islice(values, 256)) if values is not None else []
        valid = [value for value in values if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0]
        reason = 'missing_or_empty_cpu_list' if not values else 'invalid_cpu_list'
        for name, value in [('reportedCpuUsageMeanPercent', sum(valid) / len(valid) if valid else None),
                            ('reportedCpuUsageMaxPercent', max(valid) if valid else None)]:
          sample.metrics[name].add(value if len(valid) == len(values) else None, reason)
      if service == 'managerState':
        targets = {}
        entries = field(body, 'processes')
        if entries is None:
          manager_counts['missing_process_list'] += 1
        else:
          for index, process in enumerate(entries):
            if index >= MAX_PROCESSES:
              manager_counts['truncated_process_lists'] += 1
              break
            running, expected = field(process, 'running'), field(process, 'shouldBeRunning')
            manager_counts['process_observations'] += 1
            manager_counts['reported_running'] += running is True
            manager_counts['expected_but_stopped'] += expected is True and running is False
            pid = field(process, 'pid')
            if running is True and isinstance(pid, int) and pid > 0:
              targets[pid] = str(field(process, 'name'))[:128]
    for sample in samples.values():
      if sample.last_received is not None:
        sample.receive_age.add((now - sample.last_received) * 1000)
    processes.poll(now, {**targets, **explicit})
    polls += 1
    next_slot = max(polls + missed_slots, math.floor((clock() - started) * rate) + 1)
    missed_slots = next_slot - polls
    scheduled = started + next_slot / rate
  if clock() < started + duration:
    sleep(started + duration - clock())
  elapsed = clock() - started
  return {'schemaVersion': 1, 'kind': 'runtime-performance-capture',
          'capture': {'requestedDurationSeconds': duration, 'actualDurationSeconds': elapsed, 'requestedSampleRateHz': rate,
                      'pollCount': polls, 'missedScheduledPolls': missed_slots, 'pollIntervalMs': poll_intervals.summary()},
          'messageSource': {'status': messages.status, 'errorType': messages.error, 'transport': 'local conflated SubMaster',
                            'modulePath': getattr(messages, 'module_path', None),
                            'configuredPublisherRatesHz': messages.expected_rates},
          'services': {name: value.summary(elapsed, messages.status) for name, value in samples.items()},
          'managerObservations': dict(manager_counts), 'processes': processes.summary(), 'metricDefinitions': METRICS,
          'bounds': {'maxSeconds': 120, 'maxPollHz': 50, 'maxProcessesPerPoll': MAX_PROCESSES, 'maxProcessInstances': MAX_INSTANCES}}


def metadata(root=None):
  try:
    spec = importlib.util.find_spec('openpilot')
    imported_root = Path(spec.origin).resolve().parent.parent if spec is not None and spec.origin else None
  except (ImportError, ValueError):
    imported_root = None
  binding = 'explicit' if root is not None else 'imported_openpilot'
  if root is None:
    root = imported_root
    if root is None and (ROOT / 'openpilot/cereal/log.capnp').is_file():
      root, binding = ROOT, 'tool_repository_fallback'
  if root is not None:
    root = Path(root).resolve()
    if not (root / 'openpilot/cereal/log.capnp').is_file():
      raise ValueError('source root must contain openpilot/cereal/log.capnp')

  def read(path):
    try:
      return path.read_text().strip()[:256]
    except OSError:
      return None

  def git(*args):
    if root is None:
      return None
    try:
      return subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, timeout=3, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
      return None

  paths = ('openpilot/cereal/log.capnp', 'openpilot/cereal/services.py',
           'openpilot/selfdrive/ui/ui.py', 'openpilot/system/ui/lib/application.py', 'openpilot/selfdrive/modeld/modeld.py')
  return {'recordedAtUtc': datetime.now(UTC).isoformat(), 'system': platform.system(), 'release': platform.release(),
          'machine': platform.machine(), 'python': platform.python_version(), 'logicalCpuCount': os.cpu_count(),
          'agnosVersion': read(Path('/VERSION')), 'bootId': read(Path('/proc/sys/kernel/random/boot_id')),
          'sourceRoot': str(root) if root is not None else None, 'sourceBinding': binding if root is not None else 'unavailable',
          'importedOpenpilotRoot': str(imported_root) if imported_root is not None else None,
          'declaredRootMatchesImported': root == imported_root if root is not None and imported_root is not None else None,
          'tool': {'path': str(Path(__file__).resolve()), 'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
          'gitHead': git('rev-parse', 'HEAD'),
          'gitDirty': bool(status) if (status := git('status', '--porcelain')) is not None else None,
          'sourceSha256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                           for name in paths if root is not None and (root / name).is_file()},
          'collectorEnvironment': {name: os.environ.get(name) for name in ('UI_FRAME_TIMING', 'SIMULATION', 'SCALE', 'ZMQ', 'MSGQ_PREFIX')}}


def compare(before, after):
  for report in (before, after):
    if report.get('schemaVersion') != 1 or report.get('kind') != 'runtime-performance-capture':
      raise ValueError('unsupported capture schema')
  differences = []
  for field_name in ('system', 'machine', 'agnosVersion', 'logicalCpuCount'):
    left, right = before.get('environment', {}).get(field_name), after.get('environment', {}).get(field_name)
    if left != right or left is None:
      differences.append({'field': field_name, 'before': left, 'after': right})
  for name in ('requestedDurationSeconds', 'requestedSampleRateHz'):
    if before['capture'][name] != after['capture'][name]:
      differences.append({'field': name, 'before': before['capture'][name], 'after': after['capture'][name]})

  def flatten(report):
    result = {}
    for service, value in report['services'].items():
      result[f'{service}.observedReceiveRateHz'] = value['observedReceiveRateHz']
      for metric, data in {**value['metrics'], **{name: value[name] for name in
                         ('receiveAgeMs', 'publicationAgeAtReceiveMs', 'observedReceiveIntervalMs')}}.items():
        for statistic in ('sampleCount', 'p50', 'p95', 'max'):
          result[f'{service}.{metric}.{statistic}'] = data[statistic]
    groups = {}
    for item in report['processes']['instances']:
      group = groups.setdefault(item['requestedName'], [])
      group.append(item)
    for name, items in groups.items():
      result[f'process.{name}.observedInstances'] = len(items)
      # Do not average per-incarnation percentiles into a false pooled percentile.
      for metric in ('cpuPercentOneCore', 'rssMiB'):
        available = [item[metric]['max'] for item in items if item[metric]['sampleCount']]
        result[f'process.{name}.{metric}.max'] = max(available) if available else None
    return result

  left, right = flatten(before), flatten(after)
  rows = []
  for key in sorted(left.keys() | right.keys()):
    a, b = left.get(key), right.get(key)
    rows.append({'metric': key, 'before': a, 'after': b, 'status': 'comparable' if a is not None and b is not None else 'missing_data',
                 'delta': b - a if a is not None and b is not None else None,
                 'changePercent': (b - a) / abs(a) * 100 if a is not None and b is not None and a != 0 else None})
  return {'schemaVersion': 1, 'kind': 'runtime-performance-comparison', 'environmentOrSamplingDifferences': differences,
          'interpretation': 'Descriptive differences only; workload, thermal state, conflation and instrumentation affect results.',
          'captureContext': {name: {'gitHead': report.get('environment', {}).get('gitHead'),
                                    'messageSource': report['messageSource'], 'processStatus': report['processes']['status'],
                                    'reportedStateCounts': {service: value['reportedStateCounts'] for service, value in report['services'].items()}}
                             for name, report in (('before', before), ('after', after))},
          'summary': [row for row in rows if row['metric'] in (
            'uiDebug.reportedFrameIntervalMs.p95', 'uiDebug.reportedPrePresentWallMs.p95',
            'modelV2.reportedModelExecutionMs.p95', 'modelV2.reportedFrameDropPercent.max',
            'deviceState.reportedMaxTemperatureC.max', 'deviceState.reportedMemoryUsagePercent.max')
            or row['metric'].startswith('process.')],
          'metrics': rows}


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  commands = parser.add_subparsers(dest='command', required=True)
  collect = commands.add_parser('capture', help='Read local messages and Linux /proc; write one final JSON file')
  collect.add_argument('--duration', type=float, default=30)
  collect.add_argument('--rate', type=float, default=20)
  collect.add_argument('--pid', type=int, action='append', default=[], help='Also sample this local PID (repeatable, maximum 64)')
  collect.add_argument('--source-root', type=Path, help='Source checkout to identify; default is the imported openpilot checkout')
  collect.add_argument('--output', type=Path, required=True)
  diff = commands.add_parser('compare', help='Compare two saved captures without connecting to anything')
  diff.add_argument('before', type=Path)
  diff.add_argument('after', type=Path)
  diff.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  try:
    if args.output.exists():
      raise FileExistsError(f'output already exists: {args.output}')
    if args.command == 'capture':
      environment = metadata(args.source_root)
      report = capture(args.duration, args.rate, pids=args.pid)
      report['environment'] = environment
    else:
      report = compare(json.loads(args.before.read_text()), json.loads(args.after.read_text()))
      report['inputs'] = {name: {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                          for name, path in (('before', args.before), ('after', args.after))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
      json.dump(report, output, indent=2, allow_nan=False)
      output.write('\n')
  except (ValueError, OSError) as error:
    parser.exit(1, f'{type(error).__name__}: {error}\n')
  print(f'{report["kind"]}: {args.output}')
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
