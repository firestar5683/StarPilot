"""Read-only Chestnut hotspot telemetry, shared by native UI and Galaxy."""
import math
import time


def external_gpu_temperature(sm, now_ns=None, *, envelope_max_age_ns=1_000_000_000):
  """Return (Celsius, remaining freshness ms), or (None, 0).

  Cached envelopes are not new SMU samples. Legacy publishers have no sample
  timestamp and deliberately remain unavailable. No hardware access here.
  """
  now_ns = time.monotonic_ns() if now_ns is None else now_ns
  try:
    remaining = []
    for service in ("deviceState", "chestnutState"):
      if not sm.valid.get(service, False) or not sm.alive.get(service, False):
        return None, 0
      age = now_ns - sm.logMonoTime[service]
      if not 0 <= age <= envelope_max_age_ns:
        return None, 0
      remaining.append(envelope_max_age_ns - age)
    if not sm["deviceState"].chestnutPresent:
      return None, 0
    state = sm["chestnutState"]
    sample_time = state.tempSampleMonoTime
    age = now_ns - sample_time
    if sample_time <= 0 or not 0 <= age <= 15_000_000_000:
      return None, 0
    remaining.append(15_000_000_000 - age)
    temperature = float(state.tempC)
    if not math.isfinite(temperature) or temperature <= 0:
      return None, 0
    return temperature, min(remaining) // 1_000_000
  except (AttributeError, KeyError, OverflowError, TypeError, ValueError):
    return None, 0
