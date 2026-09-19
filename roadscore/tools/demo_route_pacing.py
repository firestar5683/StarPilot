"""Read-only narrative window ranking over offline event extraction (no runtime use)."""
import argparse,json,math
from pathlib import Path
import numpy as np
parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);P=parser.parse_args().output
rank=[]
for label in 'ABCDEFGHIJK':
 d=json.loads((P/f'{label}.telemetry.private.json').read_text());e=json.loads((P/f'{label}.events.private.json').read_text())['events'];car=np.array(d['samples']['car'],float)
 curves=[]
 for item in e['curves']:
  if curves and item['direction']==curves[-1]['direction'] and item['start']-curves[-1]['end']<3:
   prev=curves[-1];prev['end']=item['end']
   if item['peak_lateral_proxy']>prev['peak_lateral_proxy']:prev.update(peak_time=item['peak_time'],peak_lateral_proxy=item['peak_lateral_proxy'])
  else:curves.append(item.copy())
 options=[]
 for length in [90,120,60]:
  for start in np.arange(math.ceil(e['observed_start']/5)*5,e['observed_end']-length+.01,5):
   end=start+length
   cv=[v for v in curves if start<v['peak_time']<end];ed=[v for v in e['engagement_edges'] if start+2<v['time']<end-2];sg=[v for v in e['signals'] if start<=v['start']<end];al=[v for v in e['alerts'] if start<v['start']<end]
   firstcue=min([v['start'] for v in cv+sg+al]+[end]);opening=max(0,firstcue-start)
   ix=(car[:,0]>=start)&(car[:,0]<min(start+20,end));moving=float(np.mean(car[ix,1]>3)) if np.any(ix) else 0
   last=(car[:,0]>=end-5)&(car[:,0]<end);stopped=float(np.mean(car[last,1]<.5))>.7 if np.any(last)else False
   stopsecs=sum(max(0,min(v['end'],end)-max(v['start'],start)) for v in e['stops'])
   nav=[r for r in d['samples']['nav']if end-10<r[0]<end and r[1]=='arrive' and r[3]<50];arrival=bool(nav and stopped)
   score=(14 if len(cv)in(1,2)else -10*abs(len(cv)-2))+min(opening,22)*.4+6*moving
   score+=(8 if len(ed)in(1,2)else -5*max(1,len(ed)-2))
   score+=3*min(len(sg),2)-5*max(0,len(sg)-2)-2*max(0,len(al)-3)
   score+=4*any(v['preceding_straight_seconds']>=7 for v in cv)
   score+=4*any(v['active'] and start+3<=v['time']<=start+25 for v in ed)
   score+=5*stopped+8*arrival-max(0,stopsecs-15)*.3
   score-=6*any(v['start']<start<v['end']for v in curves)
   score-=8*any(b['time']-a['time']<5 for a,b in zip(ed,ed[1:]))
   if label in 'BC' or d['decode_warnings']:score-=30
   options.append(dict(label=label,start=float(start),end=float(end),duration=length,score=round(score,2),opening_cue_free_seconds=round(opening,1),first20s_moving_fraction=round(moving,2),curves=cv,engagement=ed,signals=sg,alerts=al,ending_stopped=stopped,arrival_evidence=arrival,standstill_seconds=round(stopsecs,1)))
 options.sort(key=lambda x:x['score'],reverse=True);rank.append(options[0]);(P/f'{label}.pacing.private.json').write_text(json.dumps(options[:15],indent=2))
rank.sort(key=lambda x:x['score'],reverse=True);(P/'pacing_ranking.private.json').write_text(json.dumps(rank,indent=2))
for r in rank:print(r['label'],r['start'],r['end'],'score',r['score'],'opening',r['opening_cue_free_seconds'],'moving',r['first20s_moving_fraction'],'curves',len(r['curves']),'engage',[(round(x['time'],1),x['active'])for x in r['engagement']],'signal',len(r['signals']),'stopped',r['ending_stopped'],'arrival',r['arrival_evidence'])
