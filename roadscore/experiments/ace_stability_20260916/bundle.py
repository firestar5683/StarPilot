"""Explicit, portable model-boundary inputs; no route or output-device access."""
from pathlib import Path
import numpy as np,json,hashlib
R=Path(__file__).resolve().parents[2];OLD=R/'experiments/ace_chestnut_20260916';OUT=R/'results/ace_stability_20260916'
def create(name,source,seed,previous=None):
 p=Path(source);o=OUT/'cases'/name;o.mkdir(parents=True,exist_ok=True)
 arrays={k:np.load(p/(k+'.npy')).astype(np.float16) for k in ['encoder_hidden_states','context_latents']}
 arrays['encoder_attention_mask']=np.load(p/'encoder_attention_mask.npy').astype(bool)
 n=arrays['context_latents'].shape[1];arrays['noise']=np.random.default_rng(seed).standard_normal((1,n,64)).astype(np.float16)
 settings=json.loads((p/'sampler.json').read_text()) if (p/'sampler.json').exists() else {'dcw_enabled':False,'shift':1.0,'infer_steps':8}
 if (p/'sampler_repaint_mask.npy').exists():
  arrays['mask']=np.load(p/'sampler_repaint_mask.npy').astype(bool);arrays['source']=np.load(p/'sampler_clean_src_latents.npy').astype(np.float16)
  prefix=int(np.flatnonzero(arrays['mask'][0])[0])
  if previous is not None:
   prev=np.load(previous);arrays['source'][:,:prefix]=prev[:,-prefix:];arrays['context_latents'][:,:prefix,:64]=arrays['source'][:,:prefix]
 for k,v in arrays.items():np.save(o/(k+'.npy'),v)
 meta={'name':name,'source':str(p),'seed':seed,'noise_generator':'explicit NumPy PCG64 FP16 tensor shared by both runners','sampler':settings,'previous':str(previous) if previous else None,'duration':n/25,'sha256':{k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in arrays.items()}}
 (o/'case.json').write_text(json.dumps(meta,indent=2));return o
if __name__=='__main__':
 create('legacy_verse',R/'results/ace_chestnut_20260916/verse',22601)
 create('legacy_prechorus',R/'results/ace_chestnut_20260916/repaint_prechorus',22602,R/'results/ace_chestnut_20260916/flow/verse_latents.npy')
