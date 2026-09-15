"""Galaxy subscriber to modeld telemetry; no GPU collector or hardware reads."""
import threading
import math
import time

from starpilot.common.external_gpu_temperature import external_gpu_temperature
from starpilot.common.external_gpu_memory import external_gpu_memory

_lock = threading.Lock()
_sm = None


def external_gpu_vitals(*, include_onboard=False):
  global _sm
  # Flask requests may overlap; SubMaster is owned behind this lock.
  with _lock:
    onboard = {'cpuTempC': None, 'gpuTempC': None, 'onboardMaxAgeMs': 0,
               'hotspotTempC': None, 'gpuEdgeTempC': None}
    try:
      if _sm is None:
        from cereal import messaging
        _sm = messaging.SubMaster(["deviceState", "chestnutState"])
      _sm.update(0)
      if include_onboard:
        try:
          age = time.monotonic_ns() - _sm.logMonoTime['deviceState']
          if _sm.valid.get('deviceState', False) and _sm.alive.get('deviceState', False) and 0 <= age < 3_000_000_000:
            for field in ('cpuTempC', 'gpuTempC'):
              values = [float(value) for value in getattr(_sm['deviceState'], field, [])]
              values = [value for value in values if math.isfinite(value) and 0 < value < 150]
              onboard[field] = max(values) if values else None
            onboard['onboardMaxAgeMs'] = (3_000_000_000 - age) // 1_000_000
        except (AttributeError, KeyError, TypeError, ValueError):
          pass
      temperature, remaining_ms = external_gpu_temperature(_sm, envelope_max_age_ns=3_000_000_000)
      memory, memory_ms = external_gpu_memory(_sm, envelope_max_age_ns=3_000_000_000)
      result = {"tempC": temperature, "maxAgeMs": remaining_ms,
              "memoryUsedBytes": memory[0] if memory else None,
              "memoryTotalBytes": memory[1] if memory else None, "memoryMaxAgeMs": memory_ms}
      if include_onboard:
        # modeld publishes TEMP_HOTSPOT in tempC. No edge temperature is published.
        onboard['hotspotTempC'] = temperature
        result.update(onboard)
      return result
    except Exception:
      # Optional telemetry must not break the dashboard on legacy bindings.
      result = {"tempC": None, "maxAgeMs": 0, "memoryUsedBytes": None, "memoryTotalBytes": None, "memoryMaxAgeMs": 0}
      if include_onboard:
        result.update(onboard)
      return result
