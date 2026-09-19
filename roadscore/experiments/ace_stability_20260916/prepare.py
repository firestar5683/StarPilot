"""Official Mac generation with exact DiT-boundary, noise and step capture."""
import os,sys,json,time,shutil,hashlib,random
from pathlib import Path
from bundle import R,OUT
B=R/'experiments/composition_20260916'
os.environ.update(HF_HOME=str(B/'cache/hf'),HF_HUB_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false',PYTORCH_ENABLE_MPS_FALLBACK='1')
import numpy as np,torch,mlx.core as mx
from acestep.handler import AceStepHandler
from acestep.llm_inference import LLMHandler
from acestep.inference import GenerationParams,GenerationConfig,generate_music
h=AceStepHandler();lm=LLMHandler();status,ok=h.initialize_service(str(B/'models/ace'),config_path='acestep-v15-turbo',device='mps',use_mlx_dit=True,offload_to_cpu=True,offload_dit_to_cpu=False);assert ok,status
status,ok=lm.initialize(str(B/'models/ace/checkpoints'),'acestep-5Hz-lm-1.7B',backend='mlx',device='mps');assert ok,status
original=h._mlx_run_diffusion;current={}
class Trace:
 def __init__(self,inner):self.inner=inner;self.index=0
 def __getattr__(self,name):return getattr(self.inner,name)
 def __call__(self,*args,**kw):
  i=self.index;self.index+=1;x=kw.get('hidden_states',args[0] if args else None);np.save(current['out']/f'input_{i}.npy',np.array(x));ret=self.inner(*args,**kw);np.save(current['out']/f'velocity_{i}.npy',np.array(ret[0]));return ret
h.mlx_decoder=Trace(h.mlx_decoder)
def capture(*args,**kw):
 p=current['case'];o=current['out'];h.mlx_decoder.index=0
 for key in ['encoder_hidden_states','encoder_attention_mask','context_latents','src_latents','repaint_mask','clean_src_latents']:
  if isinstance(kw.get(key),torch.Tensor):np.save(p/({'repaint_mask':'mask','clean_src_latents':'source'}.get(key,key)+'.npy'),kw[key].detach().float().cpu().numpy())
 shape=tuple(kw['src_latents'].shape);seed=current['seed'];np.save(p/'noise.npy',np.array(mx.random.normal(shape,key=mx.random.key(seed))))
 scalar={k:v for k,v in kw.items() if isinstance(v,(str,int,float,bool)) or v is None};current['meta']['sampler']=scalar;current['meta']['tensor_shape']=shape;(p/'case.json').write_text(json.dumps(current['meta'],indent=2));ret=original(*args,**kw);np.save(o/'latents.npy',ret['target_latents'].detach().float().cpu().numpy());return ret
h._mlx_run_diffusion=capture
common='Instrumental polished K-pop and modern electronic game score. No vocals, no singing, no speech. Continuous tight drum groove, punchy bass, memorable recurring hook, polished dynamic arrangement. '
identities=[('prism',128,'D minor','Crystal pluck arpeggios and a playful four-note rising synth motif; crisp electronic snare, rubbery syncopated bass and bright glass leads.'),('aurora',116,'A minor','Warm analog synths, octave bass ostinato, shimmering bell answers and a lyrical three-note descending lead motif; syncopated dance-pop drums.'),('circuit',136,'E minor','Funky muted guitar chops, clavinet-like synth riffs, punchy electric bass and short brass-synth answers; energetic game-level groove.')]
def run(name,caption,lyrics,duration,seed,reference=None,thinking=True,dcw=False,**extra):
 p=OUT/'cases'/name;p.mkdir(parents=True,exist_ok=True);o=p/'official';o.mkdir(exist_ok=True)
 if (o/'report.json').exists():return
 random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);mx.random.seed(seed)
 current.update(case=p,out=o,seed=seed,meta={'name':name,'caption':caption,'lyrics':lyrics,'duration':duration,'seed':seed,'reference_audio':reference,'thinking':thinking,'noise_generator':'explicit official MLX tensor','sampler':{}})
 bpm=next((b for n,b,k,t in identities if name.startswith(n)),128);key=next((k for n,b,k,t in identities if name.startswith(n)),'D minor')
 params=GenerationParams(caption=caption,lyrics=lyrics,instrumental=True,bpm=bpm,keyscale=key,timesignature='4',duration=duration,inference_steps=8,seed=seed,thinking=thinking,dcw_enabled=dcw,use_cot_caption=False,use_cot_metas=False,use_cot_language=False,reference_audio=reference,**extra)
 st=time.monotonic();ret=generate_music(h,lm,params,GenerationConfig(batch_size=1,allow_lm_batch=False,use_random_seed=False,seeds=[seed],audio_format='wav'),save_dir=str(o/'raw'));assert ret.success,ret.error;shutil.copy(ret.audios[0]['path'],o/'audio.wav');(o/'report.json').write_text(json.dumps({'wall_seconds':time.monotonic()-st,'costs':ret.extra_outputs.get('time_costs',{}),'success':ret.success},indent=2));print('PREPARED',name,time.monotonic()-st,flush=True)
if __name__=='__main__':
 gold=json.loads((R/'results/composition_20260916/ace/verse_to_chorus/benchmark.json').read_text())
 run('gold_transition',gold['caption'],gold['lyrics'],40,12601,gold['reference_audio'],True,True)
 for identity,bpm,key,text in identities:
  for duration in [30,45,60]:run(f'{identity}_{duration}',common+f'{bpm} BPM, {key}. '+text,'[Instrumental]\n[Verse]\n[Build]\n[Chorus]',duration,44701+identities.index((identity,bpm,key,text))*100+duration)
