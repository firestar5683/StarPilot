"""Synthetic explanatory examples, separate from causal recorded-route acceptance."""
import os
import sys,json
from pathlib import Path
import numpy as np,soundfile as sf
from scipy.signal import resample_poly
R=Path(__file__).resolve().parents[2];O=R/'results/composition_20260916';sys.path.insert(0,str(R/'prototype'))
from musical_gestures import MusicalGestures
from bar_grid import grid
from phrase import pulse
G=O/'gestures';G.mkdir(exist_ok=True)
source,sr=sf.read(O/'sa3/identity.wav',dtype='float32',always_2d=True)
if sr!=48000:source=resample_poly(source,48000,sr).astype(np.float32)
p=pulse(source,48000);beat=grid(source,48000,p['bpm']);g=MusicalGestures(source,48000,beat['bpm'],beat['beat_phase']);wet=[]
for frame in range(0,len(source),4800):
 t=frame/48000
 road={'kind':'curve','phase':'anticipation','activation':8,'lead':14-t} if 8<=t<12 else {}
 nav={'valid':True,'type':'turn','modifier':'right','revision':1,'distance':30} if 18<=t<19 else {}
 g.update(frame,left=2<=t<6,road=road,nav=nav,speed=12,outro=t>=24,input_ns=round(t*1e9))
 wet.append(g.render(source[frame:frame+4800]))
sf.write(G/'dry.wav',source,48000,subtype='PCM_16');sf.write(G/'with_gestures.wav',np.concatenate(wet),48000,subtype='PCM_16')
for name in g.phrases:sf.write(G/(name+'.wav'),g.phrases[name],48000,subtype='PCM_16')
started=[e for e in g.events if e['type']=='started'];signal=next(e for e in started if e['kind']=='turn_signal')
report={'timeline_kind':'synthetic explanatory example, not a recorded route','events':g.events,'grid':beat,'turn_signal_input_seconds':2,'first_signal_seconds':signal['actual_frame']/48000,'first_signal_latency_ms':1000*(signal['actual_frame']/48000-2),'max_scheduling_lateness_samples':max(e['lateness_frames'] for e in started),'peak':float(abs(np.concatenate(wet)).max()),'source':'fresh Chestnut SA3 kpop_control identity','new_tonal_pitches':False,'human_musical_acceptance':'pending'}
(G/'evidence.json').write_text(json.dumps(report,indent=2))
# Preserve original arrival evidence unchanged. This excerpt is a listening derivative.
a=R/'routes'/os.environ['ROADSCORE_ARRIVAL_ROUTE']/'roadscore/normal_1789575069'
x,sr=sf.read(a/'score.flac',start=195*48000,dtype='float32');sf.write(O/'arrival_excerpt.wav',x,sr,subtype='PCM_16')
e=json.loads((a/'ending.json').read_text());c=json.loads((a/'composition.json').read_text());outros=[v for v in c['events'] if v['type']=='source_heard' and v['role_intent']=='outro']
(O/'arrival_audit.json').write_text(json.dumps({'run':a.name,'first_outro_audio_seconds':outros[0]['play_at_audio_s'],'cadence_trigger_audio_seconds':e['trigger_audio_frame']/48000,'outro_conditioned_seconds_before_trigger':e['trigger_audio_frame']/48000-outros[0]['play_at_audio_s'],'original_counter_bug':'navigation clearing reset the old counter; original archive retained. Fixed in subsequent implementation.','subjective_outro_pass':None},indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ('events','grid')},indent=2))
