"""Whole-section development proxies; no claim to judge taste or recognize instruments."""
import json
from pathlib import Path
import numpy as np,soundfile as sf
from density import density
R=Path(__file__).resolve().parents[1];O=R/'results/unattended';out={}
for folder in O.iterdir():
 if not (folder/'long.wav').exists():continue
 wave,sr=sf.read(folder/'long.wav',always_2d=True);jobs=json.loads((folder/'jobs.json').read_text());bounds=[0]+[j['new_material_audio_s'] for j in jobs]+[len(wave)/sr];sections=[]
 for i,(start,end) in enumerate(zip(bounds,bounds[1:])):
  a=wave[round((start+2)*sr):round((end-4.1)*sr)]
  if len(a)<sr:continue
  d=density(a,sr);d.update(start=start,end=end,state='establish' if i==0 else jobs[i-1]['state'],rms=float(np.sqrt(np.mean(a*a))))
  # Normalized chroma captures harmonic distribution; spectral shape is level-independent.
  x=a.mean(axis=1)[::4];rate=sr/4;n=2048;frames=np.lib.stride_tricks.sliding_window_view(x,n)[::1024];mag=abs(np.fft.rfft(frames*np.hanning(n)));hz=np.fft.rfftfreq(n,1/rate);energy=(mag**2).mean(axis=0);ch=np.zeros(12);good=hz>40;notes=np.rint(69+12*np.log2(hz[good]/440)).astype(int)%12
  np.add.at(ch,notes,energy[good]);ch/=max(np.linalg.norm(ch),1e-12);d['chroma']=ch.tolist();bands=[float(energy[(hz>=lo)&(hz<hi)].sum()) for lo,hi in zip([40,120,300,700,1600,3500],[120,300,700,1600,3500,5500])];bands=np.array(bands);bands/=max(bands.sum(),1e-12);d['spectral_distribution']=bands.tolist();sections.append(d)
 for i,s in enumerate(sections):
  s['harmonic_distance_from_opening']=float(1-np.dot(s['chroma'],sections[0]['chroma']));s['spectral_distance_from_opening']=float(np.linalg.norm(np.array(s['spectral_distribution'])-sections[0]['spectral_distribution']))
 blocks=wave[:len(wave)//4410*4410].reshape(-1,4410,2);rms=np.sqrt(np.mean(blocks**2,axis=(1,2)))
 out[folder.name]={'duration':len(wave)/sr,'jobs':len(jobs),'median_generation_seconds':float(np.median([j['seconds'] for j in jobs])),'playback_rtf':float(np.median([j['seconds']/j['playable_new_seconds'] for j in jobs])),'unique_rtf':float(np.median([j['seconds']/j['new_seconds'] for j in jobs])),'silence_under_minus50_seconds':float(np.sum(rms<.0031623)*.1),'peak':float(abs(wave).max()),'sections':sections}
 print(folder.name,[(s['state'],round(s['harmonic_distance_from_opening'],3),round(s['spectral_distance_from_opening'],3),round(s['transient_peaks_per_second'],2)) for s in sections],flush=True)
(O/'development_metrics.json').write_text(json.dumps(out,indent=2))
