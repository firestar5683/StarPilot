"""Estimated beat/bar grid of generated music. Meter/downbeat are hypotheses, not labels."""
import numpy as np

def grid(wave,rate,bpm_prior=None):
 x=wave.mean(axis=1)[::max(1,rate//8000)];sr=rate/max(1,rate//8000);hop=round(sr*.01);n=512
 if len(x)<sr*4:raise ValueError('At least four seconds required')
 frames=np.lib.stride_tricks.sliding_window_view(x,n)[::hop]
 mag=abs(np.fft.rfft(frames*np.hanning(n),axis=1));flux=np.maximum(0,np.diff(mag,axis=0)).mean(axis=1);flux=np.maximum(0,flux-np.median(flux))
 ac=np.correlate(flux,flux,'full')[len(flux)-1:];lags=np.arange(33,76);scores=ac[lags].copy()
 if bpm_prior is not None:scores*=np.exp(-4*np.abs(np.log2((6000/lags)/bpm_prior)))
 lag=int(lags[np.argmax(scores)]);period=lag*.01
 times=(np.arange(len(flux))+1)*.01+n/(2*sr)
 phases=np.linspace(0,period,100,endpoint=False)
 scores=[np.interp(np.arange(p,times[-1],period),times,flux).mean() for p in phases];phase=float(phases[np.argmax(scores)])
 beats=np.arange(phase,times[-1],period)
 # Accent-based 4/4 phase inference, uncertain for syncopated breakbeats.
 accent=np.interp(beats,times,flux);bar_scores=[float(np.mean(accent[i::4])) for i in range(4)];bar_phase=int(np.argmax(bar_scores));bars=beats[bar_phase::4]
 return {'bpm':60/period,'bpm_prior':bpm_prior,'tempo_candidates':[{'bpm':float(6000/i),'autocorrelation':float(ac[i]/max(ac[0],1e-10))} for i in lags[np.argsort(ac[lags])[-5:][::-1]]],'period':period,'beat_phase':phase,'downbeats':bars.tolist(),'bar_phase':bar_phase,'pulse_confidence':float(ac[lag]/max(ac[0],1e-10)),'bar_confidence':float((max(bar_scores)-np.median(bar_scores))/max(max(bar_scores),1e-10)),'meter':4,'downbeat_verified':False,'method':'spectral flux autocorrelation and four-beat accent hypothesis'}

def join(left,right,rate,overlap=0.,bpm_prior=None):
 a=grid(left,rate,bpm_prior);b=grid(right,rate,bpm_prior)
 end=max(t for t in a['downbeats'] if t<len(left)/rate-.2);start=next(t for t in b['downbeats'] if t>=.1)
 l=left[:round(end*rate)];r=right[round(start*rate):];n=min(round(overlap*rate),len(l),len(r))
 # Incoming downbeat lands at outgoing downbeat; overlap only pre-boundary tails.
 if n:
  pre=right[max(0,round(start*rate)-n):round(start*rate)];n=min(n,len(pre));alpha=np.linspace(0,1,n)[:,None]
  l[-n:]=l[-n:]*(1-alpha)+pre[-n:]*alpha
 return np.concatenate([l,r]),{'outgoing_grid':a,'incoming_grid':b,'actual_transition_seconds':len(l)/rate,'outgoing_cut_seconds':end,'incoming_cut_seconds':start,'overlap_seconds':n/rate,'estimated_bar_offset_seconds':0.,'human_rhythm_harmony_pass':None}
