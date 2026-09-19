"""Timing diagnostics supplement listening; they do not certify musical equivalence."""
import json
import numpy as np,soundfile as sf
from scipy.signal import stft,find_peaks
from bundle import OUT
reports={}
for name in ['prism_30','prism_45','prism_60','aurora_45','circuit_30','circuit_45','circuit_60']:
 p=OUT/'cases'/name;a,sr=sf.read(p/'native_0/audio.wav',always_2d=True,dtype='float32');b,_=sf.read(p/'reference_rounded/audio.wav',always_2d=True,dtype='float32')
 def features(x):
  _,_,z=stft(x.T,fs=sr,nperseg=2048,noverlap=1568,boundary=None,padded=False);s=np.log1p(abs(z).mean(0)*100);flux=np.maximum(np.diff(s,axis=1),0).sum(0);return s,flux
 sa,fa=features(a);sb,fb=features(b);lags=[]
 for start in range(0,min(len(fa),len(fb))-500+1,500):
  x=fa[start:start+500];y=fb[start:start+500];c=np.correlate(x-x.mean(),y-y.mean(),'full');lags.append(int(np.argmax(c[494:505])-5))
 pa=find_peaks(fa,distance=8,prominence=max(.1,float(np.std(fa))*.4))[0];pb=find_peaks(fb,distance=8,prominence=max(.1,float(np.std(fb))*.4))[0]
 distances=[min(abs(pb-i),default=9999) for i in pa];reports[name]={'spectral_flux_correlation':float(np.corrcoef(fa,fb)[0,1]),'five_second_flux_lag_10ms_bins':lags,'native_detected_onsets':len(pa),'reference_detected_onsets':len(pb),'native_onsets_matching_reference_within20ms':int(sum(d<=2 for d in distances)),'relative_log_spectral_l2':float(np.linalg.norm(sa-sb)/max(np.linalg.norm(sb),1e-12)),'scope':'same rounded boundary inputs, full official FP32 generation versus native FP16; automated onset extraction cannot establish subjective quality'}
(OUT/'rhythm_audit.json').write_text(json.dumps(reports,indent=2));print({k:{'flux_correlation':v['spectral_flux_correlation'],'lags':v['five_second_flux_lag_10ms_bins']} for k,v in reports.items()})
