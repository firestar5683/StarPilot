"""Offline steering-based event scoring. Fixed definitions across all cached routes."""
import json
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks,savgol_filter
R=Path(__file__).resolve().parents[1];O=R/'results/unattended';out=[]
responses=json.loads((O/'response_summary.json').read_text())['runs'] if (O/'response_summary.json').exists() else {}
for path in sorted(O.glob('*_motion.npz')):
 route=path.name.replace('_motion.npz','');cars=np.load(path)['cars'];rows=json.loads((O/(route+'_detector.json')).read_text())
 # Resample 20Hz, 350ms smoothing; neutral steering offset from lowest-angle moving samples.
 t=np.arange(cars[0,0],cars[-1,0],.05);v=np.interp(t,cars[:,0],cars[:,1]);raw=np.interp(t,cars[:,0],cars[:,2]);moving=raw[v>5];offset=float(np.median(moving[np.abs(moving)<=np.quantile(np.abs(moving),.2)]));steer=savgol_filter(raw-offset,7,2);mag=np.abs(steer)
 peaks,_=find_peaks(mag,prominence=5,height=6,distance=80)
 activations=[r for i,r in enumerate(rows) if r['activation'] is not None and (i==0 or r['activation']!=rows[i-1]['activation']) and r['kind']=='curve']
 for peak in peaks:
  if v[peak]<3:continue
  # Find last sustained low-steering interval before peak (at most 15s). Otherwise ambiguous ongoing curve.
  candidates=[j for j in range(max(6,peak-300),peak) if np.all(mag[j-6:j]<3)]
  onset=t[candidates[-1]] if candidates else None
  if onset is None or t[peak]-onset<.25:continue
  sign=int(np.sign(steer[peak]));early=[r for r in rows if onset-10<=r['t']<=t[peak] and r['candidate_sign']==-sign and r['candidate_strength']>=.8 and abs(r['candidate_peak']-t[peak])<8]
  detection=early[0]['t'] if early else None
  matched=[r for r in activations if onset-10<=r['activation']<=t[peak]+1 and r['candidate_sign']==-sign and abs(r['predicted_peak']-t[peak])<5]
  event=min(matched,key=lambda r:abs(r['predicted_peak']-t[peak])) if matched else None
  activation=event['activation'] if event else None
  # Captures cover portions of routes. Match by command timestamp, not event index.
  captured=[]
  for run,events in responses.items():
   if (route.startswith('00000202') and run in ['live_curve','live_development']) or (route.startswith('00000201') and run=='other_route') or (route.startswith('00000203') and run=='live_arrival'):
    captured += [(run,e) for e in events if activation is not None and abs(e['command_t']-activation)<.2]
  run,e=captured[0] if captured else (None,{})
  row={'route':route,'steering_onset':float(onset),'steering_peak':float(t[peak]),'steering_peak_deg':float(steer[peak]),'speed_at_peak':float(v[peak]),'speed_at_onset':float(np.interp(onset,t,v)),'class':'sharp' if mag[peak]>=30 else 'gentle','predicted_detection':detection,'activation':activation,'persistence_start':event['since'] if event else None,'command':e.get('command_t'),'first_buffer':e.get('first_buffer_t'),'measurable':e.get('measurable_1percent'),'meaningful_proxy':e.get('meaningful_10percent_300ms'),'strong_proxy':e.get('meaningful_20percent_300ms'),'capture':run,'ambiguous_onset':bool(t[peak]-onset>10)}
  row['leads']={k:None if row[k] is None else float(onset-row[k]) for k in ['predicted_detection','activation','command','first_buffer','measurable','meaningful_proxy','strong_proxy']};out.append(row)
(O/'curve_timing.json').write_text(json.dumps({'definition':'Steering proxy only, not geometric curvature or visually verified entry. 20Hz interpolation, 350ms Savitzky-Golay smoothing; onset after last 300ms below 3deg relative neutral offset, within15s of a >=6deg peak with >=5deg prominence. Speed at peak>=3m/s. Recorded model yaw and steering have opposite sign; matching uses negative steering sign. Long (>10s) onset-to-peak intervals are flagged ambiguous. Independent offline labels; never runtime inputs. Prediction matching is approximate within5s of steering peak. Missing means not demonstrated, not zero latency.','events':out},indent=2))
for r in out:print(r['route'][:8],round(r['steering_onset'],2),round(r['steering_peak'],2),r['class'],{k:None if v is None else round(v,2) for k,v in r['leads'].items()})
