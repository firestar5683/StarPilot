"""Actual trained SA3 on Chestnut. CPU text, GPU DiT + SAME-S, CPU file output."""
import argparse,gc,json,os,threading,time
from pathlib import Path
import numpy as np,psutil
start=time.monotonic();peak_rss=peak_buffers=0;proc=psutil.Process()
def monitor():
 global peak_rss,peak_buffers
 while True:
  peak_rss=max(peak_rss,proc.memory_info().rss)
  if 'GlobalCounters' in globals():peak_buffers=max(peak_buffers,GlobalCounters.mem_used)
  time.sleep(.02)
threading.Thread(target=monitor,daemon=True).start()
def log(*args):print(round(time.monotonic()-start,3),*args,flush=True)
p=argparse.ArgumentParser();p.add_argument('--durations',default='30,12');p.add_argument('--repeats',type=int,default=3)
p.add_argument('--prompt',default='Instrumental cinematic electronic music, warm synthesizer chords, melodic strings, steady drums, no vocals')
p.add_argument('--stable-inputs',action='store_true');p.add_argument('--prefix-latents',default='');p.add_argument('--keep-seconds',type=float,default=8);p.add_argument('--tag',default='trained');p.add_argument('--conditioning',default='');a=p.parse_args()
ROOT=Path('/data/sa3-feasibility');OUT=ROOT/'trained_results';OUT.mkdir(exist_ok=True)
import soundfile as sf
from tinygrad import Device,Tensor,dtypes
from tinygrad.helpers import GlobalCounters
from native_sa3 import DiT,Decoder,tensor,fourier
text_time=0
if a.conditioning:
 enc=np.load(a.conditioning)
else:
 import torch
 from transformers import AutoTokenizer,AutoConfig,T5GemmaEncoderModel
 torch.set_num_threads(4)
 path=str(ROOT/'t5gemma-b-b-ul2');t0=time.monotonic()
 tok=AutoTokenizer.from_pretrained(path,local_files_only=True,use_fast=False)
 cfg=AutoConfig.from_pretrained(path,local_files_only=True);cfg.is_encoder_decoder=False
 text_model=T5GemmaEncoderModel.from_pretrained(path,config=cfg,local_files_only=True,torch_dtype=torch.float32,low_cpu_mem_usage=True).eval()
 log('TEXT_LOADED',time.monotonic()-t0)
 with torch.no_grad():
  t0=time.monotonic();inputs=tok([a.prompt],padding='max_length',max_length=256,truncation=True,return_tensors='pt')
  enc=text_model(**inputs).last_hidden_state.numpy()
  mask=inputs['attention_mask'].numpy()[...,None]
  padding=np.load(ROOT/'native/conditioner.conditioners.prompt.padding_embedding.npy').astype(np.float32)
  enc=enc*mask+padding*(1-mask);text_time=time.monotonic()-t0
 np.save(OUT/'conditioning.npy',enc.astype(np.float16));log('TEXT_ENCODED',text_time)
 del text_model,tok,cfg,inputs;gc.collect()
log('BEFORE_GPU_LOAD')
t0=time.monotonic();dit=DiT(ROOT/'native',persistent=a.stable_inputs);decoder=Decoder(ROOT/'native');load_gpu=time.monotonic()-t0
log('GPU_LOADED',load_gpu,type(Device['AMD'].iface).__name__)
results={'model':'stabilityai/stable-audio-3-small-music','revision':'0fef1392cd842149a2b6d445e181c97608faac06','prompt':a.prompt,
 'hardware':{'backend':type(Device['AMD'].iface).__name__,'arch':Device['AMD'].arch},'text_encoding_seconds':text_time,
 'cached_text_input':bool(a.conditioning),'stable_input_buffers':a.stable_inputs,'gpu_load_seconds':load_gpu,'cpu_affinity':list(os.sched_getaffinity(0)),'runs':[]}
