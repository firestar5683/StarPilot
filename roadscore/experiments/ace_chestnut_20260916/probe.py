import os,time,json,fcntl,resource
from pathlib import Path
import numpy as np
from native_ace import DiT,tensor
from tinygrad import TinyJit,Device
from tinygrad.helpers import GlobalCounters
P=Path(__file__).resolve().parent;lock=open('/data/roadscore/generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
t=time.monotonic();m=DiT(P/'weights',layers=1);load=time.monotonic()-t
x,c,temb,co,si,mask=[tensor(np.load(P/(n+'.npy'))) for n in ['x','cond','temb','cos','sin','mask']];fn=TinyJit(lambda x,c,t,co,si,ma:m.block(x,c,t,(co.unsqueeze(1),si.unsqueeze(1)),ma))
times=[]
for i in range(4):
 t=time.monotonic();out=fn(x,c,temb,co,si,mask);Device['AMD'].synchronize();times.append(time.monotonic()-t);print('BLOCK',i,times[-1],flush=True)
y=out.numpy().astype(np.float32);ref=np.load(P/'expected.npy');np.save(P/'block_actual.npy',y)
d={'load_seconds':load,'block_times':times,'relative_rmse':float(np.sqrt(np.mean((y-ref)**2))/np.sqrt(np.mean(ref**2))),'max_abs_error':float(abs(y-ref).max()),'finite':bool(np.isfinite(y).all()),'tracked_gpu_bytes':GlobalCounters.mem_used,'peak_host_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'weights_bytes':sum(w.numel()*w.dtype.itemsize for w in m.w.values())};(P/'block_result.json').write_text(json.dumps(d,indent=2));print(d,flush=True)
assert d['finite'] and d['relative_rmse']<.01 and d['max_abs_error']<.05
