"""Compact current-pass measurements. Reads generated evidence only after generation."""
from pathlib import Path
import json
import numpy as np
R=Path(__file__).resolve().parents[2];O=R/'results/ace_demo_20260916'
rows=[]
for name in ['bad_community','bad_curve']:
 p=O/name/'result.json'
 if not p.exists():continue
 m=json.loads(p.read_text());rows.append({'case':name,'accepted':m['quality_accepted'],'accepted_seed':m['accepted_seed'],'total_wall_seconds':m['qualified_wall_seconds'],'buffer_cost_seconds':m['qualified_wall_seconds'],'buffer_remaining_from_90_seconds':90-m['qualified_wall_seconds'],'host_peak_mib':m.get('host_peak_mib'),'tracked_allocation_bytes':m.get('tracked_allocation_bytes'),'attempts':[{'seed':a['seed'],'role':a['role'],'seconds':a['wall_seconds'],'quiet_seconds':a['quality']['longest_quiet_seconds'],'accepted':a['quality']['accepted'],'reason':a['quality']['reasons'],'generation_seconds':a['runtime']['generation_seconds'],'decode_seconds':a['runtime']['decode_seconds'],'new_seconds':a['runtime']['new_seconds']} for a in m['quality_attempts']]})
report={'known_bad_cases':rows,'same_role_same_source':True,'cpu':'noise, energy gate, endpoint selection, retry decisions, file capture and arrangement','chestnut':'DiT/Euler sampling and VAE decode','human_listening_verified':False}
p=O/'soak_result.json'
if p.exists():
 m=json.loads(p.read_text());jobs=m['rows'][1:];accepted=[j for j in jobs if j.get('quality_accepted')];new=sum(j['new_seconds'] for j in accepted);cost=sum(j['qualified_wall_seconds'] for j in jobs)
 report['soak']={'accepted_continuations':m['accepted'],'accepted_new_audio_seconds':new,'qualified_generation_wall_seconds':cost,'effective_rtf_including_rejected_attempts':cost/new if new else None,'original_generations':sum(bool(j.get('quality_attempts')) for j in jobs),'rejected_attempts':sum(j['quality_rejections'] for j in jobs),'rerolls':sum(j['rerolls'] for j in jobs),'host_peak_mib_includes_standalone_flow_assembly':max([j.get('host_peak_mib',0) for j in jobs] or [0]),'tracked_allocation_bytes':max([j.get('tracked_allocation_bytes',0) for j in jobs] or [0]),'stopped_reason':jobs[-1].get('blocked') if jobs else None,'warm_per_job_rtf':[j['qualified_wall_seconds']/j['new_seconds'] for j in accepted]}
prefix_checks=[];prior=O/'soak/initial/accepted.npy'
if prior.exists():
 previous=np.load(prior)
 for folder in sorted((O/'soak').glob('section_*')):
  if not (folder/'accepted.npy').exists():break
  current=np.load(folder/'accepted.npy');stats=json.loads((folder/'result.json').read_text());n=round(stats['prefix_seconds']*25);prefix_checks.append({'section':folder.name,'exact_preserved_latent_prefix_excluding12frame_blend':bool(np.array_equal(previous[:,-n:-12],current[:,:n-12]))});previous=current
report['prefix_checks']=prefix_checks
(O/'suite_summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
