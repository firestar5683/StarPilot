"""Post-run bounded-buffer audit. Never imported into replay or generation."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'results/ace_demo_20260916'
def audit(rows):
 buffer=112.;events=[];stopped=False;estimate=30.;measured_previous=112.
 for index,row in enumerate(rows):
  if index==0:continue # Initial preparation is before playback.
  buffer=min(buffer,90.);start=buffer;attempts=[]
  measured_cost=measured_previous-row.get('buffer_equivalent_before_commit',measured_previous)
  overhead=max(0.,measured_cost-sum(a['wall_seconds'] for a in row.get('quality_attempts',[])));buffer-=overhead
  measured_previous=row.get('buffer_equivalent_after_commit',row.get('buffer_equivalent_before_commit',measured_previous))
  for attempt in row.get('quality_attempts',[]):
   allowed=buffer>=estimate+10.
   attempts.append({'seed':attempt['seed'],'buffer_before':buffer,'would_start':allowed,'wall_seconds':attempt['wall_seconds'],'accepted':attempt['quality']['accepted']})
   if not allowed:stopped=True;break
   buffer-=attempt['wall_seconds']
   if not attempt.get('runtime',{}).get('cold'):estimate=max(30.,attempt['wall_seconds']*1.2)
  if not stopped and row.get('quality_accepted'):buffer+=row['new_seconds']
  events.append({'section':index,'start_buffer':start,'end_buffer':buffer,'attempts':attempts,'accepted':bool(row.get('quality_accepted')) and not stopped})
  if stopped or not row.get('quality_accepted') or buffer<10:break
 return {'method':'post-run conservative90s request ceiling and30s estimate plus10s danger margin; not a live playback run','events':events,'all_measured_sections_fit_budget':len(events)==len(rows)-1 and not stopped and all(e['accepted'] and e['end_buffer']>=10 for e in events),'minimum_after_job':min([a['buffer_before']-a['wall_seconds'] for e in events for a in e['attempts'] if a['would_start']] or [0])}
if __name__=='__main__':
 result=json.loads((O/'soak_result.json').read_text());out=audit(result['rows']);(O/'soak_buffer_audit.json').write_text(json.dumps(out,indent=2));print(out['all_measured_sections_fit_budget'],out['minimum_after_job'])
