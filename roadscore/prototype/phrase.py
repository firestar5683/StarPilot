"""Small musical timing helpers. Inputs are generated audio, never future route data."""
import numpy as np

def pulse(wave,rate=48000):
 # 10 ms spectral-flux envelope improves on the old ~171 ms RMS pulse estimate.
 x=np.mean(wave[-rate*12:],axis=1)[::max(1,rate//8000)];sr=rate/max(1,rate//8000)
 hop=max(1,round(sr*.01));n=512
 if len(x)<sr*3:return {'bpm':100.,'confidence':0.,'period':.6,'next_beat':.6}
 f=np.lib.stride_tricks.sliding_window_view(x,n)[::hop]
 mag=np.abs(np.fft.rfft(f*np.hanning(n),axis=1));on=np.maximum(0,np.diff(mag,axis=0)).mean(axis=1)
 on=np.maximum(0,on-np.median(on));ac=np.correlate(on,on,'full')[len(on)-1:]
 lags=np.arange(round(.4*sr/hop),round(.86*sr/hop)+1);lag=int(lags[np.argmax(ac[lags])]);period=lag*hop/sr
 conf=float(ac[lag]/max(ac[0],1e-10));times=(np.arange(len(on))+1)*hop/sr+n/(2*sr)
 bins=64;phase_bins=(np.floor((times%period)/period*bins).astype(int))%bins
 fold=np.bincount(phase_bins,weights=on,minlength=bins);fold=fold+np.roll(fold,1)+np.roll(fold,-1)
 phase=(int(np.argmax(fold))+.5)/bins*period;elapsed=len(x)/sr
 return {'bpm':60/period,'confidence':conf,'period':period,'next_beat':float((phase-elapsed)%period)}

def cadence_runway(past,queued,rate=48000):
 """Choose a release/beat opportunity 0.8–3.5 s ahead in music already in the buffer.
 Pulse phase is not a verified bar/downbeat. A weak pulse uses energy release only.
 """
 info=pulse(past,rate);max_s=min(3.5,len(queued)/rate-.15)
 if max_s<.8:return 0.,{**info,'method':'insufficient queued runway','delay_seconds':0.}
 if info['confidence']>=.25:
  candidates=np.arange(info['next_beat'],max_s+.001,info['period']);candidates=candidates[candidates>=.8];method='pulse-grid plus local release'
 else:candidates=np.arange(.8,max_s,.05);method='local energy release; weak pulse'
 if not len(candidates):candidates=np.array([max_s])
 scores=[];ref=max(float(np.sqrt(np.mean(queued[:round(max_s*rate)]**2))),1e-8)
 for t in candidates:
  k=round(t*rate);before=queued[max(0,k-round(.15*rate)):k];after=queued[k:k+round(.05*rate)]
  eb=float(np.sqrt(np.mean(before**2)))/ref;ea=float(np.sqrt(np.mean(after**2)))/ref
  # Prefer a decayed phrase before the landing; avoid an imminent strong new attack.
  scores.append(eb+.4*max(0,ea-eb)+.08*abs(t-2.0))
 i=int(np.argmin(scores));delay=float(candidates[i])
 return delay,{**info,'method':method,'delay_seconds':delay,'candidate_delays':candidates.tolist(),'candidate_scores':scores,'bar_detection':False}

def mix_cadence(rendered,gesture,block_start,entry,rate=48000):
 """Sample-exact entry, including a future entry inside or after this block."""
 offset=block_start+np.arange(len(rendered))-entry
 valid=(offset>=0)&(offset<len(gesture));tail=np.zeros_like(rendered);tail[valid]=gesture[offset[valid]]
 alpha=np.clip(offset/(rate*.3),0,1)[:,None]
 return rendered*(1-alpha)+tail*alpha
