import os,time,json,fcntl,resource
from pathlib import Path
import numpy as np
from native_ace import DiT,tensor,time_features
from tinygrad import TinyJit,Device
from tinygrad.helpers import GlobalCounters
P=Path(__file__).resolve().parent;O=P/'reference15';prefix=os.environ.get('ACE_RESULT_PREFIX','');lock=open('/data/roadscore/generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
t=time.monotonic();m=DiT(P/'weights_int8');loaded=time.monotonic()-t;print('WEIGHTS_READY',loaded,GlobalCounters.mem_used,flush=True)
x,cond,ctx=[tensor(np.load(O/(k+'.npy')).astype(np.float16)) for k in ['hidden_states','encoder_hidden_states','context_latents']];m.prepare_shape(x.shape[1]);tf=tensor(time_features([1]));rf=tensor(time_features([0]));fn=TinyJit(m.forward);times=[]
for i in range(4):
 t=time.monotonic();out=fn(x,cond,ctx,tf,rf);Device['AMD'].synchronize();times.append(time.monotonic()-t);print('FULL',i,times[-1],GlobalCounters.mem_used,flush=True)
y=out.numpy().astype(np.float32);np.save(P/(prefix+'full_actual.npy'),y);reference_file=os.environ.get('ACE_REFERENCE','velocity_fp16.npy');ref=np.load(O/reference_file);error=y-ref
report={'reference_file':reference_file,'tc_opt':os.environ.get('TC_OPT','0'),'sampler':'8-step Euler; DCW disabled','load_seconds':loaded,'full_forward_seconds':times,'relative_rmse':float(np.linalg.norm(error)/np.linalg.norm(ref)),'peak_relative_error':float(abs(error).max()/abs(ref).max()),'max_abs_error':float(abs(error).max()),'finite':bool(np.isfinite(y).all()),'peak_host_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'tracked_gpu_bytes':GlobalCounters.mem_used,'weights_bytes':sum(w.numel()*w.dtype.itemsize for w in m.w.values()),'audio_seconds':x.shape[1]/25,'projection_8steps_rtf':8*times[-1]/(x.shape[1]/25)}
(P/(prefix+'full_result.json')).write_text(json.dumps(report,indent=2));print(report,flush=True)
# Exploratory storage quantization; loosened quality rejection guard is NOT equivalence.
original=np.load(O/'velocity_0.npy');report['original_fp32_weight_drift_rmse']=float(np.linalg.norm(y-original)/np.linalg.norm(original));report['quality_status']='unapproved quantization candidate; implementation comparison uses quantized official reference';report['equivalence_1pct']=report['relative_rmse']<.01 and report['peak_relative_error']<.01
assert report['finite'] and report['relative_rmse']<.01 and report['peak_relative_error']<.015
# Eight trained-weight flow steps, identical initial noise and cached conditioning.
schedule=np.linspace(1,0,9,dtype=np.float32).tolist();start=time.monotonic()
for i in range(8):
 Device['AMD'].synchronize();tf.assign(tensor(time_features([schedule[i]]))).realize();v=fn(x,cond,ctx,tf,rf);x.assign(x-v*(schedule[i]-schedule[i+1])).realize()
Device['AMD'].synchronize();elapsed=time.monotonic()-start;np.save(P/(prefix+'generated_latents.npy'),x.numpy());report.update(generation_seconds=elapsed,generation_rtf=elapsed/(x.shape[1]/25));(P/(prefix+'full_result.json')).write_text(json.dumps(report,indent=2));print('GENERATION',elapsed,flush=True)
