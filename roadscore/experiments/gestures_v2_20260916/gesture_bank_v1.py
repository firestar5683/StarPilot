"""A small drum vocabulary derived from the current generated song, never external SFX."""
import numpy as np
from scipy.signal import butter,sosfilt

def unit(wave,level=.2):
 wave=np.asarray(wave,dtype=np.float32)
 peak=float(np.max(abs(wave)))
 return wave*(level/max(peak,1e-6))

def attack_grain(source,rate,low,high,seconds):
 """Extract a real source attack; filtering preserves the source's pitch content."""
 filt=butter(2,[low,high],btype='bandpass',fs=rate,output='sos')
 band=sosfilt(filt,source,axis=0).astype(np.float32)
 hop=max(1,rate//100);energy=np.mean(band[:len(band)//hop*hop].reshape(-1,hop,2)**2,axis=(1,2))
 onset=np.maximum(0,np.diff(energy,prepend=energy[0]));index=max(0,(1+int(np.argmax(onset[1:])))*hop)
 n=round(seconds*rate);grain=np.zeros((n,2),np.float32);part=band[index:index+n];grain[:len(part)]=part
 envelope=np.exp(-np.linspace(0,5,n))[:,None];envelope[:max(2,rate//1000)]*=np.linspace(0,1,max(2,rate//1000))[:,None]
 return unit(grain*envelope)

class GestureBank:
 """Source-matched percussion and source-derived accents on an explicit tempo grid."""
 def __init__(self,source,rate=48000,bpm=128):
  self.rate=rate;self.beat=60/bpm
  self.sounds={'hat':attack_grain(source,rate,5500,14000,.07),'snare':attack_grain(source,rate,500,7000,.18),'tom':attack_grain(source,rate,130,700,.23),'accent':attack_grain(source,rate,80,10000,.4)}
  # Quiet synthetic air extends a source crash without inventing a pitched chord.
  n=round(self.beat*2*rate);rng=np.random.default_rng(20260916);noise=sosfilt(butter(2,6500,btype='highpass',fs=rate,output='sos'),rng.normal(size=(n,2)),axis=0)
  crash=noise*np.exp(-np.linspace(0,7,n))[:,None]*.03;accent=self.sounds['accent'];crash[:len(accent)]+=accent*.5
  edge=min(round(.004*rate),n//2);crash[:edge]*=np.linspace(0,1,edge)[:,None];crash[-edge:]*=np.linspace(1,0,edge)[:,None]
  self.sounds['crash']=unit(crash,.23)
  self.sounds['reverse']=self.sounds['crash'][::-1].copy()
 def phrase(self,kind):
  """Return a finite, beat-length phrase. No endless background layer."""
  patterns={
   'turn_signal':(1,[('hat',0,.65),('hat',.5,.32)]),
   'curve_prepare':(4,[('snare',0,.35),('snare',1,.45),('tom',2,.65),('snare',2.5,.55),('snare',3,.75),('snare',3.25,.8),('snare',3.5,.9),('snare',3.75,1.)]),
   'curve_apex':(2,[('crash',0,1.),('accent',0,.5)]),
   'navigation_turn':(2,[('tom',0,.6),('snare',.5,.45),('hat',1,.6),('hat',1.5,.4)]),
   'lane_change':(1,[('hat',0,.6),('tom',.5,.4)]),
   'stop':(1,[('tom',0,.4)]),
   'resume':(1,[('hat',0,.5),('snare',.5,.35)]),
   'arrival_prepare':(4,[('reverse',0,.7),('tom',2,.6),('hat',3,.35)]),
   'arrival':(2,[('crash',0,.45),('accent',0,.5)])}
  beats,events=patterns[kind];out=np.zeros((round((beats*self.beat+.5)*self.rate),2),np.float32)
  for name,beat,gain in events:
   s=self.sounds[name];i=round(beat*self.beat*self.rate);out[i:i+len(s)]+=s[:len(out)-i]*gain
  return out,{'beats':beats,'seconds':len(out)/self.rate,'source_derived':True,'new_tonal_pitches':False}
