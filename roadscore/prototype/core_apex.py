"""Optional single conservative apex contrast using only existing source samples."""
import math
import numpy as np

class CoreApex:
 def __init__(self, grid, rate=48000, enabled=False,dip_db=-1.):
  self.dip_db=max(-3.,min(0.,float(dip_db)));self.grid=grid;self.rate=rate;self.enabled=enabled;self.last_activation=None;self.peak=None;self.breath_start=None;self.events=[];self.rendered_active=False;self.rendered_end=0.
 def process(self, pcm, start_frame, state):
  self.rendered_active=False;self.rendered_end=(start_frame+len(pcm))/self.rate
  if not self.enabled:return pcm
  activation=state.get('activation');lead=state.get('lead');now=start_frame/self.rate
  if (self.grid.usable and state.get('kind')=='curve' and state.get('phase')=='anticipation' and activation is not None
      and activation!=self.last_activation and lead is not None and math.isfinite(lead) and .25<=lead<=1.5):
   self.last_activation=activation
   if (not self.events or now-self.events[-1]['trigger_seconds']>=8) and sum(now-e['trigger_seconds']<60 for e in self.events)<3:
    subdivision=60/self.grid.bpm/2
    target=self.grid.beat_phase+round((now+lead-self.grid.beat_phase)/subdivision)*subdivision
    self.peak=round(target*self.rate);self.breath_start=max(start_frame,self.peak-round(.7*self.rate));self.events.append({'trigger_seconds':now,'peak_seconds':target,'activation':activation,'dip_db':self.dip_db,'peak_gain':1.})
  if self.peak is None:return pcm
  frames=np.arange(start_frame,start_frame+len(pcm))
  # A late prediction shortens the breath instead of jumping into a partly completed dip.
  gain=np.ones(len(pcm),np.float32);inside=(frames>self.breath_start)&(frames<self.peak)
  span=max(1,self.peak-self.breath_start)
  gain[inside]=1-(1-10**(self.dip_db/20))*np.sin(np.pi*(frames[inside]-self.breath_start)/span)**2
  self.rendered_active=bool(inside.any() and np.any(pcm[inside]))
  return pcm if not self.rendered_active else pcm*gain[:,None]
 def snapshot(self):
  return {'enabled':self.enabled,'rhythm_enabled':self.enabled and self.grid.usable,'rendered_active':self.rendered_active,'rendered_block_end_seconds':self.rendered_end}
