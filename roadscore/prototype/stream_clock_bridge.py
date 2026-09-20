"""Map PortAudio timestamps to monotonic time once per output stream."""
import math
import time


class StreamClockBridge:
  def __init__(self, offset, uncertainty):
    self.offset = offset
    self.uncertainty = uncertainty
    self.source = 'bracketed-stream-time'
    self.offset_spread = None

  @classmethod
  def from_callbacks(cls, observations):
    """Freeze one offset from silent pre-roll, before any route is released.

    Some ALSA streams report zero from stream.time until their first callback,
    then return the latest callback timestamp. Callback entry is later than its
    timestamp: the minimum offset minimizes that nonnegative scheduling bias.
    It does not measure Bluetooth acoustic latency.
    """
    if len(observations)<8:raise ValueError('Output clock needs more silent callbacks')
    offsets=[];previous=None
    for wall,current,dac in observations:
      if (not all(type(value) in (int,float) and math.isfinite(value) for value in (wall,current,dac))
          or current<=0 or dac<=0 or not -.02<=dac-current<=5):
        raise ValueError('Invalid callback clock sample')
      if previous is not None and (wall<previous[0] or current<=previous[1] or dac<=previous[2]):
        raise ValueError('Output callback clock did not advance')
      previous=(wall,current,dac)
      offsets.append(wall-current)
    if observations[-1][1]-observations[0][1]<.1:
      raise ValueError('Output callback clock observation was too short')
    bridge=cls(min(offsets),None)
    bridge.source='silent-callback-minimum-entry-offset'
    bridge.offset_spread=max(offsets)-min(offsets)
    return bridge

  @classmethod
  def measure(cls, stream_time, *, clock=time.monotonic, samples=5):
    """Call outside the audio callback, while it is still awaiting route input."""
    candidates = []
    for _ in range(samples):
      before = clock()
      source = stream_time()
      after = clock()
      if (not all(type(value) in (int, float) and math.isfinite(value) for value in (before,source,after))
          or source <= 0 or after < before):
        raise ValueError('Invalid output stream clock sample')
      candidates.append((after-before, (before+after)/2-source))
    if not candidates:raise ValueError('No output stream clock samples')
    width, offset = min(candidates)
    if width > .05:raise ValueError('Output stream clock measurement is too uncertain')
    return cls(offset,width/2)

  def dac_wall(self, output_buffer_dac_time):
    if type(output_buffer_dac_time) not in (int,float) or not math.isfinite(output_buffer_dac_time):
      raise ValueError('Invalid output DAC timestamp')
    return output_buffer_dac_time+self.offset

  def snapshot(self):
    return {'portaudio_to_monotonic_seconds':self.offset,
            'measurement_uncertainty_seconds':self.uncertainty,
            'calibration_source':self.source,'callback_offset_spread_seconds':self.offset_spread,
            'mapping':'fixed-stream-clock-offset'}
