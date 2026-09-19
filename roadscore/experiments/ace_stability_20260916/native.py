"""Locked native validation runner; explicit transfers/fences, per-step evidence."""
import os
os.environ.setdefault('TC_OPT','2')
import sys,time,json,hashlib,fcntl,resource
from pathlib import Path
import numpy as np,soundfile as sf
from bundle import R,OLD,OUT
sys.path.insert(0,str(OLD))
from native_ace import DiT,tensor,time_features
if os.environ.get("ACE_RESIDUAL_FP32")=="1":from mixed_native_ace import DiT
from native_vae import VAE
from chunk_decode import ChunkDecoder
if os.environ.get("ACE_OBSERVED_DECODE")=="1":from observed_decode import ChunkDecoder
from tinygrad import Device,TinyJit
from tinygrad.helpers import GlobalCounters
import track_memory
from sampler import dcw
lock=open(R/'generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
start=time.monotonic();m=DiT(OLD/'weights');vae=VAE(OLD/'vae_weights');decoder=ChunkDecoder(vae);print('LOADED',time.monotonic()-start,flush=True);graphs={};decoder_ready=False
models={'base':m}
plan=json.loads(Path(os.environ.get('ACE_VALIDATION_PLAN',str(OUT/'plan.json'))).read_text())
for job in plan:
 variant=job.get('precision','base')
 if variant not in models:
  assert variant=='mixed'
  from mixed_native_ace import DiT as MixedDiT
  mixed=MixedDiT.__new__(MixedDiT);mixed.w=models['base'].w;mixed.layers=models['base'].layers;models[variant]=mixed
 m=models[variant]
 name=job['case'];repeat=job.get('repeat',0);p=OUT/'cases'/name
 deadline=time.monotonic()+1200
 while not (p/'case.json').exists():
  if time.monotonic()>deadline:raise TimeoutError('Case was not prepared: '+name)
  time.sleep(1)
 o=p/job.get('output',f'native_{repeat}');o.mkdir(exist_ok=True);settings=json.loads((p/'case.json').read_text())['sampler'];noise=np.load(p/'noise.npy').astype(np.float16);cond=np.load(p/'encoder_hidden_states.npy').astype(np.float16);ctx=np.load(p/'context_latents.npy').astype(np.float16);valid=np.load(p/'encoder_attention_mask.npy').astype(bool);width=max(256,((cond.shape[1]+31)//32)*32);cm=np.full((1,1,1,width),-np.inf,np.float16);cm[0,0,0,:cond.shape[1]]=np.where(valid[0],0,-np.inf);cond=np.pad(cond,((0,0),(0,width-cond.shape[1]),(0,0)))
 if 'seed' in job:noise=np.random.default_rng(job['seed']).standard_normal(noise.shape).astype(np.float16)
 if 'previous' in job:
  source_input=np.load(p/'source.npy').astype(np.float16);keep_input=np.load(p/'mask.npy').astype(bool);prefix=int(np.flatnonzero(keep_input[0])[0]);prior=np.load(OUT/job['previous']);source_input[:,:prefix]=prior[:,-prefix:];ctx[:,:prefix,:64]=source_input[:,:prefix];np.save(o/'input_source.npy',source_input);np.save(o/'input_context.npy',ctx);np.save(o/'input_noise.npy',noise)
 n=noise.shape[1];m.prepare_shape(n,job.get('align',0));key=(n,width,job.get('align',0),variant);cold=key not in graphs;fn=graphs.setdefault(key,TinyJit(m.forward));x,c,context,cm,tf,rf=[tensor(v) for v in [noise,cond,ctx,cm,time_features([1]),time_features([0])]];source=keep=blend=None
 if (p/'source.npy').exists():
  source=source_input if 'previous' in job else np.load(p/'source.npy').astype(np.float16);keep=np.load(p/'mask.npy').astype(bool);blend=keep.astype(np.float16)
  for row in blend:
   ids=np.flatnonzero(row);left,right=int(ids[0]),int(ids[-1])+1;cf=settings.get('repaint_crossfade_frames',12);lo=max(0,left-cf);hi=min(n,right+cf)
   if left>lo:row[lo:left]=np.linspace(0,1,left-lo+2)[1:-1]
   if hi>right:row[right:hi]=np.linspace(1,0,hi-right+2)[1:-1]
  src,km,bm,nt=[tensor(v) for v in [source,keep[...,None],blend[...,None],noise]]
 wall=time.monotonic();warm=[]
 if cold:
  for _ in range(3):
   st=time.monotonic();fn(x,c,context,tf,rf,cm);Device['AMD'].synchronize();warm.append(time.monotonic()-st);print('WARM',name,warm[-1],flush=True)
 st=time.monotonic();steps=[]
 for i,t in enumerate(np.linspace(1,0,9)[:-1]):
  if job.get('teacher_forcing'):
   teacher=np.load(p/'official'/f'input_{i}.npy').astype(np.float16);x.assign(tensor(teacher)).realize()
  print('SUBMIT',name,repeat,i,GlobalCounters.mem_used,flush=True);Device['AMD'].synchronize();tf.assign(tensor(time_features([t]))).realize();v=fn(x,c,context,tf,rf,cm);old=x.numpy() if settings.get('dcw_enabled',False) else None; x.assign(x-v*.125).realize()
  if old is not None:
   Device['AMD'].synchronize();vel=v.numpy();new=x.numpy();x.assign(tensor(dcw(new,old-vel*t,float(t),settings).astype(np.float16))).realize()
  if source is not None and i<7 and i<round(settings.get('repaint_injection_ratio',.5)*8):x.assign(km.where(x,nt*(t-.125)+src*(1-t+.125))).realize()
  Device['AMD'].synchronize()
  if job.get('teacher_forcing'):np.save(o/f'velocity_{i}.npy',v.numpy())
  a=x.numpy();assert np.isfinite(a).all();np.save(o/f'step_{i}.npy',a);steps.append({'step':i,'elapsed':time.monotonic()-st,'rms':float(np.sqrt(np.mean(a.astype(np.float32)**2))),'sha256':hashlib.sha256(a.tobytes()).hexdigest()});(o/'step_summaries.json').write_text(json.dumps(steps,indent=2));print('READBACK',name,repeat,i,flush=True)
 if source is not None:x.assign(bm*x+(1-bm)*src).realize()
 Device['AMD'].synchronize();latent=x.numpy();generation=time.monotonic()-st;np.save(o/'latents.npy',latent)
 if not decoder_ready:
  for warm_index in range(2):
   print('DECODER_WARM_BEGIN',warm_index,flush=True);warm_start=time.monotonic();decoder.decode(latent[:,:min(375,n)]);print('DECODER_WARM_DONE',warm_index,time.monotonic()-warm_start,flush=True)
  decoder_ready=True
 print('DECODE',name,repeat,flush=True);wave,decode=decoder.decode(latent);np.save(o/'pcm.npy',wave);sf.write(o/'audio.wav',wave*.65,48000,subtype='FLOAT')
 if 'commit_seconds' in job:
  count=round(job['commit_seconds']*25);endpoint={}
  if job.get('adaptive_commit'):
   from window_policy import retained_end
   prefix=int(np.flatnonzero(keep[0])[0])/25 if keep is not None else 0;count,endpoint=retained_end(wave,48000,prefix,job['commit_seconds'],allow_fade=name.endswith('_outro'));(o/'endpoint.json').write_text(json.dumps(endpoint,indent=2))
  np.save(o/'committed_latents.npy',latent[:,:count]);sf.write(o/'committed.wav',wave[:count*1920]*.65,48000,subtype='FLOAT')
 allocator=Device['AMD'].iface.dev_impl.mm.pa_allocator;physical_used=sum(size for size,_,_,free in allocator.blocks.values() if not free);physical_free=sum(size for size,_,_,free in allocator.blocks.values() if free)
 report={'diagnostic_teacher_forcing':bool(job.get('teacher_forcing')),'residual_precision':variant,'physical_vram_used_including_allocator_cache':physical_used,'physical_vram_free':physical_free,'case':name,'repeat':repeat,'warmup_seconds':warm,'wall_seconds':time.monotonic()-wall,'generation_seconds':generation,'decode_seconds':decode,'rtf':(generation+decode)/(n/25),'tracked_gpu_peak':track_memory.peak,'tracked_gpu_current':GlobalCounters.mem_used,'host_peak_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'steps':steps,'latent_sha256':hashlib.sha256(latent.tobytes()).hexdigest(),'pcm_sha256':hashlib.sha256(wave.tobytes()).hexdigest(),'finite':bool(np.isfinite(wave).all())};(o/'report.json').write_text(json.dumps(report,indent=2));print('DONE',name,repeat,report['rtf'],flush=True)
