"""Controlled continuation hint ablations; all other prepared inputs unchanged."""
import json,shutil
import numpy as np
from bundle import OUT
cases=OUT/'cases';base=cases/'continuous_verse_120';hint=np.load(cases/'prism_60/context_latents.npy')[...,:64];sil=np.load(OUT/'flow_cases/silence_latent.npy')
for variant in ['active_hint','raw_prefix_active_hint','blank_hint','lookahead48','lookahead52']:
 name='ablation_'+variant;p=cases/name;p.mkdir(exist_ok=True)
 for f in base.glob('*.npy'):shutil.copy2(f,p/f.name)
 meta=json.loads((base/'case.json').read_text());meta['name']=name;meta['ablation']=variant
 ctx=np.load(p/'context_latents.npy');n=1000
 if variant in ['active_hint','raw_prefix_active_hint']:
  ctx[...,:64]=hint[:,:1000]
  if variant=='raw_prefix_active_hint':ctx[:,:300,:64]=np.load(p/'source.npy')[:,:300]
 elif variant=='blank_hint':
  ctx[:,300:,:64]=np.tile(sil,(1,1+1000//sil.shape[1],1))[:,300:1000]
 else:
  n=int(variant[-2:])*25;meta['duration']=n/25
  ctx=np.concatenate([ctx,np.tile(ctx[:,-5:],(1,(n-1000)//5,1))],axis=1)
  for key in ['source','src_latents','mask']:
   f=p/(key+'.npy')
   if f.exists():
    a=np.load(f);a=np.concatenate([a,np.repeat(a[:,-1:],n-1000,axis=1)],axis=1);np.save(f,a)
  np.save(p/'noise.npy',np.random.default_rng(meta['seed']).standard_normal((1,n,64)).astype(np.float32))
 np.save(p/'context_latents.npy',ctx);(p/'case.json').write_text(json.dumps(meta,indent=2))
 print(name)
