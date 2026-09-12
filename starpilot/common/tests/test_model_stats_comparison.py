"""Synthetic deterministic comparisons and loaded-stream provenance."""
import hashlib
import io
import json
import pickle
from unittest.mock import patch
import pytest
from openpilot.starpilot.common.model_stats import Reducer, Sample, parse_identity
from openpilot.starpilot.common.model_stats_identity import LoadedDigest, loaded_identity
from openpilot.starpilot.common.model_stats_store import Store, read_stats


def test_loaded_digest_is_consumed_content_not_filename():
  for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
    content = pickle.dumps({'weights': b'a' * 10000}, protocol=protocol)
    source = LoadedDigest(io.BytesIO(content))
    assert pickle.load(source) == {'weights': b'a' * 10000}
    identity = loaded_identity('builtin', False)
    source.apply(identity)
    assert identity['artifact'] == 'loaded-sha256:' + hashlib.sha256(content).hexdigest()
    assert identity['artifactVerified'] is True
  broken = LoadedDigest(io.BytesIO(b'abc'))
  broken.digest = None
  assert broken.read() == b'abc'
  identity = loaded_identity('builtin', False)
  broken.apply(identity)
  assert not identity['artifactVerified']


def test_oob_readinto_is_part_of_digest():
  source = LoadedDigest(io.BytesIO(b'header-weights'))
  assert source.read(7) == b'header-'
  weights = bytearray(7)
  assert source.readinto(weights) == 7
  identity = loaded_identity('gpu', True)
  source.apply(identity)
  assert identity['artifact'] == 'loaded-sha256:' + hashlib.sha256(b'header-weights').hexdigest()


def test_period_revision_mode_and_pair_separation(tmp_path):
  path = tmp_path / 'stats.sqlite'
  store = Store(path)
  now = 100 * 86400
  for i, (days, revision, mode, pair) in enumerate([(1, 'a', 'full', False), (10, 'b', 'full', False), (40, 'a', 'full', False), (1, 'a', 'aol', False), (1, 'a', 'full', True)]):
    roles = [{'modelId': 'model', 'backend': 'comma', 'artifact': revision, 'artifactVerified': True}]
    if pair:
      roles.append({'modelId': 'long', 'backend': 'chestnut', 'artifact': 'c', 'artifactVerified': True})
    owner = parse_identity(json.dumps({'version': 1, 'roles': roles}))
    reducer = Reducer()
    for t in [1, 1.1]:
      reducer.update(Sample(t, owner, 10, enabled=mode == 'full', aol=mode == 'aol', lat=True))
    store.checkpoint(str(i), now-days*86400, reducer.snapshot(), complete=True, now=now-days*86400)
  store.close()
  with patch('openpilot.starpilot.common.model_stats_store.time.time', return_value=now):
    week = read_stats(path, period='7')
    month = read_stats(path, period='30')
    alltime = read_stats(path)
    lateral = read_stats(path, period='7', mode='aol')
  assert week['historyTotal'] == 3
  assert month['historyTotal'] == 4
  assert alltime['historyTotal'] == 5
  assert len(week['comparisons']) == 3
  assert len(alltime['comparisons']) == 4
  assert len(lateral['comparisons']) == 1
  assert all(row['mode'] == 'aol' for row in lateral['history'])
  assert week['models']['model']['stats']['assistedMeters'] == pytest.approx(2)
  assert week['pairs'][0]['stats']['assistedMeters'] == pytest.approx(1)
  assert read_stats(path, period='7', offset=2, limit=1)['hasMore'] is False
  with pytest.raises(ValueError):
    read_stats(path, period='bad')
