"""Post-run steering proxy for form timing. No manual route events; never runtime input."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks,savgol_filter
p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();rows=[json.loads(s) for s in (a.run/'trace.jsonl').read_text().splitlines()];form=json.loads((a.run/'song_form.json').read_text());times=np.array([x['elapsed'] for x in rows]);t=np.arange(times[0],times[-1],.05);v=np.interp(t,times,[r['speed'] for r in rows]);raw=np.interp(t,times,[r['steering'] for r in rows]);moving=raw[v>5];offset=float(np.median(moving[np.abs(moving)<=np.quantile(abs(moving),.2)])) if len(moving) else 0;steer=savgol_filter(raw-offset,7,2);mag=abs(steer);peaks,_=find_peaks(mag,prominence=5,height=6,distance=80);events=[]
for d in form['decisions']:
 if d.get('type')!='scheduled' or d.get('reason')!='predicted curve':continue
 matches=[i for i in peaks if v[i]>=3 and abs(t[i]-d['desired'])<5]
 if not matches:events.append({**d,'steering_proxy_match':False});continue
 peak=min(matches,key=lambda i:abs(t[i]-d['desired']));quiet=[i for i in range(max(6,peak-300),peak) if np.all(mag[i-6:i]<3)];onset=float(t[quiet[-1]]) if quiet else None
 prep=[e for e in form['waveform_events'] if e.get('kind')=='section_landing' and e['section']=='prechorus' and d['requested']<=e['audio_s']<=d['at']]
 landing=[e for e in form['waveform_events'] if e.get('kind')=='section_landing' and e['section']==d['section'] and abs(e['audio_s']-d['at'])<.2]
 events.append({**d,'steering_proxy_match':True,'steering_onset':onset,'steering_peak':float(t[peak]),'ambiguous_onset':bool(onset is None or t[peak]-onset>10),'requested_lead_to_steering':None if onset is None else onset-d['requested'],'prechorus_audio_start':prep[0]['audio_s'] if prep else None,'prechorus_lead_to_steering':onset-prep[0]['audio_s'] if prep and onset is not None else None,'actual_landing':landing[0]['audio_s'] if landing else None})
result={'method':'Steering proxy, not visual road-entry truth: same 20Hz/350ms smoothing, 3-degree quiet onset, 6-degree peaks and 5-degree prominence across routes. Audio elapsed clock; no labels feed runtime.','events':events};(a.run/'form_curve_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
