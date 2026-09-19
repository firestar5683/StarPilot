"""Read already-archived musical decisions on the stored score's sample clock."""
import json
class ArchivedMusicState:
 def __init__(self,path,rate=48000):
  self.rate=rate
  def read(name):
   p=path/name;return json.loads(p.read_text()) if p.exists() else {}
  decisions=path/'decisions.jsonl'
  self.decisions=[json.loads(line) for line in decisions.read_text().splitlines()] if decisions.exists() else []
  self.composition=read('composition.json').get('events',[]);self.gestures=read('gestures.json').get('events',[])
 def at(self,t):
  frame=round(t*self.rate);out={}
  decisions=[e for e in self.decisions if e.get('elapsed',float('inf'))<=t]
  if decisions:
   d=decisions[-1];road_t=d.get('route_t',0)+t-d['elapsed']
   out.update(phase=d.get('phase'),kind=d.get('kind'),lead=max(0.,d['predicted_peak']-road_t) if d.get('phase')=='anticipation' and d.get('predicted_peak') is not None else None)
  heard=[e for e in self.composition if e.get('type')=='source_heard' and e['play_at_audio_s']<=t]
  if self.composition:
   out.update(section=(heard[-1]['role_intent'] if heard else 'verse').upper()+' / CONTINUOUS',form_labels_are_intent=True,next_section=None)
  # Queue metadata currently has a play time but no request sample: don't expose
  # a future composition decision merely because it exists in the complete archive.
  cancelled={e['id'] for e in self.gestures if e.get('type')=='cancelled' and e['frame']<=frame}
  stops={e['id']:e['stop_frame'] for e in self.gestures if e.get('type')=='stop_requested'}
  active=[e for e in self.gestures if e.get('type')=='started' and e['actual_frame']<=frame<min(e['actual_frame']+e.get('duration_frames',0),stops.get(e['id'],10**30))]
  queued=[e for e in self.gestures if e.get('type')=='scheduled' and e['requested_frame']<=frame<e['scheduled_frame'] and e['id'] not in cancelled]
  out.update(gesture_active=sorted(set(e['kind'] for e in active)),gesture_queued=[{'kind':e['kind'],'at':e['scheduled_frame']/self.rate} for e in queued[:3]],turn_signal_music=any(e['kind']=='turn_signal' for e in active+queued))
  return out
