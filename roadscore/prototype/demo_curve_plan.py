"""Optional, disclosed replay staging over a real route's measured curve events.

The launcher validates the private plan and passes it to presentation only.
No route recording is opened by the audio callback or composition planner.
"""
import json
import math
from pathlib import Path


def validate(value):
 if not isinstance(value,dict) or value.get('version')!=1 or value.get('demo_only') is not True:
  raise ValueError('Expected a version 1 demo-only curve plan')
 if not isinstance(value.get('route'),str) or not value['route']:
  raise ValueError('Curve plan requires its exact route identity')
 if type(value.get('replay_start')) is not int or value['replay_start']<0:
  raise ValueError('Curve plan requires its exact replay start')
 events=value.get('curves')
 if not isinstance(events,list) or not 1<=len(events)<=3:
  raise ValueError('Curve plan requires one to three measured events')
 previous=-1.
 for event in events:
  if not isinstance(event,dict):raise ValueError('Invalid curve event')
  values=[event.get(k) for k in ('build_start','apex','end')]
  if not all(type(n) in (int,float) and math.isfinite(n) for n in values):
   raise ValueError('Curve event timing must be finite')
  start,apex,end=values
  if not (0<=start<apex<end and 1<=apex-start<=24 and .4<=end-apex<=5 and start>previous):
   raise ValueError('Curve event timing is out of bounds or overlaps')
  if not isinstance(event.get('evidence'),str) or not event['evidence'].strip():
   raise ValueError('Curve event requires measured route evidence')
  previous=end
 return value


def launch_plan(path,route,replay_start,*,native,replay,judging,policy):
 if not native or replay or judging or policy!='conservative-v4':return None
 path=Path(path)
 if not path.is_file():return None
 value=validate(json.loads(path.read_text()))
 return value if value['route']==route and value['replay_start']==replay_start else None


class ReplayCurvePlan:
 def __init__(self,value):
  self.value=validate(value)

 @classmethod
 def from_environment(cls,mode,environ):
  raw=environ.get('ROADSCORE_DEMO_CURVE_PLAN')
  if not raw or mode!='replay' or environ.get('ROADSCORE_SEED_ORIGIN')=='judging-route':return None
  if environ.get('ROADSCORE_PRESENTATION_POLICY')!='conservative-v4':return None
  return cls(json.loads(raw))

 def state(self,now,route,recorded):
  if route!=self.value['route'] or type(now) not in (int,float) or not math.isfinite(now):return recorded
  for event in self.value['curves']:
   start,apex,end=(event[k] for k in ('build_start','apex','end'))
   if start<=now<end:
    progress=min(1.,max(0.,(now-start)/(apex-start)))
    amount=progress*progress*(3.-2.*progress)
    return {**recorded,'kind':'curve','activation':start,'predicted_peak':apex,
            'phase':'anticipation' if now<apex else 'event','amount':amount,
            'demo_staged_curve':True}
  return recorded
