import copy
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.diagnostics import performance as perf


class FakeClock:
  def __init__(self):
    self.now = 10.0

  def __call__(self):
    return self.now

  def sleep(self, seconds):
    self.now += seconds


class FakeMessages:
  status = 'available'
  error = None
  expected_rates = {'uiDebug': 0}

  def __init__(self, frames=()):
    self.frames = iter(frames)

  def poll(self):
    return next(self.frames, {})


def event(body, timestamp=10_000_000_000, valid=True):
  return {'body': body, 'logMonoTime': timestamp, 'valid': valid}


def proc_stat(pid=42, cpu=20, start=100, rss=512, comm='ui (worker)'):
  parts = ['0'] * 22
  parts[0], parts[11], parts[12], parts[19], parts[21] = 'S', str(cpu), '0', str(start), str(rss)
  return f'{pid} ({comm}) ' + ' '.join(parts)


class PerformanceTests(unittest.TestCase):
  def setUp(self):
    self.temporary = tempfile.TemporaryDirectory()
    self.addCleanup(self.temporary.cleanup)
    self.root = Path(self.temporary.name)
    (self.root / 'self').mkdir()
    (self.root / 'self/stat').write_text(proc_stat())
    (self.root / '42').mkdir()
    self.reader = perf.ProcReader(self.root, ticks=100, page_size=4096)

  def write_stat(self, **values):
    (self.root / '42/stat').write_text(proc_stat(**values))

  def capture(self, frames=(), **kwargs):
    clock = FakeClock()
    return perf.capture(1, 10, messages=FakeMessages(frames), proc=self.reader, clock=clock, sleep=clock.sleep, **kwargs)

  def test_distribution_interpolation_and_missing_are_distinct_from_zero(self):
    values = perf.Distribution()
    self.assertIsNone(values.summary()['p95'])
    for value in (0, 10, 20, 30):
      values.add(value)
    values.add(None)
    values.add(float('nan'))
    result = values.summary()
    self.assertEqual(result['sampleCount'], 4)
    self.assertEqual(result['min'], 0)
    self.assertEqual(result['p50'], 15)
    self.assertAlmostEqual(result['p95'], 28.5)
    self.assertEqual(result['missingCounts'], {'missing_field': 1, 'nonfinite_or_nonnumeric': 1})
    json.dumps(result, allow_nan=False)

  def test_messages_are_sampled_once_and_receive_age_grows(self):
    report = self.capture([{'uiDebug': event({'frameTimeMillis': 50, 'cpuTimeMillis': 7}, valid=False)}])
    ui = report['services']['uiDebug']
    self.assertEqual(report['capture']['pollCount'], 10)
    self.assertAlmostEqual(report['capture']['actualDurationSeconds'], 1)
    self.assertEqual(ui['observedMessages'], 1)
    self.assertEqual(ui['invalidMessages'], 1)
    self.assertEqual(ui['observedReceiveRateHz'], 1)
    self.assertEqual(ui['metrics']['reportedPrePresentWallMs']['sampleCount'], 1)
    self.assertAlmostEqual(ui['receiveAgeMs']['max'], 900)
    self.assertEqual(report['services']['modelV2']['status'], 'no_messages')
    self.assertIsNone(report['services']['modelV2']['metrics']['reportedModelExecutionMs']['max'])

  def test_missing_message_backend_and_proc_are_unavailable(self):
    source = FakeMessages()
    source.status, source.error = 'unavailable', 'ImportError'
    clock = FakeClock()
    report = perf.capture(0.1, 10, messages=source, proc=perf.ProcReader(self.root / 'absent'),
                          pids=[42], clock=clock, sleep=clock.sleep)
    self.assertEqual(report['services']['uiDebug']['status'], 'unavailable')
    self.assertIsNone(report['services']['uiDebug']['observedReceiveRateHz'])
    self.assertEqual(report['processes']['readErrors'], {'proc_unavailable': 1})
    self.assertEqual(report['processes']['status'], 'unavailable')

  def test_reported_model_units_and_device_sentinels(self):
    report = self.capture([{'modelV2': event({'modelExecutionTime': 0.025, 'frameDropPerc': 2}),
                            'deviceState': event({'gpuUsagePercent': -1, 'memoryUsagePercent': 0, 'cpuUsagePercent': [10, 30]})}])
    self.assertEqual(report['services']['modelV2']['metrics']['reportedModelExecutionMs']['p50'], 25)
    device = report['services']['deviceState']['metrics']
    self.assertEqual(device['reportedGpuUsagePercent']['missingCounts'], {'negative_reported_value': 1})
    self.assertEqual(device['reportedMemoryUsagePercent']['min'], 0)
    self.assertEqual(device['reportedCpuUsageMeanPercent']['mean'], 20)
    self.assertIsNone(device['reportedPowerDrawW']['max'])

  def test_timestamp_discontinuities_are_not_negative_latencies(self):
    sample = perf.MessageSamples()
    for now, stamp in [(10, 0), (11, 12_000_000_000), (12, 12_000_000_000), (13, 11_000_000_000)]:
      sample.observe(now, event({}, stamp))
    result = sample.summary(4, 'available')
    self.assertEqual(result['publicationAgeAtReceiveMs']['missingCounts'],
                     {'missing_or_zero_timestamp': 1, 'future_timestamp_clock_mismatch': 1})
    self.assertEqual(result['timestampDiscontinuities'], {'repeated': 1, 'regressed': 1})
    self.assertEqual(result['publicationAgeAtReceiveMs']['min'], 0)

  def test_proc_cpu_rss_and_parentheses_in_comm(self):
    samples = perf.ProcessSamples(self.reader)
    self.write_stat(cpu=20)
    samples.poll(10, {42: 'ui'})
    self.write_stat(cpu=220)
    samples.poll(11, {42: 'ui'})
    item = samples.summary()['instances'][0]
    self.assertEqual(item['comm'], 'ui (worker)')
    self.assertEqual(item['cpuPercentOneCore']['max'], 200)
    self.assertEqual(item['cpuPercentOneCore']['missingCounts'], {'baseline_required': 1})
    self.assertEqual(item['rssMiB']['mean'], 2)

  def test_restart_with_new_pid_is_a_separate_instance(self):
    samples = perf.ProcessSamples(self.reader)
    self.write_stat(cpu=20)
    samples.poll(10, {42: 'ui'})
    (self.root / '43').mkdir()
    (self.root / '43/stat').write_text(proc_stat(pid=43, cpu=200, start=300))
    samples.poll(11, {43: 'ui'})
    result = samples.summary()
    self.assertEqual(result['observedInstanceCountsByName'], {'ui': 2})
    self.assertEqual(result['instances'][1]['cpuPercentOneCore']['sampleCount'], 0)
    self.assertEqual(result['pidReuseOrRestartEvents'], 0)

  def test_pid_reuse_does_not_attribute_previous_cpu_to_new_process(self):
    samples = perf.ProcessSamples(self.reader)
    self.write_stat(cpu=20, start=100)
    samples.poll(10, {42: 'ui'})
    self.write_stat(cpu=900, start=200)
    samples.poll(11, {42: 'ui'})
    self.write_stat(cpu=950, start=200)
    samples.poll(12, {42: 'ui'})
    result = samples.summary()
    self.assertEqual(result['pidReuseOrRestartEvents'], 1)
    self.assertEqual(len(result['instances']), 2)
    self.assertEqual(result['instances'][1]['cpuPercentOneCore']['max'], 50)
    self.assertEqual(result['instances'][1]['cpuPercentOneCore']['missingCounts'], {'pid_reused_or_restarted': 1})

  def test_process_disappears_and_reappearance_requires_new_baseline(self):
    samples = perf.ProcessSamples(self.reader)
    self.write_stat(cpu=20)
    samples.poll(10, {42: 'ui'})
    (self.root / '42/stat').unlink()
    samples.poll(11, {42: 'ui'})
    self.write_stat(cpu=500)
    samples.poll(12, {42: 'ui'})
    result = samples.summary()
    self.assertEqual(result['readErrors'], {'process_gone': 1})
    self.assertEqual(result['instances'][0]['cpuPercentOneCore']['sampleCount'], 0)
    self.assertEqual(result['instances'][0]['cpuPercentOneCore']['missingCounts'], {'baseline_required': 2, 'process_gone': 1})

  def test_proc_permissions_malformed_and_counter_regression(self):
    self.write_stat()
    with patch.object(Path, 'read_text', side_effect=PermissionError):
      self.assertEqual(self.reader.read(42)[1], 'permission_denied')
    (self.root / '42/stat').write_text('not a stat')
    self.assertEqual(self.reader.read(42)[1], 'unreadable_or_malformed_stat')
    samples = perf.ProcessSamples(self.reader)
    self.write_stat(cpu=100)
    samples.poll(10, {42: 'ui'})
    self.write_stat(cpu=50)
    samples.poll(11, {42: 'ui'})
    self.assertEqual(samples.summary()['instances'][0]['cpuPercentOneCore']['missingCounts'],
                     {'baseline_required': 1, 'cpu_counter_regressed': 1})

  def test_manager_stopped_and_no_targets_are_not_proc_failures(self):
    report = self.capture([{'managerState': event({'processes': [
      {'name': 'ui', 'pid': 0, 'running': False, 'shouldBeRunning': True}]})}])
    self.assertEqual(report['managerObservations']['expected_but_stopped'], 1)
    self.assertEqual(report['processes']['samplingStatus'], 'no_targets')
    self.assertEqual(report['processes']['readErrors'], {})

  def test_capture_and_process_instance_bounds(self):
    for duration, rate in [(121, 20), (30, 51), (float('nan'), 20)]:
      with self.assertRaises(ValueError):
        perf.capture(duration, rate)
    samples = perf.ProcessSamples(self.reader)
    with patch.object(perf, 'MAX_INSTANCES', 2):
      for start in range(3):
        self.write_stat(start=start)
        samples.poll(10 + start, {42: 'ui'})
    self.assertEqual(len(samples.instances), 2)
    self.assertEqual(samples.skipped_instances, 1)

  def test_slow_polling_skips_schedule_slots_instead_of_bursting(self):
    clock = FakeClock()
    source = FakeMessages()
    with patch.object(source, 'poll', side_effect=lambda: (clock.sleep(0.25) or {})):
      report = perf.capture(1, 10, messages=source, proc=self.reader, clock=clock, sleep=clock.sleep)
    self.assertLessEqual(report['capture']['pollCount'], 4)
    self.assertGreater(report['capture']['missedScheduledPolls'], 0)
    self.assertGreaterEqual(report['capture']['actualDurationSeconds'], 1)

  def test_comparison_missing_zero_and_different_sampling(self):
    before = self.capture([{'uiDebug': event({'frameTimeMillis': 0, 'cpuTimeMillis': 0})}])
    after = copy.deepcopy(before)
    after['capture']['requestedSampleRateHz'] = 30
    after['services']['uiDebug']['metrics']['reportedFrameIntervalMs']['p95'] = 5
    result = perf.compare(before, after)
    rows = {row['metric']: row for row in result['metrics']}
    self.assertEqual(rows['uiDebug.reportedFrameIntervalMs.p95']['delta'], 5)
    self.assertIsNone(rows['uiDebug.reportedFrameIntervalMs.p95']['changePercent'])
    self.assertEqual(rows['modelV2.reportedModelExecutionMs.p95']['status'], 'missing_data')
    self.assertTrue(any(item['field'] == 'requestedSampleRateHz' for item in result['environmentOrSamplingDifferences']))
    json.dumps(result, allow_nan=False)

  def test_standalone_metadata_uses_imported_checkout_not_tool_directory(self):
    (self.root / 'openpilot/cereal').mkdir(parents=True)
    (self.root / 'openpilot/cereal/log.capnp').write_text('schema fixture')
    with patch.object(perf.importlib.util, 'find_spec', return_value=SimpleNamespace(origin=str(self.root / 'openpilot/__init__.py'))):
      report = perf.metadata()
    self.assertEqual(report['sourceRoot'], str(self.root.resolve()))
    self.assertEqual(report['sourceBinding'], 'imported_openpilot')
    self.assertTrue(report['declaredRootMatchesImported'])
    self.assertEqual(report['tool']['path'], str(Path(perf.__file__).resolve()))
    self.assertNotIn('tools/diagnostics/performance.py', report['sourceSha256'])

  def test_explicit_metadata_root_reports_import_origin_mismatch(self):
    (self.root / 'openpilot/cereal').mkdir(parents=True)
    (self.root / 'openpilot/cereal/log.capnp').write_text('schema fixture')
    with patch.object(perf.importlib.util, 'find_spec', return_value=SimpleNamespace(origin='/other/openpilot/__init__.py')):
      report = perf.metadata(self.root)
    self.assertEqual(report['sourceBinding'], 'explicit')
    self.assertFalse(report['declaredRootMatchesImported'])


if __name__ == '__main__':
  unittest.main()
