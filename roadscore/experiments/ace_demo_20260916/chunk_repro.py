"""One fixed375-frame VAE graph, no DiT/replay/assembly. Explicit owned GPU only."""
import os,sys,time,json,fcntl,hashlib,resource
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[2];OLD=R/'experiments/ace_chestnut_20260916';OUT=Path(os.environ.get('ACE_REPRO_OUTPUT',str(R/'results/ace_demo_20260916')));OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(OLD));os.environ.setdefault('TC_OPT','2')
from native_vae import VAE
from native_ace import tensor
from tinygrad import Device,TinyJit
from link_health import LinkProbe
lock=open(R/'generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
mode=os.environ.get('ACE_REPRO_MODE','resident_readback');assert mode in ['resident_readback','resident_compute','upload_readback']
count=int(os.environ.get('ACE_REPRO_REPEATS','40'));idle=float(os.environ.get('ACE_REPRO_IDLE','0'));name=f'chunk_{mode}_idle{idle:g}'
vae=VAE(OLD/'vae_weights');dev=Device['AMD'];probe=LinkProbe(dev,OUT/(name+'_link.jsonl'));probe.install_failure_hook(contain=True);probe.preflight()
latent=np.load(Path(os.environ.get('ACE_REPRO_LATENTS',str(R/'results/ace_stability_20260916/cases/shape_56/native_0/latents.npy'))))[:,:375].transpose(0,2,1).astype(np.float16);z=tensor(latent);dev.synchronize();fn=TinyJit(vae.forward);rows=[]
for i in range(count):
 start=time.monotonic();probe.sample('before_chunk',repeat=i,mode=mode)
 if mode=='upload_readback':z=tensor(latent);dev.synchronize()
 probe.sample('upload_complete_or_resident',repeat=i);result=fn(z);probe.sample('compute_submitted',repeat=i);dev.synchronize();probe.sample('compute_complete',repeat=i)
 digest=None
 if mode!='resident_compute':
  probe.sample('copyout_begin',repeat=i);pcm=result.numpy();digest=hashlib.sha256(pcm.tobytes()).hexdigest();assert np.isfinite(pcm).all();probe.sample('copyout_complete',repeat=i)
 row={'repeat':i,'seconds':time.monotonic()-start,'pcm_sha256':digest,'host_peak_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'mode':mode,'idle_seconds':idle,'healthy':probe.last['healthy']};rows.append(row);(OUT/(name+'.json')).write_text(json.dumps(rows,indent=2));print('CHUNK_DONE',row,flush=True)
 if idle:time.sleep(idle)
print('CHUNK_LOOP_COMPLETE',len(rows),flush=True)
