"""Prism apex contrast: short stereo noise flourish and broad percussion, no new pitches."""
import numpy as np
from scipy.signal import butter,sosfilt
from gesture_bank_v3 import GestureBank as V3
from gesture_bank import unit
class GestureBank(V3):
 def phrase(self,kind):
  if kind!='curve_apex':return super().phrase(kind)
  rate=self.rate;rng=np.random.default_rng(440916);n=round(1.65*rate);t=np.arange(n)/rate
  noise=rng.normal(size=(n,2));high=sosfilt(butter(2,[2400,16000],btype='bandpass',fs=rate,output='sos'),noise,axis=0)
  low=sosfilt(butter(2,[42,200],btype='bandpass',fs=rate,output='sos'),noise,axis=0)
  # Wide bright attack, then a short alternating stereo flutter as the crash recedes.
  flourish=(1+.6*np.sin(2*np.pi*13*t))[:,None]*high*np.exp(-6*t)[:,None]
  pan=np.column_stack([.65+.35*np.cos(2*np.pi*4*t),.65-.35*np.cos(2*np.pi*4*t)])
  out=unit(high*np.exp(-4.2*t)[:,None],.23)+unit(low*np.exp(-15*t)[:,None],.30)+unit(flourish*pan,.17)
  snap=self.sounds['impact_snap'];out[:len(snap)]+=.55*snap
  edge=round(.001*rate);out[:edge]*=np.linspace(0,1,edge)[:,None];out[-edge:]*=np.linspace(1,0,edge)[:,None]
  return out.astype(np.float32),{'version':4,'new_tonal_pitches':False,'synthetic_unpitched_percussion':True,'change':'wide crash, low transient and alternating stereo flutter','human_salience_verified':False,'peak':float(abs(out).max())}
