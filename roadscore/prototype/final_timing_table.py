"""Join final measured audio delivery with independent completed-route steering labels."""
import os
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'results/unattended';labels=json.loads((O/'curve_timing.json').read_text())['events'];out=[]
for name,route in [('native_final',os.environ['ROADSCORE_CURVE_ROUTE'].split('/')[-1]),('native_final_arrival',os.environ['ROADSCORE_ARRIVAL_ROUTE'].split('/')[-1])]:
 p=O/name;timing=json.loads((p/'synchronized_timing.json').read_text());offset=timing['route_offset'];trace=[json.loads(x) for x in (p/'trace.jsonl').read_text().splitlines()]
 for event in timing['events']:
  active=[r for r in trace if r.get('activation') is not None and abs(r['activation']+offset-event['activation'])<.001]
  if not active:continue
  predicted=next((r['predicted_peak']+offset for r in reversed(active) if r['predicted_peak'] is not None),None);sign=active[0]['detector']['candidate_sign']
  matches=[r for r in labels if r['route']==route and not r['ambiguous_onset'] and r['steering_peak_deg']*sign<0 and abs(r['steering_peak']-predicted)<5]
  label=min(matches,key=lambda r:abs(r['steering_peak']-predicted)) if matches else None
  candidates=[r for r in trace if event['activation']-10<=r['route_t']+offset<=event['activation'] and r.get('detector') and r['detector']['candidate_kind']=='curve' and r['detector']['candidate_strength']>=.6 and r['detector']['candidate_sign']==sign]
  row={'capture':name,'route':route,'first_prediction':candidates[0]['route_t']+offset if candidates else None,**event,'predicted_peak':predicted,'steering_onset':None if label is None else label['steering_onset'],'steering_peak':None if label is None else label['steering_peak'],'speed_at_onset':None if label is None else label['speed_at_onset']}
  row['lead_to_steering']={k:None if label is None or row[k] is None else label['steering_onset']-row[k] for k in ['first_prediction','qualified_since','activation','command_source_t','first_output','measurable','proxy10','proxy20']};out.append(row)
(O/'final_timing_table.json').write_text(json.dumps({'definition':'Final actual live captures; offline steering-label match by sign and within5s of tracked predicted peak. Unmatched events remain visible. Qualification start is not activation. Raw first prediction may be transient. All labels are evaluation-only.','events':out},indent=2))
for r in out:print(r['route'][:8],round(r['activation'],2),'onset',r['steering_onset'],'20% lead',r['lead_to_steering']['proxy20'])
