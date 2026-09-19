"""Decode identical native latents with official FP32 VAE. No playback."""
import sys,time,json
import numpy as np,torch,soundfile as sf
from diffusers import AutoencoderOobleck
from bundle import R,OUT
vae=AutoencoderOobleck.from_pretrained(R/'experiments/composition_20260916/models/ace/checkpoints/vae').float().to('mps').eval()
reports={}
for name in sys.argv[1:]:
 p=OUT/'cases'/name;z=np.load(p/'native_0/latents.npy').astype(np.float32);t=time.monotonic()
 with torch.no_grad():a=vae.decode(torch.tensor(z.transpose(0,2,1),device='mps')).sample[0].T.cpu().numpy()
 elapsed=time.monotonic()-t;o=p/'same_latent_vae';o.mkdir(exist_ok=True);sf.write(o/'mac.wav',a*.65,48000,subtype='FLOAT');b=sf.read(p/'native_0/audio.wav',always_2d=True,dtype='float32')[0]/.65;d=a-b
 def envelope(x):return np.sqrt(np.mean(x[:len(x)//480*480].reshape(-1,480,2)**2,axis=(1,2)))
 ea,eb=envelope(a),envelope(b);lag=int(np.argmax(np.correlate(ea[:2000]-ea[:2000].mean(),eb[:2000]-eb[:2000].mean(),'full'))-len(ea[:2000])+1)
 reports[name]={'seconds':elapsed,'same_latents':True,'relative_pcm_rmse':float(np.linalg.norm(d)/np.linalg.norm(a)),'peak_absolute_difference':float(abs(d).max()),'envelope_correlation_10ms':float(np.corrcoef(ea,eb)[0,1]),'envelope_lag_10ms_bins_first20s':lag,'finite':bool(np.isfinite(a).all()),'decode_comparison':'official FP32 full decode vs native FP16 bounded375-frame windows with250-frame cores'}
 (o/'report.json').write_text(json.dumps(reports[name],indent=2));print(name,reports[name],flush=True)
(OUT/'vae_comparisons.json').write_text(json.dumps(reports,indent=2))
