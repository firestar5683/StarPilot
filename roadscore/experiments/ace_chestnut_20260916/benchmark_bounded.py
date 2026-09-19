"""Actual prepared conditions, native ACE DiT; no route or physical audio access."""
import os,time,json,fcntl,resource,gc
from pathlib import Path
import numpy as np
from native_ace import DiT,tensor,time_features
from native_vae import VAE
from chunk_decode import ChunkDecoder
import track_memory
from tinygrad import TinyJit,Device
from tinygrad.helpers import GlobalCounters
P=Path(__file__).resolve().parent
lock=open('/data/roadscore/generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
t=time.monotonic();m=DiT(P/'weights');load=time.monotonic()-t;t=time.monotonic();vae=VAE(P/'vae_weights');vae_load=time.monotonic()-t;decoder=ChunkDecoder(vae)
for duration in [int(v) for v in os.environ.get('ACE_DURATIONS','45,60,90').split(',')]:
 O=P/f'reference{duration}';x,cond,ctx=[tensor(np.load(O/(k+'.npy')).astype(np.float16)) for k in ['hidden_states','encoder_hidden_states','context_latents']]
 m.prepare_shape(x.shape[1]);tf=tensor(time_features([1]));rf=tensor(time_features([0]));fn=TinyJit(m.forward);times=[]
 for i in range(3):
  t=time.monotonic();y=fn(x,cond,ctx,tf,rf);Device['AMD'].synchronize();times.append(time.monotonic()-t);print('WARMUP',duration,i,times[-1],flush=True)
 schedule=np.linspace(1,0,9).tolist();t=time.monotonic()
 for i in range(8):
  Device['AMD'].synchronize();tf.assign(tensor(time_features([schedule[i]]))).realize();v=fn(x,cond,ctx,tf,rf);x.assign(x-v*(schedule[i]-schedule[i+1])).realize()
 Device['AMD'].synchronize();elapsed=time.monotonic()-t;a=x.numpy();np.save(O/'chestnut_latents.npy',a)
 r={'duration':x.shape[1]/25,'generation_seconds':elapsed,'latent_rtf':elapsed/(x.shape[1]/25),'load_seconds':load,'forward_seconds':times,'tc_opt':os.environ.get('TC_OPT'),'tracked_gpu_bytes':GlobalCounters.mem_used,'host_peak_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'finite':bool(np.isfinite(a).all())}
 # Fixed375-frame decode windows retain ample context and cap resident workspace.
 if not decoder.graphs:
  for _ in range(2):decoder.decode(a[:,:min(375,a.shape[1])])
 pcm,decode_time=decoder.decode(a);decode_times=[decode_time];np.save(O/'bounded_pcm.npy',pcm)
 r.update(vae_load_seconds=vae_load,decode_seconds=decode_times,total_warm_seconds=elapsed+decode_time,total_warm_rtf=(elapsed+decode_time)/r['duration'],tracked_gpu_bytes=GlobalCounters.mem_used,tracked_gpu_peak_bytes=track_memory.peak,host_peak_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,pcm_finite=bool(np.isfinite(pcm).all()),sampler='8-step Euler, DCW disabled; synchronize before timestep USB copy',conditioning='actual Mac-prepared inputs; excluded from warm device timing',decoder='375latent window/250core, discard context')
 if (O/'chestnut_pcm.npy').exists():
  ref=np.load(O/'chestnut_pcm.npy');r['chunk_relative_rmse']=float(np.linalg.norm(pcm-ref)/np.linalg.norm(ref));assert r['chunk_relative_rmse']<.01
 (O/'bounded_result.json').write_text(json.dumps(r,indent=2));print('RESULT',r,flush=True)
 assert r['finite']
 del fn,x,cond,ctx,tf,rf,y,v;gc.collect()
