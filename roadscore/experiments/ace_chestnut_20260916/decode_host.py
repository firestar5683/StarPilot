from pathlib import Path
import time,json,resource
import numpy as np,torch,soundfile as sf
from diffusers import AutoencoderOobleck
P=Path(__file__).resolve().parent;R=P.parents[1];O=R/'results/ace_chestnut_20260916'
t=time.monotonic();m=AutoencoderOobleck.from_pretrained(P.parent/'composition_20260916/models/ace/checkpoints/vae').eval().to('mps');loaded=time.monotonic()-t
x=torch.from_numpy(np.load(O/'generated_latents.npy').astype(np.float32)).transpose(1,2).to('mps');t=time.monotonic()
with torch.no_grad():y=m.decode(x).sample
torch.mps.synchronize();elapsed=time.monotonic()-t
a=y[0].cpu().numpy().T;gain=min(1.0,.98/float(abs(a).max()));sf.write(O/"chestnut15_host_decode_normalized.wav",a*gain,48000,subtype="PCM_24")
r={"decoder":"official FP32 MPS; main generation Chestnut", "listening_gain":gain,"load_seconds":loaded,"decode_seconds":elapsed,"audio_seconds":len(a)/48000,"peak":float(abs(a).max()),"rms":float(np.sqrt(np.mean(a*a))),"finite":bool(np.isfinite(a).all()),"host_peak_mib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20}
(O/"host_decode.json").write_text(json.dumps(r,indent=2));print(r,flush=True)
