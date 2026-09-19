"""Small long-horizon prompt policy; local road precision belongs to the gesture layer."""
class CompositionPolicy:
 def __init__(self,extended_buffer=False):
  self.extended_buffer=extended_buffer;self.grammar_index=0
  self.outro_intent=False;self.outro_start=None;self.outro_job=None;self.next_role='verse';self.heard=[];self.planned=[];self.events=[]
 def route_change(self):
  self.outro_intent=False
  # A navigation revision changes future requests, not PCM already heard.
  self.events.append({'type':'navigation_revised','queued_audio_retained':True})
 def choose(self,frame,rate,nav,speed,buffered):
  fresh=bool(nav.get('valid'))
  if fresh and nav.get('remaining',1e9)<(max(600,speed*(buffered+35)) if self.extended_buffer else 600) and nav.get('eta',1e9)<(buffered+35 if self.extended_buffer else 65):self.outro_intent=True
  if self.outro_intent:return 'closing'
  horizon=nav.get('distance',1e9)/max(speed,.1)
  if fresh and speed>3 and buffered+5<horizon<(buffered+60 if self.extended_buffer else 90):
   return 'approach' if self.next_role in ('verse','outro') else 'bridge_transition'
  if self.extended_buffer:return ['verse','prechorus','chorus','verse','bridge','chorus'][self.grammar_index%6]
  return 'base'
 def generated(self,meta,play_at):
  role={'closing':'outro','approach':'chorus','bridge_transition':'bridge','base':'verse'}.get(meta.get('conditioning'),meta.get('conditioning') if meta.get('conditioning') in ('verse','prechorus','chorus','bridge','outro') else 'continuation')
  if self.extended_buffer:self.grammar_index+=1
  self.next_role=role;event={'job':meta['id'],'role_intent':role,'play_at_audio_s':play_at,'conditioning':meta.get('conditioning'),'human_section_verified':False}
  self.planned.append(event);self.events.append({'type':'queued',**event})
  if role=='outro' and self.outro_start is None:self.outro_start=play_at;self.outro_job=meta['id']
 def update(self,audio_s):
  while self.planned and self.planned[0]['play_at_audio_s']<=audio_s:
   e=self.planned.pop(0);self.heard.append(e);self.events.append({'type':'source_heard',**e})
 def snapshot(self,audio_s):
  role=self.heard[-1]['role_intent'] if self.heard else 'verse'
  active_outro=[]
  for event in reversed(self.heard):
   if event['role_intent']!='outro':break
   active_outro.append(event)
  start=active_outro[-1]['play_at_audio_s'] if active_outro else None
  return {'section':role.upper()+' / CONTINUOUS','next_section':self.planned[0]['role_intent'].upper() if self.planned else None,'outro_intent':self.outro_intent,'outro_heard_seconds':max(0.,audio_s-start) if start is not None else 0.,'outro_job':active_outro[-1]['job'] if active_outro else None,'form_labels_are_intent':True}
