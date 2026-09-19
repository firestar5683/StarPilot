"""Fixed lookahead windows: preserve12s, commit interior40s, discard terminal8s."""
import json,shutil
import numpy as np
from bundle import OUT
for duration in [48,52]:
 for role in ['verse','prechorus','chorus','bridge','outro']:
  base=OUT/'cases'/f'continuous_{role}_120';p=OUT/'cases'/f'window{duration}_{role}';p.mkdir(exist_ok=True)
  for f in base.glob('*.npy'):shutil.copy2(f,p/f.name)
  n=duration*25
  for key in ['context_latents','source','src_latents','mask']:
   f=p/(key+'.npy')
   if f.exists():
    a=np.load(f);a=np.concatenate([a,np.tile(a[:,-5:],(1,(n-1000)//5)+( (1,) if a.ndim==3 else () ))],axis=1);np.save(f,a)
  meta=json.loads((base/'case.json').read_text());meta.update(name=p.name,duration=duration,commit_seconds=40,lookahead_seconds=duration-40,preparation='Official120s conditioning, fixed lookahead window, commit interior40s; dynamic actual previous12s prefix')
  np.save(p/'noise.npy',np.random.default_rng(meta['seed']).standard_normal((1,n,64)).astype(np.float16));(p/'case.json').write_text(json.dumps(meta,indent=2))
