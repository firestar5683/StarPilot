"""Objective boundary regression for the controlled long-form candidates."""
import json
from pathlib import Path
import numpy as np,soundfile as sf
from phrase import pulse
R=Path(__file__).resolve().parents[1];O=R/'results/unattended';out={}
for key in ['ignition_fixed','ignition_moving','ignition_arc_fixed','ignition_arc_fixed_anchor0','ignition_arc_fixed_anchor22','nightshift_fixed','brassline_fixed']:
 folder=O/key
 if not (folder/'long.wav').exists():continue
 a,sr=sf.read(folder/'long.wav',always_2d=True);jobs=json.loads((folder/'jobs.json').read_text());rows=[]
 for j in jobs:
  t=j['new_material_audio_s'];k=round(t*sr);before=a[max(0,k-8*sr):k];after=a[k:min(len(a),k+8*sr)];lo=a[max(0,k-sr):min(len(a),k+sr)];n=round(.01*sr);r=np.sqrt(np.mean(lo[:len(lo)//n*n].reshape(-1,n,2)**2,axis=(1,2)))
  x=pulse(before,sr);y=pulse(after,sr);rows.append({'new_material_seconds':t,'sample_jump':float(np.max(abs(a[k]-a[k-1]))),'min_10ms_rms':float(r.min()),'max_10ms_rms':float(r.max()),'pulse_before':x,'pulse_after':y,'apparent_period_change_percent':100*(y['period']/x['period']-1)})
 out[key]={'boundaries':rows,'note':'Pulse estimates on short polyphonic windows can lock onto different subdivisions; apparent period changes are listening flags, not measured beat discontinuity.'}
(O/'development_boundaries.json').write_text(json.dumps(out,indent=2))
for key,d in out.items():print(key,[(round(r['new_material_seconds'],1),round(r['sample_jump'],4),round(r['min_10ms_rms'],4),round(r['apparent_period_change_percent'],1)) for r in d['boundaries']])
