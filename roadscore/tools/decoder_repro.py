"""Run the existing minimized decoder reproducer with offroad CPU supervision."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--runtime',choices=['native','official'],default='native');p.add_argument('--mode',choices=['resident_readback','resident_compute','upload_readback'],default='resident_readback');p.add_argument('--repeats',type=int,default=40);p.add_argument('--idle',type=float,default=0);a=p.parse_args()
root=Path(__file__).resolve().parents[1]
if not Path('/TICI').exists():raise SystemExit('Run this command on the offroad event comma')
if not 1<=a.repeats<=1000 or a.idle<0:raise SystemExit('Invalid bounded test settings')
source=root/'assets/decoder_repro_latents.npy'
if not source.exists():raise SystemExit('Stage the fixed pre-event latent fixture first')
out=root/'results/event_night_one'/('decoder_'+str(time.time_ns()))
env={**os.environ,'ACE_REPRO_MODE':a.mode,'ACE_REPRO_REPEATS':str(a.repeats),'ACE_REPRO_IDLE':str(a.idle),'ACE_REPRO_LATENTS':str(source),'ACE_REPRO_OUTPUT':str(out),'ROADSCORE_WORKER':str(root/'experiments/ace_demo_20260916/chunk_repro.py'),'TC_OPT':'2','ROADSCORE_FORCE_MUTE':'1'}
if a.runtime=='official':
 candidates=list((root/'external/comma_hack_7/.venv/lib').glob('python*/site-packages'))
 candidates=[p for p in candidates if (p/'tinygrad/__init__.py').exists()]
 if len(candidates)!=1:raise SystemExit('Official pinned tinygrad installation unavailable or ambiguous')
 env['ROADSCORE_TINYGRAD_PATH']=str(candidates[0])
out.mkdir(parents=True,exist_ok=False)
manifest={'runtime':a.runtime,'tinygrad_path':env.get('ROADSCORE_TINYGRAD_PATH','/data/openpilot/tinygrad_repo'),'mode':a.mode,'repeats':a.repeats,'idle_seconds':a.idle,'jit':env.get('JIT','1'),'power_limit_watts':env.get('AM_POWER_LIMIT','driver default'),'physically_muted':True,'fixed_input':str(source),'started_wall':time.time()}
(out/'invocation.json').write_text(json.dumps(manifest,indent=2));print('DECODER_EVIDENCE',out,flush=True)
code=subprocess.call(['/usr/local/venv/bin/python',str(root/'prototype/power_worker.py')],env=env)
manifest.update(exit_code=code,finished_wall=time.time());(out/'invocation.json').write_text(json.dumps(manifest,indent=2))
raise SystemExit(code)
