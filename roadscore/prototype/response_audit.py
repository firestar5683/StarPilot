"""Counterfactual DSP audit of captured causal states; not a perceptual listening claim."""
import argparse,json
from pathlib import Path
import numpy as np,soundfile as sf
from driving_music import DrivingDSP
from event_music import EventDSP
from phrase import pulse
p=argparse.ArgumentParser();p.add_argument('--enhanced',action='store_true');p.add_argument('--root',default='/data/roadscore');a=p.parse_args();R=Path(a.root);O=R/'results/unattended';out={}
source,sr=sf.read(R/'assets/source_horizon_drive.wav');pi=pulse(source[:236*4096],sr)
for name in ['live_curve','live_development','other_route','live_arrival']:
 folder=R/'results/dense'/name
 if not (folder/'dry.wav').exists():continue
 wave,sr=sf.read(folder/'dry.wav',dtype='float32',always_2d=True);blocks=[json.loads(x) for x in (folder/'audio_blocks.jsonl').read_text().splitlines()]
 cls=EventDSP if a.enhanced else DrivingDSP;wet=cls(sr,pi['bpm']);neutral=cls(sr,pi['bpm']);rows=[]
 for b in blocks:
  k=round(b['audio_s']*sr);chunk=wave[k:k+round(.1*sr)]
  if len(chunk)!=round(.1*sr):break
  wet.event_state={'phase':b['phase'],'strength':b.get('strength',0),'kind':b.get('kind','slowdown' if b['amount']<0 else 'curve')};neutral.event_state={'phase':'neutral','strength':0}
  x=wet.process(chunk,b['amount']);y=neutral.process(chunk,0);res=float(np.sqrt(np.mean((x-y)**2)));ref=float(np.sqrt(np.mean(y*y)))
  rows.append({'audio_s':b['audio_s'],'route_t':b['callback_wall']-b['replay_origin_wall']+b['dac_delay'],'input_t':b['route_t'],'phase':b['phase'],'amount':b['amount'],'residual_rms':res,'neutral_rms':ref,'relative_response':res/max(ref,1e-8),'dac_delay':b['dac_delay']})
 (O/(name+('_enhanced_response.json' if a.enhanced else '_response.json'))).write_text(json.dumps(rows));events=[]
 for i,b in enumerate(rows):
  if b['phase']!='anticipation' or (i and rows[i-1]['phase']=='anticipation'):continue
  end=next((j for j in range(i+1,len(rows)) if rows[j]['phase']=='neutral'),len(rows))
  def crossing(threshold,hold):
   for j in range(i,end-hold+1):
    if all(r['relative_response']>=threshold and r['neutral_rms']>=.003 for r in rows[j:j+hold]):return rows[j]['route_t']
   return None
  events.append({'command_t':b['input_t'],'first_buffer_t':b['route_t'],'measurable_1percent':crossing(.01,1),'meaningful_10percent_300ms':crossing(.1,3),'meaningful_20percent_300ms':crossing(.2,3),'end_t':rows[end-1]['route_t'],'max_relative':max(r['relative_response'] for r in rows[i:end])})
 out[name]=events;print(name,events,flush=True)
(O/('enhanced_response_summary.json' if a.enhanced else 'response_summary.json')).write_text(json.dumps({'definition':'Counterfactual identical source through neutral vs event DSP. Meaningful proxy = residual RMS >=10% of neutral RMS for 300ms, neutral RMS >=0.003. This is NOT measured human audibility. DAC time is PortAudio estimate. Cadence excluded from interpretation.','runs':out},indent=2))
