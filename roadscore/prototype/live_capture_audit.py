"""Audit normal-replay captures, with original route time reconstructed for evaluation only."""
import json
from pathlib import Path
import numpy as np,soundfile as sf
from event_music import EventDSP
from phrase import pulse
R=Path(__file__).resolve().parents[1];O=R/'results/unattended';out={}
origins={}
for p in (R/'results/dense').glob('*/clock.json'):
 c=json.loads(p.read_text());origins[c['route']]=c['origin_ns']
# The other route reference comes from its original isolated capture too.
for folder in sorted(O.glob('native_*')):
 if not (folder/'summary.json').exists():continue
 s=json.loads((folder/'summary.json').read_text());clock=json.loads((folder/'clock.json').read_text());blocks=[json.loads(x) for x in (folder/'audio_blocks.jsonl').read_text().splitlines()];rows=[json.loads(x) for x in (folder/'trace.jsonl').read_text().splitlines()];route=clock['route'].split('/')[-1]
 origin=origins.get(route);offset=None if origin is None else (clock['origin_ns']-origin)/1e9
 wave,sr=sf.read(folder/'heard.wav',always_2d=True);raw,_=sf.read(folder/'dry.wav',dtype='float32',always_2d=True);n=sr//10;rms=np.sqrt(np.mean(wave[:len(wave)//n*n].reshape(-1,n,2)**2,axis=(1,2)));end=json.loads((folder/'ending.json').read_text()) if (folder/'ending.json').exists() else None;limit=round(end['audio_frame']/n) if end else len(rms)
 info={'seconds':s['audio_seconds'],'jobs':len(s['generation']),'fallbacks':s['fallbacks'],'underflows':s['underflows'],'minimum_buffer':min(x['buffered'] for x in rows),'all_muted':all(x['muted'] for x in blocks),'route_origin_offset_seconds':offset,'max_source_ahead_of_callback':max(x['route_t']-(x['callback_wall']-x['replay_origin_wall']) for x in blocks),'peak':float(abs(wave).max()),'silent_seconds_before_cadence':float(np.sum(rms[:limit]<.0031623)*.1),'ending':end,'generation_seconds':[j['seconds'] for j in s['generation']],'playback_rtf':[j['seconds']/j['playable_new_seconds'] for j in s['generation']],'unique_rtf':[j['seconds']/j['new_seconds'] for j in s['generation']],'host_peak_mib':max([j['host_peak_mib'] for j in s['generation']] or [0]),'tracked_gpu_mib':max([j['tracked_gpu_mib'] for j in s['generation']] or [0])}
 identity=rows[0]['identity'];style={'ignition':'electronic','ignition_arc':'electronic','nightshift':'synthwave','brassline':'groove'}.get(identity,'rock');source,ssr=sf.read(O/'ignition_seed.wav',always_2d=True);pi=pulse(source[:236*4096],ssr);wet=EventDSP(sr,pi['bpm'],style);neutral=EventDSP(sr,pi['bpm'],style);response=[]
 for b in blocks:
  k=round(b['audio_s']*sr);x=raw[k:k+n]
  if len(x)!=n:break
  wet.event_state={'phase':b['phase'],'strength':b.get('strength',0),'kind':b.get('kind','curve')};y=wet.process(x,b['amount']);z=neutral.process(x,0);ref=float(np.sqrt(np.mean(z*z)));res=float(np.sqrt(np.mean((y-z)**2)));response.append({'audio_s':b['audio_s'],'command':b['route_t'],'phase':b['phase'],'kind':b.get('kind','curve'),'activation':b.get('activation'),'dac_estimate':b['callback_wall']-b['replay_origin_wall']+b['dac_delay'],'response_ratio':res/max(ref,1e-9),'rms':ref})
 events=[]
 for i,b in enumerate(response):
  if b['phase']!='anticipation' or b['kind']!='curve' or (i and response[i-1]['activation']==b['activation']):continue
  stop=next((j for j in range(i+1,len(response)) if response[j]['activation']!=b['activation']),len(response));r={'activation':b['activation'],'command':b['command'],'first_dac_estimate':b['dac_estimate']}
  for th,label in [(.01,'measurable'),(.1,'proxy10'),(.2,'proxy20')]:
   hold=1 if th==.01 else 3;r[label]=next((response[j]['dac_estimate'] for j in range(i,stop-hold+1) if all(v['response_ratio']>=th and v['rms']>=.003 for v in response[j:j+hold])),None)
  if offset is not None:r={k:None if v is None else v+offset for k,v in r.items()}
  events.append(r)
 info['curve_response_route_times']=events;out[folder.name]=info;print(folder.name,info['seconds'],info['jobs'],info['minimum_buffer'],info['max_source_ahead_of_callback'],events,flush=True)
(O/'native_metrics.json').write_text(json.dumps(out,indent=2))
