"""Offline empirical tests only; runtime never imports this module."""
import os
import json,statistics
from pathlib import Path
from openpilot.tools.lib.logreader import _LogFileReader
from core import Conductor
from route_library import local_source
root=Path(__file__).resolve().parents[1];route=os.environ['ROADSCORE_CURVE_ROUTE'].split('/')[-1];samples=[];cars=[];origin=None;speed=0
source=local_source(os.environ['ROADSCORE_CURVE_ROUTE'])
if source is None:raise RuntimeError('Offline regression fixture missing')
for d in sorted(source.glob(route+'--*'),key=lambda p:int(p.name.rsplit('--',1)[1]))[:4]:
 for e in _LogFileReader(str(d/'rlog.zst'),sort_by_time=True):
  if origin is None:origin=e.logMonoTime
  t=(e.logMonoTime-origin)/1e9;k=e.which()
  if k=='carState':
   speed=e.carState.vEgo
   if 125<t<150:cars.append((t,e.carState.steeringAngleDeg))
  if k=='modelV2' and e.valid and 110<=t<=210:
   m=e.modelV2;samples.append((t,speed,{'mono':e.logMonoTime,'eof':m.timestampEof,'t':list(m.orientationRate.t),'yaw':list(m.orientationRate.z),'v':list(m.velocity.x)}))
def run(mutate=False):
 c=Conductor();out=[]
 for t,s,m in samples:
  if mutate and t>160:m=dict(m,yaw=[.5]*33)
  out.append((t,c.update(t,m,s).copy()))
 return out
one=run();two=run(True)
assert [x for x in one if x[0]<=160]==[x for x in two if x[0]<=160]
a=next(t for t,s in one if 130<t<145 and s['phase']=='anticipation')
base=statistics.median(s for t,s in cars if 130<=t<=134)
on=next(t for i,(t,s) in enumerate(cars[:-30]) if t>138 and all(y>base+3 for _,y in cars[i:i+30]))
assert on-a>=2
out={'samples':len(samples),'prefix_mutation_test':'passed through 160s; future yaw changed radically','activation':a,'physical_steering_onset':on,'lead_seconds':on-a,'note':'Steering reference used offline only. Current model trajectory test remains causal.'}
(root/'results/route_tests.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
