"""Offline capture audit, never imported by runtime."""
import json,wave
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'results/continuity'
out={}
for name in ['live_curve','live_arrival','other_route','live_development']:
 p=O/name
 if not (p/'summary.json').exists():continue
 s=json.loads((p/'summary.json').read_text());rows=[json.loads(t) for t in (p/'trace.jsonl').read_text().splitlines()];blocks=[json.loads(t) for t in (p/'audio_blocks.jsonl').read_text().splitlines()];jobs=s['generation']
 assert all(b['muted'] for b in blocks)
 assert all(b['route_t']<=b['callback_wall']-b['replay_origin_wall']+.005 for b in blocks)
 measured={'audio_seconds':s['audio_seconds'],'flags':s['underflows'],'fallbacks':s['fallbacks'],'accepted_jobs':len(jobs),'arrival_at':s['arrival_at'],'buffer_min_seconds':min(r['buffered'] for r in rows),'all_muted':True,'max_replay_late':max(r['replay_late'] for r in rows),'jobs':[{'seconds':j['seconds'],'decode_seconds':j['decode_seconds'],'usable_seconds':j['usable_new_seconds'],'unique_seconds':j['new_seconds'],'playback_rtf':j['seconds']/j['usable_new_seconds'],'unique_rtf':j['seconds']/j['new_seconds'],'host_peak_mib':j['host_peak_mib'],'tracked_gpu_mib':j['tracked_gpu_mib'],'trajectory':j.get('trajectory'),'conditioning':j['conditioning'],'conditioning_mix':j.get('conditioning_mix')} for j in jobs]}
 for fname in ['dry','heard']:
  with wave.open(str(p/(fname+'.wav'))) as f:sr=f.getframerate();x=np.frombuffer(f.readframes(f.getnframes()),'<i2').reshape(-1,2)/32768
  n=sr//10;e=np.sqrt(np.mean(x[:len(x)//n*n].reshape(-1,n,2)**2,axis=(1,2)))
  # Intentional post-ending silence must not masquerade as a source-gap failure.
  cutoff=round((s['arrival_at']-rows[0]['route_t'])*10) if s['arrival_at'] else len(e)
  measured[fname]={'peak':float(np.abs(x).max()),'minimum_rms_db_before_ending':float(20*np.log10(max(float(e[:cutoff].min()),1e-9))),'seconds_below_minus50_before_ending':float(sum(e[:cutoff]<10**(-50/20))/10)}
 if name=='live_curve':
  first=next(b for b in blocks if b['phase']=='anticipation' and b['amount']>0)
  measured['first_rendered_route_t']=first['callback_wall']-first['replay_origin_wall'];measured['rendered_lead_seconds']=141.531554781-measured['first_rendered_route_t'];measured['first_dac_delay']=first['dac_delay']
 if (p/'ending.json').exists():
  measured['ending']=json.loads((p/'ending.json').read_text())
  end_s=measured['ending']['audio_frame']/48000
  b=next(b for b in blocks if b['audio_s']>=end_s)
  measured['ending']['rendered_resolution_route_t']=b['callback_wall']-b['replay_origin_wall']
  measured['ending']['estimated_dac_resolution_route_t']=b['callback_wall']+b['dac_delay']-b['replay_origin_wall']
 out[name]=measured
(O/'live_metrics.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
