"""Run official local ACE and capture the exact boundary around its heavy DiT."""
import os,sys,time,json,resource
from pathlib import Path
import numpy as np,torch
P=Path(__file__).resolve().parent;R=P.parents[1];BASE=P.parent/'composition_20260916';O=R/'results/ace_chestnut_20260916/reference15';O.mkdir(parents=True,exist_ok=True)
os.environ.update(HF_HOME=str(BASE/'cache/hf'),HF_HUB_DISABLE_TELEMETRY='1',PYTORCH_ENABLE_MPS_FALLBACK='1',TOKENIZERS_PARALLELISM='false')
from acestep.handler import AceStepHandler
from acestep.llm_inference import LLMHandler
from acestep.inference import GenerationParams,GenerationConfig,generate_music
sys.path.insert(0,str(R/'prototype'));from composition_sa3 import BASE as TARGET,ROLES
h=AceStepHandler();lm=LLMHandler();start=time.monotonic()
status,ok=h.initialize_service(str(BASE/'models/ace'),config_path='acestep-v15-turbo',device='mps',use_mlx_dit=False,offload_to_cpu=True);assert ok,status
calls=[]
class BoundaryCaptured(Exception): pass
def pre(module,args,kwargs):
 i=len(calls);t=time.monotonic();calls.append({'start':t,'timestep':kwargs['timestep'].float().cpu().tolist()})
 if i==0:
  for key,value in kwargs.items():
   if isinstance(value,torch.Tensor):np.save(O/(key+'.npy'),value.detach().float().cpu().numpy())
  (O/'inputs.json').write_text(json.dumps({k:{'shape':list(v.shape),'dtype':str(v.dtype)} for k,v in kwargs.items() if isinstance(v,torch.Tensor)},indent=2))
  raise BoundaryCaptured('Prepared actual conditioning saved; skip host generation')
def post(module,args,kwargs,output):
 calls[-1]['seconds']=time.monotonic()-calls[-1]['start']
 np.save(O/('velocity_'+str(len(calls)-1)+'.npy'),output[0].detach().float().cpu().numpy())
h.model.decoder.register_forward_pre_hook(pre,with_kwargs=True);h.model.decoder.register_forward_hook(post,with_kwargs=True)

import soundfile as sf,functools
original_generate=h.model.generate_audio
@functools.wraps(original_generate)
def capture_sampler(*args,**kwargs):
 for key in ['clean_src_latents','repaint_mask']:
  if isinstance(kwargs.get(key),torch.Tensor):np.save(O/('sampler_'+key+'.npy'),kwargs[key].detach().float().cpu().numpy())
 (O/'sampler.json').write_text(json.dumps({k:v for k,v in kwargs.items() if isinstance(v,(str,int,float,bool)) or v is None},indent=2))
 return original_generate(*args,**kwargs)
h.model.generate_audio=capture_sampler
source,sr=sf.read(R/'results/composition_20260916/ace/verse_to_chorus.wav',always_2d=True,dtype='float32')
# Only already-generated context; no route or future musical continuation is read.
padded=np.zeros((40*sr,2),np.float32);padded[:12*sr]=source[-12*sr:]
source_path=R/'results/ace_chestnut_20260916/repaint_source.wav';sf.write(source_path,padded,sr,subtype='FLOAT')
for role in ['repaint_verse']:
 repaint=role.startswith('repaint');duration=40 if repaint else 30
 O=R/f'results/ace_chestnut_20260916/{role}';O.mkdir(parents=True,exist_ok=True);calls.clear()
 intent=role.removeprefix('repaint_')
 structure='[Instrumental]\n['+intent.title()+']'
 extra={'task_type':'repaint','src_audio':str(source_path),'repainting_start':12,'repainting_end':40,'chunk_mask_mode':'explicit','thinking':False} if repaint else {'thinking':True}
 params=GenerationParams(caption=TARGET+ROLES[intent],lyrics=structure,instrumental=True,bpm=128,keyscale='D minor',timesignature='4',duration=duration,inference_steps=8,seed=12607,dcw_enabled=False,use_cot_caption=False,use_cot_metas=False,use_cot_language=False,reference_audio=str(R/'results/composition_20260916/ace/structured90.wav'),**extra)
 t=time.monotonic()
 try: result=generate_music(h,lm,params,GenerationConfig(batch_size=1,allow_lm_batch=False,use_random_seed=False,seeds=[12607],audio_format='wav'),save_dir=str(O))
 except BoundaryCaptured: pass
 (O/'preparation.json').write_text(json.dumps({'seconds':time.monotonic()-t,'duration':duration,'role':role,'captured':(O/'context_latents.npy').exists(),'host':'Mac MPS + MLX planner','sampler_dcw':False},indent=2));print('PREPARED',role,time.monotonic()-t,flush=True)
