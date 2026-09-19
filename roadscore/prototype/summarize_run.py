"""Offline evidence summary; never used by runtime decisions."""
import os
import json,statistics,sys
from pathlib import Path
p=Path(sys.argv[1]);s=json.loads((p/'summary.json').read_text());trace=[json.loads(x) for x in (p/'trace.jsonl').read_text().splitlines()]
out={'summary':s,'max_replay_lateness_seconds':max(x['replay_late'] for x in trace),'route_audio_origin_median':statistics.median(x['route_t']-x['elapsed'] for x in trace)}
if (p/'jobs.jsonl').exists():
 jobs=[json.loads(x) for x in (p/'jobs.jsonl').read_text().splitlines()]
 assert all(max(j['input_times'].values())<=j['cutoff_ns'] for j in jobs)
 out['job_source_cutoff_check']='passed';out['jobs_requested']=len(jobs)
if (p/'audio_blocks.jsonl').exists():
 blocks=[json.loads(x) for x in (p/'audio_blocks.jsonl').read_text().splitlines()]
 assert all(x['muted'] for x in blocks)
 out['all_device_blocks_muted']=True
 if trace[0]['route']==os.environ.get('ROADSCORE_CURVE_ROUTE','').split('/')[-1]:
  a=next((x for x in blocks if 130<x['route_t']<145 and x['amount']>0),None)
  if a:
   response=a['callback_wall']-a['replay_origin_wall'] if a.get('replay_origin_wall') is not None else a['route_t']
   out['audio_file_route_origin']=blocks[0]['callback_wall']-blocks[0]['replay_origin_wall'] if blocks[0].get('replay_origin_wall') is not None else None
   out['first_curve_render']={'block':a,'estimated_route_time':response,'steering_reference_time':141.531554781,'lead_to_steering_seconds':141.531554781-response,'note':'Callback wall time mapped to replay clock when available; otherwise source availability only. Not microphone latency.'}
(p/'evidence.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='summary'},indent=2))
