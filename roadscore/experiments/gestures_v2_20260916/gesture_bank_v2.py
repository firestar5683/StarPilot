"""Distinct, unpitched percussion plus untransposed song accents. No guessed notes."""
import numpy as np
from scipy.signal import butter,sosfilt
from gesture_bank import GestureBank as Original,unit,attack_grain
class GestureBank(Original):
 def __init__(self,source,rate=48000,bpm=128):
  super().__init__(source,rate,bpm)
  rng=np.random.default_rng(160926)
  def air(seconds,lo,hi,decay):
   n=round(seconds*rate);t=np.arange(n)/rate
   a=sosfilt(butter(2,[lo,hi],btype='bandpass',fs=rate,output='sos'),rng.normal(size=(n,2)),axis=0)
   a*=np.exp(-t*decay)[:,None];edge=max(2,round(.001*rate));a[:edge]*=np.linspace(0,1,edge)[:,None];a[-edge:]*=np.linspace(1,0,edge)[:,None]
   return unit(a,.16)
  # Short broadband, filtered bursts: no oscillators or asserted harmonic key.
  self.sounds['click']=air(.055,1800,6500,85)
  self.sounds['tick']=air(.035,8000,15000,110)
  self.sounds['brush']=air(.22,900,9500,17)
  # No current-chord estimator is validated. These added voices stay unpitched.
  self.sounds['body']=air(.22,70,400,25)
  self.sounds['call']=air(.20,700,2200,23)
  self.sounds['answer']=air(.16,2500,6500,30)
  self.sounds['accent']=air(.24,100,9500,22)
  n=round(2*self.beat*rate);s=air(2*self.beat,2500,12000,.1);s*=np.linspace(0,1,n)[:,None]**2
  self.sounds['riser']=unit(s,.16)
  sweep=air(self.beat,1400,11000,6);pan=np.linspace(-1,1,len(sweep));mono=sweep.mean(1)
  self.sounds['sweep']=np.stack([mono*np.sqrt((1-pan)/2),mono*np.sqrt((1+pan)/2)],axis=1)
 def phrase(self,kind):
  patterns={
   'turn_signal':(2,[('click',0,1),('tick',.25,.5),('click',.75,.7),('click',1.5,.8)]),
   'turn_signal_sustain':(4,[('click',0,.65),('tick',.5,.45),('click',2,.55),('tick',2.5,.35)]),
   'turn_signal_off':(.5,[('brush',0,.4),('tick',.25,.3)]),
   'curve_prepare':(4,[('riser',2,.6),('snare',0,.5),('body',1,.7),('snare',2,.7),('brush',2.5,.7),('snare',3,.8),('brush',3.25,.8),('snare',3.5,.9),('brush',3.75,.9)]),
   'curve_apex':(2,[('crash',0,1),('body',0,.8),('accent',.25,.4)]),
   'navigation_turn':(2,[('call',0,.9),('answer',1,.7),('tick',1.5,.35)]),
   'lane_change':(1,[('sweep',0,1),('click',.75,.5)]),
   'stop':(1,[('body',0,.6),('brush',.5,.4)]),
   'resume':(2,[('brush',0,.6),('click',.25,.6),('snare',.5,.7),('body',1,.8),('tick',1.5,.5)]),
   'arrival_prepare':(4,[('riser',0,.4),('call',2,.5),('answer',3,.35)]),
   'arrival':(2,[('crash',0,.4),('body',0,.6)])}
  beats,events=patterns[kind];out=np.zeros((round((beats*self.beat+.5)*self.rate),2),np.float32)
  for name,beat,gain in events:
   s=self.sounds[name];i=round(beat*self.beat*self.rate);out[i:i+len(s)]+=s[:len(out)-i]*gain
  return out,{'version':2,'beats':beats,'seconds':len(out)/self.rate,'source_derived':True,'synthetic_unpitched_percussion':True,'new_tonal_pitches':False,'harmonic_confidence_policy':'no validated current chord: added voices are filtered noise; no pitched oscillators or transposition'}
