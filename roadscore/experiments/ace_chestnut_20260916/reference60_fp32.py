from pathlib import Path
import sys,time,json
import numpy as np,torch
P=Path(__file__).resolve().parent;R=P.parents[1];O=R/'results/ace_chestnut_20260916/reference60';M=P.parent/'composition_20260916/models/ace/checkpoints/acestep-v15-turbo';sys.path.insert(0,str(M))
from configuration_acestep_v15 import AceStepConfig
from modeling_acestep_v15_turbo import AceStepDiTModel
c=AceStepConfig.from_pretrained(M);c._attn_implementation='sdpa'
with torch.device('meta'):m=AceStepDiTModel(c)
w={p.stem:torch.from_numpy(np.load(p)) for p in (P/'weights').glob('*.npy')};m.load_state_dict(w,assign=True);del w
from transformers.models.qwen3.modeling_qwen3 import Qwen3RotaryEmbedding
m.rotary_emb=Qwen3RotaryEmbedding(c);m=m.to(device='mps',dtype=torch.float32).eval()
a={k:torch.tensor(np.load(O/(k+'.npy')),device='mps',dtype=torch.float32) for k in ['hidden_states','timestep','timestep_r','attention_mask','encoder_hidden_states','encoder_attention_mask','context_latents']}
with torch.no_grad():
 t=time.monotonic();y=m(**a,use_cache=False)[0];torch.mps.synchronize();elapsed=time.monotonic()-t
 np.save(O/'velocity_fp32.npy',y.float().cpu().numpy());print({'seconds':elapsed,'shape':list(y.shape),'peak':y.abs().max().item()},flush=True)
