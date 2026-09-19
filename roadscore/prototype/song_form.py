"""Small causal form planner. It schedules pre-generated material, never future road data."""
import math
class SongForm:
 def __init__(self,bpm=138):
  self.period=60/bpm;self.grid_origin=0.;self.section='verse';self.start=0.;self.next=None;self.last_major=-1e9;self.last_activation=None;self.major_count=0;self.revision=0;self.events=[];self.preparation=None
 def boundary(self,t):return self.grid_origin+math.ceil((t-self.grid_origin)/(4*self.period))*(4*self.period)
 def update(self,t,road,arrival=False,nav_approach=False):
  landed=None
  if self.preparation and t>=self.preparation["at"]:
   self.section="prechorus";self.start=self.preparation["at"];self.events.append({"type":"landed",**self.preparation});self.preparation=None
  if self.next and t>=self.next['at']:
   self.section=self.next['section'];self.start=self.next['at'];landed=self.next;self.events.append({'type':'landed',**landed});self.next=None;self.revision+=1
  if arrival:
   self.preparation=None
   if self.section!='outro' and (not self.next or self.next['section']!='outro'):self.schedule('outro',t,t,'arrival')
   return landed
  if self.section=='outro':return landed
  activation=road.get('activation');lead=road.get('lead') or 0
  major=road.get('kind')=='curve' and road.get('phase')=='anticipation' and (road.get('strength',0)>=1.2 or abs(road.get('predicted_turn_radians',0))>=.35) and lead>=3
  if major and activation!=self.last_activation and t-self.last_major>=24 and t-self.start>=8:
   self.last_activation=activation;self.last_major=t;self.major_count+=1
   target='bridge' if self.major_count%2==0 else 'chorus'
   self.schedule(target,t,t+max(0,lead),'predicted curve')
  elif not self.next and nav_approach and self.section=='verse' and t-self.start>=32:self.schedule('chorus',t,t+4,'navigation approach')
  elif not self.next and self.section in ['chorus','bridge'] and t-self.start>=32:self.schedule('verse',t,t,'post-event release')
  return landed
 def schedule(self,section,requested,desired,reason):
  at=self.boundary(max(requested+.1,desired));self.next={'section':section,'requested':requested,'desired':desired,'at':at,'reason':reason,'bar_offset_seconds':at-desired,'bpm':60/self.period};self.events.append({'type':'scheduled',**self.next})
  prep_at=self.grid_origin+math.ceil((requested+.1-self.grid_origin)/self.period)*self.period
  if reason=='predicted curve' and prep_at<at-.5:
   self.preparation={'section':'prechorus','at':prep_at,'requested':requested,'reason':'curve preparation'}
 def snapshot(self):return {'section':self.section.upper(),'next_section':self.next['section'].upper() if self.next else None,'section_start':self.start,'scheduled':self.next,'revision':self.revision,'prechorus_intent':self.next is not None and self.next['reason']=='predicted curve'}
