"""Private normal-launch regression fixtures. No route content feeds configuration."""
import os
import json,os,re,subprocess,sys,time
from pathlib import Path
from bundle import R,OUT
sys.path.insert(0,str(R/'experiments/ace_chestnut_20260916'))
from integration_audit import audit

fixtures=[('arrival',os.environ['ROADSCORE_ARRIVAL_ROUTE'],3600),
          ('curve',os.environ['ROADSCORE_CURVE_ROUTE'],3600),
          ('community',os.environ['ROADSCORE_COMMUNITY_ROUTE'],3600)]
# A generous common watchdog; success requires native EOF, not guessed route length.
only=os.environ.get('ACE_REPLAY_ONLY')
if only:
 if only not in [x[0] for x in fixtures]:raise ValueError('Unknown regression fixture')
 fixtures=[x for x in fixtures if x[0]==only]
rows=json.loads((OUT/'replay_results.json').read_text()) if only and (OUT/'replay_results.json').exists() else []
for label,route,seconds in fixtures:
 log=OUT/(label+'_native_replay.log');print('BEGIN',label,flush=True)
 with log.open('w') as f:
  result=subprocess.run(['ssh','comma@192.168.3.111',f'cd /data/roadscore && ./onroad --routeid {route} --roadscore --composer ace --muted --duration {seconds}'],stdout=f,stderr=subprocess.STDOUT)
 paths=re.findall(r'/data/roadscore/results/(normal_\d+)',log.read_text())
 row={'label':label,'route':route,'returncode':result.returncode}
 if paths:
  name=paths[-1];dest=R/'results'/name;dest.mkdir(exist_ok=True)
  subprocess.run(['rsync','-az',f'comma@192.168.3.111:/data/roadscore/results/{name}/',str(dest)+'/'],check=True)
  a=audit(dest);a['full_route_completed']=a['launch'].get('end_reason')=='native final segment exhausted'
  ui=a.get('ui_last') or {}
  started=any(json.loads(line).get('started') for line in (dest/'ui_audit.jsonl').read_text().splitlines())
  a['normal_ui_verified']=bool(started and all(ui.get(k,0)>0 for k in ['accepted_camera_frames','nonempty_path_draws','nonempty_lane_draws','camera_texture_draws']))
  a['full_route_pass']=a['instrumented_pass'] and a['full_route_completed'] and a['normal_ui_verified'] and result.returncode==0
  (OUT/(label+'_replay_audit.json')).write_text(json.dumps(a,indent=2));row.update(run=name,pass_instrumented=a['instrumented_pass'],full_route_pass=a['full_route_pass'])
  archive=R/'routes'/route/'roadscore'/name;archive.mkdir(parents=True,exist_ok=True)
  copy=subprocess.run(['rsync','-az',f'comma@192.168.3.111:/data/roadscore/routes/{route}/roadscore/{name}/',str(archive)+'/'])
  row['archive_copied']=copy.returncode==0
  if copy.returncode==0:
   link=dest/'host_heard.flac'
   if link.is_symlink():link.unlink();link.symlink_to(archive/'score.flac')
   sys.path.insert(0,str(R/'prototype'))
   from score_archive import prefer_new_score
   latest=archive.parent/'latest.json';old={}
   if latest.exists():
    previous=json.loads(latest.read_text())['session'];old_path=archive.parent/previous/'metadata.json'
    if old_path.exists():old=json.loads(old_path.read_text())
   metadata=json.loads((archive/'metadata.json').read_text())
   (archive.parent/'last_generated.json').write_text(json.dumps({'session':name}))
   if prefer_new_score(metadata,old):latest.write_text(json.dumps({'session':name}))
  row['audio']=str((archive/'score.flac').relative_to(R))
  row['summary']=f"{'PASS' if a['full_route_pass'] else 'REQUIRES REVIEW'}; {a['audio_seconds']}s captured; {a['completed_jobs']} fresh jobs; {a['underflows']} underflows; {a['fallbacks']} fallbacks; muted."
 rows=[r for r in rows if r['label']!=label]+[row];(OUT/'replay_results.json').write_text(json.dumps(rows,indent=2));print('END',json.dumps(row),flush=True)
 if result.returncode or (paths and (a['generation_errors'] or a['worker_failed'])):
  raise SystemExit('Stopped route batch for investigation; original failure retained.')
