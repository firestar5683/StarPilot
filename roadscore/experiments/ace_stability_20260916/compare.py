"""Numerical and temporal comparison; retains failures rather than changing limits."""
import sys,json,hashlib
from pathlib import Path
import numpy as np,soundfile as sf
from bundle import OUT

def metrics(a,b):
 a=a.astype(np.float64);b=b.astype(np.float64);d=a-b;frame=np.sqrt(np.mean(d*d,axis=-1)).reshape(-1);return {'relative_rmse':float(np.linalg.norm(d)/max(np.linalg.norm(b),1e-20)),'peak_relative_error':float(abs(d).max()/max(abs(b).max(),1e-20)),'max_error_frame':int(np.argmax(frame)),'max_abs_error':float(abs(d).max()),'finite':bool(np.isfinite(a).all())}
reports={}
for name in sys.argv[1:]:
 p=OUT/'cases'/name;ref=p/'reference';native=p/'native_0';official=p/'official';ref=(p/'reference_rounded') if (p/'reference_rounded/latents.npy').exists() else (ref if (ref/'latents.npy').exists() else official)
 if not (native/'latents.npy').exists():continue
 r={'reference_directory':ref.name,'input_match':'same FP16 boundary values' if ref.name=='reference_rounded' or name.startswith(('legacy_','paired45_')) else 'original FP32 captured values; native rounds inputs toFP16','latents':metrics(np.load(native/'latents.npy'),np.load(ref/'latents.npy')),'steps':[]}
 for i in range(8):
  f=ref/f'step_{i}.npy';f=f if f.exists() else ref/f'input_{i+1}.npy'
  if f.exists():r['steps'].append({'step':i,**metrics(np.load(native/f'step_{i}.npy'),np.load(f))})
 for label,folder in [('native',native),('reference',ref)]:
  if (folder/'pcm.npy').exists():a=np.load(folder/'pcm.npy')
  else:a,sr=sf.read(folder/'audio.wav',always_2d=True)
  n=4800;e=np.sqrt(np.mean(a[:len(a)//n*n].reshape(-1,n,2).astype(np.float64)**2,axis=(1,2)));r[label+'_energy']=e.tolist();r[label+'_quiet_seconds']=float(sum(e<.003)/10)
 r['envelope_correlation']=float(np.corrcoef(r['native_energy'],r['reference_energy'])[0,1]);reports[name]=r
(OUT/'comparisons.json').write_text(json.dumps(reports,indent=2));print({k:{'latents':v['latents'],'envelope_correlation':v['envelope_correlation']} for k,v in reports.items()})
