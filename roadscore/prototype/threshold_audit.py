"""Offline threshold sensitivity across whole routes; no runtime tuning or future inputs."""
import json
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'results/unattended';labels=json.loads((O/'curve_timing.json').read_text())['events'];report={}
for path in O.glob('*_detector.json'):
 if 'handoff' in path.name or 'threshold' in path.name:continue
 route=path.name.replace('_detector.json','');rows=json.loads(path.read_text());cars=np.load(O/(route+'_motion.npz'))['cars'];per={}
 for threshold in [.4,.6,.8]:
  episodes=[];since=None;sign=None;last=None
  for r in rows:
   eligible=r['candidate_strength']>=threshold and r['speed']>=3
   if not eligible:since=None;sign=None;last=None;continue
   if since is None or sign!=r['candidate_sign'] or r['t']-last>.4:
    since=r['t'];sign=r['candidate_sign'];episode={'start':since,'sign':sign,'qualified':None,'predicted_peak':r['candidate_peak']};episodes.append(episode)
   if r['t']-since>=.3 and episode['qualified'] is None:episode['qualified']=r['t'];episode['predicted_peak']=r['candidate_peak']
   last=r['t']
  episodes=[e for e in episodes if e['qualified'] is not None];leads=[]
  for label in labels:
   if label['route']!=route or label['ambiguous_onset']:continue
   matching=[e for e in episodes if label['steering_onset']-10<=e['qualified']<=label['steering_peak'] and e['sign']==-int(np.sign(label['steering_peak_deg'])) and abs(e['predicted_peak']-label['steering_peak'])<5]
   hit=min(matching,key=lambda e:e['qualified']) if matching else None
   leads.append({'onset':label['steering_onset'],'peak':label['steering_peak'],'class':label['class'],'lead':None if hit is None else label['steering_onset']-hit['qualified']})
  # Conservative non-turn proxy: future steering stays within +/-3deg of its starting value throughout 8s.
  straight=[]
  for e in episodes:
   t=e['qualified'];m=cars[(cars[:,0]>=t)&(cars[:,0]<=t+8)]
   if len(m)>100 and np.min(m[:,1])>5 and np.max(abs(m[:,2]-m[0,2]))<3:straight.append(t)
  per[str(threshold)]={'qualified_episodes':len(episodes),'straight_candidate_times':straight,'labeled_leads':leads}
 report[route]=per
(O/'threshold_sensitivity.json').write_text(json.dumps({'note':'Candidates reconstructed from original raw model max lateral acceleration. Persistence0.3s, no Conductor cooldown. Independent fixed steering labels. Straight test is conservative and not a definitive false-positive classifier. No deployment based on this proxy alone.','routes':report},indent=2))
for route,per in report.items():
 print(route,[(k,v['qualified_episodes'],len(v['straight_candidate_times']),sum(x['lead'] is not None and x['lead']>0 for x in v['labeled_leads'])) for k,v in per.items()])
