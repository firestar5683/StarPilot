"""Experimental generated-section player. Cached GPU material provides low-latency form.
New GPU continuations replace a role only at a loop boundary. No external music assets.
"""
from pathlib import Path
import threading
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from bar_grid import grid
class SectionBank:
 def __init__(self,root,rate=48000):
  self.rate=rate;self.clips={};self.pending={};self.section='verse';self.position=0;self.events=[];self.frames=0;self.scheduled=None;self.plan_tail=[];self.plan_key=None;self.plan_lock=threading.RLock()
  for role in ['intro','verse','prechorus','chorus','bridge','outro']:
   path=Path(root)/f'anchored_{role}.wav';wave,sr=sf.read(path,dtype='float32',always_2d=True)
   if sr!=rate:wave=resample_poly(wave,rate,sr).astype(np.float32)
   self.clips[role]=self.prepare(wave)
 def prepare(self,wave):
  info=grid(wave,self.rate);bars=info['downbeats'];lo=next(t for t in bars if t>=.1);hi=bars[-1]
  if hi-lo<4:raise ValueError('Insufficient bar-aligned generated section')
  return (wave[round(lo*self.rate):round(hi*self.rate)].copy(),{**info,'crop_start':lo,'crop_end':hi})
 def update(self,role,wave,job):
  clip,info=self.prepare(wave);self.pending[role]=(clip,{**info,'job':job})
 def context(self,past_seconds=12,ahead_seconds=4):
  clip,_=self.clips[self.section];p=round(past_seconds*self.rate);a=round(ahead_seconds*self.rate)
  past=clip[np.arange(self.position-p,self.position)%len(clip)].copy();ahead=clip[np.arange(self.position,self.position+a)%len(clip)].copy()
  return past,ahead
 def schedule(self,role,frame):
  self.scheduled=(role,frame)
 def set_plan(self,plan,preparation=None):
  key=tuple(plan[k] for k in ("section","at","requested","reason"))
  with self.plan_lock:
   if key==self.plan_key:return
   self.plan_key=key
   events=([preparation] if preparation else [])+[plan]
   items=[(e["section"],round(e["at"]*self.rate)) for e in events]
   self.scheduled=items[0];self.plan_tail=items[1:]
 def render(self,n,section=None):
  # The complete plan is queued once; control ticks cannot erase a due pickup.
  with self.plan_lock:return self._render(n,section)
 def consume_plan(self):
  self.scheduled=self.plan_tail.pop(0) if self.plan_tail else None
 def _render(self,n,section=None):
  if self.scheduled and self.scheduled[1]<self.frames:
   section=self.scheduled[0];self.consume_plan()
  if self.scheduled and self.frames<=self.scheduled[1]<self.frames+n:
   role,frame=self.scheduled;self.consume_plan();k=frame-self.frames
   left=self.render(k) if k else np.empty((0,2),np.float32)
   right=self.render(n-k,role);return np.concatenate([left,right])
  section=section or self.section
  if section!=self.section:
   self.section=section;self.position=0;self.events.append({'audio_s':self.frames/self.rate,'section':section,'kind':'section_landing','grid':self.clips[section][1]})
  out=np.empty((n,2),np.float32);cursor=0
  while cursor<n:
   clip,info=self.clips[self.section]
   if self.position>=len(clip):
    self.position=0
    if self.section in self.pending and self.scheduled is None:self.clips[self.section]=self.pending.pop(self.section);clip,info=self.clips[self.section]
    self.events.append({'audio_s':(self.frames+cursor)/self.rate,'section':self.section,'kind':'generated_phrase_boundary','grid':info})
   count=min(n-cursor,len(clip)-self.position);out[cursor:cursor+count]=clip[self.position:self.position+count];self.position+=count;cursor+=count
  self.frames+=n;return out
