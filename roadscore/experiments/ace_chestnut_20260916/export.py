"""Export only the DiT and validate a trained block without loading the whole stack."""
from pathlib import Path
import sys,json,time
import numpy as np,torch
from safetensors import safe_open
P=Path(__file__).resolve().parent;M=P.parent/'composition_20260916/models/ace/checkpoints/acestep-v15-turbo';O=P/'weights';O.mkdir(exist_ok=True)
sys.path.insert(0,str(M))
from configuration_acestep_v15 import AceStepConfig
from modeling_acestep_v15_turbo import AceStepDiTLayer
config=AceStepConfig.from_pretrained(M);config._attn_implementation='sdpa'
counts={};block={}
with safe_open(str(M/'model.safetensors'),framework='pt',device='cpu') as f:
 for k in f.keys():
  shape=f.get_slice(k).get_shape();num=int(np.prod(shape));prefix=k.split('.')[0];counts[prefix]=counts.get(prefix,0)+num
  if not k.startswith('decoder.'):continue
  w=f.get_tensor(k).to(torch.float16);name=k[len('decoder.'):];np.save(O/(name+'.npy'),w.numpy())
  if k.startswith('decoder.layers.0.'):block[k[len('decoder.layers.0.'):]]=w
(P/'tensor_census.json').write_text(json.dumps({'parameters_by_component':counts,'fp16_bytes_by_component':{k:v*2 for k,v in counts.items()}},indent=2));print(counts,flush=True)
torch.manual_seed(421);layer=AceStepDiTLayer(config,0).half().eval();layer.load_state_dict(block)
N=160;E=48;x=torch.randn(1,N,2048).half()*.3;cond=torch.randn(1,E,2048).half()*.2;temb=torch.randn(1,6,2048).half()*.1
freq=torch.arange(N)[:,None].float()*(1/(1000000**(torch.arange(0,128,2).float()/128)))[None,:];freq=torch.cat((freq,freq),-1)[None];cs=(freq.cos().half(),freq.sin().half());idx=torch.arange(N);mask=torch.where((idx[:,None]-idx[None,:]).abs()<=128,0.,-float('inf')).half()[None,None]
with torch.no_grad():y=layer(x,cs,temb,attention_mask=mask,encoder_hidden_states=cond)[0]
for k,v in dict(x=x,cond=cond,temb=temb,cos=cs[0],sin=cs[1],mask=mask,expected=y).items():np.save(P/(k+'.npy'),v.float().numpy() if k=='expected' else v.numpy())
print('REFERENCE_READY',y.shape,flush=True)
