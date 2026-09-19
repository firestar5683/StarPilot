"""Offline evidence only. Never imported by musical runtime."""
import os
import json
from pathlib import Path
from openpilot.tools.lib.logreader import _LogFileReader
R=Path('/data/roadscore');route=os.environ['ROADSCORE_ARRIVAL_ROUTE'].split('/')[-1]
origin=next(iter(_LogFileReader(str(R/'routes'/f'{route}--0/rlog.zst')))).logMonoTime
out=[];last=-1
for seg in [3,4]:
 for e in _LogFileReader(str(R/'routes'/f'{route}--{seg}/rlog.zst'),sort_by_time=True):
  t=(e.logMonoTime-origin)/1e9;k=e.which()
  if not 220<=t<=258:continue
  if k=='carState' and (t-last>=.25):
   c=e.carState;out.append({'t':t,'service':k,'speed':c.vEgo,'gear':str(c.gearShifter),'standstill':c.standstill,'brakePressed':c.brakePressed,'gasPressed':c.gasPressed,'steering':c.steeringAngleDeg,'leftBlinker':c.leftBlinker,'rightBlinker':c.rightBlinker});last=t
  elif k in ['navInstruction','navRoute']:
   r={'t':t,'service':k,'valid':e.valid}
   if k=='navInstruction':r.update(type=e.navInstruction.maneuverType,remaining=e.navInstruction.distanceRemaining,eta=e.navInstruction.timeRemaining,distance=e.navInstruction.maneuverDistance)
   out.append(r)
(R/'results/continuity/arrival_cereal.json').write_text(json.dumps(out,indent=2))
for r in out:
 if r['service']!='carState' or int(r['t'])!=int(r['t']-.25):print(json.dumps(r))
