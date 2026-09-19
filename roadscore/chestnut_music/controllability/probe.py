"""Bounded continuation probe. Experimental only; CPU text/codec, Chestnut decoder."""
import gc, json, os, threading, time
from pathlib import Path
import psutil
import numpy as np
import torch
import soundfile as sf
from transformers import AutoProcessor, MusicgenForConditionalGeneration
from transformers.utils import logging
from tinygrad import Tensor, Device
from tinygrad.helpers import GlobalCounters
from native_decoder import NativeDecoder

ROOT = Path('/data/roadscore-feasibility')
OUT = ROOT / 'controllability'
OUT.mkdir(exist_ok=True)
start = time.monotonic()
peak_rss = peak_buffers = 0
proc = psutil.Process()
def monitor():
  global peak_rss, peak_buffers
  while True:
    peak_rss = max(peak_rss, proc.memory_info().rss)
    peak_buffers = max(peak_buffers, GlobalCounters.mem_used)
    time.sleep(.05)
threading.Thread(target=monitor, daemon=True).start()
def log(*args): print(round(time.monotonic()-start, 3), *args, flush=True)
logging.set_verbosity_error()
torch.set_num_threads(4)
common = 'Instrumental cinematic downtempo electronic score, repeating warm synthesizer motif, soft strings, A minor, 100 BPM, no vocals. '
prompts = {
  'base': common + 'Steady restrained drums, calm flowing mood, medium intensity.',
  'neutral': common + 'Steady restrained drums, calm flowing mood, medium intensity.',
  'low': common + 'Very gentle sparse arrangement, soft sustained pads, minimal percussion, quiet relaxed mood.',
  'high': common + 'Intense driving drums, urgent pulsing synthesizers, rising strings, dramatic tension and energy.',
  'release': common + 'Drums recede, gentle sustained strings and warm pads, calm peaceful resolution, tension dissolves.',
}
path = str(ROOT/'musicgen-small-fp16')
processor = AutoProcessor.from_pretrained(path, local_files_only=True)
model = MusicgenForConditionalGeneration.from_pretrained(path, local_files_only=True, torch_dtype=torch.float16,
  low_cpu_mem_usage=True, attn_implementation='eager').eval()
