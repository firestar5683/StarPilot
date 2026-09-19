"""Isolated local ACE-Step composition screen. Writes files; opens no audio device."""
import os,time,json,resource,sys,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1];O=R/'results/composition_20260916/ace';O.mkdir(parents=True,exist_ok=True)
os.environ.update(HF_HOME=str(P/'cache/hf'),HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',PYTORCH_ENABLE_MPS_FALLBACK='1',TOKENIZERS_PARALLELISM='false')
BOOT=time.monotonic()
import torch,soundfile as sf,numpy as np
from acestep.handler import AceStepHandler
from acestep.llm_inference import LLMHandler
from acestep.inference import GenerationParams,GenerationConfig,generate_music
sys.path.insert(0,str(R/'prototype'))
from composition_sa3 import BASE,ROLES
h=AceStepHandler();lm=LLMHandler()
status,ok=h.initialize_service(str(P/'models/ace'),config_path='acestep-v15-turbo',device='mps',use_mlx_dit=True,offload_to_cpu=True,offload_dit_to_cpu=False)
(O/'dit_startup.json').write_text(json.dumps({'seconds':time.monotonic()-BOOT,'success':ok,'status':status},indent=2));assert ok,status
status,ok=lm.initialize(str(P/'models/ace/checkpoints'),'acestep-5Hz-lm-1.7B',backend='mlx',device='mps')
(O/'startup.json').write_text(json.dumps({'seconds':time.monotonic()-BOOT,'success':ok,'status':status,'backend':'official ACE-Step1.5 turbo / MLX, LM1.7B / MLX; Apple M1 Max32GB'},indent=2));assert ok,status
print('READY',time.monotonic()-BOOT,flush=True)
def generate(name,caption,lyrics,duration,reference=None):
 dest=O/name
 if (dest/'benchmark.json').exists():return
 params=GenerationParams(caption=caption,lyrics=lyrics,instrumental=True,bpm=128,keyscale='D minor',timesignature='4',duration=duration,inference_steps=8,seed=12601,thinking=True,use_cot_caption=False,use_cot_metas=False,use_cot_language=False,reference_audio=reference)
 config=GenerationConfig(batch_size=1,allow_lm_batch=False,use_random_seed=False,seeds=[12601],audio_format='wav')
 start=time.monotonic();result=generate_music(h,lm,params,config,save_dir=str(dest));elapsed=time.monotonic()-start
 meta={'seconds':elapsed,'success':result.success,'error':result.error,'caption':caption,'lyrics':lyrics,'requested_duration':duration,'reference_audio':reference,'host_peak_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20,'human_musical_acceptance':'pending','time_costs':result.extra_outputs.get('time_costs',{})}
 if result.success:
  file=Path(result.audios[0]['path']);info=sf.info(file);shutil.copy(file,O/(name+'.wav'));meta.update(duration=info.duration,rtf=elapsed/info.duration,path=str(O/(name+'.wav')),sample_rate=info.samplerate)
 dest.mkdir(exist_ok=True,parents=True);(dest/'benchmark.json').write_text(json.dumps(meta,indent=2,default=str));print(name,json.dumps(meta),flush=True)
 if not result.success:raise RuntimeError(result.error)
structure='[Instrumental]\n[Intro - hook pickup]\n[Verse - stripped drums and bass]\n[Pre-Chorus - rising tension]\n[Chorus - massive full synth hook]\n[Verse - return to sparse groove]\n[Bridge - contrasting modal color]\n[Chorus - triumphant return]\n[Outro - concluding hook and final cadence]'
generate('structured90',BASE+'An instrumental song with clear restrained verse, rising prechorus, massive chorus, contrasting bridge, recurring hook and a purposeful concluding outro. Strong section hierarchy and dramatic orchestration changes.',structure,90)
for role in ['verse','prechorus','chorus','bridge','outro']:
 tag={'prechorus':'Pre-Chorus'}.get(role,role.title())
 generate(role,BASE+ROLES[role],f'[Instrumental]\n[{tag}]',30,reference=str(O/'structured90.wav'))
generate('verse_to_chorus',BASE+ROLES['verse_to_chorus'],'[Instrumental]\n[Verse - restrained]\n[Pre-Chorus - two bar build]\n[Chorus - massive hook]',40,reference=str(O/'structured90.wav'))
