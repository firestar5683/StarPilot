"""Offline selection/evaluation only. Never imported by runtime."""
import os
import sys,json,math
from pathlib import Path
import numpy as np
from collections import Counter
sys.path.insert(0,'/Users/dominickthompson/starpilot')
from tools.lib.logreader import _LogFileReader
ROOT=Path(__file__).resolve().parents[1]
cache=ROOT/'routes'/os.environ['ROADSCORE_FIXTURE_DONGLE'];result={}
for route in [os.environ['ROADSCORE_OTHER_ROUTE'].split('/')[-1],os.environ['ROADSCORE_CURVE_ROUTE'].split('/')[-1],os.environ['ROADSCORE_ARRIVAL_ROUTE'].split('/')[-1]]:
 origin=None;last_sample=0;models=[];cars=[];nav=[];routes=[];counts=Counter();lastcar=-1
 for folder in sorted(cache.glob(route+'--*'),key=lambda p:int(p.name.rsplit('--',1)[1])):
  for e in _LogFileReader(str(folder/'rlog.zst')):
   if origin is None:origin=e.logMonoTime
   t=(e.logMonoTime-origin)/1e9;k=e.which();counts[k]+=1
   if k=='modelV2' and e.valid and t-last_sample>=.19:
    m=e.modelV2;tt=np.array(m.orientationRate.t);v=np.array(m.velocity.x);w=np.array(m.orientationRate.z)
    if len(tt)!=33 or len(v)!=33 or len(w)!=33:continue
    age=(e.logMonoTime-m.timestampEof)/1e9;lat=v*w;ii=np.where((tt-age>=1)&(tt-age<=8)&(v>=3))[0]
    i=int(ii[np.argmax(np.abs(lat[ii]))]) if len(ii) else 0
    models.append({'t':t,'lead':float(tt[i]-age),'strength':float(lat[i]),'age':age,'v':float(v[0]),'tgrid':tt.tolist(),'lat':lat.tolist(),'vel':v.tolist()});last_sample=t
   elif k=='carState' and t-lastcar>=.095:
    c=e.carState;cars.append({'t':t,'v':c.vEgo,'a':c.aEgo,'steer':c.steeringAngleDeg,'yaw':c.yawRate});lastcar=t
   elif k=='navInstruction':
    n=e.navInstruction;nav.append({'t':t,'valid':e.valid,'type':n.maneuverType,'modifier':n.maneuverModifier,'distance':n.maneuverDistance,'remaining':n.distanceRemaining,'eta':n.timeRemaining})
   elif k=='navRoute':routes.append({'t':t,'valid':e.valid,'points':len(e.navRoute.coordinates)})
 result[route]={'origin_ns':origin,'counts':dict(counts),'models':models,'cars':cars,'nav':nav,'routes':routes}
 events=[];last=-100
 for j in range(2,len(models)):
  a=models[j-2:j+1];m=a[-1]
  if all(abs(x['strength'])>=.8 for x in a) and m['t']-last>12:
   future=[c for c in cars if m['t']<=c['t']<=m['t']+10]
   actual=max(future,key=lambda c:abs(c['v']*c['yaw'])) if future else None
   events.append({'detected':round(m['t'],2),'predicted_lead':round(m['lead'],2),'strength':round(m['strength'],2),'actual_peak':actual,'nav':next((n for n in reversed(nav) if n['t']<=m['t']),None)});last=m['t']
 result[route]['candidates']=events
 (ROOT/'results/inventory.json').write_text(json.dumps(result))
 print(route,'models',len(models),'route_updates',routes,'candidates',json.dumps(events[:12]),flush=True)
