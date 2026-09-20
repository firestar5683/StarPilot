"""Causal stopped-to-moving brightness lift; output only, no musical replanning."""
import math
from engagement_presentation import EngagementPresentation, PresentationConfig


class MotionPresentation:
  def __init__(self, rate=48000, enabled=False, lift_ms=500., contain_ms=700.):
    self.rate=rate;self.enabled=enabled;self.stopped=False;self.stop_seconds=0.;self.move_seconds=0.
    self.dsp=EngagementPresentation(rate,cutoff_hz=900.,width=1.,gain=1.)
    self.config=PresentationConfig.read(dict(enabled=True,attack_ms=lift_ms,release_ms=contain_ms))
    self.target=1.;self.fresh=False

  def process(self, pcm, *, speed, source_fresh, engagement_open_mix=1.):
    dt=len(pcm)/self.rate
    self.fresh=bool(source_fresh and math.isfinite(speed) and speed>=0.)
    if self.fresh:
      self.stop_seconds=self.stop_seconds+dt if speed<=.25 else 0.
      self.move_seconds=self.move_seconds+dt if speed>=.8 else 0.
      if self.stop_seconds>=.4:self.stopped=True
      if self.move_seconds>=.15:self.stopped=False
    else:
      self.stopped=False;self.stop_seconds=0.;self.move_seconds=0.
    # Moving bypass restores the downstream engagement state, never bypasses it.
    strength=1. if self.fresh and self.stopped and self.enabled else 0.
    self.target=1.-strength
    return self.dsp.process(pcm,False,self.config,target_mix=self.target)

  def snapshot(self):
    return {'motion_presentation':dict(enabled=self.enabled,stopped=self.stopped,input_fresh=self.fresh,
                target_open_mix=self.target,rendered_open_mix=self.dsp.mix,cutoff_hz=900.,
                lift_ms=self.config.attack_ms,contain_ms=self.config.release_ms,
                stop_threshold_mps=.25,move_threshold_mps=.8,stop_dwell_seconds=.4,move_dwell_seconds=.15,
                gain=1.,width=1.,added_delay_samples=0,unknown_policy='smooth bypass',
                source='fresh current carState.vEgo; no future data')}
