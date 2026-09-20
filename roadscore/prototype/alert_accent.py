"""Sparse beat-locked warning fills; bounded priority over routine musical cues."""
import math
import numpy as np


class AlertAccent:
 def __init__(self, grid, rate=48000, enabled=False):
  self.grid=grid;self.rate=rate;self.enabled=enabled
  n=round(.11*rate);t=np.arange(n)/rate;rng=np.random.default_rng(1701)
  frequency=np.fft.rfftfreq(n,1/rate);spectrum=np.fft.rfft(rng.standard_normal(n))
  spectrum*=np.clip((frequency-650)/700,0,1)*np.clip((6500-frequency)/2000,0,1)
  grain=np.fft.irfft(spectrum,n);envelope=(1-np.exp(-t/.004))*np.exp(-t/.032)
  grain*=envelope;grain/=max(float(np.max(np.abs(grain))),1e-9)
  self.grain=np.column_stack((grain,grain)).astype(np.float32)*.045
  self.duck=(np.sin(np.pi*np.arange(n)/(n-1))**2).astype(np.float32)
  self.key=None;self.since=0;self.handled=False;self.pending=[]
  self.last=-60*rate;self.events=[];self.rendered_active=False;self.priority_active=False

 def process(self, pcm, start, key, meaningful, fresh, competing=False):
  self.rendered_active=False;self.priority_active=False
  if not self.enabled:return pcm
  current=key if meaningful and fresh else None
  if current!=self.key:
   self.key=current;self.since=start;self.handled=False
  if not fresh:
   self.pending=[]
   return pcm
  elapsed=(start-self.since)/self.rate
  if self.grid.usable and current and not self.handled and elapsed>=.05:
   # Warning priority replaces routine-cue deferral; qualify one stable input first.
   self.handled=True
   if start-self.last>=12*self.rate and sum(start-e['frame']<60*self.rate for e in self.events)<3:
    beat=self.rate*60/self.grid.bpm;origin=self.grid.beat_phase*self.rate
    frame=round(origin+math.ceil((start-origin)/(beat/2)-1e-10)*(beat/2))
    self.pending=[(frame,1.),(frame+round(beat/2),.55),(frame+round(beat),.8)]
    self.last=start;self.events.append({'kind':'native_alert_fill','frame':start,'scheduled_frame':frame,'alert':current,
                                      'competition_deferred':bool(competing),'priority':'warning over routine cues'})
  self.priority_active=bool(self.pending)
  end=start+len(pcm);overlay=None;duck=None;remaining=[]
  for frame,gain in self.pending:
   left=max(start,frame);right=min(end,frame+len(self.grain))
   if right>left:
    if overlay is None:overlay=np.zeros_like(pcm);duck=np.zeros(len(pcm),np.float32)
    overlay[left-start:right-start]+=self.grain[left-frame:right-frame]*gain
    duck[left-start:right-start]=np.maximum(duck[left-start:right-start],self.duck[left-frame:right-frame]*gain)
   if frame+len(self.grain)>end:remaining.append((frame,gain))
  self.pending=remaining
  # Do not fill an intentional musical rest with an isolated notification.
  if overlay is None or np.max(np.abs(pcm),initial=0)<.002:return pcm
  self.rendered_active=bool(np.any(overlay))
  base=pcm*(1-(1-10**(-1.5/20))*duck[:,None])
  headroom=np.maximum(1-np.abs(base),0)
  return base+np.clip(overlay,-headroom,headroom)

 def snapshot(self):
  return {'enabled':self.enabled,'rhythm_enabled':self.enabled and self.grid.usable,
          'rendered_active':self.rendered_active,'priority_active':self.priority_active,
          'minimum_spacing_seconds':12,'maximum_per_minute':3,'maximum_competition_deferral_seconds':0.,'qualification_seconds':.05,
          'peak_limit':.045,'duck_db':1.5,'fill':'next eighth, plus eighth, plus beat','source':'selfdriveState.alertStatus'}
