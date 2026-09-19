"""Every-join diagnostics; pulse mismatch estimates are listening flags, not verdicts."""
import json,wave
from pathlib import Path
import numpy as np
from phrase import pulse
from density import density
R=Path(__file__).resolve().parents[1];O=R/'results/dense';out={}
for name in ['stress_baseline','live_development','live_curve','live_arrival']:
 p=O/name
 if not (p/'summary.json').exists():continue
 with wave.open(str(p/'dry.wav')) as f:sr=f.getframerate();a=np.frombuffer(f.readframes(f.getnframes()),'<i2').reshape(-1,2)/32768
 joins=[json.loads(t)['new_material_audio_s'] for t in (p/'boundaries.jsonl').read_text().splitlines()];items=[]
 end=json.loads((p/'ending.json').read_text())['audio_frame']/sr if (p/'ending.json').exists() else len(a)/sr
 points=[(t,'new_material') for t in joins]
 for t in joins:
  anchor_start=t+26.006354166666668-44*4096/44100
  if anchor_start<end:points.append((anchor_start,'suffix_anchor_entry'))
 for t,kind in sorted(points):
  if t>=end:continue
  k=round(t*sr);pre=a[max(0,k-8*sr):k];post=a[k:min(round(end*sr),k+8*sr)]
  if len(post)<sr:continue
  before=pulse(pre,sr);after=pulse(post,sr);item={'t':t,'kind':kind,'pulse_before':before,'pulse_after':after}
  if min(before['confidence'],after['confidence'])>=.25 and abs(before['period']/after['period']-1)<.06:
   period=(before['period']+after['period'])/2;diff=(len(post)/sr+after['next_beat']-before['next_beat'])/period
   item['apparent_phase_displacement_beats']=float(abs((diff+.5)%1-.5))
  region=a[max(0,k-sr):min(len(a),k+sr)];n=sr//100;e=np.sqrt(np.mean(region[:len(region)//n*n].reshape(-1,n,2)**2,axis=(1,2)))
  item['local_rms_db_range_10ms']=[float(20*np.log10(max(e.min(),1e-9))),float(20*np.log10(max(e.max(),1e-9)))];item['density_before']=density(pre,sr);item['density_after']=density(post,sr);items.append(item)
 out[name]={'boundaries':items,'section_density':[{'start':i,'metrics':density(a[i*sr:min((i+20)*sr,round(end*sr))],sr)} for i in range(0,max(0,int(end)-20),26)]}
(O/'boundary_metrics.json').write_text(json.dumps(out,indent=2))
for name,r in out.items():print(name,[(round(x['t'],3),x['kind'],round(x.get('apparent_phase_displacement_beats',-1),3)) for x in r['boundaries']])
