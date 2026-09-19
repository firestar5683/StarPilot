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
status,ok=lm.initialize(str(BASE/'models/ace/checkpoints'),'acestep-5Hz-lm-1.7B',backend='mlx',device='mps');assert ok,status
calls=[]
def pre(module,args,kwargs):
 i=len(calls);t=time.monotonic();calls.append({'start':t,'timestep':kwargs['timestep'].float().cpu().tolist()})
 if i==0:
  for key,value in kwargs.items():
   if isinstance(value,torch.Tensor):np.save(O/(key+'.npy'),value.detach().float().cpu().numpy())
  (O/'inputs.json').write_text(json.dumps({k:{'shape':list(v.shape),'dtype':str(v.dtype)} for k,v in kwargs.items() if isinstance(v,torch.Tensor)},indent=2))
def post(module,args,kwargs,output):
 calls[-1]['seconds']=time.monotonic()-calls[-1]['start']
 np.save(O/('velocity_'+str(len(calls)-1)+'.npy'),output[0].detach().float().cpu().numpy())
h.model.decoder.register_forward_pre_hook(pre,with_kwargs=True);h.model.decoder.register_forward_hook(post,with_kwargs=True)
params=GenerationParams(caption=TARGET+ROLES['verse_to_chorus'],lyrics='[Instrumental]\n[Verse]\n[Pre-Chorus]\n[Chorus]',instrumental=True,bpm=128,keyscale='D minor',timesignature='4',duration=15,inference_steps=8,seed=12601,thinking=True,use_cot_caption=False,use_cot_metas=False,use_cot_language=False,reference_audio=str(R/'results/composition_20260916/ace/structured90.wav'))
t=time.monotonic();result=generate_music(h,lm,params,GenerationConfig(batch_size=1,allow_lm_batch=False,use_random_seed=False,seeds=[12601],audio_format='wav'),save_dir=str(O))
report={'success':result.success,'error':result.error,'wall_seconds':time.monotonic()-t,'prepare_seconds':t-start,'dit_calls':calls,'audios':result.audios,'extra':result.extra_outputs,'peak_host_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20}
(O/'result.json').write_text(json.dumps(report,indent=2,default=str));print('RESULT',report['success'],report['error'],flush=True)
