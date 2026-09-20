"""Read-only passive safety evidence, not vehicle authorization or live readiness.

The collector must still enforce calibration, camera/model validity, local model
placement, CPU/thermal/link bounds, parked coexistence and explicit driver ready.
No Params, control messages, safety modes, or engagement state are modified here.
"""
import hashlib
import json
import math

MODE = 'passive-observer-v1'


def _mapping(value):
    return value if isinstance(value,dict) else {}


def _fresh(snapshot, topic, maximum):
    age=_mapping(snapshot.get('ages')).get(topic)
    return (_mapping(snapshot.get('valid')).get(topic) is True and type(age) in (int,float)
            and math.isfinite(age) and 0<=age<=maximum)


def evaluate_passive_observer(snapshot, requested_mode):
    """Accept only actual nonactuating passive evidence; never infer it from a toggle.

    snapshot adds car_identity.passive/notCar/dashcamOnly to the collector's
    fingerprint/firmware/safety identity, plus raw carControl/selfdriveState dicts
    as `control`/`selfdrive_state`. Freshness uses the collector's source ages.
    """
    snapshot=_mapping(snapshot)
    reasons=[]
    if requested_mode!=MODE:reasons.append('Explicit passive observer mode is required')
    cp=_mapping(snapshot.get('car_identity'))
    if cp.get('passive') is not True:reasons.append('Actual CarParams must be passive')
    if cp.get('notCar') is not False:reasons.append('Actual recognized-car mode is required')
    if type(cp.get('dashcamOnly')) is not bool:reasons.append('Actual dashcamOnly metadata is missing')
    configs=cp.get('safety')
    if not isinstance(configs,list) or not configs or any(not isinstance(s,dict) or s.get('model')!='noOutput' or type(s.get('param')) is not int or s['param']!=0 for s in configs):
        reasons.append('Every configured safety model must be noOutput with zero parameter')
    pandas=snapshot.get('pandas')
    if not isinstance(pandas,list) or not pandas:
        reasons.append('Actual panda safety evidence is missing');pandas=[]
    actual_modes={p.get('safetyModel') for p in pandas if isinstance(p,dict)}
    elm=actual_modes=={'elm327'}
    if len(actual_modes)>1:reasons.append('Mixed panda startup safety modes are not an established passive baseline')
    if elm:
        startup=_mapping(snapshot.get('passive_startup'))
        if startup.get('controls_ready') is not False:reasons.append('ELM passive baseline requires actual ControlsReady=false')
        if startup.get('firmware_query_done') is not True:reasons.append('ELM passive baseline requires completed firmware query')
        if startup.get('obd_multiplexing_enabled') is not False:reasons.append('ELM parameter-1 baseline requires OBD multiplexing disabled')
    for index,panda in enumerate(pandas):
        if not isinstance(panda,dict):reasons.append(f'Panda {index} evidence is malformed');continue
        if panda.get('safetyModel') not in ('noOutput','elm327'):reasons.append(f'Panda {index} is not in a supported passive safety mode')
        if panda.get('safetyModel')=='elm327' and (type(panda.get('safetyParam')) is not int or panda['safetyParam']!=1):
            reasons.append(f'Panda {index} is not the expected ELM327 parameter-1 startup state')
        if panda.get('controlsAllowed') is not False:reasons.append(f'Panda {index} permits or has unknown actuation')
        if panda.get('faults')!=[]:reasons.append(f'Panda {index} fault state is not explicitly clear')
        if panda.get('safetyRxChecksInvalid') is not False:reasons.append(f'Panda {index} safety receive checks are invalid or unknown')
    for topic,maximum in [('pandaStates',2.),('carState',.5),('carControl',.5),('selfdriveState',.5)]:
        if not _fresh(snapshot,topic,maximum):reasons.append(f'{topic} must be valid and fresh')
    car=_mapping(snapshot.get('car'))
    if car.get('canValid') is not True or car.get('canTimeout') is not False:
        reasons.append('Actual car CAN input must be valid without timeout')
    for name,fields in [('control',('enabled','latActive','longActive')),('selfdrive_state',('enabled','active'))]:
        values=_mapping(snapshot.get(name))
        for field in fields:
            if values.get(field) is not False:reasons.append(f'{name}.{field} must be explicitly inactive')
    # Stable mode identity supplements, and never replaces, the complete car and
    # baseline hashes. Runtime freshness/booleans are validated above, not hashed.
    material={'mode':MODE,'passive':cp.get('passive'),'notCar':cp.get('notCar'),
              'dashcamOnly':cp.get('dashcamOnly'),'configured_safety':configs,
              'actual_panda_safety':[{'model':p.get('safetyModel'),'parameter':p.get('safetyParam') if p.get('safetyModel')=='elm327' else 0} if isinstance(p,dict) else None for p in pandas]}
    mode_identity=hashlib.sha256(json.dumps(material,sort_keys=True,separators=(',',':')).encode()).hexdigest() if not reasons else None
    return {'mode':MODE,'safety_eligible':not reasons,'reasons':reasons,'mode_identity':mode_identity,
            'engagement_available':False,'diagnostic_tx_possible':elm,'actual_passive_variant':'elm327-diagnostic' if elm else 'noOutput','label':'Passive observer — vehicle engagement unavailable'}


def authorization_mode_matches(record, assessment):
    """Additional pin only. Does not grant user/coexistence authorization."""
    record=_mapping(record);assessment=_mapping(assessment)
    return (assessment.get('safety_eligible') is True and record.get('live_mode')==MODE
            and isinstance(assessment.get('mode_identity'),str)
            and record.get('passive_mode_identity')==assessment['mode_identity'])
