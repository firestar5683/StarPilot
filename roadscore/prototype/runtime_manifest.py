"""Implementation provenance only; no route/model-content reads."""
import hashlib,json,subprocess
from render_policy import selected as render_mode_selected
from pathlib import Path
from composer_choice import choice,NAMES
from ace_profiles import selected
root=Path('/data/roadscore');files=[root/'prototype'/name for name in ['app.py','render_policy.py','worker.py','core.py','musical.py','rolling.py','event_music.py','render_clock.py','song_form.py','section_bank.py','bar_grid.py','audio_policy.py','musical_gestures.py','gesture_bank.py','composition_policy.py','graph_cache.py']]+[Path('/data/sa3-feasibility/native_sa3.py')]
result={'render_mode':render_mode_selected(),'backend':NAMES[choice()],'composer':choice(),'implementation_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.exists()},'runtime':json.loads((root/'runtime.json').read_text()),'weight_hash':'not collected in this integration pass'}
source=root/('assets/source_'+result['runtime'].get('identity','legacy')+'.wav')
if choice()=='ace':
 source=root/'generated/ace_initial.wav'
 for folder in [root/'experiments/ace_chestnut_20260916',root/'prototype']:
  for name in ['ace_worker.py','ace_runtime.py','window_runtime.py','window_policy.py','native_ace.py','native_vae.py','chunk_decode.py','gesture_bank_v2.py','musical_gestures_v2.py','gesture_bank_v3.py','musical_gestures_v3.py','ending_policy.py','quality_gate.py','link_health.py','safe_extension.py','ace_profiles.py','gesture_bank_v4.py','musical_gestures_v4.py']:
   path=folder/name
   if path.exists():result['implementation_sha256'][str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
if choice()=='ace':
 profile=root/'experiments/ace_chestnut_20260916/profiles'/selected()/'profile.json'
 initial=root/'generated/ace_initial.json'
 if initial.exists():result['ace_initial_provenance']=json.loads(initial.read_text())
 if profile.exists() and result.get('ace_initial_provenance',{}).get('prepared_profile')==selected():result['prepared_profile_manifest']=json.loads(profile.read_text())
if source.exists():result['source_identity']={'name':result['runtime'].get('identity'),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
for name,path in [('openpilot','/data/openpilot'),('tinygrad','/data/openpilot/tinygrad_repo')]:
 process=subprocess.run(['git','-C',path,'rev-parse','HEAD'],text=True,capture_output=True);result[name+'_revision']=process.stdout.strip() if process.returncode==0 else 'unavailable'
(root/'results/current/runtime_manifest.json').write_text(json.dumps(result,indent=2))
