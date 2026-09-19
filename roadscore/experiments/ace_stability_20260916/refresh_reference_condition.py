"""Diagnostic: change only the prepared timbre reference to the actual preceding music.
Source/noise/mask remain the captured live failure; no runtime host dependency is added.
"""
from prepare import *
class Captured(BaseException):pass
base=OUT/'cases/live_community_chorus';p=OUT/'cases/live_gap_refreshed_reference';p.mkdir(exist_ok=True)
for f in base.glob('*.npy'):shutil.copy2(f,p/f.name)
seed=55102;random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);mx.random.seed(seed)
original=json.loads((OUT/'cases/window45_chorus/case.json').read_text());reference=OUT/'live_chorus_source/ace_job_1789597789267.wav'
captured=False
def capture_condition(*args,**kw):
 global captured
 captured=True
 for key in ['encoder_hidden_states','encoder_attention_mask']:
  np.save(p/(key+'.npy'),kw[key].detach().float().cpu().numpy().astype(np.float16))
 raise Captured()
h._mlx_run_diffusion=capture_condition
params=GenerationParams(caption=original['caption'],lyrics='[Instrumental]\n[Chorus]',instrumental=True,bpm=128,keyscale='D minor',timesignature='4',duration=120,inference_steps=8,seed=seed,thinking=False,dcw_enabled=False,use_cot_caption=False,use_cot_metas=False,use_cot_language=False,reference_audio=str(reference),task_type='repaint',src_audio=str(OUT/'flow_cases45/prefix_120.wav'),repainting_start=8,repainting_end=120,chunk_mask_mode='explicit')
st=time.monotonic()
try:generate_music(h,lm,params,GenerationConfig(batch_size=1,allow_lm_batch=False,use_random_seed=False,seeds=[seed],audio_format='wav'),save_dir=str(p/'unused'))
except Captured:pass
assert captured, 'Official preparation did not reach the model boundary'
meta=json.loads((base/'case.json').read_text());meta.update(name=p.name,reference_audio=str(reference),ablation='Only encoder conditioning refreshed with actual preceding audio; same caption/role/settings and original noise/source/mask',preparation_seconds=time.monotonic()-st,expected_boundary_stop=True,sha256={f.stem:hashlib.sha256(np.load(f).tobytes()).hexdigest() for f in p.glob('*.npy')});(p/'case.json').write_text(json.dumps(meta,indent=2))
plan=[{'case':p.name,'output':'reference_rounded'}]+[{'case':p.name,'seed':(2891394132+0x9e3779b9*i)%2**32,'output':f'reference_seed{i}'} for i in [1,2]]
(OUT/'live_gap_refreshed_plan.json').write_text(json.dumps(plan,indent=2));print('CONDITION_REFRESHED',meta['preparation_seconds'],flush=True)
