"""Official Torch DiT/sampler helpers and FP32 VAE on MPS, exact portable noise."""
import os,sys,time,json,hashlib
from pathlib import Path
os.environ['PYTORCH_ENABLE_MPS_FALLBACK']='1'
import numpy as np,torch,soundfile as sf
from bundle import R,OLD,OUT
M=R/'experiments/composition_20260916/models/ace/checkpoints/acestep-v15-turbo';sys.path.insert(0,str(M))
from configuration_acestep_v15 import AceStepConfig
from modeling_acestep_v15_turbo import AceStepDiTModel,_repaint_step_injection,_repaint_boundary_blend
from transformers.models.qwen3.modeling_qwen3 import Qwen3RotaryEmbedding
from diffusers import AutoencoderOobleck
config=AceStepConfig.from_pretrained(M);config._attn_implementation='sdpa'
with torch.device('meta'):model=AceStepDiTModel(config)
model.load_state_dict({p.stem:torch.from_numpy(np.load(p)) for p in (OLD/'weights').glob('*.npy')},assign=True);model.rotary_emb=Qwen3RotaryEmbedding(config);model=model.float().to('mps').eval()
half=os.environ.get('ACE_REFERENCE_FP16')=='1'
if half:
 model=model.half();model.rotary_emb=Qwen3RotaryEmbedding(config).to('mps')
vae=AutoencoderOobleck.from_pretrained(M.parent/'vae').float().to('mps').eval()
def ten(p,k):return torch.tensor(np.load(p/(k+'.npy')),device='mps')
plan=json.loads(Path(os.environ['ACE_REFERENCE_PLAN']).read_text()) if 'ACE_REFERENCE_PLAN' in os.environ else [{'case':n} for n in sys.argv[1:]]
for job in plan:
 name=job['case']
 p=OUT/'cases'/name;o=p/job.get('output','reference');o.mkdir(exist_ok=True);meta=json.loads((p/'case.json').read_text());settings=meta['sampler'];noise=ten(p,'noise').float();x=noise.clone();cond=ten(p,'encoder_hidden_states').float();ctx=ten(p,'context_latents').float();mask=ten(p,'encoder_attention_mask');am=torch.ones(x.shape[:2],device='mps');source=ten(p,'source').float() if (p/'source.npy').exists() else None;keep=ten(p,'mask').bool() if source is not None else None;steps=[];start=time.monotonic()
 if 'seed' in job:
  noise=torch.tensor(np.random.default_rng(job['seed']).standard_normal(tuple(noise.shape)).astype(np.float16),device='mps').float();x=noise.clone()
 if 'previous' in job:
  prefix=int(torch.nonzero(keep[0])[0].item());prior=np.load(OUT/job['previous']);source[:,:prefix]=torch.tensor(prior[:,-prefix:],device='mps');ctx[:,:prefix,:64]=source[:,:prefix];np.save(o/'input_source.npy',source.cpu().numpy());np.save(o/'input_context.npy',ctx.cpu().numpy());np.save(o/'input_noise.npy',noise.cpu().numpy())
 if half:
  x=x.half();noise=noise.half();cond=cond.half();ctx=ctx.half();source=source.half() if source is not None else None
 elif os.environ.get('ACE_ROUND_INPUTS')=='1':
  x=x.half().float();noise=noise.half().float();cond=cond.half().float();ctx=ctx.half().float();source=source.half().float() if source is not None else None
 from modeling_acestep_v15_turbo import DCWCorrector
 corrector=DCWCorrector(enabled=settings.get('dcw_enabled',False),mode=settings.get('dcw_mode','double'),scaler=settings.get('dcw_scaler',.05),high_scaler=settings.get('dcw_high_scaler',.02),wavelet=settings.get('dcw_wavelet','haar'))
 with torch.no_grad():
  for i,t in enumerate(np.linspace(1,0,9)[:-1]):
   if job.get('teacher_forcing'):
    x=ten(p/'official',f'input_{i}').half();x=x if half else x.float()
   st=time.monotonic();tt=torch.tensor([t],device='mps',dtype=torch.float16 if half else torch.float32);v=model(hidden_states=x,timestep=tt,timestep_r=tt,attention_mask=am,encoder_hidden_states=cond,encoder_attention_mask=mask,context_latents=ctx,use_cache=False)[0]
   np.save(o/f'velocity_{i}.npy',v.cpu().numpy());before=x;x=x-v*.125
   if corrector.is_active:x=corrector.apply(x,before-v*float(t),float(t))
   if source is not None and i<7 and i<round(settings.get('repaint_injection_ratio',.5)*8):x=_repaint_step_injection(x,source,keep,float(t-.125),noise)
   a=x.cpu().numpy();np.save(o/f'step_{i}.npy',a);steps.append({'step':i,'seconds':time.monotonic()-st,'rms':float(np.sqrt(np.mean(a*a))),'peak':float(abs(a).max())});print(name,'step',i,steps[-1],flush=True)
  if source is not None:x=_repaint_boundary_blend(x,source,keep,settings.get('repaint_crossfade_frames',12))
  a=x.cpu().numpy();np.save(o/'latents.npy',a);generation=time.monotonic()-start;st=time.monotonic();wave=vae.decode(x.float().transpose(1,2)).sample[0].T.cpu().numpy();decode=time.monotonic()-st
 if 'commit_seconds' in job:
  count=round(job['commit_seconds']*25)
  if job.get('adaptive_commit'):
   sys.path.insert(0,str(OLD));from window_policy import retained_end
   prefix=int(torch.nonzero(keep[0])[0].item())/25 if keep is not None else 0;count,endpoint=retained_end(wave,48000,prefix,job['commit_seconds'],allow_fade=name.endswith('_outro'));(o/'endpoint.json').write_text(json.dumps(endpoint,indent=2))
  np.save(o/'committed_latents.npy',a[:,:count]);sf.write(o/'committed.wav',wave[:count*1920]*.65,48000,subtype='FLOAT')
 np.save(o/'pcm.npy',wave);sf.write(o/'audio.wav',wave*.65,48000,subtype='FLOAT');report={'diagnostic_teacher_forcing':bool(job.get('teacher_forcing')),'generation_seconds':generation,'decode_seconds':decode,'steps':steps,'precision':'official '+('FP16' if half else 'FP32')+' MPS with exact exported weights','rounded_inputs':os.environ.get('ACE_ROUND_INPUTS')=='1','finite':bool(np.isfinite(wave).all()),'sha256':hashlib.sha256(a.tobytes()).hexdigest()};(o/'report.json').write_text(json.dumps(report,indent=2));print('DONE',name,report['generation_seconds'],flush=True)
 del x,noise,cond,ctx,mask,am,source,keep,v,before,tt
 torch.mps.synchronize();torch.mps.empty_cache()
