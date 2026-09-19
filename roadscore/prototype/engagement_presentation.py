"""Version 2 output-only engagement presentation. Never changes generation/time.

Sample-ramped blend to a fixed causal low-pass avoids coefficient zipper noise.
Mixing workspaces are bounded; scipy sosfilt allocates bounded output/state arrays.
Returned arrays own storage for the asynchronous recorder. Not allocation-free.
"""
from dataclasses import dataclass, asdict
import math
import numpy as np
from scipy.signal import butter, sosfilt


@dataclass(frozen=True)
class PresentationConfig:
  version: int = 2
  enabled: bool = False
  attack_ms: float = 220.
  release_ms: float = 650.

  @classmethod
  def read(cls, value):
    if not isinstance(value, dict) or value.get('version', 2) != 2:
      return cls()
    def duration(key, default):
      try:
        n = float(value.get(key, default))
        return min(5000., max(20., n)) if math.isfinite(n) else default
      except (TypeError, ValueError):
        return default
    return cls(enabled=value.get('enabled') is True,
               attack_ms=duration('attack_ms', 220.), release_ms=duration('release_ms', 650.))


def engagement_active(valid, active, source_ns, latest_source_ns, received_wall, now_wall):
  """Reject invalid/stale/future data and transport stalls; no route lookahead.

  active means openpilot actively controlling (not merely enabled/pre-enabled).
  Both replay timestamps are from delivered cereal, wall times local receipt.
  """
  age = (latest_source_ns - source_ns) / 1e9
  fresh = valid and source_ns > 0 and 0 <= age <= 1. and 0 <= now_wall - received_wall <= 1.
  return bool(fresh and active), bool(fresh)


class EngagementPresentation:
  def __init__(self, rate=48000, max_frames=4800):
    self.rate = rate
    self.max_frames = max_frames
    self.sos = butter(2, 4500, fs=rate, output='sos').astype(np.float32)
    self.zi = np.zeros((len(self.sos), 2, 2), np.float32)
    self.mix = 1.  # startup bypass; opting in ramps into contained presentation
    self.indices = np.arange(1, max_frames + 1, dtype=np.float32)
    self.ramp = np.empty(max_frames, np.float32)
    self.scratch = np.empty((max_frames, 2), np.float32)
    self.mid = np.empty(max_frames, np.float32)
    self.delta = np.empty((max_frames, 2), np.float32)
    # Exercise scipy dispatch before audio callbacks.
    sosfilt(self.sos, np.zeros((1, 2), np.float32), axis=0, zi=self.zi)

  def process(self, pcm, active, config):
    """Stereo float32 in/out, same frames, never mutates caller PCM.

    Fully bypassed output is original PCM (read-only use by downstream). Split
    unusually large blocks into bounded workspace chunks; no buffering latency.
    """
    if not len(pcm):
      return pcm
    # Keep filter warm even during bypass; allocated size bounded by max_frames.
    target = 1. if active or not config.enabled else 0.
    output = None if target == 1. and self.mix == 1. else np.empty_like(pcm)
    for start in range(0, len(pcm), self.max_frames):
      x = pcm[start:start + self.max_frames]
      n = len(x)
      low, self.zi = sosfilt(self.sos, x, axis=0, zi=self.zi)
      if output is None:
        continue
      duration = config.attack_ms if target > self.mix else config.release_ms
      step = 1000. / (duration * self.rate)
      ramp = self.ramp[:n]
      np.multiply(self.indices[:n], step if target > self.mix else -step, out=ramp)
      np.add(ramp, self.mix, out=ramp)
      np.clip(ramp, min(self.mix, target), max(self.mix, target), out=ramp)
      self.mix = float(ramp[-1])
      # Contained: 85% stereo width and -1 dB. Convex mixing avoids gain boosts.
      mid = self.mid[:n]
      np.add(low[:, 0], low[:, 1], out=mid)
      mid *= .5
      wet = self.scratch[:n]
      np.subtract(low, mid[:, None], out=wet)
      wet *= .85
      wet += mid[:, None]
      wet *= .8912509
      delta = self.delta[:n]
      np.subtract(x, wet, out=delta)
      np.multiply(delta, ramp[:, None], out=delta)
      np.add(wet, delta, out=output[start:start+n])
      # Exact full-bandwidth endpoint rather than floating-point cancellation.
      full = ramp >= 1.
      output[start:start+n][full] = x[full]
    return pcm if output is None else output

  def snapshot(self, config, active, fresh):
    return {'engagement_presentation': {**asdict(config), 'active': active,
            'input_fresh': fresh, 'source': 'selfdriveState.active',
            'unknown_policy': 'contained', 'added_delay_samples': 0}}
