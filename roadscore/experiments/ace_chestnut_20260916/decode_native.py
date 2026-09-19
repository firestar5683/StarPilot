"""File-only Chestnut ACE VAE decoding. No audio output API."""
import os,time,json,resource,fcntl,gc
from pathlib import Path
import numpy as np
from tinygrad import TinyJit,Device
from tinygrad.helpers import GlobalCounters
from native_ace import tensor
from native_vae import VAE
P=Path(__file__).resolve().parent;lock=open('/data/roadscore/generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
t=time.monotonic();m=VAE(P/'vae_weights');load=time.monotonic()-t
for relative in os.environ.get('ACE_LATENTS','tc2_generated_latents.npy').split(','):
 path=P/relative;raw=np.load(path).astype(np.float16).transpose(0,2,1);x=tensor(raw);fn=TinyJit(m.forward);times=[]
 for i in range(3):
  t=time.monotonic();y=fn(x);Device['AMD'].synchronize();times.append(time.monotonic()-t);print('DECODE',relative,i,times[-1],flush=True)
 a=y.numpy()[0].T.astype(np.float32);np.save(path.with_name(path.stem+'_pcm.npy'),a)
 r={'input':relative,'load_seconds':load,'decode_seconds':times,'duration':len(a)/48000,'warm_decode_rtf':times[-1]/(len(a)/48000),'tracked_gpu_bytes':GlobalCounters.mem_used,'host_peak_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'peak':float(abs(a).max()),'rms':float(np.sqrt(np.mean(a*a))),'finite':bool(np.isfinite(a).all())};path.with_name(path.stem+'_decode.json').write_text(json.dumps(r,indent=2));print(r,flush=True)
 assert r['finite']
 del fn,x,y;gc.collect()
