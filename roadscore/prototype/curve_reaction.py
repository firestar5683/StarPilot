"""Live conductor-driven curve contrast, using only the current music samples."""
import math
import numpy as np
from scipy.signal import butter
from engagement_presentation import EngagementPresentation,PresentationConfig


class CurveReaction:
 def __init__(self,grid,rate=48000,enabled=False,bass_build=False):
  self.grid=grid;self.rate=rate;self.enabled=enabled
  self.bass_build=bool(bass_build);self.cutoff=300. if self.bass_build else 1800.
  self.dsp=EngagementPresentation(rate,cutoff_hz=self.cutoff,width=.92,gain=.92 if self.bass_build else 1.)
  if self.bass_build:
   # Fixed coefficients are prepared before playback. The existing sample ramp
   # blends toward this high-pass, then restores the track's own bass at apex.
   self.dsp.sos=butter(2,self.cutoff,btype='highpass',fs=rate,output='sos').astype(np.float32)
  self.config=PresentationConfig(enabled=True,attack_ms=80. if self.bass_build else 130.,release_ms=180.)
  self.normal_config=self.config
  self.impact_config=PresentationConfig(enabled=True,attack_ms=25.,release_ms=180.)
  self.impact=None;self.impact_activation=None;self.impact_payoff=None;self.impact_start=None;self.impact_grid=None
  if self.bass_build:
   from curve_build_drop import CurveBuildDrop
   self.impact=CurveBuildDrop(rate)
  self.staged=False
  self.activation=None;self.payoff=None;self.target=1.;self.phase='neutral';self.fresh=False;self.end_frame=0;self.valid=False;self.armed=False

 def process(self,pcm,start_frame,state,source_fresh=True,blocked=False,route_time=None,payoff_grid=None):
  requested=self.impact is not None and state.get('demo_build_drop') is True
  valid=requested and self.enabled and source_fresh and not blocked
  valid=valid and type(route_time) in (int,float) and math.isfinite(route_time)
  valid=valid and all(type(state.get(k)) in (int,float) and math.isfinite(state[k]) for k in ('activation','predicted_peak'))
  if valid and state['activation']!=self.impact_activation:
   self.impact_activation=state['activation'];self.impact_payoff=None;self.impact_start=None;self.impact_grid=None
  if valid and self.impact_payoff is None:
   grid=payoff_grid if payoff_grid is not None else self.grid
   if grid.usable:
    desired=start_frame+round((state['predicted_peak']-route_time)*self.rate)
    step=self.rate*60/grid.bpm/2;origin=grid.beat_phase*self.rate
    scheduled=round(origin+round((desired-origin)/step)*step)
    # Arm only before the silence window, never introduce a late fake drop.
    if scheduled-start_frame>=round(.14*self.rate):
     self.impact_payoff=scheduled;self.impact_grid=grid
     self.impact_start=max(0,start_frame+round((state['activation']-route_time)*self.rate))
  armed=bool(valid and self.impact_payoff is not None)
  self.config=self.impact_config if armed else self.normal_config
  filtered_state=state
  if armed and start_frame+len(pcm)>self.impact_payoff:
   filtered_state={**state,'phase':'event'}
  result=self._filter(pcm,start_frame,filtered_state,source_fresh,blocked,self.impact_payoff if armed else None)
  if self.impact is not None:
   result=self.impact.process(result,start_frame,self.grid,self.impact_start,self.impact_payoff,
                              enabled=armed,source_fresh=source_fresh,blocked=blocked)
  if not valid:
   self.impact_activation=None;self.impact_payoff=None;self.impact_start=None;self.impact_grid=None
  return result

 def _filter(self,pcm,start_frame,state,source_fresh=True,blocked=False,scheduled_payoff=None):
  self.end_frame=start_frame+len(pcm)
  amount=state.get('amount',0.)
  self.fresh=bool(source_fresh and isinstance(amount,(int,float)) and math.isfinite(amount))
  phase=state.get('phase','neutral');activation=state.get('activation')
  self.staged=state.get('demo_staged_curve') is True
  identified=isinstance(activation,(int,float)) and not isinstance(activation,bool) and math.isfinite(activation)
  valid=self.enabled and self.fresh and not blocked and state.get('kind')=='curve' and identified
  self.valid=bool(valid)
  if activation!=self.activation:
   self.activation=activation;self.payoff=None;self.armed=False
  if not valid:
   self.payoff=None;self.armed=False
  elif scheduled_payoff is not None:self.payoff=scheduled_payoff
  target=1.
  if valid and phase=='anticipation':
   target=1.-(.98 if self.bass_build else .8)*min(1.,max(0.,amount))
   if scheduled_payoff is None:self.payoff=None
  elif valid and phase=='event' and self.armed:
   if self.payoff is None:
    step=self.rate*60/self.grid.bpm/2 if self.grid.usable else 0.
    origin=self.grid.beat_phase*self.rate if self.grid.usable else 0.
    self.payoff=round(origin+math.ceil((start_frame-origin)/step-1e-10)*step) if step else start_frame
   if start_frame<self.payoff:
    target=self.target
    split=min(len(pcm),self.payoff-start_frame)
    first=self.dsp.process(pcm[:split],False,self.config,target_mix=target)
    if split<len(pcm):
     second=self.dsp.process(pcm[split:],False,self.config,target_mix=1.)
     self.target=1.;self.phase=phase
     return np.concatenate((first,second))
    self.target=target;self.phase=phase
    return first
  self.target=target;self.phase=phase
  result=self.dsp.process(pcm,False,self.config,target_mix=target)
  if valid and phase=='anticipation' and self.dsp.mix<.999:self.armed=True
  return result

 def snapshot(self):
  apex=bool(self.valid and self.phase=='event' and self.armed and self.payoff is not None and self.payoff<self.end_frame<self.payoff+round(.3*self.rate))
  build=bool(self.valid and self.armed and self.phase in ('anticipation','event') and self.dsp.mix<.999)
  return {'curve_reaction':dict(enabled=self.enabled,input_fresh=self.fresh,phase=self.phase,
          rendered_phase=('apex' if apex else 'build' if build else 'neutral'),
          rendered_active=apex or build,rendered_open_mix=self.dsp.mix,target_open_mix=self.target,cutoff_hz=self.cutoff,maximum_wet_mix=.98 if self.bass_build else .8,
          treatment='bass-return' if self.bass_build else 'filter-opening',filter_type='highpass' if self.bass_build else 'lowpass',
          build_drop=None if self.impact is None else self.impact.snapshot(),
          payoff_audio_s=None if self.payoff is None else self.payoff/self.rate,attack_ms=self.config.attack_ms,contain_ms=180.,
          added_delay_samples=0,source='known replay route event' if self.staged else 'current causal conductor state',demo_staged=self.staged,unknown_policy='smooth bypass')}
