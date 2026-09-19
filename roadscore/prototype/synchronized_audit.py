"""Host/bench-clock-aware evaluation of native replay captures. Offline only."""
import argparse,json
from pathlib import Path
import numpy as np,soundfile as sf
from scipy.signal import resample_poly
from event_music import EventDSP
from phrase import pulse
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('host',type=Path);p.add_argument('--original-origin',type=int,required=True);a=p.parse_args();R=Path(__file__).resolve().parents[1];cap=a.capture
sync=json.loads((a.host/'clock_sync.json').read_text())['best'];delta=sync['bench_minus_host_seconds'];unc=sync['uncertainty_seconds'];drift_bound=0.;post_check='not measured'
if (a.host/'clock_sync_after.json').exists():
 after=json.loads((a.host/'clock_sync_after.json').read_text())['best'];shift=abs(after['bench_minus_host_seconds']-delta)
 if shift<.25:drift_bound=shift+after['uncertainty_seconds'];post_check='consistent post-run clock sample'
 else:post_check='Late post-run offset discontinuity; sample excluded. In-run delivery timestamps are continuous.'
unc+=drift_bound
delivery=[json.loads(x) for x in (cap/'model_delivery.jsonl').read_text().splitlines()];clock=json.loads((cap/'clock.json').read_text());offset=(clock['origin_ns']-a.original_origin)/1e9;blocks=[json.loads(x) for x in (cap/'audio_blocks.jsonl').read_text().splitlines()];trace=[json.loads(x) for x in (cap/'trace.jsonl').read_text().splitlines()];deliveries={x['mono']:x for x in delivery};rows=[]
latencies=[x['bench_receive_wall']-delta-x['host_send_wall'] for x in delivery]
# Map host wall time to recorded route time from already-published model messages.
host_times=np.array([x['host_send_wall'] for x in delivery]);route_times=np.array([(x['mono']-a.original_origin)/1e9 for x in delivery]);order=np.argsort(host_times);host_times=host_times[order];route_times=route_times[order]
def route_time(wall):
 i=int(np.clip(np.searchsorted(host_times,wall,side='right')-1,0,len(host_times)-1));return float(route_times[i]+wall-host_times[i])
raw,sr=sf.read(cap/'dry.wav',dtype='float32',always_2d=True);source,ssr=sf.read(R/'results/unattended/ignition_seed.wav',dtype='float32',always_2d=True);source=resample_poly(source,48000,ssr).astype(np.float32)[:round(236*4096/44100*48000)];pi=pulse(source,48000);wet=EventDSP(sr,pi['bpm'],'electronic');neutral=EventDSP(sr,pi['bpm'],'electronic');n=sr//10;heard,_=sf.read(cap/'heard.wav',dtype='float32',always_2d=True);errors=[]
for b in blocks:
 k=round(b['audio_s']*sr);x=raw[k:k+n]
 if len(x)!=n:break
 wet.event_state={'phase':b['phase'],'strength':b['strength'],'kind':b['kind']};y=wet.process(x,b['amount']);z=neutral.process(x,0);ref=float(np.sqrt(np.mean(z*z)));res=float(np.sqrt(np.mean((y-z)**2)));host_dac=b['callback_wall']+b['dac_delay']-delta
 if b.get('cadence_entry_audio_s') is None or b['audio_s']<b['cadence_entry_audio_s']-.1:errors.append(float(np.mean((y-heard[k:k+n])**2)))
 rows.append({**b,'source_route_t':b['route_t']+offset,'output_route_t':route_time(host_dac),'response_ratio':res/max(ref,1e-9),'neutral_rms':ref,'command_to_output_seconds':b['callback_wall']+b['dac_delay']-b['command_received_wall']})
events=[]
for i,b in enumerate(rows):
 if b['phase']!='anticipation' or b['kind']!='curve' or (i and rows[i-1]['activation']==b['activation']):continue
 end=next((j for j in range(i+1,len(rows)) if rows[j]['activation']!=b['activation']),len(rows));tr=next((x for x in trace if x['activation']==b['activation']),{})
 event={'activation':b['activation']+offset,'qualified_since':None if tr.get('qualified_since') is None else tr['qualified_since']+offset,'command_source_t':b['source_route_t'],'first_output':b['output_route_t'],'command_to_output_seconds':b['command_to_output_seconds']}
 for th,label in [(.01,'measurable'),(.1,'proxy10'),(.2,'proxy20')]:
  hold=1 if th==.01 else 3;event[label]=next((rows[j]['output_route_t'] for j in range(i,end-hold+1) if all(v['response_ratio']>=th and v['neutral_rms']>=.003 for v in rows[j:j+hold])),None)
 events.append(event)
report={'counterfactual_reconstruction_rms_error':float(np.sqrt(np.mean(errors))),'bpm_used':pi['bpm'],'clock_sync':sync,'network_delay_range_seconds':[float(min(latencies)),float(max(latencies))],'network_delay_median_seconds':float(np.median(latencies)),'output_uncertainty_seconds':unc,'additional_clock_drift_bound_seconds':drift_bound,'post_run_clock_check':post_check,'observed_in_run_offset_floor_change_seconds':float(max(min(x) for x in np.array_split(np.asarray(latencies),6))-min(min(x) for x in np.array_split(np.asarray(latencies),6))),'route_offset':offset,'first_output_route_t':rows[0]['output_route_t'],'events':events,'note':'Output time uses host-published model timestamp mapping plus measured host/bench monotonic offset and PortAudio DAC estimate. Hardware speaker remains muted. Human perceptual thresholds are unverified.'}
(cap/'synchronized_timing.json').write_text(json.dumps(report,indent=2));(cap/'response_blocks.json').write_text(json.dumps(rows));print(json.dumps(report,indent=2))
