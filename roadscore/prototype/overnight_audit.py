"""Post-run evidence audit. Never imported by the live runtime."""
import argparse,json
from pathlib import Path

def lines(path):
 return [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
def audit(run):
 run=Path(run);result={'run':str(run)}
 for name in ['launch','host_audio_summary','stored_summary','summary','song_form']:
  p=run/(name+'.json')
  if p.exists():result[name]=json.loads(p.read_text())
 blocks=[b for b in lines(run/'host_audio.jsonl') if 'audio_s' in b];trace=lines(run/'trace.jsonl');jobs=lines(run/'jobs.jsonl')
 if blocks:
  result['stream']={'blocks':len(blocks),'all_physically_muted':all(b.get('presentation_muted',b.get('muted')) for b in blocks),'max_transport_seconds':max(b.get('transport_seconds',0) for b in blocks),'max_host_alignment_seconds':max(abs(b.get('host_lateness_seconds',0)) for b in blocks),'sequence_gaps':sum(b.get('pcm_sequence',i)!=i for i,b in enumerate(blocks)),'capture_audio_seconds':blocks[-1]['audio_s']+.1}
 if trace:
  result['runtime']={'minimum_buffer_seconds':min(x['buffered'] for x in trace),'sections':sorted(set(x.get('section','unknown') for x in trace)),'maximum_replay_delay_seconds':max(x.get('replay_late',0) for x in trace),'all_causal_jobs':all(max(j.get('input_times',{'unused':0}).values())<=j.get('cutoff_ns',0) for j in jobs)}
 form=result.get('song_form',{});decisions=form.get('decisions',[]);events=form.get('waveform_events',[])
 result['fresh_jobs_heard']=sorted(set(e.get('grid',{}).get('job') for e in events if e.get('grid',{}).get('job') is not None))
 result['curve_section_requests']=[x for x in decisions if x.get('type')=='scheduled' and x.get('reason')=='predicted curve']
 result['transition_timing']=[]
 for d in decisions:
  if d.get('type')!='scheduled':continue
  candidates=[e for e in events if e.get('kind')=='section_landing' and e['section']==d['section'] and abs(e['audio_s']-d['at'])<.2]
  if candidates:
   e=candidates[0];result['transition_timing'].append({'section':d['section'],'request':d['requested'],'scheduled':d['at'],'actual':e['audio_s'],'scheduler_error_seconds':e['audio_s']-d['at'],'predicted_road_event_offset_seconds':e['audio_s']-d['desired'],'human_downbeat_verified':False})
 (run/'overnight_audit.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('run');a=p.parse_args();r=audit(a.run);print(json.dumps({k:v for k,v in r.items() if k not in ['summary','song_form']},indent=2))
