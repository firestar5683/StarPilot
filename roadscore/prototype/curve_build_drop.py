"""Opt-in presentation for one explicitly scheduled replay curve; no route inference."""
import math

import numpy as np
from scipy.signal import butter, sosfilt

from signal_shaker import ShakerGrid, SignalShaker


class CurveBuildDrop:
  def __init__(self, rate=48000, max_frames=4800, *, cut_ms=120., ramp_ms=10., low_boost_db=1.5):
    self.rate=rate;self.max_frames=max_frames
    self.cut_frames=round(cut_ms*rate/1000);self.ramp_frames=max(1,round(ramp_ms*rate/1000))
    self.cancel_frames=max(1,round(.03*rate));self.boost_frames=round(.22*rate)
    self.low_boost=10**(min(3.,max(0.,low_boost_db))/20)-1.
    # Reuse the signal shaker's unpitched voice; RNG/FFT/filter design happen once.
    prepared=SignalShaker(ShakerGrid(128.,0.,1.,1.,True,'prepared voice only'),rate,peak=.08)
    self.grain=prepared.grain/.08
    self.sos=butter(2,160.,fs=rate,output='sos').astype(np.float32)
    self.zi=np.zeros((len(self.sos),2,2),np.float32)
    sosfilt(self.sos,np.zeros((1,2),np.float32),axis=0,zi=self.zi)
    self.indices=np.arange(max_frames,dtype=np.float64)
    self.schedule=None;self.last_pulse=None;self.tail=np.zeros((0,2),np.float32)
    self.strength=0.;self.actual_payoff=None;self.pulse_frames=[]
    self.status=dict(rendered_stage='bypass',rendered_active=False,added_delay_samples=0)

  def process(self, pcm, start_frame, grid, build_start_frame, payoff_frame, *, enabled=False,
              source_fresh=True, blocked=False):
    """Same frames, no input mutation. Caller supplies and authorizes the schedule.

    Disabling a fully bypassed instance is bit exact; cancelling an active effect
    returns smoothly to the original PCM within 30ms. Uncertain beat grids never
    start a roll. Nothing in this class reads future route state or calls I/O.
    """
    if not len(pcm):return pcm
    finite=lambda n:isinstance(n,(int,float)) and not isinstance(n,bool) and math.isfinite(n)
    valid=bool(enabled and source_fresh and not blocked and grid.usable
               and finite(build_start_frame) and finite(payoff_frame)
               and payoff_frame-build_start_frame>self.cut_frames+self.ramp_frames)
    candidate=(round(build_start_frame),round(payoff_frame)) if valid else None
    # Keep the old schedule only long enough to finish a cancellation ramp.
    if candidate is not None and candidate!=self.schedule:
      self.schedule=candidate;self.last_pulse=None;self.actual_payoff=None;self.tail=np.zeros((0,2),np.float32)
    outputs=[];peaks=[];cut_min=1.;any_active=False;stage='bypass'
    for offset in range(0,len(pcm),self.max_frames):
      x=pcm[offset:offset+self.max_frames];n=len(x);first=start_frame+offset;end=first+n
      low,self.zi=sosfilt(self.sos,x,axis=0,zi=self.zi)
      if self.schedule is None:
        outputs.append(x);continue
      build,payoff=self.schedule;cut_start=payoff-self.cut_frames
      requested=valid and end>build and first<payoff+self.boost_frames
      target=1. if requested else 0.
      strength=np.clip(self.strength+(self.indices[:n]+1)*(1. if target>self.strength else -1.)/self.cancel_frames,
                       min(self.strength,target),max(self.strength,target)).astype(np.float32)
      self.strength=float(strength[-1])
      if not np.any(strength):
        self.tail=np.zeros((0,2),np.float32);outputs.append(x);continue
      frames=self.indices[:n]+first
      roll=np.zeros_like(x);take=min(n,len(self.tail));roll[:take]+=self.tail[:take];self.tail=self.tail[take:].copy()
      if requested and first<cut_start and end>build:
        beat=self.rate*60/grid.bpm;origin=grid.beat_phase*self.rate
        # Eighth notes establish the motif; the final four beats use sixteenths.
        boundary=max(build,payoff-4*beat)
        for lo,hi,step in ((build,boundary,beat/2),(boundary,cut_start,beat/4)):
          lo=max(first,lo);hi=min(end,hi)
          if hi<=lo:continue
          tick=math.ceil((lo-origin)/step-1e-10)
          while round(origin+tick*step)<hi:
            frame=round(origin+tick*step);tick+=1
            if frame<first or (self.last_pulse is not None and frame-self.last_pulse<beat/8):continue
            progress=np.clip((frame-build)/max(1.,cut_start-build),0.,1.)
            gain=.024+.056*progress**1.3
            grain=self.grain*gain;index=frame-first;count=min(len(grain),n-index)
            roll[index:index+count]+=grain[:count]
            if count<len(grain):
              rest=grain[count:];tail=np.zeros((max(len(rest),len(self.tail)),2),np.float32)
              tail[:len(self.tail)]+=self.tail;tail[:len(rest)]+=rest;self.tail=tail
            self.last_pulse=frame;self.pulse_frames.append(frame)
      cut=np.ones(n,np.float32)
      falling=(frames>=cut_start)&(frames<payoff)
      cut[falling]=np.clip(1.-(frames[falling]-cut_start+1)/self.ramp_frames,0.,1.)
      rising=(frames>=payoff)&(frames<payoff+self.ramp_frames)
      cut[rising]=np.clip((frames[rising]-payoff+1)/self.ramp_frames,0.,1.)
      elapsed=frames-payoff
      boost=np.where((elapsed>=0)&(elapsed<self.boost_frames),
                     np.clip(elapsed/self.ramp_frames,0.,1.)*np.exp(-np.maximum(elapsed,0)/(self.rate*.075)),0.).astype(np.float32)
      delta=roll+low*(boost*self.low_boost)[:,None]
      np.clip(delta,-np.maximum(0.,1.+x),np.maximum(0.,1.-x),out=delta)
      wet=(x+delta)*cut[:,None]
      out=x+(wet-x)*strength[:,None]
      # Exact neutral endpoint avoids floating-point cancellation after the drop.
      neutral=(cut==1)&(boost==0)&(np.max(abs(roll),axis=1)==0)
      out[neutral]=x[neutral]
      effective_cut=1.-strength+strength*cut
      rendered_roll=roll*(strength*cut)[:,None]
      outputs.append(out);peaks.append(float(np.max(abs(rendered_roll),initial=0)))
      cut_min=min(cut_min,float(np.min(effective_cut)))
      rendered=bool(np.any(effective_cut<1.) or np.any(rendered_roll) or np.any(boost*strength*self.low_boost))
      any_active |= rendered
      if valid and first<=payoff<end and strength[int(payoff-first)]>0:self.actual_payoff=payoff
      if not rendered:continue
      if not valid:stage='cancelling'
      elif end<=cut_start:stage='build'
      elif first<payoff:stage='cut' if end<=payoff else 'drop'
      else:stage='drop'
    if not any_active:
      if self.strength==0 and not valid:self.schedule=None
      result=pcm
    else:result=np.concatenate(outputs) if len(outputs)>1 else outputs[0]
    self.status=dict(enabled=bool(enabled),input_fresh=bool(source_fresh),blocked=bool(blocked),grid_usable=bool(grid.usable),
      rendered_stage=stage,rendered_active=any_active,rendered_strength=self.strength,rendered_roll_peak=max(peaks,default=0.),
      rendered_cut_gain_min=cut_min,planned_build_frame=None if self.schedule is None else self.schedule[0],
      planned_payoff_frame=None if self.schedule is None else self.schedule[1],actual_payoff_frame=self.actual_payoff,
      pulse_count=len(self.pulse_frames),cut_ms=1000*self.cut_frames/self.rate,ramp_ms=1000*self.ramp_frames/self.rate,
      low_boost_db=20*math.log10(1+self.low_boost),added_delay_samples=0,
      source='explicit replay presentation schedule; no composition or route lookup')
    return result

  def snapshot(self):return dict(self.status)