for duration in map(float,a.durations.split(',')):
 n=int(np.ceil(duration*44100/4096/2)*2)
 number=fourier([duration/384]).astype(np.float32)
 w=np.load(ROOT/'native/conditioner.conditioners.seconds_total.embedder.embedding.1.weight.npy').astype(np.float32)
 b=np.load(ROOT/'native/conditioner.conditioners.seconds_total.embedder.embedding.1.bias.npy').astype(np.float32)
 g=(number@w.T+b).astype(np.float16)
 prefix=None;keep_frames=0
 if a.prefix_latents:
  source=np.load(a.prefix_latents);keep_frames=min(round(a.keep_seconds*44100/4096),source.shape[1],n-2)
  prefix=np.zeros((1,n,256),dtype=np.float16);prefix[:,:keep_frames]=source[:,:keep_frames]
 cond=tensor(np.concatenate([enc.astype(np.float16),g[:,None,:]],axis=1));glob=tensor(g);local=tensor(np.zeros((1,n,257),dtype=np.float16))
 if prefix is not None:
  mask_np=np.zeros((1,n,1),dtype=np.float16);mask_np[:,:keep_frames]=1
  local=tensor(np.concatenate([mask_np,prefix],axis=-1));known=tensor(prefix);keep=tensor(mask_np)
 sigmas=np.linspace(1,0,9,dtype=np.float32);sigmas=1/(1+np.exp(2-sigmas*8.2));sigmas[0]=1;sigmas[-1]=0
 # CPU Fourier features computed with FP32 before transferring the small timestep inputs.
 tfs=[tensor(fourier([t])) for t in sigmas[:-1]]
 for repeat in range(a.repeats):
  seed=991+repeat;rng=np.random.default_rng(seed);runstart=time.monotonic()
  x=tensor(rng.standard_normal((1,n,256)).astype(np.float16));steps=[];dispatch=[]
  for i in range(8):
   t0=time.monotonic();v=dit(x,tfs[i],cond,glob,local);dispatch.append(time.monotonic()-t0)
   if repeat==0 and i==0:
    np.savez(OUT/f'first_step_{int(duration)}.npz',x=x.numpy(),tf=fourier([sigmas[i]]),cond=cond.numpy(),g=g,v=v.numpy())
   clean=x.float()-float(sigmas[i])*v.float()
   if i<7:
    noise=tensor(rng.standard_normal((1,n,256)).astype(np.float16))
    x=((1-float(sigmas[i+1]))*clean+float(sigmas[i+1])*noise.float()).cast(dtypes.float16).realize()
   else:x=clean.cast(dtypes.float16).realize()
   Device['AMD'].synchronize();steps.append(time.monotonic()-t0);log('STEP',duration,repeat,i,steps[-1])
  if prefix is not None:x=(x*(1-keep)+known*keep).realize()
  gen=time.monotonic()-runstart
  t0=time.monotonic();audio_tensor=decoder(x);Device['AMD'].synchronize();decode_gpu=time.monotonic()-t0
  t0=time.monotonic();audio=audio_tensor.float().numpy()[0,:,:round(duration*44100)].T;transfer=time.monotonic()-t0
  assert np.isfinite(audio).all()
  if repeat==0:
   np.savez(OUT/f'decoder_probe_{int(duration)}.npz',latents=x.numpy()[:,:8],audio=audio[:4*4096])
  peak=float(np.abs(audio).max());rms=float(np.sqrt(np.mean(audio**2)))
  assert rms>1e-5,(peak,rms)
  # Preserve raw model scale unless clipping would occur; report any output gain.
  gain=min(1.,.98/max(peak,1e-9));name=f'{a.tag}_{int(duration)}s_r{repeat}'
  sf.write(OUT/(name+'.wav'),audio*gain,44100,subtype='PCM_16')
  np.save(OUT/(name+'_latents.npy'),x.numpy())
  total=time.monotonic()-runstart
  row={'duration_seconds':len(audio)/44100,'retained_seconds':keep_frames*4096/44100,'new_seconds':len(audio)/44100-keep_frames*4096/44100,'latent_frames':n,'seed':seed,'repeat':repeat,'generation_seconds':gen,'step_seconds':steps,'dit_call_seconds':dispatch,
   'decode_gpu_seconds':decode_gpu,'waveform_transfer_seconds':transfer,'total_to_wav_seconds':total,
   'rtf':total/(len(audio)/44100),'rtf_per_new_audio':total/(len(audio)/44100-keep_frames*4096/44100),'fresh_prompt_rtf':(total+text_time)/(len(audio)/44100),'process_elapsed_seconds':time.monotonic()-start,
   'raw_audio_rms':rms,'raw_audio_peak':peak,'output_gain':gain,'peak_host_rss_bytes':peak_rss,'peak_tracked_buffer_bytes':peak_buffers,'output':name+'.wav'}
  results['runs'].append(row);(OUT/(a.tag+'_result.json')).write_text(json.dumps(results,indent=2));log('RESULT',json.dumps(row))
log('COMPLETE')
