"""Assess already-generated audio off the callback; refresh its audible beat grid."""
from dataclasses import replace, asdict
from signal_shaker import ShakerGrid, assess_grid

UNKNOWN=ShakerGrid(128.,0.,0.,0.,False,'no current acoustic assessment')

class RhythmTimeline:
 def __init__(self, rate, bpm_prior):
  self.rate=rate;self.prior=bpm_prior;self.entries=()

 def add(self, wave, start_frame):
  prepared=[]
  for offset in range(0,len(wave),10*self.rate):
   window=wave[offset:offset+24*self.rate]
   if len(window)<12*self.rate:break
   grid,_=assess_grid(window,self.rate,self.prior)
   first=start_frame+offset
   prepared.append((first,first+len(window),replace(grid,beat_phase=grid.beat_phase+first/self.rate)))
  # Publish once; callback readers never observe a partially-built schedule.
  self.entries=tuple(e for e in self.entries if e[0]<start_frame)+tuple(prepared)

 def snapshot(self):
  return [{'start_frame':first,'end_frame':end,'grid':asdict(grid)} for first,end,grid in self.entries]

 def at(self, frame):
  for first,end,grid in reversed(self.entries):
   if first<=frame:return grid if frame<end else UNKNOWN
  return UNKNOWN
