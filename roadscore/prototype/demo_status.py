from device_target import device_target
"""Read-only private demo readiness. Never opens an audio or GPU device."""
import argparse,json,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def read(path):
 try:return json.loads(path.read_text())
 except (OSError,ValueError):return {}
def summarize(service,worker,initial,last_link,ready_file,muted):
 same_profile=service.get('profile')==worker.get('profile')==initial.get('prepared_profile')
 current_initial=same_profile and initial.get('created_wall',0)>=service.get('started_wall',float('inf')) and worker.get('phase')=='READY'
 own_link=bool(last_link) and last_link.get('owner_pid')==worker.get('pid')
 ready=bool(service.get('running') and service.get('phase')=='READY' and ready_file and worker.get('phase')=='READY' and current_initial and initial.get('duration',0)>=112 and own_link and last_link.get('healthy'))
 return {'ready_for_replay':ready,'profile':service.get('profile'),'service_phase':service.get('phase','Stopped'),'service_running':service.get('running',False),'accepted_initial_seconds':initial.get('duration',0) if current_initial else None,'last_observed_link_healthy':last_link.get('healthy') if own_link else None,'link_observation_age_seconds':max(0,time.time()-last_link['wall']) if own_link and 'wall' in last_link else None,'link_health_is_prediction':False,'session_mute_lock':muted,'note':'Link health is the last recorded observation, not a guarantee against the known intermittent compute/link fault.'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--bench',default=device_target());p.add_argument('--json',action='store_true');a=p.parse_args()
 if not Path('/TICI').exists():raise SystemExit(subprocess.run(['ssh',a.bench,'/usr/local/venv/bin/python','/data/roadscore/prototype/demo_status.py']+(['--json'] if a.json else [])).returncode)
 from worker_service import state
 link={}
 try:
  with (R/'generated/ace_link.jsonl').open('rb') as f:
   f.seek(0,2);f.seek(max(0,f.tell()-32768));lines=f.read().splitlines()
   for line in reversed(lines):
    try:link=json.loads(line);break
    except ValueError:pass
 except OSError:pass
 result=summarize(state(),read(R/'generated/ace_worker_state.json'),read(R/'generated/ace_initial.json'),link,(R/'generated/worker_ready').exists(),(R/'.session-muted').exists())
 if a.json:print(json.dumps(result,indent=2));return
 print(('READY FOR REPLAY' if result['ready_for_replay'] else ('NOT READY — checks incomplete' if result['service_phase']=='READY' else result['service_phase'].upper()))+' · '+str(result['profile'] or 'no profile'))
 print('Accepted starting music:',result['accepted_initial_seconds'],'seconds')
 print('Session mute lock:', 'ON' if result['session_mute_lock'] else 'OFF — confirm intended output before playback')
 print('Last link observation:',result['last_observed_link_healthy'],'· age:',result['link_observation_age_seconds'],'seconds')
 print(result['note'])
if __name__=='__main__':main()
