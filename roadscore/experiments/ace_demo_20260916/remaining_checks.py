"""Muted integration regressions; explicit owned-service stop tests containment."""
import os
import argparse,json,re,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'results/ace_demo_20260916'
sys.path.insert(0,str(R/'experiments/ace_chestnut_20260916'))
from integration_audit import audit
P=argparse.ArgumentParser();P.add_argument('mode',choices=['mac_fresh','containment','sa3','stored_native']);a=P.parse_args()
route=os.environ['ROADSCORE_ARRIVAL_ROUTE']
local=a.mode=='mac_fresh';stored=a.mode=='stored_native';duration=180 if a.mode in ['mac_fresh','containment'] else 120
args=['./onroad','--routeid',route,'--roadscore','--muted','--duration',str(duration)]
args+=['--replay'] if stored else ['--composer','sa3' if a.mode=='sa3' else 'ace','--profile','prism']
if local:args+=['--headless']
command=args if local else ['ssh','comma@192.168.3.111','cd /data/roadscore && '+' '.join(args)]
log=O/(a.mode+'.log');injection=None;started=time.time()
with log.open('w') as f:
 proc=subprocess.Popen(command,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 while proc.poll() is None:
  if a.mode=='containment' and injection is None:
   status=subprocess.run(['ssh','comma@192.168.3.111','cat /data/roadscore/results/current/status.json'],capture_output=True,text=True)
   try:s=json.loads(status.stdout)
   except ValueError:s={}
   # Verify this launch has started and the current status belongs to it.
   paths=re.findall(r'/data/roadscore/results/(normal_\d+)',log.read_text())
   if paths and s.get('completed_jobs',0)>=1:
    # Current session starts at zero; require its status to have been modified after launch.
    stamp=subprocess.run(['ssh','comma@192.168.3.111','stat -c %Y /data/roadscore/results/current/status.json'],capture_output=True,text=True)
    if stamp.returncode==0 and float(stamp.stdout)>started:
     stopped=subprocess.run([sys.executable,str(R/'prototype/worker_service.py'),'stop'],cwd=R,capture_output=True,text=True)
     injection={'wall':time.time(),'trigger':'first accepted generation reported by current replay','status_before_stop':s,'stop_returncode':stopped.returncode,'stop_output':stopped.stdout,'stop_stderr':stopped.stderr,'kind':'intentional owned-service stop; not a spontaneous GPU fault'}
     (O/'containment_injection.json').write_text(json.dumps(injection,indent=2))
  time.sleep(3)
paths=re.findall(r'(?:/data/roadscore|'+re.escape(str(R))+r')/results/(normal_\d+)',log.read_text())
result={'mode':a.mode,'returncode':proc.returncode,'elapsed':time.time()-started,'injection':injection}
if paths:
 name=paths[-1];dest=R/'results'/name
 if not local:
  dest.mkdir(exist_ok=True);subprocess.run(['rsync','-az',f'comma@192.168.3.111:/data/roadscore/results/{name}/',str(dest)+'/'],check=True)
 if not stored:
  archive=R/'routes'/route/'roadscore'/name
  if not local:
   archive.mkdir(parents=True,exist_ok=True);subprocess.run(['rsync','-az',f'comma@192.168.3.111:/data/roadscore/routes/{route}/roadscore/{name}/',str(archive)+'/'],check=True)
   for link,target in [('host_heard.flac','score.flac'),('quality','quality')]:
    p=dest/link
    if p.is_symlink():p.unlink();p.symlink_to(archive/target,target_is_directory=target=='quality')
  result.update(audit(dest));result['archive']=str(archive)
  if a.mode=='containment':
   trace=[json.loads(x) for x in (dest/'trace.jsonl').read_text().splitlines()]
   degraded=any(x.get('readiness')=='DEGRADED' for x in trace)
   result['degraded_observed']=degraded
   result['containment_pass']=bool(injection and injection['stop_returncode']==0 and result['worker_failed'] and result['safe_extensions'] and degraded and not(result['fallbacks'] or result['underflows'] or result['input_time_violations'] or any(result['host_audio'].get(k,0) for k in ['late_frames','starved_callbacks','portaudio_flags'])) and result['all_blocks_muted'] and proc.returncode==0)
 else:
  result.update(json.loads((dest/'stored_summary.json').read_text()));result['run']=name
  result['pass']=not result.get('generation_invoked',True) and result.get('contiguous_samples_verified') and result.get('muted') and result.get('portaudio_flags')==0 and proc.returncode==0
(O/(a.mode+'_audit.json')).write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['composition','gestures','runtime_manifest','ui_last']},indent=2))
