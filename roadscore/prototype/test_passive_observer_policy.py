from copy import deepcopy
import pytest
from passive_observer_policy import MODE,evaluate_passive_observer,authorization_mode_matches


def healthy():
    return {'car_identity':{'passive':True,'notCar':False,'dashcamOnly':False,'safety':[{'model':'noOutput','param':0}]},
            'pandas':[{'safetyModel':'noOutput','controlsAllowed':False,'faults':[],'safetyRxChecksInvalid':False}],
            'ages':{key:0.1 for key in ('pandaStates','carState','carControl','selfdriveState')},
            'valid':{key:True for key in ('pandaStates','carState','carControl','selfdriveState')},
            'car':{'canValid':True,'canTimeout':False},
            'control':{'enabled':False,'latActive':False,'longActive':False},
            'selfdrive_state':{'enabled':False,'active':False}}


def test_safety_eligible_is_not_authorization_or_ready():
    result=evaluate_passive_observer(healthy(),MODE)
    assert result['safety_eligible'] and result['engagement_available'] is False
    assert 'ready' not in result and 'coexistence_verified' not in result
    assert not authorization_mode_matches({},result)
    assert authorization_mode_matches({'live_mode':MODE,'passive_mode_identity':result['mode_identity']},result)

@pytest.mark.parametrize('part,field,value',[
    ('car_identity','passive',False),('car_identity','passive',1),('car_identity','notCar',True),
    ('car_identity','dashcamOnly',None),('control','enabled',True),('control','latActive',True),
    ('control','longActive',True),('control','latActive',None),('selfdrive_state','enabled',True),
    ('selfdrive_state','active',True),('car','canValid',False),('car','canTimeout',True)])
def test_active_missing_or_invalid_vehicle_evidence_rejected(part,field,value):
    snapshot=healthy();snapshot[part][field]=value
    assert not evaluate_passive_observer(snapshot,MODE)['safety_eligible']

@pytest.mark.parametrize('field,value',[('safetyModel','tesla'),('safetyModel','silent'),('controlsAllowed',True),
    ('controlsAllowed',None),('faults',['interruptRateCan2']),('faults',None),('safetyRxChecksInvalid',True)])
def test_actual_panda_invariants(field,value):
    snapshot=healthy();snapshot['pandas'][0][field]=value
    result=evaluate_passive_observer(snapshot,MODE)
    assert not result['safety_eligible'] and result['mode_identity'] is None

@pytest.mark.parametrize('topic',('pandaStates','carState','carControl','selfdriveState'))
@pytest.mark.parametrize('age',(-.01,3.,float('nan'),float('inf'),None))
def test_source_age_not_collector_liveness(topic,age):
    snapshot=healthy();snapshot['ages'][topic]=age
    assert not evaluate_passive_observer(snapshot,MODE)['safety_eligible']


def test_toggle_or_offroad_nooutput_cannot_substitute_actual_passive_cp():
    snapshot=healthy();snapshot['car_identity']['passive']=False
    snapshot['params']={'OpenpilotEnabledToggle':False,'AlwaysOnLateral':False};snapshot['offroad']=True
    assert not evaluate_passive_observer(snapshot,MODE)['safety_eligible']


def test_all_pandas_configs_and_authorization_pin():
    snapshot=healthy();baseline=evaluate_passive_observer(snapshot,MODE)
    record={'live_mode':MODE,'passive_mode_identity':baseline['mode_identity']}
    snapshot['pandas'].append(deepcopy(snapshot['pandas'][0]))
    assert not authorization_mode_matches(record,evaluate_passive_observer(snapshot,MODE))
    snapshot['pandas'][1]['safetyModel']='tesla'
    assert not evaluate_passive_observer(snapshot,MODE)['safety_eligible']
    snapshot=healthy();snapshot['car_identity']['safety'][0]['model']='tesla'
    assert not evaluate_passive_observer(snapshot,MODE)['safety_eligible']


def test_explicit_mode_no_auto_inference_and_input_unchanged():
    snapshot=healthy();before=deepcopy(snapshot)
    assert not evaluate_passive_observer(snapshot,None)['safety_eligible']
    evaluate_passive_observer(snapshot,MODE);assert snapshot==before

@pytest.mark.parametrize('field',('car_identity','ages','valid','car','control','selfdrive_state'))
def test_malformed_fields_fail_closed(field):
    snapshot=healthy();snapshot[field]=None
    assert not evaluate_passive_observer(snapshot,MODE)['safety_eligible']


def elm_baseline():
    snapshot=healthy();snapshot['pandas'][0].update(safetyModel='elm327',safetyParam=1)
    snapshot['passive_startup']={'controls_ready':False,'firmware_query_done':True,'obd_multiplexing_enabled':False}
    return snapshot


def test_exact_upstream_passive_elm_state_is_diagnostic_not_tx_disabled():
    result=evaluate_passive_observer(elm_baseline(),MODE)
    assert result['safety_eligible'] and result['diagnostic_tx_possible']
    assert result['actual_passive_variant']=='elm327-diagnostic'
    assert not result['engagement_available']
    nooutput=evaluate_passive_observer(healthy(),MODE)
    assert result['mode_identity']!=nooutput['mode_identity']

@pytest.mark.parametrize('field,value',[('controls_ready',True),('controls_ready',None),('firmware_query_done',False),('firmware_query_done',None),('obd_multiplexing_enabled',True),('obd_multiplexing_enabled',None)])
def test_elm_requires_exact_observed_startup_conditions(field,value):
    snapshot=elm_baseline();snapshot['passive_startup'][field]=value
    assert not evaluate_passive_observer(snapshot,MODE)['safety_eligible']

@pytest.mark.parametrize('parameter',(0,2,None,True,'1'))
def test_elm_parameter_mismatch_rejected(parameter):
    snapshot=elm_baseline();snapshot['pandas'][0]['safetyParam']=parameter
    assert not evaluate_passive_observer(snapshot,MODE)['safety_eligible']


def test_elm_does_not_waive_faults_or_active_flags():
    for field,value in [('faults',['interruptRateCan2']),('controlsAllowed',True),('safetyRxChecksInvalid',True)]:
        snapshot=elm_baseline();snapshot['pandas'][0][field]=value
        assert not evaluate_passive_observer(snapshot,MODE)['safety_eligible']
    snapshot=elm_baseline();snapshot['control']['latActive']=True
    assert not evaluate_passive_observer(snapshot,MODE)['safety_eligible']
    snapshot=elm_baseline();snapshot['pandas'].append(deepcopy(healthy()['pandas'][0]))
    assert not evaluate_passive_observer(snapshot,MODE)['safety_eligible']
