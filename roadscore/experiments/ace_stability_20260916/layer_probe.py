"""Same teacher input, layer-boundary capture; diagnostic, not a speed benchmark."""
import os,sys,json,fcntl
import numpy as np
from bundle import R,OLD,OUT
case=OUT/'cases/circuit_30';backend=os.environ.get('ACE_LAYER_BACKEND','reference')
out=case/('layers_'+backend);out.mkdir(exist_ok=True)
def load(name):return np.load(case/(name+'.npy')).astype(np.float16)
if backend=='native':
 os.environ.setdefault('TC_OPT','2');sys.path.insert(0,str(OLD))
 from native_ace import DiT,tensor,time_features
 from tinygrad import Device
 lock=open(R/'generated/gpu.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 class Capture(DiT):
  def block(self,*args,**kw):
   result=super().block(*args,**kw);i=kw.get('i',args[5] if len(args)>5 else 0)
   np.save(out/f'step_{step}_layer_{i}.npy',result.numpy());return result
 model=Capture(OLD/'weights');model.prepare_shape(750)
 cond=load('encoder_hidden_states');width=max(256,((cond.shape[1]+31)//32)*32)
 mask=np.full((1,1,1,width),-np.inf,np.float16);mask[...,:cond.shape[1]]=0
 cond=np.pad(cond,((0,0),(0,width-cond.shape[1]),(0,0)))
 for step in [0,7]:
  value=model.forward(tensor(load(f'official/input_{step}')),tensor(cond),tensor(load('context_latents')),tensor(time_features([1-step/8])),tensor(time_features([0])),tensor(mask))
  np.save(out/f'step_{step}_velocity.npy',value.numpy())
  Device['AMD'].synchronize();print('LAYER_CAPTURE_DONE',step,flush=True)
else:
 import torch
 M=R/'experiments/composition_20260916/models/ace/checkpoints/acestep-v15-turbo';sys.path.insert(0,str(M))
 from configuration_acestep_v15 import AceStepConfig
 from modeling_acestep_v15_turbo import AceStepDiTModel
 from transformers.models.qwen3.modeling_qwen3 import Qwen3RotaryEmbedding
 config=AceStepConfig.from_pretrained(M);config._attn_implementation='sdpa'
 with torch.device('meta'):model=AceStepDiTModel(config)
 model.load_state_dict({p.stem:torch.from_numpy(np.load(p)) for p in (OLD/'weights').glob('*.npy')},assign=True)
 model.rotary_emb=Qwen3RotaryEmbedding(config);model=model.float().to('mps').eval()
 def hook(i):
  def save(_,inputs,value):np.save(out/f'step_{step}_layer_{i}.npy',value[0].detach().cpu().numpy())
  return save
 for i,layer in enumerate(model.layers):layer.register_forward_hook(hook(i))
 def ten(name):return torch.tensor(load(name).astype(np.float32),device='mps')
 with torch.no_grad():
  for step in [0,7]:
   t=torch.tensor([1-step/8],device='mps');x=ten(f'official/input_{step}')
   value=model(hidden_states=x,timestep=t,timestep_r=t,attention_mask=torch.ones(x.shape[:2],device='mps'),encoder_hidden_states=ten('encoder_hidden_states'),encoder_attention_mask=ten('encoder_attention_mask'),context_latents=ten('context_latents'),use_cache=False)
   np.save(out/f'step_{step}_velocity.npy',value[0].cpu().numpy())
   print('LAYER_CAPTURE_DONE',step,flush=True)
