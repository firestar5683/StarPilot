"""Two additional reusable identities, prepared offline without route data or playback."""
import random,shutil
from prepare import *
import soundfile as sf
class Captured(BaseException):pass
roles={'verse':'Ongoing restrained verse, clear steady pulse, recurring hook; no ending or fade.', 'prechorus':'Ongoing prechorus, rising subdivisions and opening filters, steady bass and kick through the next chorus; no silent gap or terminal fade.', 'chorus':'Large bright chorus, continue the same hook and bass groove, continuous pulse; no ending or fade.', 'bridge':'Contrasting bridge in the same tonal center, preserve groove identity, different texture and instrumentation, new lead timbre, then rebuild. No modulation, silence or fade.', 'outro':'Motif return, same tonal center, thinning arrangement and gentle resolution, short intentional final fade allowed.'}
for identity,bpm,key,timbre in identities[1:]:
 reference=OUT/'cases'/f'{identity}_60/official/audio.wav';source,sr=sf.read(reference,dtype='float32',always_2d=True);base=OUT/'demo_profiles'/identity;base.mkdir(parents=True,exist_ok=True);padded=np.zeros((120*48000,2),np.float32);padded[:8*48000]=source[8*48000:16*48000];source_path=base/'prefix.wav';sf.write(source_path,padded,48000,subtype='FLOAT')
 initial=OUT/'cases'/f'{identity}_initial';initial.mkdir(exist_ok=True);original=OUT/'cases'/f'{identity}_60'
 for field in ['encoder_hidden_states','encoder_attention_mask','context_latents','noise']:
  array=np.load(original/(field+'.npy'))
  if field in ['context_latents','noise']:array=array[:,:750]
  np.save(initial/(field+'.npy'),array)
 meta=json.loads((original/'case.json').read_text());meta.update(name=initial.name,duration=30,preparation='first30s of60s prepared planner hints, new runtime noise');(initial/'case.json').write_text(json.dumps(meta,indent=2))
 for index,(role,prompt) in enumerate(roles.items()):
  p=OUT/'cases'/f'{identity}45_{role}';p.mkdir(exist_ok=True);o=p/'official';o.mkdir(exist_ok=True);seed=77100+identities.index((identity,bpm,key,timbre))*100+index;random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);mx.random.seed(seed);caption=common+f'{bpm} BPM, {key}. '+timbre+' '+prompt
  current.update(case=p,out=o,seed=seed,meta={'name':p.name,'caption':caption,'duration':45,'declared_condition_duration':120,'seed':seed,'reference_audio':str(reference),'thinking':False,'sampler':{},'preparation':'official120s source/task conditioning; first45s bounded window;8s prefix'})
  def boundary(*args,**kw):
   for field in ['encoder_hidden_states','encoder_attention_mask','context_latents','src_latents','repaint_mask','clean_src_latents']:
    if isinstance(kw.get(field),torch.Tensor):
     a=kw[field].detach().float().cpu().numpy()
     if field not in ['encoder_hidden_states','encoder_attention_mask']:a=a[:,:1125]
     np.save(p/({'repaint_mask':'mask','clean_src_latents':'source'}.get(field,field)+'.npy'),a)
   np.save(p/'noise.npy',np.random.default_rng(seed).standard_normal((1,1125,64)).astype(np.float16));current['meta']['sampler']={k:v for k,v in kw.items() if isinstance(v,(str,int,float,bool)) or v is None};(p/'case.json').write_text(json.dumps(current['meta'],indent=2));raise Captured('Prepared boundary complete')
  h._mlx_run_diffusion=boundary;params=GenerationParams(caption=caption,lyrics='[Instrumental]\n['+role.title()+']',instrumental=True,bpm=bpm,keyscale=key,timesignature='4',duration=120,inference_steps=8,seed=seed,thinking=False,dcw_enabled=False,use_cot_caption=False,use_cot_metas=False,use_cot_language=False,reference_audio=str(reference),task_type='repaint',src_audio=str(source_path),repainting_start=8,repainting_end=120,chunk_mask_mode='explicit');started=time.monotonic()
  try:generate_music(h,lm,params,GenerationConfig(batch_size=1,allow_lm_batch=False,use_random_seed=False,seeds=[seed],audio_format='wav'),save_dir=str(o/'unused'))
  except Captured:pass
  assert (p/'case.json').exists();(p/'preparation.json').write_text(json.dumps({'seconds':time.monotonic()-started,'expected_boundary_stop':True}));print('PREPARED_PROFILE',p.name,flush=True)
