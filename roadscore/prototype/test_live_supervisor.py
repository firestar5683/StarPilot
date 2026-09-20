from dataclasses import replace
from unittest.mock import Mock
import pytest
from live_supervisor import Observation,Authorization,LiveSupervisor,blocked_reason
from live_controller import LiveController

GOOD=Observation(10.,True,True,True,True,True,True,'baseline','car',True)
AUTH=Authorization('baseline','car',True,True)

def make():
    calls=Mock()
    return LiveSupervisor(calls.prepare,calls.start_app,calls.stop,clock=lambda:10.),calls

@pytest.mark.parametrize('field,value',[('monotonic',8.),('monotonic',11.),('monotonic',float('nan')),('parked',False),('driving_model_local',False),('model_fresh',False),('car_fresh',False),('modeld_healthy',False),('device_healthy',False),('chestnut_healthy',False),('baseline_id','different'),('car_id','different')])
def test_fail_closed_before_process_start(field,value):
    sup,calls=make()
    with pytest.raises(RuntimeError):sup.enable(replace(GOOD,**{field:value}),AUTH)
    calls.prepare.assert_not_called()

def test_capability_not_implied_by_car_connection():
    sup,calls=make()
    with pytest.raises(RuntimeError):sup.enable(GOOD,replace(AUTH,coexistence_verified=False))
    calls.prepare.assert_not_called()

def test_gate_then_health_failure_stops_only_owned_callbacks():
    sup,calls=make();sup.enable(GOOD,AUTH)
    sup.tick(GOOD,AUTH,worker_healthy=True,accepted_ready=True)
    calls.start_app.assert_not_called()
    with pytest.raises(RuntimeError):sup.confirm_driver_ready('previous-session',GOOD,AUTH)
    sup.confirm_driver_ready(sup.session_id,GOOD,AUTH)
    assert sup.state=='STARTING'
    sup.tick(replace(GOOD,parked=False),AUTH,worker_healthy=True,app_ready=True)
    assert sup.state=='LIVE'
    sup.tick(replace(GOOD,model_fresh=False),AUTH,worker_healthy=True)
    calls.stop.assert_called_once();assert sup.state=='COLD'

def test_movement_before_ready_stops_preparation():
    sup,calls=make();sup.enable(GOOD,AUTH)
    sup.tick(replace(GOOD,parked=False),AUTH,worker_healthy=True)
    calls.stop.assert_called_once();calls.start_app.assert_not_called()

def test_controller_off_ignores_missing_health_and_only_stops_adapter():
    adapter=Mock();adapter.status.return_value={'enabled':False,'state':'COLD'}
    adapter.health_and_authorization.side_effect=RuntimeError('stale')
    controller=LiveController(adapter=adapter,clock=lambda:10.)
    controller.set_enabled(False);adapter.stop_owned.assert_called_once()
    with pytest.raises(RuntimeError):controller.set_enabled(True)
    adapter.enable.assert_not_called()

def test_missing_adapter_unavailable():
    controller=LiveController()
    assert not controller.status()['available'] and not controller.status()['can_enable']
    with pytest.raises(RuntimeError):controller.set_enabled(True)
    assert controller.set_enabled(False)['enabled'] is False
