"""Export candidate boundary templates only; weights remain shared with original ACE."""
import json,hashlib
import numpy as np
from bundle import OUT,OLD
for identity,style,initial,stem in [('prism','128 BPM D minor crystal-pluck K-pop/game score','shape_30','window45_'),('aurora','116 BPM A minor warm analog and bell game score','aurora_initial','aurora45_'),('circuit','136 BPM E minor funky guitar/clavinet game score','circuit_initial','circuit45_')]:
 root=OLD/'profiles'/identity;root.mkdir(parents=True,exist_ok=True);manifest={'profile':identity,'style':style,'preparation_host':'Mac official ACE; runtime needs only prepared tensors','initial_seed':33602,'roles':{},'policy':'initial30s commit28; continuation45s preserve8 commit36; final9s lookahead excluded; adaptive terminal-energy endpoint checked before next-prefix selection'}
 for role in ['initial','verse','prechorus','chorus','bridge','outro']:
  source=OUT/'cases'/(initial if role=='initial' else stem+role);dest=root/role;dest.mkdir(exist_ok=True)
  for key in ['encoder_hidden_states','encoder_attention_mask','context_latents','source','mask']:
   f=source/(key+'.npy')
   if not f.exists():continue
   name={'source':'sampler_clean_src_latents','mask':'sampler_repaint_mask'}.get(key,key);a=np.load(f).astype(bool if 'mask' in key else np.float16);np.save(dest/(name+'.npy'),a)
  meta=json.loads((source/'case.json').read_text());(dest/'sampler.json').write_text(json.dumps(meta['sampler'],indent=2));(dest/'preparation.json').write_text(json.dumps(meta,indent=2));manifest['roles'][role]={'source_case':source.name,'commit_seconds':28 if role=='initial' else 36,'sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in dest.glob('*.npy')}}
 (root/'profile.json').write_text(json.dumps(manifest,indent=2));print(root)
