import time,json,resource,fcntl
from pathlib import Path
import numpy as np
from tinygrad import TinyJit,Device
from tinygrad.helpers import GlobalCounters
from native_ace import tensor
from native_vae import VAE
P=Path(__file__).resolve().parent;lock=open('/data/roadscore/generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
t=time.monotonic();m=VAE(P/'vae_weights');load=time.monotonic()-t;x=tensor(np.load(P/'vae_input.npy').astype(np.float16));fn=TinyJit(m.forward);times=[]
for i in range(4):
 t=time.monotonic();y=fn(x);Device['AMD'].synchronize();times.append(time.monotonic()-t);print('VAE',i,times[-1],flush=True)
y=y.numpy().astype(np.float32);ref=np.load(P/'vae_expected.npy');np.save(P/'vae_actual.npy',y)
d={'load_seconds':load,'times':times,'relative_rmse':float(np.linalg.norm(y-ref)/np.linalg.norm(ref)),'max_abs_error':float(abs(y-ref).max()),'finite':bool(np.isfinite(y).all()),'tracked_gpu_bytes':GlobalCounters.mem_used,'peak_host_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024};(P/'vae_result.json').write_text(json.dumps(d,indent=2));print(d,flush=True)
assert d['finite'] and d['relative_rmse']<.03
