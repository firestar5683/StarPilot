"""Experimental salient percussion. No synthesized harmonic notes or extra events."""
import numpy as np
from scipy.signal import butter,sosfilt
from gesture_bank_v2 import GestureBank as V2
from gesture_bank import unit
class GestureBank(V2):
 def __init__(self,source,rate=48000,bpm=128):
  super().__init__(source,rate,bpm);rng=np.random.default_rng(330916)
  def burst(seconds,bands,decay,level):
   n=round(seconds*rate);t=np.arange(n)/rate;raw=rng.normal(size=(n,2));a=np.zeros_like(raw)
   for low,high,gain in bands:a+=gain*sosfilt(butter(2,[low,high],btype='bandpass',fs=rate,output='sos'),raw,axis=0)
   a*=np.exp(-decay*t)[:,None];edge=round(.001*rate);a[:edge]*=np.linspace(0,1,edge)[:,None];a[-edge:]*=np.linspace(1,0,edge)[:,None];return unit(a,level)
  self.sounds['signal_rim']=burst(.095,[(1500,3600,1),(9000,16000,.55)],45,.24)
  self.sounds['signal_shaker']=burst(.11,[(5200,14000,1)],30,.16)
  self.sounds['impact_low']=burst(.42,[(45,160,1),(160,420,.4)],12,.32)
  self.sounds['impact_crash']=burst(1.1,[(1800,14500,1)],5,.28)
  self.sounds['impact_snap']=burst(.11,[(400,2400,1),(6500,14000,.7)],50,.24)
 def phrase(self,kind):
  patterns={
   'turn_signal':(2,[('signal_rim',0,1),('signal_shaker',.125,.65),('signal_rim',.75,.9),('signal_rim',1.5,.8)]),
   'turn_signal_sustain':(4,[('signal_rim',0,.72),('signal_shaker',.75,.55),('signal_rim',1.5,.58),('signal_shaker',2.75,.35)]),
   'turn_signal_off':(.5,[('signal_rim',0,.6),('signal_shaker',.25,.45)]),
   'curve_apex':(2,[('impact_low',0,1),('impact_crash',0,1),('impact_snap',0,.85),('tick',.125,.6),('tick',.25,.42),('tick',.375,.25)])}
  if kind not in patterns:return super().phrase(kind)
  beats,events=patterns[kind];out=np.zeros((round((beats*self.beat+.5)*self.rate),2),np.float32)
  for name,beat,gain in events:
   x=self.sounds[name];i=round(beat*self.beat*self.rate);count=min(len(x),len(out)-i);out[i:i+count]+=gain*x[:count]
  return out,{'version':3,'beats':beats,'new_tonal_pitches':False,'synthetic_unpitched_percussion':True,'change':'dual-band rim/shaker motif; layered broad crash/low noise impact/short snap','peak':float(abs(out).max()),'human_salience_verified':False}
