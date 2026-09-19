"""Bounded local instrumental screen; writes audio only, never opens a device."""
import os,sys,json,time,resource,traceback
from pathlib import Path
P=Path(__file__).resolve().parent; R=P.parents[1]; O=R/'results/composition_20260916/yue';O.mkdir(exist_ok=True)
os.environ['HF_HUB_DISABLE_TELEMETRY']='1';os.environ['HF_HOME']=str(P/'cache/hf');os.environ['PYTORCH_ENABLE_MPS_FALLBACK']='1'
sys.path.insert(0,str(P/'vendor/YuE/src'))
start=time.perf_counter(); report={'human_musical_acceptance':'pending','device':'M1 Max MPS','maximum_audio_seconds':90,'physical_output':False}
try:
 import torch
 from yue2 import YuE2Pipeline
 from yue2.protocol import GenerationConfig
 config=GenerationConfig.from_dict({'abc':{'max_tokens':2048},'semantic':{'max_tokens':2250}})
 deadline=time.monotonic()+1200
 with YuE2Pipeline.from_pretrained(str(P/'models/yue2'),vae=str(P/'models/yue2_vae'),device='mps',backend='torch-eager',memory_budget_gib=16,offload_ar=True,vae_core_frames=512,generation_config=config,local_files_only=True) as pipe:
  report['prepare_seconds']=time.perf_counter()-start;t=time.perf_counter()
  song=pipe(style='Instrumental polished K-pop and electronic game-score, 128 BPM, D minor, crisp compressed electronic drums, electric and synth bass, bright arpeggios, memorable recurring synth hook. Restrained verse, unmistakable rising prechorus, massive wide chorus, contrasting bridge, purposeful concluding outro. One coherent ninety-second song. No vocals, singing, chanting or speech.',lyrics='[Instrumental]\n[Intro]\n[Verse]\n[Pre-Chorus]\n[Chorus]\n[Bridge]\n[Chorus]\n[Outro]',cot='full',seed=12601,id='kpop_control',cancelled=lambda:time.monotonic()>deadline)
  song.save_artifacts(O/'structured90');report.update(success=True,generation_seconds=time.perf_counter()-t,duration=len(song.audio)/48000,timing=song.timing,truncated=song.truncated)
  report['rtf']=report['generation_seconds']/report['duration']
  report['mps_current_bytes']=torch.mps.current_allocated_memory();report['mps_driver_bytes']=torch.mps.driver_allocated_memory()
except Exception as e:
 report.update(success=False,error=repr(e));traceback.print_exc()
finally:
 report.update(wall_seconds=time.perf_counter()-start,host_peak_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20)
 (O/'benchmark.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
