import os,json,time,fcntl,resource
from pathlib import Path
import numpy as np
from native_vae import VAE
from chunk_decode import ChunkDecoder
import track_memory
P=Path(__file__).resolve().parent;lock=open('/data/roadscore/generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);vae=VAE(P/'vae_weights');decoder=ChunkDecoder(vae)
for case in os.environ.get('ACE_CASES','reference30,reference90').split(','):
 O=P/case;latent=np.load(O/'chestnut_latents.npy');times=[]
 for i in range(2):
  pcm,t=decoder.decode(latent);times.append(t);print('CHUNK',case,i,t,flush=True)
 np.save(O/'chunk_pcm.npy',pcm);r={'seconds':times,'duration':len(pcm)/48000,'rtf':times[-1]/(len(pcm)/48000),'tracked_gpu_peak_bytes':track_memory.peak,'host_peak_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'window_latent_frames':375,'core_latent_frames':250,'finite':bool(np.isfinite(pcm).all())}
 if (O/'chestnut_pcm.npy').exists():
  ref=np.load(O/'chestnut_pcm.npy');r.update(relative_rmse=float(np.linalg.norm(pcm-ref)/np.linalg.norm(ref)),max_abs_error=float(abs(pcm-ref).max()))
 (O/'chunk_result.json').write_text(json.dumps(r,indent=2));print(r,flush=True)
 if 'relative_rmse' in r:assert r['relative_rmse']<.01
