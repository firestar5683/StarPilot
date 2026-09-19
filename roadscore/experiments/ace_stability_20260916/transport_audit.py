"""Separate packet delivery delay, bench export delay, and host callback failures."""
import json,sys
from pathlib import Path
import numpy as np
p=Path(sys.argv[1]);out=Path(sys.argv[2]);h=json.loads((p/'host_audio_summary.json').read_text())
packets=[json.loads(x) for x in (p/'transport_packets.jsonl').read_text().splitlines()]
origin=json.loads((p/'replay_origin.json').read_text());offset=json.loads((p/'clock_sync.json').read_text())['best']['bench_minus_host_seconds']
requests=[json.loads(x) for x in (p/'jobs.jsonl').read_text().splitlines()];summary=json.loads((p/'summary.json').read_text());jobs={j['id']:j for j in summary['generation']}
intervals=[(j['route_t'],j['route_t']+jobs[j['id']]['seconds']) for j in requests if j['id'] in jobs]
def during(row):
 t=row['callback_wall']-offset-origin['host_received_wall'];return any(a<=t<=b for a,b in intervals)
def stats(values):
 a=np.asarray(values);return {'count':len(a),'p50':float(np.quantile(a,.5)) if len(a) else None,'p99':float(np.quantile(a,.99)) if len(a) else None,'max':float(max(a)) if len(a) else None}
report={'source':str(p),'all_packets_logged':len(packets),'host':h,'transport':stats([r['transport_seconds'] for r in packets]),'bench_export_delay':stats([r['export_wall']-r['callback_wall'] for r in packets]),'receive_gap':stats([r['receive_gap_seconds'] for r in packets]),'transport_during_generation':stats([r['transport_seconds'] for r in packets if during(r)]),'transport_outside_generation':stats([r['transport_seconds'] for r in packets if not during(r)]),'worst_packets':sorted(packets,key=lambda r:r['transport_seconds'],reverse=True)[:12],'generation_overlap_scope':'Approximate wall interval from causal request route time plus measured job time; association does not establish causation.'}
out.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='worst_packets'},indent=2))
