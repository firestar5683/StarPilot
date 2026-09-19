"""Sequential muted integration gates. Stop on failure; never reset the accelerator."""
import json,os,shutil,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'results/ace_demo_20260916'
def run(args,log=None,**kw):
 print('RUN',args,flush=True)
 if log:
  with (O/log).open('w') as f:return subprocess.run(args,cwd=R,stdout=f,stderr=subprocess.STDOUT,check=True,**kw)
 return subprocess.run(args,cwd=R,check=True,**kw)
def service(action,profile='prism'):
 return run([sys.executable,'prototype/worker_service.py',action,'--composer','ace','--profile',profile])
def prepare(profile):
 start=time.time();service('start',profile);deadline=time.monotonic()+1500
 while True:
  s=subprocess.run(['ssh','comma@192.168.3.111','cat /data/roadscore/generated/worker_service.json'],capture_output=True,text=True,check=True);state=json.loads(s.stdout)
  if state.get('phase')=='READY':break
  if state.get('phase') in ['Stopped','Failed'] or time.monotonic()>deadline:raise RuntimeError('Preparation failed; inspect preserved resident log')
  time.sleep(5)
 run(['scp','comma@192.168.3.111:/data/roadscore/generated/ace_initial.json',str(O/(profile+'_v2_preparation.json'))])
 (O/(profile+'_v2_startup.json')).write_text(json.dumps({'elapsed':time.time()-start,'state':state},indent=2))
 print('READY',profile,time.time()-start,flush=True)
def replay(profile,route):
 run([sys.executable,'experiments/ace_demo_20260916/replays.py'],profile+'_v2_replay_runner.log',env={**os.environ,'ACE_PROFILE':profile,'ACE_REPLAY_ONLY':route})
 row=next(r for r in json.loads((O/'replay_results.json').read_text()) if r['label']==('aurora_' if profile=='aurora' else '')+route)
 if not row.get('full_route_pass'):raise RuntimeError('Full route failed; do not call this completed')
# Wait only for the already-dispatched containment experiment, not for user input.
deadline=time.monotonic()+1800
while not (O/'containment_audit.json').exists():
 if time.monotonic()>deadline:raise RuntimeError('Containment watchdog elapsed; no extra jobs launched')
 time.sleep(5)
a=json.loads((O/'containment_audit.json').read_text())
# The first completed stop test exposed concatenate under the callback lock.
# Preserve it; the corrected app must pass a second injected-stop run below.
if not a.get('worker_failed') or not a.get('safe_extensions'):raise RuntimeError('Unexpected first containment result')
for name in ['containment_audit.json','containment_injection.json','containment.log','containment_runner.log']:
 f=O/name;backup=O/name.replace('containment','containment_first',1)
 if f.exists() and not backup.exists():shutil.copy2(f,backup)
# These are the precise changed private runtime files. The active v1 worker is now stopped.
run(['rsync','-az','experiments/ace_chestnut_20260916/quality_gate.py','experiments/ace_chestnut_20260916/ace_worker.py','comma@192.168.3.111:/data/roadscore/experiments/ace_chestnut_20260916/'])
run(['rsync','-az','prototype/worker_service.py','prototype/host_audio.py','prototype/app.py','comma@192.168.3.111:/data/roadscore/prototype/'])
run(['rsync','-az','experiments/ace_demo_20260916/gain_reroll.py','comma@192.168.3.111:/data/roadscore/experiments/ace_demo_20260916/'])
checkpoint=subprocess.check_output(['git','rev-parse','--short','HEAD'],cwd=R,text=True).strip();(R/'CHECKPOINT').write_text(checkpoint+'\n');run(['scp','CHECKPOINT','comma@192.168.3.111:/data/roadscore/CHECKPOINT'])
try:
 prepare('prism')
 run(['ssh','comma@192.168.3.111','cd /data/roadscore && /data/sa3-feasibility/venv/bin/python -u experiments/ace_demo_20260916/gain_reroll.py'],'gain_reroll_runner.log')
 run(['rsync','-az','comma@192.168.3.111:/data/roadscore/results/ace_demo_20260916/gain_reroll/',str(O/'gain_reroll')+'/'])
 for suffix in ['audit.json','runner.log','log']:
  f=O/('mac_fresh_'+suffix if suffix!='log' else 'mac_fresh.log')
  if f.exists():shutil.copy2(f,O/('mac_fresh_first_'+suffix))
 run([sys.executable,'experiments/ace_demo_20260916/remaining_checks.py','mac_fresh'],'mac_fresh_runner.log')
 rows=json.loads((O/'replay_results.json').read_text())
 for r in rows:
  if r['label']=='curve':r['label']='curve_v1'
 (O/'replay_results.json').write_text(json.dumps(rows,indent=2));shutil.copy2(O/'curve_replay_audit.json',O/'curve_v1_replay_audit.json');shutil.copy2(O/'curve_native_replay.log',O/'curve_v1_native_replay.log')
 replay('prism','curve')
 run([sys.executable,'experiments/ace_demo_20260916/remaining_checks.py','containment'],'containment_runner.log')
 if not json.loads((O/'containment_audit.json').read_text()).get('containment_pass'):raise RuntimeError('Corrected containment did not pass')
 service('stop')
 prepare('aurora');replay('aurora','arrival');service('stop','aurora')
 for mode in ['sa3','stored_native']:
  run([sys.executable,'experiments/ace_demo_20260916/remaining_checks.py',mode],mode+'_runner.log')
  a=json.loads((O/(mode+'_audit.json')).read_text())
  if not a.get('pass' if mode=='stored_native' else 'instrumented_pass'):raise RuntimeError(mode+' did not pass')
 print('ALL_FINAL_REGRESSIONS_COMPLETED',flush=True)
finally:service('stop')
