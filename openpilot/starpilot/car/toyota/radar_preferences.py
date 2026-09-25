"""One canonical saved startup choice, default Off, for the RAV4 Continental receiver."""

from opendbc.car.toyota.ars510_preferences import supported
from openpilot.starpilot.saved_source import read_saved

KEY = 'ToyotaRadarMode'
CHOICES = ('Off', 'ACC Target', 'Fused Tracks')


def selected(params, *, enabled):
  try:
    raw, readable = read_saved(params, KEY, 8)
    safe, safe_readable = read_saved(params, 'SafeMode', 8)
    return int(raw) if enabled and readable and raw in (b'1', b'2') and safe_readable and safe in (None, b'0') else 0
  except (OSError, TypeError, ValueError):
    return 0


def capability(cp):
  try:
    if cp is None or not supported(cp):
      return None
    return (
      str(cp.carFingerprint),
      str(cp.brand),
      int(cp.flags),
      bool(cp.pcmCruise),
      bool(cp.openpilotLongitudinalControl),
      int(cp.alternativeExperience),
      tuple((str(config.safetyModel), int(config.safetyParam)) for config in cp.safetyConfigs),
      str(cp.carVin) if cp.carVin else None,
    )
  except (AttributeError, TypeError, ValueError):
    return None
