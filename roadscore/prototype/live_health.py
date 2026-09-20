"""Read-only live observations. Authorization and measured limits are external inputs."""
import hashlib
import json
import math
import os
from pathlib import Path
import time
from live_supervisor import Observation, Authorization

SERVICES=('carState','modelV2','selfdriveState','pandaStates','deviceState','managerState','liveCalibration','carControl','controlsState','onroadEvents')
METRICS=('model_execution_ms','model_drop_percent','model_age_ms','control_age_ms','cpu_percent','max_temp_c','modeld_cpu_percent','controlsd_cpu_percent')


def read_json(path):
  try:return json.loads(Path(path).read_text())
  except (OSError,ValueError):return {}


def finite(value):
  return type(value) in (float,int) and math.isfinite(value) and value>=0


def identity(value):
  return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def evaluate(snapshot, record, now):
  ages=snapshot.get('ages',{});valid=snapshot.get('valid',{})
  # These are stale-input guards, not performance/coexistence acceptance limits.
  fresh={k:valid.get(k) is True and finite(ages.get(k)) and ages[k]<= (2. if k in ('deviceState','managerState','liveCalibration','pandaStates','onroadEvents') else .5) for k in SERVICES}
  car=snapshot.get('car',{});device=snapshot.get('device',{});pandas=snapshot.get('pandas',[])
  safety=bool(pandas) and all(not p.get('faults') and p.get('safetyRxChecksInvalid') is False and p.get('safetyModel') not in (None,'silent','noOutput') for p in pandas)
  car_ok=fresh['carState'] and car.get('canValid') is True and car.get('canTimeout') is False and finite(car.get('vEgo'))
  parked=car_ok and car.get('standstill') is True and car['vEgo']<=.1
  calibration=fresh['liveCalibration'] and snapshot.get('calibration')=='calibrated'
  processes=snapshot.get('processes',{});running=all(processes.get(k,{}).get('running') is True for k in ('modeld','controlsd'))
  local=snapshot.get('driving_model_local') is True and running
  model_ok=fresh['modelV2'] and snapshot.get('model_geometry_valid') is True and finite(snapshot.get('metrics',{}).get('model_execution_ms'))
  device_ok=fresh['deviceState'] and device.get('thermalStatus')=='ok' and finite(snapshot.get('metrics',{}).get('max_temp_c'))
  events=snapshot.get('events',[])
  event_fault=any(e.get('immediateDisable') or e.get('softDisable') for e in events)
  hard=all(fresh.values()) and car_ok and calibration and safety and running and local and model_ok and device_ok and not event_fault and snapshot.get('chestnut_present') is True
  matched=(record.get('schema')=='roadscore-live-authorization-v1' and record.get('measured_parked') is True
           and bool(snapshot.get('car_id')) and bool(snapshot.get('baseline_id'))
           and record.get('car_id')==snapshot['car_id'] and record.get('baseline_id')==snapshot['baseline_id'])
  bounds=record.get('bounds',{});metrics=snapshot.get('metrics',{})
  exceeded=[key for key in METRICS if not finite(metrics.get(key)) or not finite(bounds.get(key+'_max')) or metrics[key]>bounds[key+'_max']]
  link=snapshot.get('link',{});link_age=now-link.get('monotonic',float('-inf'))
  link_fresh=finite(link_age) and finite(bounds.get('link_max_age_s')) and link_age<=bounds['link_max_age_s']
  gpu=link.get('healthy') is True and snapshot.get('link_owner_verified') is True and link_fresh
  accepted=matched and not exceeded
  auth=Authorization(str(record.get('baseline_id','')),str(record.get('car_id','')),
                     record.get('coexistence_verified') is True,record.get('user_authorized') is True)
  obs=Observation(now,parked,model_ok,car_ok,hard and accepted,device_ok and accepted,gpu,
                  snapshot.get('baseline_id',''),snapshot.get('car_id',''),local)
  snapshot.update(diagnostic_healthy=bool(hard and parked),fresh=fresh,measured_bounds_accepted=accepted,
                  missing_or_exceeded_metrics=exceeded,authorization_matches=matched,link_fresh=link_fresh,
                  production_healthy=bool(hard and accepted and gpu))
  return obs,auth


