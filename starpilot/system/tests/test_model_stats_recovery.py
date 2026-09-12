"""Synthetic storage faults; no daemon or real vehicle telemetry."""
from openpilot.starpilot.common.model_stats import Reducer, Sample, parse_identity
from openpilot.starpilot.system.model_statsd import Checkpoints
import json


def test_failed_final_checkpoint_retained_across_next_drive(tmp_path):
  from openpilot.starpilot.common.model_stats_store import Store, read_stats
  owner = parse_identity(json.dumps({'version': 1, 'roles': [{'modelId': 'test', 'artifact': 'test', 'backend': 'comma'}]}))
  r = Reducer()
  r.update(Sample(1, owner, 10, enabled=True, lat=True))
  r.update(Sample(1.1, owner, 10, enabled=True, lat=True))
  store = Store(tmp_path / 'stats.sqlite')
  class Fault:
    def checkpoint(self, *a, **kw):
      raise OSError('synthetic full disk')
    def close(self):
      pass
  writer = Checkpoints(lambda: store)
  writer.store = Fault()
  writer.submit('first', 100, r.snapshot(), complete=True)
  assert not writer.flush(1)
  assert 'first' in writer.pending
  writer.submit('next', 200, Reducer().snapshot())
  assert writer.flush(32)
  assert not writer.pending
  result = read_stats(tmp_path / 'stats.sqlite')
  assert result['models']['test']['stats']['assistedMeters'] > .99
  assert next(row for row in result['history'] if row['drive'] == 'first')['complete']
  store.close()
