"""Offline warning A/B with recorded event timing and exactly the archived music."""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
import soundfile as sf
from alert_accent import AlertAccent
from signal_shaker import ShakerGrid
from engagement_presentation import EngagementPresentation,PresentationConfig


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def render(locked,out):
 source=locked/'render/heard.wav';trace=locked/'render/trace.jsonl';timing=locked/'render/audio_blocks.jsonl';audit=locked/'source_alert_audit.private.json'
 paths=(source,trace,timing,audit);hashes={str(p):sha(p) for p in paths}
 rows=[json.loads(x) for x in trace.read_text().splitlines()];blocks=[json.loads(x) for x in timing.read_text().splitlines()]
 events=[e for e in json.loads(audit.read_text())['intervals'] if e['eligible_status_and_size']]
 if not events:raise ValueError('No recorded meaningful alert for comparison')
 out.mkdir(parents=True,exist_ok=False);info=sf.info(source);rate=info.samplerate
 accent=AlertAccent(ShakerGrid(128,0,0,0,False,'not yet observed'),rate,True)
 delta_filter=EngagementPresentation(rate);config=PresentationConfig(enabled=True)
 index=-1;observations=[];times=[]
 with sf.SoundFile(source) as src,sf.SoundFile(out/'full_alert.wav','w',samplerate=rate,channels=2,subtype='FLOAT') as dst:
  for i,block in enumerate(blocks):
   start=round(block['audio_s']*rate);end=round(blocks[i+1]['audio_s']*rate) if i+1<len(blocks) else info.frames
   pcm=src.read(end-start,dtype='float32',always_2d=True)
   while index+1<len(rows) and rows[index+1]['command_wall']<=block['callback_wall']:index+=1
   row=rows[index] if index>=0 else {};route_t=row.get('route_t',-1)
   grid=row.get('signal_shaker',{}).get('grid')
   if grid:accent.grid=ShakerGrid(**grid)
   event=next((e for e in events if e['start_demo_s']<=route_t<=e['start_demo_s']+e['duration_observed_s']),None)
   fresh=bool(block.get('engagement_fresh') and row and 0<=block['callback_wall']-row['command_wall']<=1.)
   competing=bool(row.get('signal_shaker',{}).get('sequence_active') or row.get('core_apex',{}).get('rendered_active'))
   before=time.perf_counter();wet=accent.process(pcm,start,str(event['key']) if event else None,event is not None,fresh,competing)
   # Baseline already contains engagement processing. Filter only the new delta;
   # this approximates placement before that stage without filtering music twice.
   delta=delta_filter.process(wet-pcm,bool(block.get('engagement_active')),config)
   y=pcm+delta;times.append(time.perf_counter()-before);dst.write(y)
   observations.append(dict(audio_s=block['audio_s'],route_t=route_t,meaningful=event is not None,competing=competing,**accent.snapshot()))
 first=next(x for x in observations if x['rendered_active']);start=max(0.,first['audio_s']-8);duration=min(24.,info.duration-start)
 for name,path in [('A_baseline.wav',source),('B_alert.wav',out/'full_alert.wav')]:
  with sf.SoundFile(path) as handle:
   handle.seek(round(start*rate));wave=handle.read(round(duration*rate),dtype='float32',always_2d=True)
  sf.write(out/name,wave,rate,subtype='FLOAT')
 if hashes!={str(p):sha(p) for p in paths}:raise RuntimeError('Protected input changed')
 report=dict(source_sha256=hashes,source_unchanged=True,excerpt_start_audio_s=start,duration_seconds=duration,events=accent.events,
             approximation='New alert delta passed through reconstructed engagement filter; archived prior shaker/apex remains. Native priority ordering can differ. Same generated PCM, no normalization.',
             runtime_cost='Mac offline only',median_ms=float(np.median(times)*1000),p95_ms=float(np.quantile(times,.95)*1000))
 (out/'report.json').write_text(json.dumps(report,indent=2));(out/'alert_states.json').write_text(json.dumps(observations))
 (out/'index.html').write_text('<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Warning fill A/B</title><style>body{background:#101016;color:#eee;font:18px system-ui;max-width:760px;margin:40px auto;padding:20px}audio{width:100%}</style><h1>Warning fill A/B</h1><p>Same archived music and recorded warning. B adds one beat-locked percussion fill with a brief gentle duck. Existing archived cues remain; live priority will make them yield. This is an offline approximation, not a new hardware recording.</p><h2>A · Baseline</h2><audio controls src="A_baseline.wav"></audio><h2>B · Warning fill</h2><audio controls src="B_alert.wav"></audio>')
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('locked',type=Path);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(render(a.locked,a.output),indent=2))
