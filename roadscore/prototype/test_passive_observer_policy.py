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
