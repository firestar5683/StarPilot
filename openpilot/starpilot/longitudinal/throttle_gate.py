"""Source-timed Ioniq longitudinal throttle/coast comfort gate."""

import math

DISABLE_PROBABILITY = 0.35
ENABLE_PROBABILITY = 0.45
CONFIRM_NS = 250_000_000
MAX_MODEL_AGE_NS = 250_000_000
MAX_MODEL_GAP_NS = 150_000_000


class ModelThrottleGate:
  def __init__(self):
    self.allowed = True
    self.pending_since_ns: int | None = None
    self.last_model_ns: int | None = None

  def reset(self) -> None:
    self.allowed = True
    self.pending_since_ns = None
    self.last_model_ns = None

  def step(self, probability: float, speed_mps: float, *, low_speed_mps: float,
           model_ns: int, now_ns: int, model_valid: bool) -> bool:
    previous_ns = self.last_model_ns
    if (model_valid is True and type(model_ns) is int and model_ns > 0 and
        type(now_ns) is int and model_ns <= now_ns and now_ns - model_ns <= MAX_MODEL_AGE_NS and
        (previous_ns is None or model_ns > previous_ns)):
      self.last_model_ns = model_ns
    if (model_valid is not True or type(model_ns) is not int or model_ns <= 0 or
        type(now_ns) is not int or now_ns <= 0 or model_ns > now_ns or now_ns - model_ns > MAX_MODEL_AGE_NS or
        (previous_ns is not None and not 0 < model_ns - previous_ns <= MAX_MODEL_GAP_NS) or
        type(probability) not in (int, float) or not math.isfinite(probability) or not 0.0 <= probability <= 1.0 or
        type(speed_mps) not in (int, float) or not math.isfinite(speed_mps)):
      self.allowed = False
      self.pending_since_ns = None
      return False

    if speed_mps <= low_speed_mps:
      self.allowed = True
      self.pending_since_ns = None
      return True

    crossing = probability <= DISABLE_PROBABILITY if self.allowed else probability > ENABLE_PROBABILITY
    if crossing:
      if self.pending_since_ns is None:
        self.pending_since_ns = model_ns
      elif model_ns - self.pending_since_ns >= CONFIRM_NS:
        self.allowed = not self.allowed
        self.pending_since_ns = None
    else:
      self.pending_since_ns = None
    return self.allowed
