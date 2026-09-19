"""Exclusive fixed-shape SA3 continuation worker; does not import/open routes."""
import sys,time,json,os,fcntl,traceback,resource
BOOT=time.monotonic();startup={}
from pathlib import Path
import numpy as np
import soundfile as sf
sys.path.insert(0,'/data/sa3-feasibility')
from native_sa3 import DiT,Decoder,tensor,fourier
from tinygrad import Device,dtypes
from tinygrad.helpers import GlobalCounters
ROOT=Path('/data/roadscore')
from rolling import anchor_options,INITIAL_END,WINDOW
from privacy_guard import install
install(ROOT)
OUT=ROOT/'generated';OUT.mkdir(exist_ok=True)
(OUT/'worker_ready').unlink(missing_ok=True)
lock=(OUT/'gpu.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
modelroot=Path('/data/sa3-feasibility');n=int(os.environ.get('ROADSCORE_WINDOW_FRAMES','324'));keepn=86;duration=n*4096/44100
enc=np.load(modelroot/'trained_results/conditioning.npy').astype(np.float16)
w=np.load(modelroot/'native/conditioner.conditioners.seconds_total.embedder.embedding.1.weight.npy').astype(np.float32);b=np.load(modelroot/'native/conditioner.conditioners.seconds_total.embedder.embedding.1.bias.npy').astype(np.float32)
g=(fourier([duration/384]).astype(np.float32)@w.T+b).astype(np.float16)
cond=tensor(np.concatenate([enc,g[:,None]],axis=1));glob=tensor(g);local=tensor(np.zeros((1,n,257),np.float16))
startup['imports_inputs_seconds']=time.monotonic()-BOOT
t=time.monotonic();dit=DiT(modelroot/'native',persistent=True);startup['dit_load_seconds']=time.monotonic()-t
t=time.monotonic();decoder=Decoder(modelroot/'native');startup['decoder_load_seconds']=time.monotonic()-t
sigmas=1/(1+np.exp(2-np.linspace(1,0,9,dtype=np.float32)*8.2));sigmas[0]=1;sigmas[-1]=0
tfs=[tensor(fourier([t])) for t in sigmas[:-1]]
def generate(req):
 start=time.monotonic()
 style=req.get('conditioning','base');identity=req.get('identity','legacy')
 requested_seconds=float(req.get('seconds_total',30))
 gv=(fourier([requested_seconds/384]).astype(np.float32)@w.T+b).astype(np.float16)
 glob.assign(tensor(gv)).realize()
 cache=ROOT/f'assets/conditioning_{identity}_{style}.npy' if identity!='legacy' else ROOT/f'assets/conditioning_{style}.npy'
 active=np.load(cache).astype(np.float16) if cache.exists() else enc
 mix=req.get('conditioning_mix')
 if mix is not None and style!='closing':
  base=np.load(ROOT/f'assets/conditioning_{identity}_base.npy').astype(np.float32)
  develop=np.load(ROOT/f'assets/conditioning_{identity}_approach.npy').astype(np.float32)
  active=((1-float(mix))*base+float(mix)*develop).astype(np.float16)
 cond.assign(tensor(np.concatenate([active,gv[:,None]],axis=1))).realize()
 seed=int(req.get('seed',2000+int(req['id'])));rng=np.random.default_rng(seed)
 context=int(req.get('context_frames',keepn));context=0 if req.get('fresh') else context
 src=np.load(req['latents']);prefix=np.zeros((1,n,256),np.float16);end=min(int(req.get('source_end',323)),src.shape[1])
 if context:prefix[:,:context]=src[:,end-context:end]
 mask=np.zeros((1,n,1),np.float16);mask[:,:context]=1
 anchor_frames=int(req.get('anchor_frames',0))
 if anchor_frames:
  anchor=np.load(req['anchor_latents']);ae=int(req['anchor_end'])
  prefix[:,-anchor_frames:]=anchor[:,ae-anchor_frames:ae];mask[:,-anchor_frames:]=1
 local.assign(tensor(np.concatenate([mask,prefix],axis=-1))).realize()
 x=tensor(rng.standard_normal((1,n,256)).astype(np.float16))
 for i in range(8):
  v=dit(x,tfs[i],cond,glob,local);clean=x.float()-float(sigmas[i])*v.float()
  if i<7:x=((1-float(sigmas[i+1]))*clean+float(sigmas[i+1])*tensor(rng.standard_normal((1,n,256)).astype(np.float16)).float()).cast(dtypes.float16).realize()
  else:x=clean.cast(dtypes.float16).realize()
  Device['AMD'].synchronize()
 x=(x*(1-tensor(mask))+tensor(prefix)*tensor(mask)).realize();gen=time.monotonic()-start
 t=time.monotonic();wave=decoder(x);Device['AMD'].synchronize();decode=time.monotonic()-t
 audio=wave.float().numpy()[0].T
 assert np.isfinite(audio).all() and np.sqrt((audio**2).mean())>1e-5
 tag=str(req['id']);wav=OUT/f'job_{tag}.wav';lat=OUT/f'job_{tag}.npy'
 gain=min(1.,.98/max(float(np.abs(audio).max()),1e-8));sf.write(wav,audio*gain,44100);np.save(lat,x.numpy())
 return {'id':req['id'],'run_id':req.get('run_id'),'wav':str(wav),'latents':str(lat),'retained_seconds':context*4096/44100,'window_frames':n,'anchor_frames':anchor_frames,'anchor_end':req.get('anchor_end'),'anchor_latents':req.get('anchor_latents'),'new_seconds':(n-context-anchor_frames)*4096/44100,'playable_new_seconds':(n-context)*4096/44100,'host_peak_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'tracked_gpu_mib':GlobalCounters.mem_used/2**20,'identity':identity,'seconds_total':requested_seconds,'source_end':end,'generation_seconds':gen,'decode_seconds':decode,'seconds':time.monotonic()-start,'cutoff_ns':req.get('cutoff_ns'),'seed':seed,'gain':gain,'conditioning':style,'conditioning_mix':req.get('conditioning_mix'),'trajectory':req.get('trajectory'),'nav_revision':req.get('nav_revision',0)}
# Eight denoising calls capture DiT within the first inference.
# Decoder needs a second call for TinyJit capture, not another complete denoising run.
for i in [-1]:
 cfg=json.loads((ROOT/'runtime.json').read_text()) if (ROOT/'runtime.json').exists() else {}
 identity=cfg.get('identity','legacy');musical=cfg.get('musical',False)
 rolling=cfg.get('rolling',False)
 r=generate({'id':i,'identity':identity,'seconds_total':120 if musical else 30,'source_end':INITIAL_END if rolling else (301 if musical else 323),'latents':str(ROOT/f'assets/source_{identity}_latents.npy' if identity!='legacy' else ROOT/'assets/source_latents.npy'),**(anchor_options(ROOT,identity) if rolling else {})});print('WARMUP',json.dumps(r),flush=True)
startup['first_generation']=r
t=time.monotonic();decoder(tensor(np.load(r['latents'])));Device['AMD'].synchronize();startup['decoder_capture_seconds']=time.monotonic()-t
startup['ready_seconds']=time.monotonic()-BOOT
(OUT/'startup.json').write_text(json.dumps(startup,indent=2));print('STARTUP',json.dumps(startup),flush=True)
(OUT/'warm_metadata.json').write_text(json.dumps(r))
(OUT/'worker_ready').write_text('ready');print('READY',flush=True)
while True:
 reqpath=OUT/'request.json'
 if not reqpath.exists():time.sleep(.05);continue
 req=json.loads(reqpath.read_text());reqpath.unlink();(OUT/'busy').write_text(str(req['id']))
 try:r=generate(req)
 except Exception as e:
  r={'id':req['id'],'run_id':req.get('run_id'),'error':type(e).__name__+': '+str(e)};traceback.print_exc()
 p=OUT/f'result_{req["id"]}.tmp';p.write_text(json.dumps(r));p.replace(OUT/f'result_{req["id"]}.json');print('RESULT',json.dumps(r),flush=True)
 (OUT/'busy').unlink(missing_ok=True)
 if 'error' in r:break
