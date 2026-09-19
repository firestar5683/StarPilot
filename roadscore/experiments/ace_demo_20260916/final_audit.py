"""Read-only final regression/cleanup evidence. Run after all owned tests exit."""
import json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'results/ace_demo_20260916'
def read(name):
 p=O/name;return json.loads(p.read_text()) if p.exists() else {}
remote=r'''
import json,os,fcntl,subprocess
from pathlib import Path
R=Path('/data/roadscore');out={}
def read(p):
 try:return json.loads(p.read_text())
 except (OSError,ValueError):return {}
locks={}
for name in ['gpu.lock','native_session.lock','display.lock','worker_service.lock']:
 with (R/'generated'/name).open('a+') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks[name]=True
  except BlockingIOError:locks[name]=False
out['locks_free']=locks
owned=[]
needles=[str(R/p) for p in ['prototype/app.py','prototype/worker.py','prototype/power_worker.py','prototype/worker_service.py','prototype/normal_onroad.py','prototype/stored_score.py','experiments/ace_chestnut_20260916/ace_worker.py','native_build/replay']]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:args=(p/'cmdline').read_bytes().split(b'\0');args=[a.decode(errors='replace') for a in args]
 except OSError:continue
 if any(n in args for n in needles):owned.append({'pid':int(p.name),'command':args})
out['owned_processes']=owned;out['worker_ready_file']=(R/'generated/worker_ready').exists();out['session_mute_lock']=(R/'.session-muted').exists()
before=read(R/'worker_power_before.json');after=read(R/'worker_power_after.json');actual={p:Path(p).read_text().strip() for p in before};out['cpu_restored']=bool(before) and before==after==actual;out['cpu_before']=before;out['cpu_actual']=actual
pid=subprocess.run(['pgrep','-f','^selfdrive.ui.ui$'],text=True,capture_output=True)
out['normal_ui_pids']=pid.stdout.split()
if out['normal_ui_pids']:
 stat=Path('/proc/'+out['normal_ui_pids'][0]+'/stat').read_text().split();manager=stat[3];out['manager_pid']=manager;out['manager_state']=Path('/proc/'+manager+'/stat').read_text().split()[2]
env=os.environ.copy()
for k in ['OPENPILOT_PREFIX','PARAMS_ROOT','ZMQ']:env.pop(k,None)
p=subprocess.run(['/usr/local/venv/bin/python','-c','from openpilot.common.params import Params; print(int(Params().get_bool("IsOnroad")))'],cwd='/data/openpilot',env=env,capture_output=True,text=True)
out['verified_offroad']=p.returncode==0 and p.stdout.strip()=='0'
print(json.dumps(out))
'''
bench=subprocess.run(['ssh','comma@192.168.3.111','/usr/local/venv/bin/python','-'],input=remote,text=True,capture_output=True,check=True)
cleanup=json.loads(bench.stdout);cleanup['mac_system_muted']=subprocess.check_output(['osascript','-e','output muted of (get volume settings)'],text=True).strip()=='true';cleanup['mac_session_mute_lock']=(R/'.session-muted').exists();cleanup['public_starpilot_status']=subprocess.check_output(['git','-C','/Users/dominickthompson/starpilot','status','--short'],text=True)
processes=subprocess.check_output(['ps','-axo','pid=,command='],text=True).splitlines()
cleanup['host_audio_processes']=[line.strip() for line in processes if str(R/'prototype') in line and any('/'+name+'.py' in line for name in ['normal_onroad','host_audio','stored_score','pcm_transport','replay_bridge'])]
cleanup['pass']=not cleanup['host_audio_processes'] and all(cleanup['locks_free'].values()) and not cleanup['owned_processes'] and not cleanup['worker_ready_file'] and cleanup['session_mute_lock'] and cleanup['mac_session_mute_lock'] and cleanup['mac_system_muted'] and cleanup['cpu_restored'] and cleanup['verified_offroad'] and bool(cleanup['normal_ui_pids']) and cleanup.get('manager_state') not in ['T','t']
(O/'cleanup.json').write_text(json.dumps(cleanup,indent=2))
rows=read('replay_results.json');energy={x['label']:x for x in read('archive_energy.json')}
validation={'routes':[{**r,'audio_energy':energy.get(r['label'])} for r in rows], 'mac_fresh_pass':read('mac_fresh_audit.json').get('instrumented_pass'), 'mac_first_transport_failure_retained':not read('mac_fresh_first_audit.json').get('instrumented_pass',True), 'containment_pass':read('containment_audit.json').get('containment_pass'),'first_containment_failure_retained':not read('containment_first_audit.json').get('containment_pass',True),'sa3_pass':read('sa3_audit.json').get('instrumented_pass'),'stored_mac_pass':read('stored_mac_audit.json').get('pass'),'stored_native_pass':read('stored_native_audit.json').get('pass'),'cleanup_pass':cleanup['pass'],'human_listening_pending':True,'gpu_root_cause_resolved':False,'live_modeld_coexistence_verified':False}
(O/'validation.json').write_text(json.dumps(validation,indent=2));print(json.dumps({k:v for k,v in validation.items() if k!='routes'},indent=2));print('Cleanup',cleanup['pass'])
