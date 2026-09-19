"""Prepare continuing-section intents without short-song planner ending tokens."""
import random,functools
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ace_stability_20260916'))
from prepare import *
from acestep.inference import GenerationParams,GenerationConfig,generate_music
class Captured(BaseException):pass
base=OUT/'flow_cases45';base.mkdir(exist_ok=True)
np.save(base/'silence_latent.npy',h.silence_latent.detach().float().cpu().numpy())
source,sr=__import__('soundfile').read(OUT/'cases/prism_60/official/audio.wav',dtype='float32',always_2d=True)
# An active early section, not the terminal tail, for preparation only. Runtime replaces
# it with the exact already-generated preceding latent context.
reference=OUT/'cases/prism_60/official/audio.wav';padded=np.zeros((120*48000,2),np.float32);padded[:8*48000]=source[8*48000:16*48000];source_path=base/'prefix_template.wav';__import__('soundfile').write(source_path,padded,48000,subtype='FLOAT')
roles={
 'bridge_glass':'Contrasting bridge, same D minor tonal center, preserve the established groove identity. Reduced drum arrangement, new glass lead timbre, filtered bass and restrained arpeggios. Rebuild density into the following chorus. Maintain continuous bass and percussion pulse through this interior excerpt.',
 'bridge_percussion':'Contrasting bridge, same D minor tonal center and recognizable crystal pluck motif. Reduce the lead and foreground syncopated percussion and filtered bass, then rebuild the bright arrangement into the following chorus. Preserve the steady groove and continuous audible pulse.',
 'bridge_air':'Contrasting bridge, same D minor tonal center, new airy synth texture answering the recurring pluck motif. Reduced arrangement with bass and restrained drums carrying the same groove, steadily rebuilding toward the chorus. Continuous interior song excerpt, no terminal fade.'}

for role in roles:
 for declared in [120]:
  name=f'demo45_{role}';p=OUT/'cases'/name;p.mkdir(parents=True,exist_ok=True);o=p/'official';o.mkdir(exist_ok=True);seed=55100+list(roles).index(role);random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);mx.random.seed(seed)
  current.update(case=p,out=o,seed=seed,meta={'name':name,'caption':common+roles[role],'duration':45,'declared_condition_duration':declared,'seed':seed,'reference_audio':str(reference),'thinking':False,'sampler':{},'preparation':'official120s metadata/conditioning, bounded first45s diffusion window; prefix8s'})
  def only(*args,**kw):
   for key in ['encoder_hidden_states','encoder_attention_mask','context_latents','src_latents','repaint_mask','clean_src_latents']:
    if isinstance(kw.get(key),torch.Tensor):
     arr=kw[key].detach().float().cpu().numpy()
     if key not in ['encoder_hidden_states','encoder_attention_mask']:arr=arr[:,:1125]
     np.save(p/({'repaint_mask':'mask','clean_src_latents':'source'}.get(key,key)+'.npy'),arr)
   np.save(p/'noise.npy',np.array(mx.random.normal((1,1125,64),key=mx.random.key(seed))));current['meta']['sampler']={k:v for k,v in kw.items() if isinstance(v,(str,int,float,bool)) or v is None};(p/'case.json').write_text(json.dumps(current['meta'],indent=2));raise Captured('Boundary saved; bounded sampling is a separate matched test')
  h._mlx_run_diffusion=only
  bounded_source=base/f'prefix_{declared}.wav';__import__('soundfile').write(bounded_source,padded[:declared*48000],48000,subtype='FLOAT')
  params=GenerationParams(caption=common+roles[role],lyrics='[Instrumental]\n['+role.title()+']',instrumental=True,bpm=128,keyscale='D minor',timesignature='4',duration=declared,inference_steps=8,seed=seed,thinking=False,dcw_enabled=False,use_cot_caption=False,use_cot_metas=False,use_cot_language=False,reference_audio=str(reference),task_type='repaint',src_audio=str(bounded_source),repainting_start=8,repainting_end=declared,chunk_mask_mode='explicit')
  st=time.monotonic()
  try:ret=generate_music(h,lm,params,GenerationConfig(batch_size=1,allow_lm_batch=False,use_random_seed=False,seeds=[seed],audio_format='wav'),save_dir=str(o/'unused'))
  except Captured:pass
  assert (p/'case.json').exists();(p/'preparation.json').write_text(json.dumps({'seconds':time.monotonic()-st,'expected_boundary_stop':True}));print('PREPARED_FLOW',name,flush=True)
