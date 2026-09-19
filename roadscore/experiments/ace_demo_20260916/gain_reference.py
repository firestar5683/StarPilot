"""One exact musical-input reference counterfactual, after Mac transport is finished."""
import json,os,subprocess,time,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'results/ace_demo_20260916'
deadline=time.monotonic()+1800
while True:
 first=O/'mac_fresh_first_audit.json';current=O/'mac_fresh_audit.json'
 if first.exists() and current.exists() and json.loads(first.read_text()).get('run')!=json.loads(current.read_text()).get('run'):break
 if time.monotonic()>deadline:raise RuntimeError('No completed second Mac transport test; reference not launched')
 if 'Traceback' in (O/'final_regressions_v2.log').read_text():raise RuntimeError('Primary regression batch stopped; reference not launched')
 time.sleep(5)
meta=json.loads((O/'gain_reroll/result.json').read_text());plan=[]
for row in meta['quality_attempts']:
 plan.append({'case':'window45_verse','output':'gain_reference_'+str(row['attempt']),'seed':row['seed'],'previous':str(O/'curve_gain_source.npy'),'commit_seconds':36,'adaptive_commit':True})
p=O/'gain_reference_plan.json';p.write_text(json.dumps(plan,indent=2))
with (O/'gain_reference.log').open('w') as f:
 subprocess.run([str(R/'experiments/composition_20260916/venv/bin/python'),str(R/'experiments/ace_stability_20260916/reference.py')],cwd=R,env={**os.environ,'ACE_ROUND_INPUTS':'1','ACE_REFERENCE_PLAN':str(p)},stdout=f,stderr=subprocess.STDOUT,check=True)
sys.path.insert(0,str(R/'experiments/ace_chestnut_20260916'))
import soundfile as sf
from quality_gate import inspect
rows=[]
for job,native in zip(plan,meta['quality_attempts']):
 folder=R/'results/ace_stability_20260916/cases'/job['case']/job['output'];wave,sr=sf.read(folder/'committed.wav',always_2d=True,dtype='float32');q=inspect(wave/.65,sr,8,role='verse')
 rows.append({'seed':job['seed'],'reference':q,'native':native['quality'],'acceptance_agrees':q['accepted']==native['quality']['accepted'],'reference_report':json.loads((folder/'report.json').read_text()),'source':str(folder)})
(O/'gain_reference_audit.json').write_text(json.dumps(rows,indent=2));print([(r['seed'],r['acceptance_agrees'],r['reference']['longest_quiet_seconds']) for r in rows],flush=True)
