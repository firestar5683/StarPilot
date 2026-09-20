"""Bounded prepared-PCM clock recovery; no I/O, regeneration, or resampling."""
from collections import deque
import math
import numpy as np


class ClockDiscontinuity(RuntimeError):
  pass


class PreparedClock:
  """One audio-callback owner. Read snapshot outside the callback for evidence.

  expected_frame comes from the existing original-model/DAC mapping. Small
  scheduling jitter keeps contiguous PCM. Bounded DAC estimate changes blend
  old and new source for 40 ms without inserting samples. A short backwards
  output-delay correction is distinct from rewinding the route/model clock,
  which the caller separately guards. Explicit seeks may move either direction;
  the caller must reset presentation state outside the callback when seeking.
  """
  def __init__(self, rate=48000, *, threshold_ms=50., crossfade_ms=40., maximum_forward_seconds=5., maximum_backward_seconds=.25):
    if type(rate) is not int or rate <= 0:raise ValueError('Invalid sample rate')
    values=(threshold_ms,crossfade_ms,maximum_forward_seconds,maximum_backward_seconds)
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ValueError('Invalid clock recovery limits')
    if (not 0<threshold_ms<=100 or not 1<=crossfade_ms<=40 or maximum_forward_seconds<=threshold_ms/1000
        or not threshold_ms/1000<maximum_backward_seconds<=.25):
      raise ValueError('Clock recovery limits are out of bounds')
    self.rate=rate
    self.threshold=round(rate*threshold_ms/1000)
    self.fade_frames=max(1,round(rate*crossfade_ms/1000))
    self.maximum_forward=round(rate*maximum_forward_seconds)
    self.maximum_backward=round(rate*maximum_backward_seconds)
    self.position=None
    self.fade_from=None
    self.fade_done=0
    self.corrections=0
    self.explicit_seeks=0
    self.max_pre_error=0
    self.max_post_error=0
    self.current_post_error=0
    self.events=deque(maxlen=64)

  @staticmethod
  def _slice(core,start,frames):
    result=np.zeros((frames,core.shape[1]),dtype=np.float32)
    low=max(0,-start);high=min(frames,len(core)-start)
    if high>low:result[low:high]=core[start+low:start+high]
    return result

  def render(self,core,expected_frame,frames,*,explicit_seek=False):
    if type(expected_frame) is not int or type(frames) is not int or frames<=0:
      raise ValueError('Clock frames must be finite integers')
    if not isinstance(core,np.ndarray) or core.ndim!=2 or core.dtype!=np.float32:
      raise ValueError('Expected prepared float32 PCM')
    if type(explicit_seek) is not bool:raise ValueError('Seek authorization must be explicit')
    if expected_frame < -2*self.rate or expected_frame > len(core)+self.rate:
      raise ClockDiscontinuity('Expected playhead is outside the prepared recording')
    initial=self.position is None
    previous=expected_frame if initial else self.position
    delta=expected_frame-previous
    self.max_pre_error=max(self.max_pre_error,abs(delta))
    correction=None;deferred=False
    if not initial and (explicit_seek or abs(delta)>self.threshold):
      if not explicit_seek:
        if delta < -self.maximum_backward:raise ClockDiscontinuity('Prepared audio clock moved backwards beyond the output-delay recovery bound')
        if delta>self.maximum_forward:raise ClockDiscontinuity('Prepared audio clock discontinuity exceeds the recovery bound')
        # Finish the existing blend before correcting another bounded DAC
        # estimate change. Do not queue this target: the next callback after
        # the fade must use its newest estimate. Bounds still apply immediately.
        deferred=self.fade_from is not None
      if not deferred:
        kind='explicit-seek' if explicit_seek else 'backward-dac-recovery' if delta<0 else 'forward-clock-recovery'
        correction={'kind':kind,'from_frame':previous,'to_frame':expected_frame,'delta_frames':delta,'crossfade_frames':self.fade_frames}
        self.events.append(correction)
        self.corrections+=not explicit_seek
        self.explicit_seeks+=explicit_seek
        self.fade_from=previous
        self.fade_done=0
        self.position=expected_frame
    elif initial:self.position=expected_frame
    start=self.position
    result=self._slice(core,start,frames)
    faded=0
    if self.fade_from is not None:
      faded=min(frames,self.fade_frames-self.fade_done)
      old=self._slice(core,self.fade_from,faded)
      alpha=(np.arange(1,faded+1,dtype=np.float32)+self.fade_done)/self.fade_frames
      result[:faded]=old+(result[:faded]-old)*alpha[:,None]
      self.fade_done+=faded
      self.fade_from+=faded
      if self.fade_done>=self.fade_frames:self.fade_from=None
    self.position+=frames
    post_error=expected_frame-start
    self.current_post_error=post_error
    self.max_post_error=max(self.max_post_error,abs(post_error))
    return result,{'source_frame':start,'next_source_frame':self.position,'expected_frame':expected_frame,
                   'pre_error_frames':delta,'post_error_frames':post_error,'crossfade_frames_rendered':faded,
                   'correction':correction,'correction_deferred':deferred}

  def snapshot(self):
    return {'next_source_frame':self.position,'corrections':self.corrections,'explicit_seeks':self.explicit_seeks,
            'max_pre_error_seconds':self.max_pre_error/self.rate,'max_post_error_seconds':self.max_post_error/self.rate,
            'current_post_error_seconds':self.current_post_error/self.rate,
            'crossfade_ms':1000*self.fade_frames/self.rate,'recovery_in_progress':self.fade_from is not None,
            'maximum_backward_recovery_seconds':self.maximum_backward/self.rate,
            'events':list(self.events),'added_delay_samples':0,'resampling':False}
