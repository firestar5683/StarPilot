"""Independent released PyTorch model references versus saved native GPU outputs."""
import gc,json,sys,types,time
from pathlib import Path
import numpy as np,torch
ROOT=Path('/data/sa3-feasibility');OUT=ROOT/'trained_results';W=ROOT/'native'
torch.set_num_threads(4)
# Import the released model code without importing its unrelated application/deployment dependencies.
for name,rel in [('stable_audio_3','stable_audio_3'),('stable_audio_3.models','stable_audio_3/models')]:
 mod=types.ModuleType(name);mod.__path__=[str(ROOT/'reference_source'/rel)];sys.modules[name]=mod
from stable_audio_3.models.dit import DiffusionTransformer
from same_s_decoder_torch import SAMESDecoder

def load(k):return torch.from_numpy(np.load(W/(k+'.npy'))).float()
def compare(a,b):
 a=a.astype(np.float64).ravel();b=b.astype(np.float64).ravel()
 return {'cosine':float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))), 'mae':float(np.mean(np.abs(a-b))),
  'relative_rmse':float(np.linalg.norm(a-b)/np.linalg.norm(b)),'max_error':float(np.max(np.abs(a-b)))}
results={};t0=time.monotonic()
cfg=json.loads((ROOT/'model_config.json').read_text())['model']['diffusion']['config']
with torch.device('meta'):model=DiffusionTransformer(**cfg,diffusion_objective='rf_denoiser')
# Materialize one tensor at a time, avoiding an extra full state-dict copy.
for name,param in list(model.named_parameters())+list(model.named_buffers()):
 path=W/('model.model.'+name+'.npy')
 if not path.exists():raise RuntimeError('Missing reference tensor '+name)
 parts=name.split('.');parent=model
 for part in parts[:-1]:parent=getattr(parent,part)
 value=load('model.model.'+name)
 if isinstance(param,torch.nn.Parameter):value=torch.nn.Parameter(value,requires_grad=False)
 setattr(parent,parts[-1],value)
model.eval();print('REFERENCE_DIT_LOADED',time.monotonic()-t0,flush=True)
with torch.no_grad():
 for seconds in [30,12]:
  file=OUT/f'first_step_{seconds}.npz'
  if not file.exists():continue
  d=np.load(file);x=torch.from_numpy(d['x']).float().transpose(1,2)
  ref=model(x,torch.ones(1),cross_attn_cond=torch.from_numpy(d['cond']).float(),global_embed=torch.from_numpy(d['g']).float(),local_add_cond=torch.zeros(1,257,x.shape[-1])).transpose(1,2).numpy()
  c=compare(d['v'],ref);results[f'dit_{seconds}']=c;print('DIT_COMPARE',seconds,c,flush=True)
  assert c['cosine']>.995 and c['relative_rmse']<.1,c
 del model;gc.collect()
 model=SAMESDecoder(output_audio=True).eval()
 sd={}
 sd['project_in.weight']=load('pretransform.model.decoder.layers.1.weight');sd['project_in.bias']=load('pretransform.model.decoder.layers.1.bias')
 sd['new_tokens']=load('pretransform.model.decoder.layers.3.new_tokens')
 sd['mapping.weight']=load('pretransform.model.decoder.layers.3.mapping.weight');sd['mapping.bias']=load('pretransform.model.decoder.layers.3.mapping.bias')
 sd['running_std']=load('pretransform.model.bottleneck.running_std')
 for name in model.state_dict():
  if not name.startswith('blocks.'):continue
  key=name.replace('blocks.','pretransform.model.decoder.layers.3.transformers.').replace('.attn.','.self_attn.').replace('.ff.glu_proj.','.ff.ff.0.proj.').replace('.ff.proj_out.','.ff.ff.2.')
  sd[name]=load(key)
 missing,unexpected=model.load_state_dict(sd,strict=False)
 assert set(missing)<= {'rope_cos','rope_sin'} and not unexpected,(missing,unexpected)
 del sd;gc.collect()
 for seconds in [30,12]:
  file=OUT/f'decoder_probe_{seconds}.npz'
  if not file.exists():continue
  d=np.load(file);ref=model(torch.from_numpy(d['latents']).float().transpose(1,2))[0,:,:4*4096].transpose(0,1).numpy()
  c=compare(d['audio'],ref);results[f'decoder_{seconds}']=c;print('DECODER_COMPARE',seconds,c,flush=True)
  assert c['cosine']>.99 and c['relative_rmse']<.15,c
results['elapsed_seconds']=time.monotonic()-t0
(OUT/'validation.json').write_text(json.dumps(results,indent=2))
print('TRAINED_REFERENCE_CHECKS_PASSED',flush=True)
