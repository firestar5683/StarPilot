"""Pure causal event detector and deterministic audio processing. No route I/O."""
import math
import numpy as np
from scipy.signal import butter,sosfilt

class Conductor:
 def __init__(self,handoff=False,threshold=.8):
  self.threshold=threshold;self.handoff=handoff;self.detection=None;self.since=None;self.last_seen=None;self.target=None;self.strength=0.;self.phase='neutral';self.activation=None;self.last_event=-1e9;self.sign=0;self.event_sign=0;self.initial_peak=None;self.kind='curve';self.arrival_since=None;self.arrived=False
 def update(self,t,model,speed):
  age=(model['mono']-model['eof'])/1e9
  tt=np.asarray(model['t'])-age;lat=np.asarray(model['yaw'])*np.asarray(model['v'])
  good=(tt>=1)&(tt<=8)&(np.asarray(model['v'])>=3)
  if not np.isfinite(lat).all() or age<0 or age>.5 or speed<3 or not good.any():self.since=None;return self.state(t)
  i=np.where(good)[0][np.argmax(np.abs(lat[good]))];strength=float(abs(lat[i]));sign=int(np.sign(lat[i]));kind='curve'
  slow=np.where(good & (np.asarray(model['v'])<speed*.5))[0]
  if strength<self.threshold and speed>5 and len(slow):
   i=int(slow[0]);strength=1.;sign=0;kind='slowdown'
  self.detection={'candidate_strength':strength,'candidate_peak':t+float(tt[i]),'candidate_kind':kind,'candidate_sign':sign,'qualified_since':self.since}
  if strength>=self.threshold:
   if self.since is None or sign!=self.sign or (self.last_seen is not None and t-self.last_seen>.4):self.since=t
   self.sign=sign;self.last_seen=t
   if t-self.since>=.3:
    proposed=t+float(tt[i])
    new_direction=self.handoff and kind=='curve' and sign!=self.event_sign
    can_handoff=self.handoff and self.target is not None and kind=='curve' and (self.kind=='slowdown' or (new_direction and t>self.target+.5))
    can_rearm=self.target is None and (t-self.last_event>4 or (new_direction and t-self.last_event>.3))
    if can_rearm or can_handoff:
     self.target=proposed;self.kind=kind;self.initial_peak=proposed;self.event_sign=sign;self.activation=t;self.strength=strength
    elif self.target is not None and sign==self.event_sign and t<self.target-.6 and abs(proposed-self.target)<2:
     self.target=max(self.initial_peak-2,min(self.initial_peak+2,.85*self.target+.15*proposed));self.strength=strength
  else:self.since=None
  return self.state(t)
 def state(self,t):
  phase='neutral';amount=0.
  if self.target is not None:
   if self.last_seen is not None and t-self.last_seen>1.5 and t<self.target-1:self.target=min(self.target,t)
   left=self.target-t
   if left>0:
    phase='anticipation';amount=.25+.65*min(1.,(t-self.activation)/max(.5,self.target-self.activation))
   elif left>-1:phase='event';amount=1.
   elif left>-4:phase='release';amount=max(0.,(4+left)/3)
   else:self.last_event=t;self.target=None;self.activation=None
  self.phase=phase
  return {'kind':self.kind,'phase':phase,'amount':amount,'predicted_peak':self.target,'lead':None if self.target is None else self.target-t,'strength':self.strength,'activation':self.activation,'detector':self.detection,'qualified_since':self.since}

class DSP:
 def __init__(self,rate=48000):
  self.sos=butter(2,700,fs=rate,output='sos');self.zi=np.zeros((len(self.sos),2,2));self.level=0.
 def process(self,a,amount,ending=1.):
  low,self.zi=sosfilt(self.sos,a,axis=0,zi=self.zi)
  ramp=np.linspace(self.level,amount,len(a))[:,None];self.level=amount
  # Same generated source: warm/soft baseline opens toward a clear event peak.
  out=(low+(a-low)*np.maximum(.05,.25+.75*ramp))*(.55+.25*ramp)*ending
  return np.tanh(out*1.3).astype(np.float32)