class LiveHealth:
  def __init__(self,root,*,reader=None,clock=time.monotonic,proc=Path('/proc'),params=None,sm=None):
    self.root=Path(root);self.clock=clock;self.proc=Path(proc);self.reader=reader
    self.params=params;self.sm=sm;self.last_snapshot={};self.previous_cpu={}

  def _cpu(self,pid,name,now):
    try:
      fields=(self.proc/str(pid)/'stat').read_text().rsplit(') ',1)[1].split()
      args=(self.proc/str(pid)/'cmdline').read_bytes()
      if name.encode() not in args or fields[0]=='Z':return None,False
      ticks=int(fields[11])+int(fields[12]);start=fields[19];old=self.previous_cpu.get(name)
      self.previous_cpu[name]=(pid,start,ticks,now)
      cpu=100*(ticks-old[2])/os.sysconf('SC_CLK_TCK')/(now-old[3]) if old and old[:2]==(pid,start) and now>old[3] else None
      return cpu,True
    except (OSError,ValueError,IndexError):return None,False

  def _read(self,now):
    if self.sm is None:
      if any(os.environ.get(k) for k in ('OPENPILOT_PREFIX','OPENPILOT_ZMQ_NAMESPACE','PARAMS_ROOT','ZMQ','SIMULATION','NOBOARD')):
        raise RuntimeError('Live health refuses replay/simulation IPC or Params overrides')
      from cereal import messaging
      from openpilot.common.params import Params
      self.params=self.params or Params();self.sm=messaging.SubMaster(list(SERVICES))
    self.sm.update(0);sm=self.sm
    from cereal import car
    from openpilot.system.hardware.usb import chestnut_firmware_ready
    from openpilot.starpilot.assets.model_manager import load_model_artifact_metadata
    raw=self.params.get('CarParams')
    if not raw:raise RuntimeError('Actual CarParams unavailable')
    with car.CarParams.from_bytes(raw) as cp:
      car_info={'fingerprint':cp.carFingerprint,'firmware':[{'ecu':str(f.ecu),'address':f.address,'version_sha256':hashlib.sha256(bytes(f.fwVersion)).hexdigest()} for f in cp.carFw],
                'safety':[{'model':str(s.safetyModel),'param':s.safetyParam} for s in cp.safetyConfigs]}
    def text(key):
      value=self.params.get(key);return value.decode() if isinstance(value,bytes) else value
    if not car_info['fingerprint']:raise RuntimeError('Actual car fingerprint unavailable')
    model=text('DrivingModel');version=text('DrivingModelVersion');build=text('GitCommit')
    if not build or not model or not version:raise RuntimeError('Actual software/model identity unavailable')
    payload={k:sm[k].to_dict() for k in SERVICES if k not in ('pandaStates','onroadEvents')}
    pandas=[p.to_dict() for p in sm['pandaStates']];events=[e.to_dict() for e in sm['onroadEvents']]
    source_now=time.clock_gettime(time.CLOCK_BOOTTIME) if hasattr(time,'CLOCK_BOOTTIME') else now
    ages={k:source_now-sm.logMonoTime[k]/1e9 for k in SERVICES};valid={k:bool(sm.valid[k]) for k in SERVICES}
    processes={};cpu={}
    for row in payload['managerState'].get('processes',[]):
      name=row['name'].rsplit('.',1)[-1]
      if name in ('modeld','controlsd'):
        usage,verified=self._cpu(row['pid'],name,now);cpu[name]=usage
        processes[name]={**row,'running':row.get('running') is True and verified}
    m=payload['modelV2'];d=payload['deviceState'];usage=d.get('cpuUsagePercent',[])
    metrics={'model_execution_ms':m['modelExecutionTime']*1000 if finite(m.get('modelExecutionTime')) else None,'model_drop_percent':m.get('frameDropPerc'),
             'model_age_ms':ages['modelV2']*1000,'control_age_ms':ages['carControl']*1000,
             'cpu_percent':max(usage) if usage else None,'max_temp_c':d.get('maxTempC'),
             'modeld_cpu_percent':cpu.get('modeld'),'controlsd_cpu_percent':cpu.get('controlsd')}
    link={};path=self.root/'generated/ace_link.jsonl'
    try:
      with path.open('rb') as stream:
        stream.seek(max(0,path.stat().st_size-65536));lines=stream.read().splitlines()
      link=json.loads(lines[-1])
    except (OSError,ValueError,IndexError):pass
    owner=False
    try:
      pid=int(link['owner_pid']);args=(self.proc/str(pid)/'cmdline').read_bytes()
      state=read_json(self.root/'generated/ace_worker_state.json')
      owner=state.get('pid')==pid and b'/ace_worker.py' in args and state.get('phase') in ('READY','preparing','PREPARING')
      fields=(self.proc/str(pid)/'stat').read_text().rsplit(') ',1)[1].split()
      owner=owner and fields[0]!='Z' and int(fields[19])/os.sysconf('SC_CLK_TCK')<=link['monotonic']<=now
    except (OSError,ValueError,KeyError,IndexError,TypeError):owner=False
    return {'monotonic':now,'car_identity':car_info,'car_id':identity(car_info),'baseline_id':identity({'git':build,'model':model,'version':version}),
            'git_commit':build,'driving_model':model,'driving_model_version':version,'driving_model_local':load_model_artifact_metadata(model).get('uses_external_gpu') is False,
            'chestnut_present':chestnut_firmware_ready(),'model_geometry_valid':len(m.get('position',{}).get('t',[]))==33,'ages':ages,'valid':valid,'car':payload['carState'],'device':d,'pandas':pandas,'events':events,
            'calibration':payload['liveCalibration'].get('calStatus'),'processes':processes,'metrics':metrics,'link':link,'link_owner_verified':bool(owner)}

  def collect(self):
    now=self.clock()
    try:snapshot=self.reader(now) if self.reader else self._read(now)
    except Exception as error:snapshot={'monotonic':now,'error':str(error),'car_id':'','baseline_id':''}
    record=read_json(self.root/'generated/live_authorization.json')
    result=evaluate(snapshot,record,now);self.last_snapshot=snapshot
    return result
