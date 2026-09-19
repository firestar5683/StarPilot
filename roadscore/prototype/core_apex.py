"""Optional single conservative apex contrast using only existing source samples."""
import math
import numpy as np

class CoreApex:
 def __init__(self, grid, rate=48000, enabled=False):
  self.grid=grid;self.rate=rate;self.enabled=enabled;self.last_activation=None;self.peak=None;self.events=[]
 def process(self, pcm, start_frame, state):
  if not self.enabled or not self.grid.usable:return pcm
  activation=state.get('activation');lead=state.get('lead');now=start_frame/self.rate
  if (state.get('kind')=='curve' and state.get('phase')=='anticipation' and activation is not None
      and activation!=self.last_activation and lead is not None and math.isfinite(lead) and .25<=lead<=1.5):
   self.last_activation=activation
   if (not self.events or now-self.events[-1]['trigger_seconds']>=8) and sum(now-e['trigger_seconds']<60 for e in self.events)<3:
    subdivision=60/self.grid.bpm/2
    target=self.grid.beat_phase+round((now+lead-self.grid.beat_phase)/subdivision)*subdivision
    self.peak=round(target*self.rate);self.events.append({'trigger_seconds':now,'peak_seconds':target,'activation':activation,'dip_db':-1.,'peak_gain':1.})
  if self.peak is None:return pcm
  offset=(np.arange(start_frame,start_frame+len(pcm))-self.peak)/self.rate
  # Half-second breath, then original unity source at the estimated apex. Never boosts/clips the hook.
  gain=np.ones(len(pcm),np.float32);inside=(offset>-.7)&(offset<0)
  gain[inside]=1-(1-10**(-1/20))*np.sin(np.pi*(offset[inside]+.7)/.7)**2
  return pcm if not inside.any() else pcm*gain[:,None]
