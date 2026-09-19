"""Isolated hardware gate; CPU text/codec, actual Chestnut music transformer."""
import time,json,threading,gc,argparse,os
from pathlib import Path
import psutil
p=argparse.ArgumentParser()
p.add_argument('--seconds',type=float,default=8);p.add_argument('--repeats',type=int,default=2)
p.add_argument('--prompt',default='Instrumental cinematic electronic music, warm synthesizer chords, melodic strings, steady drums, no vocals')
p.add_argument('--tag',default='bench8');a=p.parse_args()
root=Path('/data/roadscore-feasibility'); start=time.monotonic(); stages={};peak_rss=0;peak_buffers=0
proc=psutil.Process()
def monitor():
 global peak_rss,peak_buffers
 while True:
  peak_rss=max(peak_rss,proc.memory_info().rss)
  if 'GlobalCounters' in globals(): peak_buffers=max(peak_buffers,GlobalCounters.mem_used)
  time.sleep(.05)
threading.Thread(target=monitor,daemon=True).start()
def mark(s):
 stages[s]=time.monotonic()-start;print(s,round(stages[s],3),'RSS_MB',round(proc.memory_info().rss/1e6),flush=True)
import torch,numpy as np,soundfile as sf
from transformers import AutoProcessor,MusicgenForConditionalGeneration
from transformers.utils import logging
from tinygrad import Device
from tinygrad.helpers import GlobalCounters
from native_decoder import NativeDecoder
logging.set_verbosity_error();mark('imports');torch.set_num_threads(4)
path=str(root/'musicgen-small-fp16')
processor=AutoProcessor.from_pretrained(path,local_files_only=True)
model=MusicgenForConditionalGeneration.from_pretrained(path,local_files_only=True,torch_dtype=torch.float16,low_cpu_mem_usage=True,attn_implementation='eager').eval();mark('loaded')
model.text_encoder.float();model.enc_to_dec_proj.float();model.audio_encoder.float();gc.collect()
with torch.no_grad():
 t0=time.monotonic()
 inputs=processor(text=[a.prompt],padding=True,return_tensors='pt')
 enc=model.text_encoder(**inputs).last_hidden_state
 enc=torch.cat([enc,torch.zeros_like(enc)],0);enc=model.enc_to_dec_proj(enc)
 mask=torch.cat([inputs['attention_mask'],torch.zeros_like(inputs['attention_mask'])],0)
 enc=(enc*mask[...,None]).half();conditioning_seconds=time.monotonic()-t0;mark('conditioned')
 n=round(a.seconds*50);length=n+4
 initial,delay=model.decoder.build_delay_pattern_mask(torch.full((4,1),2048,dtype=torch.long),2048,length)
 reference=model.decoder(input_ids=initial.repeat(2,1),encoder_hidden_states=enc,encoder_attention_mask=mask,use_cache=True,return_dict=True).logits[:,-1].float().numpy();mark('reference')
 native=NativeDecoder(model.decoder,enc,mask,length)
 del model.decoder;gc.collect();mark('gpu_loaded')
 dev=Device['AMD'];hardware=dict(backend=type(dev.iface).__name__,arch=dev.arch,vram_bytes=dev.iface.dev_impl.vram_size)
 runs=[]
 for repeat in range(a.repeats):
  seed=123+repeat;torch.manual_seed(seed);ids=initial.clone();step_seconds=[];k0=GlobalCounters.kernel_count;g0=time.monotonic()
  for t in range(1,length):
   t0=time.monotonic();x=ids[:,-1:].repeat(2,1);raw=native(x,t-1)
   if t<=4: np.savez(root/f'{a.tag}_r{repeat}_step{t}.npz',inputs=x.numpy(),logits=raw)
   if t==1:
    compare=dict(mae=float(np.abs(raw-reference).mean()),max_error=float(np.abs(raw-reference).max()),cosine=float(np.dot(raw.ravel(),reference.ravel())/(np.linalg.norm(raw)*np.linalg.norm(reference))))
    print('REFERENCE_COMPARE',json.dumps(compare),flush=True)
    assert np.isfinite(raw).all() and compare['cosine']>.999,compare
   logits=torch.from_numpy(raw);logits=logits[4:]+3.0*(logits[:4]-logits[4:])
   vals,idx=logits.topk(250,dim=-1);nxt=idx.gather(-1,torch.multinomial(vals.softmax(-1),1)).squeeze(-1)
   nxt=torch.where(delay[:,t]!=-1,delay[:,t],nxt);ids=torch.cat([ids,nxt[:,None]],dim=1)
   step_seconds.append(time.monotonic()-t0)
   if t<=4 or t%50==0: print('RUN',repeat,'STEP',t,'elapsed',time.monotonic()-g0,'kernels',GlobalCounters.kernel_count-k0,flush=True)
  generation_seconds=time.monotonic()-g0;mark(f'generated_{repeat}')
  codes=ids[ids!=2048].reshape(1,1,4,-1);torch.save(codes,root/f'{a.tag}_r{repeat}_codes.pt')
  t0=time.monotonic();audio=model.audio_encoder.decode(codes,audio_scales=[None]).audio_values[0,0].float().numpy();decode_seconds=time.monotonic()-t0
  assert np.isfinite(audio).all()
  out=root/f'{a.tag}_r{repeat}.wav';sf.write(out,audio,32000,subtype='PCM_16');mark(f'decoded_{repeat}')
  run=dict(seed=seed,generation_seconds=generation_seconds,decode_seconds=decode_seconds,audio_seconds=len(audio)/32000,rtf=(generation_seconds+decode_seconds)/(len(audio)/32000),step_seconds=step_seconds,steady_seconds_per_step=float(np.mean(step_seconds[4:])),peak_host_rss_bytes=peak_rss,peak_tinygrad_buffer_bytes=peak_buffers,active_tinygrad_buffer_bytes=GlobalCounters.mem_used,gpu_kernel_counter_delta=GlobalCounters.kernel_count-k0,reference_compare=compare,audio_rms=float(np.sqrt(np.mean(audio**2))),audio_peak=float(np.max(np.abs(audio))),clip_fraction=float(np.mean(np.abs(audio)>=1)),output=str(out))
  runs.append(run)
  result=dict(model='facebook/musicgen-small',revision='4c8334b02c6ec4e8664a91979669a501ec497792',prompt=a.prompt,hardware=hardware,cpu_affinity=list(os.sched_getaffinity(0)),torch_threads=torch.get_num_threads(),conditioning_seconds=conditioning_seconds,stages=stages,runs=runs)
  (root/f'{a.tag}_result.json').write_text(json.dumps(result,indent=2));print('RESULT',json.dumps({k:v for k,v in run.items() if k!='step_seconds'}),flush=True)
