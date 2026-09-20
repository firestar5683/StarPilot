"""Only source/clock differ between live cereal and historical cereal adapters."""
import json
import time


def source_time_ns():
 return time.clock_gettime_ns(getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC))


class InputClock:
 def __init__(self,mode,run,*,source_clock=source_time_ns,wall_clock=time.monotonic):
  self.mode=mode;self.run=run;self.origin=None;self.wall=None
  self.source_clock=source_clock;self.wall_clock=wall_clock;self.previous={}

 def read(self,sm):
  if self.mode=='replay':
   try:return json.loads((self.run/'clock.json').read_text())
   except (FileNotFoundError,json.JSONDecodeError):return None
  now=self.source_clock()
  problem=None
  for topic in ('modelV2','carState','selfdriveState'):
   stamp=sm.logMonoTime.get(topic,0)
   if not sm.valid.get(topic,False) or stamp<=0 or not 0<=now-stamp<=500_000_000:
    problem=f'Live {topic} input is invalid, stale, or future-dated';break
   if stamp<self.previous.get(topic,0):
    problem=f'Live {topic} clock moved backwards';break
  if problem:
   if self.origin is not None:raise RuntimeError(problem)
   return None
  self.previous={topic:sm.logMonoTime[topic] for topic in ('modelV2','carState','selfdriveState')}
  if self.origin is None:
   if not sm.updated['modelV2']:return None
   self.origin=sm.logMonoTime['modelV2'];self.wall=self.wall_clock()
  return {'done':False,'origin_ns':self.origin,'origin_wall':self.wall,'route':'live','late':0.,'t':(sm.logMonoTime['modelV2']-self.origin)/1e9}
