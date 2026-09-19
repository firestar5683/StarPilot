"""Diagnostic proxies, not instrument recognition or musical acceptance."""
import numpy as np
from phrase import pulse

def density(a,sr):
 x=np.mean(a,axis=1);step=max(1,sr//11025);x=x[::step];r=sr/step;n=1024;hop=round(r*.01)
 f=np.lib.stride_tricks.sliding_window_view(x,n)[::hop];m=np.abs(np.fft.rfft(f*np.hanning(n),axis=1));hz=np.fft.rfftfreq(n,1/r)
 flux=np.maximum(0,np.diff(m,axis=0)).mean(axis=1);med=np.median(flux);mad=np.median(abs(flux-med));cut=med+2*mad
 peaks=[]
 for i in range(1,len(flux)-1):
  if flux[i]>cut and flux[i]>=flux[i-1] and flux[i]>flux[i+1] and (not peaks or (i-peaks[-1])*hop/r>.15):peaks.append(i)
 energy=(m*m).mean(axis=0);total=max(float(energy.sum()),1e-12)
 return {'transient_peaks_per_second':len(peaks)/(len(a)/sr),'bass_energy_share_40_220_hz':float(energy[(hz>=40)&(hz<=220)].sum()/total),'high_energy_share_2000_8000_hz':float(energy[(hz>=2000)&(hz<=8000)].sum()/total),'normalized_flux':float(flux.mean()/max(m.mean(),1e-12)),'pulse':pulse(a,sr)}
