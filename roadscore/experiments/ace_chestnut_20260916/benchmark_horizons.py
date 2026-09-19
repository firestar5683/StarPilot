"""Actual prepared conditions, native ACE DiT; no route or physical audio access."""
import os,time,json,fcntl,resource,gc
from pathlib import Path
import numpy as np
from native_ace import DiT,tensor,time_features
from native_vae import VAE
from tinygrad import TinyJit,Device
from tinygrad.helpers import GlobalCounters
P=Path(__file__).resolve().parent
lock=open('/data/roadscore/generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
t=time.monotonic();m=DiT(P/'weights');load=time.monotonic()-t;t=time.monotonic();vae=VAE(P/'vae_weights');vae_load=time.monotonic()-t
for duration in [int(v) for v in os.environ.get('ACE_DURATIONS','30,45,60,90').split(',')]:
 O=P/f'reference{duration}';x,cond,ctx=[tensor(np.load(O/(k+'.npy')).astype(np.float16)) for k in ['hidden_states','encoder_hidden_states','context_latents']]
 m.prepare_shape(x.shape[1]);tf=tensor(time_features([1]));rf=tensor(time_features([0]));fn=TinyJit(m.forward);times=[]
 for i in range(3):
  t=time.monotonic();y=fn(x,cond,ctx,tf,rf);Device['AMD'].synchronize();times.append(time.monotonic()-t);print('WARMUP',duration,i,times[-1],flush=True)
 schedule=np.linspace(1,0,9).tolist();t=time.monotonic()
 for i in range(8):
  tf.assign(tensor(time_features([schedule[i]]))).realize();v=fn(x,cond,ctx,tf,rf);x.assign(x-v*(schedule[i]-schedule[i+1])).realize()
 Device['AMD'].synchronize();elapsed=time.monotonic()-t;a=x.numpy();np.save(O/'chestnut_latents.npy',a)
 r={'duration':x.shape[1]/25,'generation_seconds':elapsed,'latent_rtf':elapsed/(x.shape[1]/25),'load_seconds':load,'forward_seconds':times,'tc_opt':os.environ.get('TC_OPT'),'tracked_gpu_bytes':GlobalCounters.mem_used,'host_peak_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'finite':bool(np.isfinite(a).all())}
 decode=TinyJit(vae.forward);z=tensor(a.transpose(0,2,1));decode_times=[]
 for j in range(3):
  t=time.monotonic();wave=decode(z);Device['AMD'].synchronize();decode_times.append(time.monotonic()-t);print('DECODE',duration,j,decode_times[-1],flush=True)
 pcm=wave.numpy()[0].T.astype(np.float32);np.save(O/'chestnut_pcm.npy',pcm)
 r.update(vae_load_seconds=vae_load,decode_seconds=decode_times,total_warm_seconds=elapsed+decode_times[-1],total_warm_rtf=(elapsed+decode_times[-1])/r['duration'],tracked_gpu_bytes=GlobalCounters.mem_used,host_peak_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,pcm_finite=bool(np.isfinite(pcm).all()),sampler='8-step Euler, DCW disabled',conditioning='actual Mac-prepared inputs; excluded from warm device timing')
 (O/'chestnut_result.json').write_text(json.dumps(r,indent=2));print('RESULT',r,flush=True)
 assert r['finite']
 del fn,x,cond,ctx,tf,rf,y,v,decode,z,wave;gc.collect()
