"""Live conductor-driven curve contrast, using only the current music samples."""
import math
from engagement_presentation import EngagementPresentation,PresentationConfig


class CurveReaction:
 def __init__(self,grid,rate=48000,enabled=False):
  self.grid=grid;self.rate=rate;self.enabled=enabled
  self.dsp=EngagementPresentation(rate,cutoff_hz=1800.,width=.92,gain=1.)
  self.config=PresentationConfig(enabled=True,attack_ms=130.,release_ms=180.)
  self.activation=None;self.payoff=None;self.target=1.;self.phase='neutral';self.fresh=False;self.end_frame=0

 def process(self,pcm,start_frame,state,source_fresh=True,blocked=False):
  self.end_frame=start_frame+len(pcm)
  amount=state.get('amount',0.)
  self.fresh=bool(source_fresh and isinstance(amount,(int,float)) and math.isfinite(amount))
  phase=state.get('phase','neutral');activation=state.get('activation')
  valid=self.enabled and self.fresh and not blocked and state.get('kind')=='curve'
  if activation!=self.activation:
   self.activation=activation;self.payoff=None
  target=1.
  if valid and phase=='anticipation':
   target=1.-.8*min(1.,max(0.,amount));self.payoff=None
  elif valid and phase=='event':
   if self.payoff is None:
    step=self.rate*60/self.grid.bpm/2 if self.grid.usable else 0.
    origin=self.grid.beat_phase*self.rate if self.grid.usable else 0.
    self.payoff=round(origin+math.ceil((start_frame-origin)/step-1e-10)*step) if step else start_frame
   if start_frame<self.payoff:
    target=self.target
    split=min(len(pcm),self.payoff-start_frame)
    first=self.dsp.process(pcm[:split],False,self.config,target_mix=target)
    if split<len(pcm):
     import numpy as np
     second=self.dsp.process(pcm[split:],False,self.config,target_mix=1.)
     self.target=1.;self.phase=phase
     return np.concatenate((first,second))
  self.target=target;self.phase=phase
  return self.dsp.process(pcm,False,self.config,target_mix=target)

 def snapshot(self):
  return {'curve_reaction':dict(enabled=self.enabled,input_fresh=self.fresh,phase=self.phase,
          rendered_phase=('apex' if self.payoff is not None and self.payoff<=self.end_frame<self.payoff+round(.3*self.rate) else 'build' if self.dsp.mix<.999 else 'neutral'),
          rendered_active=self.dsp.mix<.999,rendered_open_mix=self.dsp.mix,target_open_mix=self.target,cutoff_hz=1800.,maximum_wet_mix=.8,
          payoff_audio_s=None if self.payoff is None else self.payoff/self.rate,attack_ms=130.,contain_ms=180.,
          added_delay_samples=0,source='current causal conductor state',unknown_policy='smooth bypass')}
