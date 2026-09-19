"""Post-run evidence only; never an input to the composer or replay."""
import json,sys,collections
from pathlib import Path

def read(p,default=None):return json.loads(p.read_text()) if p.exists() else default

def lines(p):return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

def audit(p):
 s=read(p/'summary.json',{});h=read(p/'host_audio_summary.json',{});launch=read(p/'launch.json',{});jobs=s.get('generation',[]);trace=lines(p/'trace.jsonl');requests=lines(p/'jobs.jsonl');ui=lines(p/'ui_audit.jsonl');blocks=[x for x in lines(p/'host_audio.jsonl') if 'audio_s' in x];g=read(p/'gestures.json',{})
 result={'run':str(p),'launch':launch,'audio_seconds':s.get('audio_seconds'),'completed_jobs':len(jobs),'generation_seconds':[j.get('seconds') for j in jobs],'rtf_per_new_audio':[j['seconds']/j['new_seconds'] for j in jobs if 'seconds' in j and j.get('new_seconds')],'generation_errors':[j for j in jobs if j.get('error')],'minimum_buffer_seconds':min([x['buffered'] for x in trace] or [0]),'fallbacks':s.get('fallbacks'),'underflows':s.get('underflows'),'worker_failed':any(x.get('worker_failed') for x in trace),'host_audio':h,'all_blocks_muted':bool(blocks) and all(x.get('muted') and x.get('presentation_muted',True) for x in blocks),'input_time_violations':sum(any(v>r['cutoff_ns'] for v in r['input_times'].values()) for r in requests),'request_roles':dict(collections.Counter(r['conditioning'] for r in requests)),'navigation_present':any(x.get('nav',{}).get('valid') for x in trace),'curve_activations':len({x['activation'] for x in trace if x.get('kind')=='curve' and x.get('activation') is not None}),'ui_last':ui[-1] if ui else None,'ending':read(p/'ending.json'),'composition':read(p/'composition.json'),'gestures':g,'runtime_manifest':read(p/'runtime_manifest.json')}
 result['quality_rejected_jobs']=sum(bool(j.get('quality_rejected')) for j in jobs)
 result['quality_rejections']=sum(j.get('quality_rejections',0) for j in jobs)
 result['rerolls']=sum(j.get('rerolls',0) for j in jobs)
 result['accepted_jobs']=sum(j.get('quality_accepted',not j.get('error')) for j in jobs)
 result['safe_extensions']=s.get('safe_extensions',[])
 result['instrumented_pass']=bool(jobs) and not (result['generation_errors'] or result['fallbacks'] or result['underflows'] or result['worker_failed'] or result['input_time_violations'] or any(h.get(k,0) for k in ['late_frames','starved_callbacks','portaudio_flags'])) and result['all_blocks_muted']
 return result
if __name__=='__main__':
 p=Path(sys.argv[1]);r=audit(p);out=Path(sys.argv[2]);out.write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in ['composition','gestures','runtime_manifest']},indent=2))
