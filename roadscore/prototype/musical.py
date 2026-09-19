"""Small deterministic musical tools; no route access or model changes."""
import numpy as np
from scipy.signal import butter,sosfilt

class Arrival:
 """Destination context arms resolution; parking evidence or a sustained stop triggers it."""
 def __init__(self):self.near_at=None;self.stop_since=None;self.arrived_at=None;self.parking_since=None;self.reason=None
 def route_change(self,valid):
  if valid:self.near_at=None;self.stop_since=None;self.arrived_at=None;self.parking_since=None;self.reason=None
 def update(self,t,speed,nav,fresh,gear=None,brake=False,standstill=False):
  if fresh and nav.get('type')=='arrive' and nav.get('remaining',1e9)<40:self.near_at=t
  armed=self.near_at is not None and 0<=t-self.near_at<30
  parking=armed and gear=='reverse' and brake and abs(speed)<2
  if parking:
   if self.parking_since is None:self.parking_since=t
   if t-self.parking_since>=.8 and nav.get('valid') is False and self.arrived_at is None:
    self.arrived_at=t;self.reason='recent arrive guidance within 40 m, sustained braking reverse below 2 m/s, and navigation subsequently invalidated'
  else:self.parking_since=None
  if armed and gear=='park' and standstill and self.arrived_at is None:
   self.arrived_at=t;self.reason='recent destination context plus parked standstill'
  if armed and abs(speed)<.15:
   if self.stop_since is None:self.stop_since=t
   if t-self.stop_since>=2 and self.arrived_at is None:self.arrived_at=t;self.reason='recent destination context plus speed below 0.15 m/s sustained 2 s'
  else:self.stop_since=None
  return self.arrived_at

def analyze_music(wave,rate=48000):
 """Approximate pulse and pitch classes from already-generated material, not route future."""
 x=np.mean(wave[-rate*12:],axis=1)[::8];sr=rate/8
 n=4096;hop=1024
 if len(x)<n:return {'bpm':100.,'pulse_confidence':0.,'root':0,'mode':'open','tonal_confidence':0.}
 frames=np.stack([x[i:i+n] for i in range(0,len(x)-n+1,hop)])
 spec=np.abs(np.fft.rfft(frames*np.hanning(n),axis=1));freq=np.fft.rfftfreq(n,1/sr)
 valid=(freq>60)&(freq<1600);midi=69+12*np.log2(freq[valid]/440);pcs=np.round(midi).astype(int)%12
 chroma=np.bincount(pcs,weights=np.mean(spec[:,valid],axis=0),minlength=12)
 scores=[]
 for root in range(12):
  for third,mode in [(4,'major'),(3,'minor')]:scores.append((chroma[root]+.8*chroma[(root+third)%12]+.7*chroma[(root+7)%12],root,mode))
 scores.sort(reverse=True);best=scores[0];conf=(best[0]-scores[2][0])/max(best[0],1e-9)
 # Onset envelope pulse estimate, kept as approximate; no key/tempo guarantee.
 energy=np.sqrt(np.mean(frames**2,axis=1));onset=np.maximum(0,np.diff(energy));ac=np.correlate(onset,onset,'full')[len(onset)-1:]
 lags=np.arange(max(1,int(np.ceil(60/150*sr/hop))),min(len(ac),int(np.floor(60/65*sr/hop))+1))
 lag=int(lags[np.argmax(ac[lags])]);pc=float(ac[lag]/max(ac[0],1e-9))
 return {'bpm':float(60*sr/hop/lag),'pulse_confidence':pc,'root':best[1],'mode':best[2] if conf>.025 else 'open','tonal_confidence':float(conf),'chroma':chroma.tolist()}

def ending_gesture(wave,rate=48000):
 """A source-informed final sonority; an approximate resolution, not verified tonic."""
 info=analyze_music(wave,rate);root=info['root'];midi=48+root
 intervals=[0,7,12] if info['mode']=='open' else [0,3 if info['mode']=='minor' else 4,7,12]
 t=np.arange(rate*5)/rate;y=np.zeros_like(t)
 for i,interval in enumerate(intervals):
  f=440*2**((midi+interval-69)/12)
  y+=(np.sin(2*np.pi*f*t)+.18*np.sin(2*np.pi*2*f*t))*np.exp(-t/(1.15+i*.24))/(1+i*.2)
 y+=.7*np.sin(2*np.pi*(440*2**((midi-12-69)/12))*t)*np.exp(-t/.9)
 envelope=(1-np.exp(-t/.012))*np.minimum(1,(5-t)/.25)
 rms=float(np.sqrt(np.mean(wave[-rate*3:]**2)))
 y=y*envelope;y*=min(.16,max(.025,rms*.8))/max(np.sqrt(np.mean(y[:rate]**2)),1e-6)
 return np.repeat(y[:,None],2,axis=1).astype(np.float32),info

class MusicalDSP:
 """Same causal amount; modest level change, phrase echoes and transient emphasis."""
 def __init__(self,rate=48000,bpm=100):
  self.rate=rate;self.sos=butter(2,700,fs=rate,output='sos');self.zi=np.zeros((1,2,2));self.level=0.
  self.delay=np.zeros((int(rate*60/bpm*.75),2),np.float32);self.pos=0
 def process(self,a,amount,ending=1.):
  low,self.zi=sosfilt(self.sos,a,axis=0,zi=self.zi);high=a-low
  ramp=np.linspace(self.level,amount,len(a))[:,None];self.level=amount
  # Dotted pulse echoes develop existing notes; no arbitrary new melody or telemetry pitch mapping.
  idx=(np.arange(len(a))+self.pos)%len(self.delay);echo=self.delay[idx].copy()
  self.delay[idx]=(a*.3+echo*.35);self.pos=(self.pos+len(a))%len(self.delay)
  body=low+high*(.75+.18*ramp)
  out=(body+echo*.65*np.maximum(ramp,0))*.67
  return np.tanh(out*1.15).astype(np.float32)*ending

def match_continuation(previous,incoming,overlap=96000):
 """Level-match only common retained context; do not normalize every piece independently."""
 n=min(overlap,len(previous),len(incoming));a=previous[-n:];b=incoming[:n]
 ea=float(np.sqrt(np.mean(a*a)));eb=float(np.sqrt(np.mean(b*b)))
 # Reject silence as a level reference; amplification cannot repair missing music.
 gain=float(np.clip(ea/max(eb,1e-9),.7,1.4)) if min(ea,eb)>.01 else 1.
 gain=min(gain,.98/max(float(np.max(np.abs(incoming))),1e-9))
 return incoming*gain,{'context_rms_old':ea,'context_rms_new':eb,'gain':gain}
