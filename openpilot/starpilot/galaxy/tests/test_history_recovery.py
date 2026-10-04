from unittest.mock import Mock
import tempfile
import unittest
from pathlib import Path
from openpilot.starpilot.galaxy.drive_stats import DriveStatsOwner, MAX_RETRY_ATTEMPTS
from openpilot.starpilot.galaxy.tests.test_drive_stats import History, route, analyzed, NOW


class HistoryRecoveryTest(unittest.TestCase):
  def test_retry_budget_survives_restart_and_changed_sources_recover(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory) / 'logs'
      root.mkdir()
      store = Path(directory) / 'cache.json'
      selected = route('abc')
      segment = root / 'abc--0'
      segment.mkdir()
      source = segment / 'rlog.zst'
      source.write_bytes(b'bad')
      now = [NOW]
      calls = []

      def analyzer(root, selected, permitted):
        calls.append(selected['routeId'])
        result = analyzed(root, selected, permitted)
        if source.read_bytes() == b'bad':
          result.update(complete=False, reason='Invalid compressed recording')
        return result

      def owner():
        return DriveStatsOwner(
          root=root, store=store, history=Mock(wraps=History(root, [selected])), analyzer=analyzer, permitted=lambda: True,
          clock=lambda: now[0], monotonic=lambda: now[0]
        )

      for _ in range(MAX_RETRY_ATTEMPTS):
        current = owner()
        current._run()
        current.close()
        now[0] += 3601
      current = owner()
      current._run()
      self.assertEqual(len(calls), MAX_RETRY_ATTEMPTS)
      self.assertEqual(current._snapshot_locked()['analysis']['state'], 'ready')
      self.assertEqual(current._snapshot_locked()['analysis']['quarantined'], 1)
      source.write_bytes(b'repaired')
      current._run()
      self.assertEqual(len(calls), MAX_RETRY_ATTEMPTS + 1)
      self.assertEqual(current._snapshot_locked()['totals']['drives'], 1)
      self.assertFalse(current._failures)
      current.close()

  def test_interruption_does_not_consume_failure_budget(self):
    with tempfile.TemporaryDirectory() as directory:
      active = [True]

      def analyzer(root, selected, permitted):
        active[0] = False
        return {'routeId': selected['routeId'], 'complete': False, 'reason': 'Analysis cancelled'}

      current = DriveStatsOwner(
        root=Path(directory),
        store=Path(directory) / 'cache.json',
        history=Mock(wraps=History(Path(directory), [route('abc')])),
        analyzer=analyzer,
        permitted=lambda: active[0],
        monotonic=lambda: NOW if active[0] else NOW + 1,
      )
      current._run()
      self.assertFalse(current._failures)
      current.close()


class RlogRecoveryTest(unittest.TestCase):
  def test_complete_rlog_recovers_gapped_qlog_without_source_mismatch(self):
    from openpilot.starpilot.galaxy.drive_analysis import analyze_route
    from openpilot.starpilot.galaxy.tests.test_drive_analysis import BASE, DriveAnalysisTest, event, selection, write
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory).resolve()
      def sample(stamp):
        return DriveAnalysisTest.sample(Mock(wraps=self), stamp, 5, True)
      qlog = [*sample(BASE), *sample(BASE + 2_000_000_000), event('sentinel', BASE + 2_000_000_000, type='endOfRoute')]
      segment = write(root, 0, qlog, kind='qlog')
      rlog = [*sample(BASE), *sample(BASE + 500_000_000), *sample(BASE + 1_000_000_000),
              *sample(BASE + 1_500_000_000), *sample(BASE + 2_000_000_000),
              event('sentinel', BASE + 2_000_000_000, type='endOfRoute')]
      import zstandard as zstd
      (root / segment['segmentName'] / 'rlog.zst').write_bytes(zstd.compress(b''.join(item.to_bytes() for item in rlog)))
      segment['files']['rlog'] = True
      result = analyze_route(root, selection(segment), permitted=lambda: True)
      self.assertTrue(result['complete'], result)
      self.assertEqual(result['durationSeconds'], 2)
      self.assertEqual(result['distanceMeters'], 10)
