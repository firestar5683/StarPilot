from dataclasses import replace
import fcntl
import json
from pathlib import Path
import queue
import sys
from types import SimpleNamespace
from unittest.mock import Mock,patch
import pytest
from live_supervisor import Observation,Authorization
from live_target_daemon import Engine
from live_owned_processes import OwnedLiveProcesses
from live_target_adapter import TargetAdapter

GOOD=Observation(10.,True,True,True,True,True,True,'baseline','car',True)
AUTH=Authorization('baseline','car',True,True)

class Collector:
    def __init__(self):self.observation=GOOD;self.authorization=AUTH;self.last_snapshot={'diagnostic_healthy':True}
    def collect(self):return self.observation,self.authorization

@pytest.fixture
def engine(tmp_path):
    owned=Mock();owned.folder=None
    owned.health.return_value=dict(worker_healthy=True,accepted_ready=True,app_healthy=True,app_ready=False)
    result=Engine(tmp_path,Collector(),owned,clock=lambda:10.);result.refresh();return result

def test_diagnostic_not_circular_but_cannot_play(engine):
    engine.collector.authorization=replace(AUTH,coexistence_verified=False,user_authorized=False)
    engine.command({'command':'diagnostic'})
    engine.owned.prepare.assert_called_once_with(engine.supervisor.session_id,diagnostic=True)
    engine.tick();assert engine.supervisor.state=='READY'
    with pytest.raises(RuntimeError,match='cannot start playback'):
        engine.command({'command':'driver_ready','session_id':engine.supervisor.session_id})
    engine.owned.start_app.assert_not_called()

def test_diagnostic_rejects_bad_preflight_and_stops_on_movement(engine):
    engine.collector.last_snapshot['diagnostic_healthy']=False
    with pytest.raises(RuntimeError):engine.command({'command':'diagnostic'})
    engine.owned.prepare.assert_not_called()
    engine.collector.last_snapshot['diagnostic_healthy']=True
    engine.command({'command':'diagnostic'})
    engine.collector.observation=replace(GOOD,parked=False);engine.tick()
    engine.owned.stop_owned.assert_called_once()

def test_production_requires_auth_and_explicit_current_driver_confirmation(engine):
    engine.collector.authorization=replace(AUTH,coexistence_verified=False)
    with pytest.raises(RuntimeError):engine.command({'command':'enable'})
    engine.collector.authorization=AUTH;engine.command({'command':'enable'});engine.tick()
    engine.owned.start_app.assert_not_called()
    with pytest.raises(RuntimeError):engine.command({'command':'driver_ready','session_id':'old'})
    engine.command({'command':'driver_ready','session_id':engine.supervisor.session_id,'audible':True})
    engine.owned.start_app.assert_called_once_with(engine.supervisor.session_id,audible=True)

def test_stop_priority_cancels_pending_start_and_signals_before_tick(engine):
    response=queue.Queue();engine.commands.put(({'command':'enable'},response))
    assert engine.command({'command':'stop'})['state']=='STOPPING'
    engine.owned.signal_stop.assert_called_once()
    engine.tick();assert 'Canceled' in response.get()['error']
    engine.owned.prepare.assert_not_called()

def test_health_read_failure_stops_active_session(engine):
    engine.command({'command':'enable'})
    engine.collector.collect=Mock(side_effect=RuntimeError('stale collector'))
    engine.tick();engine.owned.stop_owned.assert_called_once()

def fixture_owned(tmp_path):
    (tmp_path/'generated').mkdir();(tmp_path/'runtime.json').write_text(json.dumps({'identity':'kpop_control'}))
    popen=Mock();popen.return_value.pid=999999;popen.return_value.poll.return_value=None
    return OwnedLiveProcesses(tmp_path,popen=popen),popen

