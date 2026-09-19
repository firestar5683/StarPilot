import json,numpy as np,soundfile as sf
from bundle import OUT
reports={}
for name in ['prism_30','prism_45','prism_60','gold_transition']:
 p=OUT/'cases'/name;a,sr=sf.read(p/'same_latent_vae/mac.wav',dtype='float32',always_2d=True);b,_=sf.read(p/'native_0/audio.wav',dtype='float32',always_2d=True);lags=[];relative=[]
 for i in range(0,min(len(a),len(b))-sr+1,sr):
  x=a[i:i+sr].mean(-1);y=b[i:i+sr].mean(-1);n=2**17;c=np.fft.irfft(np.fft.rfft(x,n)*np.conj(np.fft.rfft(y,n)),n)
  z=np.concatenate([c[-64:],c[:65]]);lags.append(int(z.argmax()-64));relative.append(float(np.linalg.norm(x-y)/max(np.linalg.norm(x),1e-10)))
 reports[name]={'one_second_window_lags_samples':lags,'max_absolute_lag_samples':max(abs(x) for x in lags),'one_second_relative_pcm_errors':relative}
(OUT/'vae_timing_details.json').write_text(json.dumps(reports,indent=2))
prefix={}
for name in ['legacy_prechorus']:
 p=OUT/'cases'/name;source=np.load(p/'source.npy').astype(np.float16);native=np.load(p/'native_0/latents.npy');mask=np.load(p/'mask.npy');boundary=int(np.flatnonzero(mask[0])[0]);prefix[name]={'first_generated_frame':boundary,'prefix_seconds':boundary/25,'samples_per_latent_frame':1920,'blend_frames':12,'exact_preserved_frames':boundary-12,'preserved_prefix_exact':bool(np.array_equal(native[:,:boundary-12],source[:,:boundary-12])),'mask_true_means':'generate'}
(OUT/'prefix_validation.json').write_text(json.dumps(prefix,indent=2));print({k:v['max_absolute_lag_samples'] for k,v in reports.items()},prefix)
