"""Correlate captured callback deadlines with observed Python GC pauses."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args();rows=[json.loads(x) for x in (a.capture/'audio_blocks.jsonl').read_text().splitlines()];gc=json.loads((a.capture/'gc_events.json').read_text());gaps=[]
for i,b in enumerate(rows):
 if not i:continue
 previous=rows[i-1]['callback_wall'];dt=b['callback_wall']-previous
 if dt>.14 or b.get('portaudio_status'):
  matches=[x for x in gc if x['start'] is not None and x['start']<b['callback_wall'] and x['end']>previous];gaps.append({'audio_s':b['audio_s'],'interval':dt,'status':b.get('portaudio_status'),'gc_overlaps':[{'generation':g['generation'],'seconds':g['end']-g['start']} for g in matches]})
report={'gc_count':len(gc),'maximum_gc_seconds':max([x['end']-x['start'] for x in gc if x['start'] is not None] or [0]),'late_callbacks':gaps};(a.capture/'gc_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
