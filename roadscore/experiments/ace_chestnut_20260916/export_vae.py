from pathlib import Path
import json
import numpy as np,torch
from diffusers import AutoencoderOobleck
P=Path(__file__).resolve().parent;M=P.parent/'composition_20260916/models/ace/checkpoints/vae';O=P/'vae_weights';O.mkdir(exist_ok=True)
m=AutoencoderOobleck.from_pretrained(M).eval()
for module in m.decoder.modules():
 if hasattr(module,'weight_g'):torch.nn.utils.remove_weight_norm(module)
for k,v in m.decoder.state_dict().items():np.save(O/(k+'.npy'),v.detach().half().numpy())
torch.manual_seed(20);x=torch.randn(1,64,32)*.2
with torch.no_grad():y=m.decoder(x)
np.save(P/'vae_input.npy',x.numpy());np.save(P/'vae_expected.npy',y.numpy());print({'weights':sum(v.numel()*2 for v in m.decoder.parameters()),'input':list(x.shape),'output':list(y.shape)},flush=True)
