import json
from pathlib import Path
import numpy as np,soundfile as sf
from scipy.signal import resample_poly
from musical import match_continuation
R=Path('/data/roadscore/results/quality');rate=48000;end=round(301*4096/44100*rate);context=86*4096/44100

def read(name):
 w,sr=sf.read(R/(name+'.wav'),dtype='float32',always_2d=True);return resample_poly(w,rate,sr).astype('float32')
w=read('nocturne_initial')[:end];metrics=[]
for i in range(3):
 new=read(f'nocturne_trim_{i}')[round((context-2)*rate):end];n=rate*2;new,m=match_continuation(w,new,n);m['seam_audio_s']=len(w)/rate;m['correlation']=float(np.corrcoef(w[-n:].ravel(),new[:n].ravel())[0,1]);metrics.append(m)
 alpha=np.linspace(0,1,n)[:,None];w=np.concatenate([w[:-n],w[-n:]*(1-alpha)+new[:n]*alpha,new[n:]])
sf.write(R/'nocturne_trim_journey.wav',w,rate);sf.write(R/'continuation_trim_new.wav',w[end-rate*6:end+rate*8],rate)
old=read('nocturne_journey');sf.write(R/'continuation_trim_old.wav',old[24*rate:38*rate],rate)
x=w[:len(w)//4800*4800].reshape(-1,4800,2);r=np.sqrt(np.mean(x*x,axis=(1,2)))
(R/'trim_metrics.json').write_text(json.dumps({'seconds':len(w)/rate,'near_silence_seconds':float((r<.00316).sum()/10),'boundaries':metrics},indent=2))
