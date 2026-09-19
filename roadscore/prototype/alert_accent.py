"""Sparse native-alert accents using the signal shaker's percussion vocabulary."""
import math
import numpy as np
from signal_shaker import SignalShaker


class AlertAccent:
 def __init__(self, grid, rate=48000, enabled=False):
  self.grid=grid;self.rate=rate;self.enabled=enabled
  self.grain=SignalShaker(grid,rate,peak=.016).grain
  self.key=None;self.since=0;self.handled=False;self.pending=[]
  self.last=-60*rate;self.events=[];self.rendered_active=False

 def process(self, pcm, start, key, meaningful, fresh, competing=False):
  self.rendered_active=False
  if not self.enabled:return pcm
  current=key if meaningful and fresh else None
  if current!=self.key:
   self.key=current;self.since=start;self.handled=False;self.pending=[]
  if not fresh or competing:
   self.pending=[]
   if current:self.handled=True
   return pcm
  if self.grid.usable and current and not self.handled and start-self.since>=round(.2*self.rate):
   self.handled=True
   if start-self.last>=12*self.rate and sum(start-e['frame']<60*self.rate for e in self.events)<3:
    beat=self.rate*60/self.grid.bpm;origin=self.grid.beat_phase*self.rate
    frame=round(origin+math.ceil((start-origin)/beat-1e-10)*beat)
    self.pending=[(frame,1.),(frame+round(beat/2),.55)]
    self.last=start;self.events.append({'kind':'native_alert_accent','frame':start,'scheduled_frame':frame,'alert':current})
  end=start+len(pcm);overlay=None;remaining=[]
  for frame,gain in self.pending:
   left=max(start,frame);right=min(end,frame+len(self.grain))
   if right>left:
    if overlay is None:overlay=np.zeros_like(pcm)
    overlay[left-start:right-start]+=self.grain[left-frame:right-frame]*gain
   if frame+len(self.grain)>end:remaining.append((frame,gain))
  self.pending=remaining
  # Never create an isolated notification sound in a musical rest.
  if overlay is None or np.max(np.abs(pcm),initial=0)<.002:return pcm
  self.rendered_active=bool(np.any(overlay))
  return pcm+overlay

 def snapshot(self):
  return {'enabled':self.enabled,'rhythm_enabled':self.enabled and self.grid.usable,
          'rendered_active':self.rendered_active,'minimum_spacing_seconds':12,
          'maximum_per_minute':3,'source':'selfdriveState.alertStatus'}
