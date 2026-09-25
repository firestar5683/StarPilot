from dataclasses import dataclass
import math


@dataclass(frozen=True)
class NavigationDisplay:
  key: tuple[str, int]
  text: str
  maneuver_type: str
  modifier: str
  distance_m: float
  remaining_distance_m: float
  remaining_seconds: float
  arrived: bool = False


def navigation_display(message, *, now_ns: int, drive_id: int) -> NavigationDisplay | None:
  if message is None or drive_id <= 0:
    return None
  try:
    if (not message.enabled or message.status not in ('guiding', 'arrived') or
        message.startedMonoTime != drive_id or not message.sessionId or
        not drive_id <= message.frameMonoTime <= now_ns <= message.frameMonoTime + 3_000_000_000 or
        not drive_id <= message.locationMonoTime <= now_ns <= message.locationMonoTime + 3_000_000_000):
      return None
    instruction = message.instruction
    distances = (instruction.distanceMeters, instruction.remainingDistanceMeters, instruction.remainingDurationSeconds)
    if not all(math.isfinite(value) and value >= 0 for value in distances):
      return None
    text = 'You have arrived' if message.status == 'arrived' else ' '.join(instruction.text.split())[:240]
    if not text:
      return None
    return NavigationDisplay((message.sessionId, drive_id), text, instruction.maneuverType,
                             instruction.maneuverModifier, *distances, message.status == 'arrived')
  except (AttributeError, TypeError, ValueError, OverflowError):
    return None


def distance_text(meters: float, metric: bool) -> str:
  if metric:
    if meters < 1000:
      step = 25 if meters < 500 else 50
      return f'{round(meters / step) * step} m'
    kilometers = meters / 1000
    return f'{kilometers:.0f} km' if kilometers >= 10 else f'{kilometers:.1f} km'
  feet = meters * 3.28084
  if feet < 1000:
    step = 10 if feet <= 100 else 50
    return f'{round(feet / step) * step} ft'
  miles = feet / 5280
  return f'{miles:.0f} mi' if miles >= 10 else f'{miles:.1f} mi'
