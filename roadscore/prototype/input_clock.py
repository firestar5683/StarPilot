"""Only source/clock differ between live cereal and historical cereal adapters."""
import json,time
class InputClock:
 def __init__(self,mode,run):self.mode=mode;self.run=run;self.origin=None;self.wall=None
 def read(self,sm):
  if self.mode=='replay':
   try:return json.loads((self.run/'clock.json').read_text())
   except (FileNotFoundError,json.JSONDecodeError):return None
  if self.origin is None:
   if not sm.updated['modelV2']:return None
   self.origin=sm.logMonoTime['modelV2'];self.wall=time.monotonic()
  return {'done':False,'origin_ns':self.origin,'origin_wall':self.wall,'route':'live','late':0.,'t':(sm.logMonoTime['modelV2']-self.origin)/1e9}
