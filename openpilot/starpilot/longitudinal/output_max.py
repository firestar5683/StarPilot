"""Fixed shared ceiling for the final longitudinal control output."""

# Retained identifier only for refusing obsolete edits and preserving saved bytes.
KEY = "LongitudinalMaxOutputAcceleration"
DEFAULT = 4.0


def final_output(acceleration: float) -> float:
  """Cap the returned command without changing controller state or lower limits."""
  return float(min(acceleration, DEFAULT))
