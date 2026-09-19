"""Post-run evidence only. Never imported by the live RoadScore process."""
import os
import json,statistics
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'results/composition_20260916'
def audit(score,ui=None):
 s=json.loads((score/'summary.json').read_text());g=json.loads((score/'gestures.json').read_text());events=g['events'];started=[e for e in events if e['type']=='started'];scheduled={e['id']:e for e in events if e['type']=='scheduled'}
 signal=[e for e in started if e['kind']=='turn_signal' and e['requested_frame']+48000*.5>=e['actual_frame']]
 kinds={k:sum(e['kind']==k for e in started) for k in sorted({e['kind'] for e in started})};jobs=s['generation'];rows={'run':score.name,'audio_seconds':s['audio_seconds'],'fallbacks':s['fallbacks'],'renderer_underflows':s['underflows'],'fresh_jobs':len(jobs),'median_generation_seconds':statistics.median(j['seconds'] for j in jobs),'median_unique_rtf':statistics.median(j['seconds']/j['usable_new_seconds'] for j in jobs),'gesture_starts':kinds,'max_gesture_scheduling_lateness_samples':max((e['lateness_frames'] for e in started),default=0),'turn_signal_queue_wait_ms_max':max(((e['actual_frame']-e['requested_frame'])/48 for e in signal),default=None),'timing_scope':'sample scheduling only; add input polling and output buffering for physical response','curve_payoffs':[{'request_audio_s':e['requested_frame']/48000,'heard_audio_s':e['actual_frame']/48000,'input_ns':e['input_ns']} for e in started if e['kind']=='curve_apex']}
 if ui and ui.exists():rows['normal_ui_final']=json.loads(ui.read_text().splitlines()[-1])
 if (score/'host_audio_summary.json').exists():rows['host_audio']=json.loads((score/'host_audio_summary.json').read_text())
 if (score/'ending.json').exists():rows['ending']=json.loads((score/'ending.json').read_text())
 return rows
scores=[(R/'routes'/os.environ['ROADSCORE_ARRIVAL_ROUTE']/'roadscore/normal_1789575069',None),(R/'routes'/os.environ['ROADSCORE_CURVE_ROUTE']/'roadscore/normal_1789575654',O/'native_curve/ui_audit.jsonl')]
rows=[audit(*p) for p in scores];(O/'native_regressions.json').write_text(json.dumps(rows,indent=2));print(json.dumps([{k:v for k,v in r.items() if k not in ('curve_payoffs','ending','normal_ui_final')} for r in rows],indent=2))
