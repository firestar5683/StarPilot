"""Completed-route evaluation only; exports causal model snapshots and measured steering.
Never imported by RoadScore. No future labels are sent back to the runtime.
"""
import json,os
from pathlib import Path
import numpy as np
from openpilot.tools.lib.logreader import _LogFileReader
from core import Conductor
R=Path('/data/roadscore');O=R/'results/unattended';O.mkdir(exist_ok=True)
for route in sorted({p.name.rsplit('--',1)[0] for p in (R/'routes').glob('*--0')}):
 rows=[];cars=[];poses=[];origin=None;speed=0.;c=Conductor(handoff=bool(os.environ.get('HANDOFF')),threshold=float(os.environ.get('CURVE_THRESHOLD','.8')))
 for folder in sorted((R/'routes').glob(route+'--*'),key=lambda x:int(x.name.rsplit('--',1)[1])):
  for e in _LogFileReader(str(folder/'rlog.zst'),sort_by_time=True):
   if origin is None:origin=e.logMonoTime
   t=(e.logMonoTime-origin)/1e9;k=e.which()
   if k=='carState':
    speed=e.carState.vEgo;cars.append([t,speed,e.carState.steeringAngleDeg])
   elif k=='livePose' and e.valid:
    p=e.livePose
    try:poses.append([t,*p.angularVelocityDevice.value])
    except Exception:pass
   elif k=='modelV2' and e.valid:
    m=e.modelV2
    if len(m.orientationRate.t)!=33:continue
    model={'mono':e.logMonoTime,'eof':m.timestampEof,'t':list(m.orientationRate.t),'yaw':list(m.orientationRate.z),'v':list(m.velocity.x)}
    age=(model['mono']-model['eof'])/1e9;tt=np.array(model['t'])-age;lat=np.array(model['yaw'])*model['v'];good=(tt>=1)&(tt<=8)&(np.array(model['v'])>=3)
    eligible=age>=0 and age<=.5 and speed>=3 and bool(good.any()) and np.isfinite(lat).all()
    i=np.where(good)[0][np.argmax(abs(lat[good]))] if eligible else 0
    s=c.update(t,model,speed)
    rows.append({'t':t,'speed':speed,'candidate_strength':float(abs(lat[i])) if eligible else 0,'candidate_peak':float(t+tt[i]) if eligible else None,'candidate_sign':int(np.sign(lat[i])) if eligible else 0,'since':c.since,**s})
  print(route,folder.name,len(rows),flush=True)
 np.savez_compressed(O/(route+'_motion.npz'),cars=np.asarray(cars),poses=np.asarray(poses))
 (O/(route+(('_threshold'+os.environ['CURVE_THRESHOLD']+'_detector.json') if os.environ.get('CURVE_THRESHOLD') else ('_handoff_detector.json' if os.environ.get('HANDOFF') else '_detector.json')))).write_text(json.dumps(rows))
 print('DONE',route,len(rows),len(poses),flush=True)
