"""SYNTHETIC fixtures, real candidate imports; no daemon, network or production DB.
Tests assert desired behavior and intentionally fail when review defects reproduce.
"""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(tempfile.mkdtemp(prefix='model-stats-review-'))
import atexit, shutil
atexit.register(shutil.rmtree, OUT)
sys.dont_write_bytecode = True
# Resolve openpilot namespace to this candidate without importing native conftest.
pkg = types.ModuleType('openpilot')
pkg.__path__ = [str(ROOT)]
sys.modules['openpilot'] = pkg
from openpilot.starpilot.system.model_statsd import Telemetry
from openpilot.starpilot.common.model_stats import Reducer, parse_identity
from openpilot.starpilot.common.model_stats_store import Store, read_stats
from openpilot.starpilot.system.the_galaxy.model_stats_api import ModelStatsAPI
from types import SimpleNamespace as NS

OWNER = parse_identity(json.dumps({'version': 1, 'roles': [{'modelId': 'synthetic-a', 'artifact': 'synthetic.pkl', 'backend': 'synthetic'}]}))
PAIR = parse_identity(json.dumps({'version': 1, 'roles': [{'modelId': m, 'artifact': 'synthetic.pkl', 'backend': 'synthetic'} for m in ['synthetic-a', 'synthetic-b']]}))

def save(name, payload):
    (OUT / (name + '.json')).write_text(json.dumps({'fixture': 'SYNTHETIC — not vehicle evidence', **payload}, indent=2) + '\n')

def frame(tel, t, enabled=True, owner=OWNER, selfdrive=True, car=True):
    stamp = round(t * 1e9)
    fields = {'deviceState': NS(started=True), 'carControl': NS(latActive=enabled, longActive=enabled), 'starpilotCarState': NS(alwaysOnLateralEnabled=False), 'modelV2': NS(), 'starpilotModelV2': NS(modelMonoTime=stamp, runtimeIdentity=owner)}
    if selfdrive:
        fields['selfdriveState'] = NS(enabled=enabled)
    for name, data in fields.items():
        assert tel.feed(name, stamp, True, data) is None
    if car:
        return tel.feed('carState', stamp, True, NS(vEgo=10, canValid=True, gearShifter='drive', steeringPressed=False, brakePressed=False, gasPressed=False))

def replay(delayed):
    tel, reducer = Telemetry(), Reducer()
    trace = []
    for t, enabled, sd in [(1.0, True, True), (1.1, False, True), (1.15, False, False), (1.2, False, True)]:
        if delayed and t == 1.15:
            tel.feed('selfdriveState', 1_020_000_000, True, NS(enabled=True))
        sample = frame(tel, t, enabled, selfdrive=sd)
        reducer.update(sample)
        trace.append({'carStateTime': t, 'cachedSelfdriveTime': tel.latest['selfdriveState'][0], 'sampleEnabled': sample.enabled, 'usable': sample.usable})
    return {'trace': trace, 'snapshot': reducer.snapshot(), 'disengagements': sum(r['disengagements'] for r in reducer.metrics.values())}

def test_delayed_selfdrive_does_not_duplicate_disengagement():
    control, delayed = replay(False), replay(True)
    save('delayed-selfdrive', {'control': control, 'delayed': delayed})
    assert control['disengagements'] == 1
    assert delayed['disengagements'] == 1

def test_missing_carstate_does_not_keep_recording():
    tel, reducer = Telemetry(), Reducer()
    reducer.update(frame(tel, 1.0))
    reducer.update(frame(tel, 1.1))
    with tempfile.TemporaryDirectory(prefix='synthetic-heartbeat-', dir=OUT) as tmp:
        db = Path(tmp) / 'stats.sqlite'
        store = Store(db)
        try:
            store.checkpoint('synthetic-drive', 1000, reducer.snapshot(), now=1000)
            with patch('openpilot.starpilot.common.model_stats_store.time.time', return_value=1031):
                stale = read_stats(db)
            # Main loop keeps checkpointing even with no new carState sample.
            for t in (11.1, 21.1, 31.1):
                assert frame(tel, t, car=False) is None
                store.checkpoint('synthetic-drive', 1000, reducer.snapshot(), now=999 + t)
            with patch('openpilot.starpilot.common.model_stats_store.time.time', return_value=1031):
                heartbeat = read_stats(db)
            save('missing-carstate', {'withoutHeartbeat': stale, 'withHeartbeat': heartbeat, 'lastSampleMonotonic': reducer.last_t, 'lastNonCarStateMonotonic': 31.1, 'sequence': reducer.sequence})
        finally:
            store.close()
    assert stale['trackingStatus'] == 'inactive'
    assert heartbeat['trackingStatus'] != 'recording'
