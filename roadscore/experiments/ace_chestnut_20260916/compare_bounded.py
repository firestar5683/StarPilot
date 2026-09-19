from pathlib import Path
import time,json
import torch,numpy as np,soundfile as sf
from diffusers import AutoencoderOobleck
P=Path(__file__).resolve().parent;O=P.parents[1]/'results/ace_chestnut_20260916/reference45'
m=AutoencoderOobleck.from_pretrained(P.parent/'composition_20260916/models/ace/checkpoints/vae').eval().to('mps');x=torch.from_numpy(np.load(O/'chestnut_latents.npy').astype(np.float32)).transpose(1,2).to('mps');t=time.monotonic()
with torch.no_grad():y=m.decode(x).sample
torch.mps.synchronize();elapsed=time.monotonic()-t
a=y[0].cpu().numpy().T;b=np.load(O/"bounded_pcm.npy");e=b-a
r={"official_decode_seconds":elapsed,"relative_rmse":float(np.linalg.norm(e)/np.linalg.norm(a)),"peak_relative_error":float(abs(e).max()/abs(a).max()),"cosine":float(np.vdot(a,b)/np.linalg.norm(a)/np.linalg.norm(b))}
(O/"bounded_decode_comparison.json").write_text(json.dumps(r,indent=2));sf.write(O/"official_decode.wav",a*min(1,.98/abs(a).max()),48000,subtype="PCM_24");print(r)