def test_direct_worker_clean_environment_and_verified_bundle(tmp_path,monkeypatch):
    owned,popen=fixture_owned(tmp_path)
    monkeypatch.setenv('OPENPILOT_PREFIX','replay');monkeypatch.setenv('PARAMS_ROOT','fake');monkeypatch.setenv('AM_POWER_LIMIT','45')
    with patch.dict(sys.modules,cached_composition=SimpleNamespace(validate_bank=Mock(),digest=lambda p:'a'*64)):
        owned.prepare('session-a',diagnostic=True)
    command=popen.call_args.args[0];env=popen.call_args.kwargs['env']
    assert command==['bash',str(tmp_path/'prototype/run_worker.sh')]
    assert 'OPENPILOT_PREFIX' not in env and 'PARAMS_ROOT' not in env and 'AM_POWER_LIMIT' not in env
    assert env['ROADSCORE_FORCE_MUTE']=='1' and env['ROADSCORE_RESIDENT']=='1'
    assert not owned.accepted_ready()
    g=tmp_path/'generated';(g/'worker_ready').write_text('ace')
    (g/'ace_worker_state.json').write_text(json.dumps({'pid':owned.worker.pid,'phase':'READY'}))
    meta={'generation_seed':owned.seed,'prepared_profile':'prism','composition_policy':'hook-cache-v1','conditioning_bank_sha256':'a'*64,'duration':110}
    (g/'ace_initial.json').write_text(json.dumps(meta));assert owned.accepted_ready()
    with pytest.raises(RuntimeError):owned.start_app('session-a',audible=True)
    (g/'ace_initial.json').write_text(json.dumps({**meta,'generation_seed':owned.seed+1}));assert not owned.accepted_ready()
    with patch('live_owned_processes.os.killpg') as kill:owned.stop_owned();kill.assert_called_once_with(999999,15)

def test_external_gpu_owner_not_stopped_or_overwritten(tmp_path):
    owned,popen=fixture_owned(tmp_path)
    ready=tmp_path/'generated/worker_ready';ready.write_text('external')
    with (tmp_path/'generated/gpu.lock').open('a') as external:
        fcntl.flock(external,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with patch('live_owned_processes.os.killpg') as kill,pytest.raises(BlockingIOError):owned.prepare('blocked')
        kill.assert_not_called()
    popen.assert_not_called();assert ready.read_text()=='external'

def test_target_client_never_spawns_or_ssh_on_mac(tmp_path):
    adapter=TargetAdapter(tmp_path)
    with patch('live_target_adapter.subprocess.Popen') as popen:
        assert adapter.status()['available'] is False
        assert adapter.stop_owned()['state']=='COLD'
        with pytest.raises(RuntimeError,match='only on the comma'):adapter.prepare_diagnostic()
        popen.assert_not_called()

def test_stop_while_preflight_prevents_late_child_start(tmp_path):
    owned,popen=fixture_owned(tmp_path)
    def validation(*args,**kwargs):owned.signal_stop()
    with patch.dict(sys.modules,cached_composition=SimpleNamespace(validate_bank=validation,digest=lambda p:'a'*64)):
        with pytest.raises(RuntimeError,match='Stop requested'):owned.prepare('canceled')
    popen.assert_not_called()

def test_production_app_uses_live_namespace_preserves_prior_current(tmp_path):
    owned,popen=fixture_owned(tmp_path)
    with patch.dict(sys.modules,cached_composition=SimpleNamespace(validate_bank=Mock(),digest=lambda p:'a'*64)):
        owned.prepare('production')
    current=tmp_path/'results/current';current.mkdir();(current/'evidence').write_text('keep')
    with patch.object(owned,'accepted_ready',return_value=True):owned.start_app('production',audible=False)
    command=popen.call_args.args[0];env=popen.call_args.kwargs['env']
    assert command[-2:]==['--input','live'] and '--audible' not in command
    assert 'OPENPILOT_PREFIX' not in env and 'ZMQ' not in env
    assert (owned.folder/'previous_current/evidence').read_text()=='keep'
    with patch('live_owned_processes.os.killpg'):owned.stop_owned()
