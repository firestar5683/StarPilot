"""Horizon Drive transient reprises; uses generated music, not a prerecorded drum kit."""
import numpy as np
from scipy.signal import butter,sosfilt,lfilter
from musical import MusicalDSP

class DrivingDSP(MusicalDSP):
 def __init__(self,rate=48000,bpm=108):
  super().__init__(rate,bpm);self.event_state={};self.last_phase='neutral';self.hit_age=10.
  self.hp=butter(2,1200,fs=rate,output='sos');self.lp=butter(2,180,fs=rate,output='sos');self.hz=np.zeros((1,2,2));self.lz=np.zeros((1,2,2))
  self.fast=0.;self.slow=0.;self.af=np.exp(-1/(rate*.003));self.aslow=np.exp(-1/(rate*.065))
  self.reprises=[np.zeros((round(rate*60/bpm/div),2),np.float32) for div in [2,4]];self.rpos=[0,0];self.last_mix=0.
 def process(self,a,amount,ending=1.):
  base=super().process(a,amount,ending);hi,self.hz=sosfilt(self.hp,a,axis=0,zi=self.hz);lo,self.lz=sosfilt(self.lp,a,axis=0,zi=self.lz)
  band=hi+.35*lo;env=np.max(abs(band),axis=1)
  fast,z=lfilter([1-self.af],[1,-self.af],env,zi=[self.fast]);self.fast=z[0]
  slow,z=lfilter([1-self.aslow],[1,-self.aslow],env,zi=[self.slow]);self.slow=z[0]
  attack=np.clip((fast/(slow+1e-4)-1)*1.5,0,1)[:,None];transients=band*attack
  echoes=[]
  for i,buf in enumerate(self.reprises):
   idx=(np.arange(len(a))+self.rpos[i])%len(buf);echoes.append(buf[idx].copy());buf[idx]=transients;self.rpos[i]=(self.rpos[i]+len(a))%len(buf)
  state=self.event_state;phase=state.get('phase','neutral');severity=float(np.clip((state.get('strength',1)-.8)/1.5,.15,1))
  if phase=='event' and self.last_phase!='event':self.hit_age=0.
  if phase=='anticipation':target=max(0,amount)**2*severity
  elif phase=='release':target=max(0,amount)*severity*.25
  else:target=0.
  ramp=np.linspace(self.last_mix,target,len(a))[:,None];self.last_mix=target
  # Eighth-note reprise grows first, sixteenth subdivision only late in the build.
  add=.32*echoes[0]*ramp+.22*echoes[1]*np.maximum(0,ramp-.45)
  hit=np.exp(-(self.hit_age+np.arange(len(a))/self.rate)/.22)[:,None]
  if phase=='event':add+=.22*severity*transients*hit
  self.hit_age+=len(a)/self.rate;self.last_phase=phase
  return np.clip(base+add*ending,-.98,.98).astype(np.float32)
