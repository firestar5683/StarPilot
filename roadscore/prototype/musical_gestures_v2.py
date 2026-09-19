"""Causal, sample-addressed musical punctuation above the existing final PCM stream."""
import math,threading
import numpy as np
from gesture_bank_v2 import GestureBank
from scipy.signal import lfilter

class MusicalGestures:
 def __init__(self,source,rate=48000,bpm=128,origin=0.):
  self.rate=rate;self.bpm=bpm;self.period=rate*60/bpm;self.origin=origin*rate;self.frames=0
  self.bank=GestureBank(source,rate,bpm);self.phrases={k:self.bank.phrase(k)[0] for k in ['turn_signal','turn_signal_sustain','turn_signal_off','curve_prepare','curve_apex','navigation_turn','lane_change','stop','resume','arrival_prepare','arrival']}
  self.lock=threading.RLock();self.queue=[];self.voices=[];self.events=[];self.counter=0;self.signal=False;self.signal_next=0
  self.last_curve=None;self.nav_token=None;self.nav_last=-1e9;self.last_moving=None;self.last_motion=-1e9;self.arrival=False;self.level=.12;self.last_input_ns=0;self.duck_state=np.zeros(1)
 def beat(self,frame,subdivision=1):
  step=self.period/subdivision
  return round(self.origin+math.ceil((frame-self.origin)/step)*step)
 def schedule(self,kind,frame,requested,input_ns,reason,tag=None):
  frame=max(self.frames,int(frame));self.counter+=1
  event={'id':self.counter,'kind':kind,'scheduled_frame':frame,'requested_frame':int(requested),'input_ns':int(input_ns),'bpm':self.bpm,'grid_origin_frame':self.origin,'reason':reason,'tag':tag,'type':'scheduled','duration_frames':len(self.phrases[kind])}
  self.queue.append({**event,'wave':self.phrases[kind]});self.queue.sort(key=lambda e:e['scheduled_frame']);self.events.append(event)
 def cancel(self,kinds,frame,reason):
  removed=[e for e in self.queue if e['kind'] in kinds]
  self.queue=[e for e in self.queue if e['kind'] not in kinds]
  self.events.extend({'type':'cancelled','id':e['id'],'frame':frame,'reason':reason} for e in removed)
 def update(self,frame,*,left=False,right=False,road=None,nav=None,speed=0.,outro=False,arrived=False,input_ns=0):
  """Inputs are the currently delivered cereal snapshot; no route/history lookup."""
  with self.lock:
   frame=max(int(frame),self.frames);self.last_input_ns=input_ns;road=road or {};nav=nav or {}
   signal=bool(left or right)
   if signal and not self.signal and not arrived:
    first=self.beat(frame+1,4)
    self.schedule('turn_signal',first,frame,input_ns,'turn signal activation','signal')
    self.signal_next=first+round(4*self.period)
   if not signal and self.signal:
    cancelled=[e for e in self.queue if e.get('tag')=='signal'];self.queue=[e for e in self.queue if e.get('tag')!='signal']
    for e in cancelled:self.events.append({'type':'cancelled','id':e['id'],'frame':frame,'reason':'turn signal ended'})
    for voice in self.voices:
     if voice.get('tag')=='signal':
      voice['stop_frame']=frame+round(.02*self.rate);self.events.append({'type':'stop_requested','id':voice['id'],'stop_frame':voice['stop_frame']})
    if not arrived:self.schedule('turn_signal_off',self.beat(frame+1,4),frame,input_ns,'turn signal release','signal_release')
   self.signal=signal
   if signal and not arrived:
    while self.signal_next<frame+self.period:
     self.schedule('turn_signal_sustain',self.signal_next,frame,input_ns,'turn signal sustained','signal');self.signal_next+=round(4*self.period)
   activation=road.get('activation');lead=road.get('lead') or 0.
   if not outro and activation is not None and activation!=self.last_curve and road.get('kind')=='curve' and road.get('phase')=='anticipation' and lead>=1.:
    self.last_curve=activation;apex=self.beat(frame+lead*self.rate)
    prepare=self.beat(max(frame+1,apex-4*self.period),4)
    self.schedule('curve_prepare',prepare,frame,input_ns,'current model-predicted curve')
    self.schedule('curve_apex',apex,frame,input_ns,'current predicted peak; not future steering')
   # Follow revised *current* forecasts until the payoff is one beat away.
   # Never move an already-started sound or read a later recorded sample.
   if not outro and activation==self.last_curve and road.get('phase')=='anticipation' and lead>=1.:
    old=next((e for e in self.queue if e['kind']=='curve_apex'),None)
    target=self.beat(frame+lead*self.rate)
    if old and old['scheduled_frame']-frame>self.period and abs(target-old['scheduled_frame'])>self.period/2:
     self.cancel(('curve_apex',),frame,'current forecast revised')
     self.schedule('curve_apex',target,frame,input_ns,'revised current predicted peak')
   token=(nav.get('type'),nav.get('modifier'),nav.get('revision'))
   near=nav.get('valid',False) and nav.get('type') not in ('arrive',None,'') and speed>3 and 2<nav.get('distance',1e9)/speed<8
   if near and not outro and (token!=self.nav_token or frame-self.nav_last>30*self.rate):
    self.nav_token=token;self.nav_last=frame;self.schedule('navigation_turn',self.beat(frame+1),frame,input_ns,'delivered navigation proximity')
   moving=speed>(1 if self.last_moving is True else 3)
   if self.last_moving is not None and moving!=self.last_moving and frame-self.last_motion>2*self.rate and not outro:
    self.last_motion=frame;self.schedule('resume' if moving else 'stop',self.beat(frame+1),frame,input_ns,'delivered vehicle motion')
   self.last_moving=moving
   if outro and not self.arrival:
    self.arrival=True;self.cancel(('curve_prepare','curve_apex','navigation_turn'),frame,'outro superseded preparation')
    self.schedule('arrival_prepare',self.beat(frame+1),frame,input_ns,'delivered arrival intent')
   if arrived:
    self.cancel(tuple(self.phrases),frame,'arrival cadence');self.signal=False
    for voice in self.voices:
     if 'stop_frame' not in voice:
      voice['stop_frame']=frame+round(.02*self.rate);self.events.append({'type':'stop_requested','id':voice['id'],'stop_frame':voice['stop_frame']})
 def render(self,dry):
  with self.lock:
   n=len(dry);start=self.frames;end=start+n;wet=np.zeros_like(dry)
   while self.queue and self.queue[0]['scheduled_frame']<end:
    e=self.queue.pop(0);actual=max(start,e['scheduled_frame']);self.voices.append({**e,'actual':actual,'offset':0})
    self.events.append({k:v for k,v in {**e,'type':'started','actual_frame':actual,'lateness_frames':actual-e['scheduled_frame']}.items() if k!='wave'})
   keep=[]
   for v in self.voices:
    lo=max(0,v['actual']-start);offset=max(0,start-v['actual']);count=min(n-lo,len(v['wave'])-offset)
    if count<=0:continue
    clip=v['wave'][offset:offset+count].copy()
    if 'stop_frame' in v:
     sample=start+lo+np.arange(count);clip*=np.clip((v['stop_frame']-sample)/max(1,round(.02*self.rate)),0,1)[:,None]
    wet[lo:lo+count]+=clip
    if offset+count<len(v['wave']) and end<v.get('stop_frame',end+1):keep.append(v)
   self.voices=keep;self.frames=end
   self.level=.9*self.level+.1*float(np.sqrt(np.mean(dry*dry)))
   wet*=np.clip(self.level/.12,.25,1.25)
   # Reserve headroom only when a gesture is actually active; never alter the clock.
   active=(np.max(abs(wet),axis=1)>1e-7).astype(np.float32)
   alpha=1-np.exp(-1/(self.rate*.01))
   duck,self.duck_state=lfilter([alpha],[1,-(1-alpha)],active,zi=self.duck_state)
   mixed=dry*(1-.08*duck[:,None])+wet
   return np.clip(mixed,-.98,.98).astype(np.float32)
 def status(self):
  with self.lock:
   return {'turn_signal_music':self.signal,'gesture_active':sorted(set(v['kind'] for v in self.voices)),'gesture_queued':[{'kind':e['kind'],'at':e['scheduled_frame']/self.rate} for e in self.queue[:3]],'gesture_bpm':self.bpm}
