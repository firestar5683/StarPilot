"""Replay-only musical engagement override; never publishes vehicle state."""
import json
import math
import time
from pathlib import Path

MODES = ('recorded', 'engaged', 'disengaged')


class DemoEngagement:
 def __init__(self, run, session_id, input_mode, *, clock=time.monotonic):
  self.path=Path(run)/'demo_engagement.json';self.session_id=session_id
  self.input_mode=input_mode;self.clock=clock;self.started=clock();self.mode='recorded'

 def poll(self):
  self.mode='recorded'
  if self.input_mode!='replay':return self.mode
  try:
   value=json.loads(self.path.read_text())
   stamp=value.get('created_wall')
   if (value.get('version')==1 and value.get('session_id')==self.session_id
       and value.get('mode') in MODES and type(stamp) in (int,float)
       and math.isfinite(stamp) and self.started<=stamp<=self.clock()):
    self.mode=value['mode']
  except (OSError,ValueError,AttributeError):pass
  return self.mode


def presentation_active(mode, recorded_active):
 return recorded_active if mode=='recorded' else mode=='engaged'


def annotate(snapshot, mode, recorded_active):
 result=dict(snapshot)
 result['engagement_presentation']={**result.get('engagement_presentation',{}),
   'simulated':mode!='recorded','demo_mode':mode,'recorded_active':bool(recorded_active)}
 return result