model.text_encoder.float(); model.enc_to_dec_proj.float(); model.audio_encoder.float()
log('LOADED')
conditions = {}; references = {}; conditioning_seconds = {}
with torch.no_grad():
  for name, prompt in prompts.items():
    t0 = time.monotonic()
    inputs = processor(text=[prompt], padding='max_length', max_length=64, truncation=True, return_tensors='pt')
    enc = model.text_encoder(**inputs).last_hidden_state
    enc = model.enc_to_dec_proj(torch.cat([enc, torch.zeros_like(enc)], 0))
    mask = torch.cat([inputs['attention_mask'], torch.zeros_like(inputs['attention_mask'])], 0)
    enc = (enc * mask[..., None]).half()
    conditions[name] = (enc, mask)
    conditioning_seconds[name] = time.monotonic()-t0
    references[name] = model.decoder(input_ids=torch.full((8,1),2048,dtype=torch.long),
      encoder_hidden_states=enc, encoder_attention_mask=mask, use_cache=True).logits[:,-1].float().numpy()
    log('CONDITION', name, conditioning_seconds[name])
  # Retain official delay-mask builder without retaining the full CPU transformer.
  build_mask = model.decoder.build_delay_pattern_mask
  patterns = {}
  # Empty base and dummy prefix establish mask layout before deleting CPU weights.
  for n, prefix_n in [(600, 0), (800, 400)]:
    inp = torch.cat([torch.full((4,1),2048,dtype=torch.long), torch.zeros((4,prefix_n),dtype=torch.long)], 1)
    _, patterns[(n,prefix_n)] = build_mask(inp,2048,n+4)
  native = NativeDecoder(model.decoder, *conditions['base'], 804)
  del build_mask, model.decoder, model.text_encoder, model.enc_to_dec_proj
  gc.collect()
  log('GPU_LOADED', type(Device['AMD'].iface).__name__)
  results = {'prompts':prompts, 'conditioning_seconds':conditioning_seconds, 'runs':[],
    'hardware':{'backend':type(Device['AMD'].iface).__name__, 'arch':Device['AMD'].arch},
    'cpu_affinity':list(os.sched_getaffinity(0)), 'torch_threads':torch.get_num_threads()}
  def set_condition(name):
    enc, mask = conditions[name]
    native.enc.assign(Tensor(enc.numpy(),device='AMD')).realize()
    native.mask.assign(Tensor(((1-mask.numpy())*-65504.).astype(np.float16),device='AMD').reshape(2,1,1,-1)).realize()
    # Assign existing buffers: TinyJit must read changed content, not stale captured objects.
    for i, (dstk,dstv) in enumerate(native.cross):
      p = f'model.decoder.layers.{i}.encoder_attn.'
      k = native.linear(native.enc,p+'k_proj').reshape(2,-1,16,64).transpose(1,2)
      v = native.linear(native.enc,p+'v_proj').reshape(2,-1,16,64).transpose(1,2)
      dstk.assign(k).realize(); dstv.assign(v).realize()
  all_codes = {}
  for name in ['base','neutral','low','high','release']:
    run_start = time.monotonic()
    set_condition(name)
    condition_update_seconds = time.monotonic()-run_start
    prefix = None if name=='base' else all_codes['high' if name=='release' else 'base'][...,-400:]
    prefix_n = 0 if prefix is None else prefix.shape[-1]
    n = 600 if name=='base' else 800
    delay = patterns[(n,prefix_n)].clone()
    if prefix is not None:
      for c in range(4): delay[c,c+1:c+1+prefix_n] = prefix[0,0,c]
    ids = torch.full((4,1),2048,dtype=torch.long)
    # Same seed for neutral/low/high: paired branch experiment, not a diversity trick.
    torch.manual_seed(321)
    steps=[]; k0=GlobalCounters.kernel_count; g0=time.monotonic(); first_new=None
    for t in range(1,n+4):
      t0=time.monotonic()
      raw=native(ids[:,-1:].repeat(2,1),t-1)
      if t==1:
        ref=references[name]
        cosine=float(np.dot(raw.ravel(),ref.ravel())/(np.linalg.norm(raw)*np.linalg.norm(ref)))
        assert np.isfinite(raw).all() and cosine>.999, (name,cosine)
        log('REFERENCE',name,cosine)
      if (delay[:,t]==-1).any():
        if first_new is None: first_new=time.monotonic()-g0
        logits=torch.from_numpy(raw); logits=logits[4:]+3*(logits[:4]-logits[4:])
        vals,idx=logits.topk(250,dim=-1)
        nxt=idx.gather(-1,torch.multinomial(vals.softmax(-1),1)).squeeze(-1)
        nxt=torch.where(delay[:,t]!=-1,delay[:,t],nxt)
      else: nxt=delay[:,t]
      ids=torch.cat([ids,nxt[:,None]],1)
      steps.append(time.monotonic()-t0)
      if t%100==0: log('STEP',name,t,'elapsed',time.monotonic()-g0)
    generation_seconds=time.monotonic()-g0
    codes=ids[ids!=2048].reshape(1,1,4,-1)
    assert codes.shape[-1]==n
    if prefix is not None: assert torch.equal(codes[...,:prefix_n],prefix)
    all_codes[name]=codes
    torch.save(codes,OUT/f'{name}_codes.pt')
    t0=time.monotonic()
    audio=model.audio_encoder.decode(codes,audio_scales=[None]).audio_values[0,0].float().numpy()
    decode_seconds=time.monotonic()-t0
    assert np.isfinite(audio).all()
    sf.write(OUT/f'{name}_full.wav',audio,32000,subtype='PCM_16')
    sf.write(OUT/f'{name}_new.wav',audio[prefix_n*640:],32000,subtype='PCM_16')
    run={'name':name,'prefix_source':None if prefix is None else ('high' if name=='release' else 'base'),
      'prefix_seconds':prefix_n/50,'new_seconds':(n-prefix_n)/50,'total_audio_seconds':len(audio)/32000,
      'condition_update_seconds':condition_update_seconds,'generation_seconds':generation_seconds,
      'decode_seconds':decode_seconds,'total_run_seconds':time.monotonic()-run_start,
      'prefix_plus_first_new_logits_seconds':first_new,'steady_step_seconds':float(np.mean(steps[4:])),
      'rtf_per_new_audio':(generation_seconds+decode_seconds)/((n-prefix_n)/50),
      'reference_cosine':cosine,'prefix_tokens_exact':prefix is not None,
      'peak_host_rss_bytes':peak_rss,'peak_tracked_buffer_bytes':peak_buffers,
      'gpu_dispatch_counter_delta':GlobalCounters.kernel_count-k0,
      'rms':float(np.sqrt(np.mean(audio**2))),'peak':float(np.max(np.abs(audio))),
      'clip_fraction':float(np.mean(np.abs(audio)>=1))}
    results['runs'].append(run);results['elapsed_seconds']=time.monotonic()-start
    (OUT/'result.json').write_text(json.dumps(results,indent=2))
    log('RESULT',json.dumps(run))
log('COMPLETE')
