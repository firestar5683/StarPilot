"""Map PortAudio timestamps to monotonic time once per output stream."""
import math
import time


class StreamClockBridge:
  def __init__(self, offset, uncertainty):
    self.offset = offset
    self.uncertainty = uncertainty

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
            'mapping':'fixed-stream-clock-offset'}
