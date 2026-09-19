"""Sequential fresh native composition; each next section sees only prior generated latents."""
import os,fcntl,json,time,resource
from pathlib import Path
import numpy as np
from ace_runtime import Composer
from native_ace import tensor,time_features
from tinygrad import Device
import track_memory
P=Path(__file__).resolve().parent;O=P/'flow';O.mkdir(exist_ok=True);lock=open('/data/roadscore/generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
t=time.monotonic();c=Composer(P);load=time.monotonic()-t;previous=None;reports=[]
# Validate newly-added condition padding/masking against the saved official FP32 boundary.
cond,context,mask,*_=c.prepare('reference15');c.dit.prepare_shape(context.shape[1]);x=tensor(np.load(P/'reference15/hidden_states.npy').astype(np.float16));y=c.dit.forward(x,tensor(cond),tensor(context),tensor(time_features([1])),tensor(time_features([0])),tensor(mask)).numpy().astype(np.float32);ref=np.load(P/'reference15/velocity_0.npy');e=y-ref
check={'relative_rmse':float(np.linalg.norm(e)/np.linalg.norm(ref)),'peak_relative_error':float(abs(e).max()/abs(ref).max())};(O/'padding_validation.json').write_text(json.dumps(check,indent=2));print('PADDED_REFERENCE',check,flush=True);assert check['relative_rmse']<.01 and check['peak_relative_error']<.01

for i,case in enumerate(os.environ.get('ACE_CASES','verse,repaint_prechorus,repaint_chorus,repaint_bridge,repaint_outro').split(',')):
 wave,latent,r=c.generate(case,22601+i,previous);np.save(O/(case+'_pcm.npy'),wave);np.save(O/(case+'_latents.npy'),latent);r.update(load_seconds=load,tracked_gpu_peak_bytes=track_memory.peak,peak_host_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
 if previous is not None:
  # Before boundary blend starts, preserved latent prefix must remain exactly equal.
  count=round(r['prefix_seconds']*25);r['preserved_prefix_max_error']=float(abs(latent[:,:count-12]-previous[:,-count:-12]).max());assert r['preserved_prefix_max_error']==0
 assert np.isfinite(wave).all();reports.append(r);(O/'results.json').write_text(json.dumps(reports,indent=2));print('SECTION',r,flush=True);previous=latent

quant=P/'int8_generated_latents.npy'
if quant.exists():
 pcm,elapsed=c.decoder.decode(np.load(quant));np.save(O/'int8_pcm.npy',pcm);(O/'int8_decode.json').write_text(json.dumps({'decode_seconds':elapsed,'duration':len(pcm)/48000,'decoder':'native bounded Chestnut; shared warm decoder'},indent=2))

for label in ['aligned60','reference90']:
 path=P/'aligned60_generated_latents.npy' if label=='aligned60' else P/'reference90/chestnut_latents.npy'
 if path.exists():
  pcm,elapsed=c.decoder.decode(np.load(path));np.save(O/(label+'_pcm.npy'),pcm);(O/(label+'_decode.json')).write_text(json.dumps({'decode_seconds':elapsed,'duration':len(pcm)/48000,'decoder':'native bounded Chestnut; shared warm decoder'},indent=2));print('ADDITIONAL_DECODE',label,elapsed,flush=True)
