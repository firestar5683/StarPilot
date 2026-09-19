"""Style realizes semantic curve intent using only current generated audio.
Explicit early texture changes avoid hiding anticipation in a quadratic late ramp.
No road-derived pitches or prerecorded assets. Original DrivingDSP remains a control.
"""
import numpy as np
from scipy.signal import butter,sosfilt
from driving_music import DrivingDSP
class EventDSP(DrivingDSP):
 def __init__(self,rate=48000,bpm=108,style='rock'):
  super().__init__(rate,bpm);self.style=style;self.frame=0;self.texture=0.
  self.bass_filter=butter(2,240,fs=rate,output='sos');self.bass_zi=np.zeros((1,2,2));self.period=rate*60/bpm
 def process(self,a,amount,ending=1.):
  state=self.event_state;phase=state.get('phase','neutral');curve=state.get('kind','curve')=='curve'
  active=curve and phase=='anticipation'
  # The first 100ms block ramps from the prior state; no hard discontinuity.
  early=.65+.3*np.clip((amount-.25)/.65,0,1) if active else amount
  if self.style=='rock':out=super().process(a,early,ending)
  else:
   # Suppress the rock reprise layer; each family below has its own texture gesture.
   self.event_state={'phase':'neutral','strength':0}
   out=super().process(a,early if self.style=='synthwave' else amount,ending);self.event_state=state
  low,self.bass_zi=sosfilt(self.bass_filter,a,axis=0,zi=self.bass_zi);high=a-low
  target=(.45+.45*np.clip((amount-.25)/.65,0,1)) if active else 0.
  if phase=='release':target=max(0,amount)*.15
  ramp=np.linspace(self.texture,target,len(a))[:,None];self.texture=target
  ticks=(self.frame+np.arange(len(a)))/self.period;self.frame+=len(a)
  if self.style=='electronic':
   # Bass subtraction creates an early preparation; upper-band subdivisions become denser.
   pulse=(.5+.5*np.cos(2*np.pi*ticks*(4 if amount>.65 else 2)))[:,None]**4
   out+=(-.32*low+.16*high*pulse)*ramp*ending
  elif self.style=='synthwave':
   # Existing notes get a stereo rhythmic answer, while the low register clears slightly.
   idx=(np.arange(len(a))+self.pos)%len(self.delay);answer=self.delay[idx][:,::-1]
   out+=(.3*answer-.16*low)*ramp*ending
  elif self.style=='groove':
   # Dry, clipped accents emphasize the player's existing attacks, not a synthetic riser.
   transient=np.tanh(high*3)*.12
   out+=(transient-.22*low)*ramp*ending
  return np.clip(out,-.98,.98).astype(np.float32)
