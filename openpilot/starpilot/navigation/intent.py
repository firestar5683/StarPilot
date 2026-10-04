"""Route advice admitted through existing lateral and longitudinal owners."""

import math

from openpilot.cereal import log
from openpilot.common.constants import CV

from openpilot.starpilot.navigation.wire import navigation_state

SERVICE = 'starpilotNavigation'
MAX_AGE_NS = 2_500_000_000
TARGET_MPH = {'uturn': 5., 'sharpLeft': 10., 'sharpRight': 10., 'left': 14., 'right': 14.}


def current_instruction(sm, now_ns: int):
  try:
    nav, device = navigation_state(sm[SERVICE]), sm['deviceState']
    stamp = sm.logMonoTime[SERVICE]
    device_stamp = sm.logMonoTime['deviceState']
    if (not sm.valid[SERVICE] or not sm.alive[SERVICE] or not nav.enabled or not nav.controlValid or
        nav.status != 'guiding' or not nav.sessionId or not nav.revision or
        not 0 < nav.frameMonoTime <= stamp <= now_ns <= nav.frameMonoTime + MAX_AGE_NS or
        not sm.valid['deviceState'] or not sm.alive['deviceState'] or not device.started or
        not 0 < device.startedMonoTime == nav.startedMonoTime <= device_stamp <= now_ns <= device_stamp + 2_000_000_000 or
        not nav.startedMonoTime <= nav.locationMonoTime <= now_ns <= nav.locationMonoTime + MAX_AGE_NS):
      return None
    for service in ('carState', 'carControl'):
      source = sm.logMonoTime[service]
      if not sm.valid[service] or not sm.alive[service] or not nav.startedMonoTime <= source <= now_ns <= source + 100_000_000:
        return None
    cs = sm['carState']
    if not cs.canValid or cs.canTimeout or str(cs.gearShifter) != 'drive':
      return None
    return nav
  except (KeyError, AttributeError, TypeError):
    return None


def turn_desire(sm, now_ns: int, current_desire, *, supported: bool):
  if not supported or current_desire != log.Desire.none:
    return current_desire
  nav = current_instruction(sm, now_ns)
  if nav is None:
    return current_desire
  cs, cc, instruction = sm['carState'], sm['carControl'], nav.instruction
  if (not cc.latActive or cs.standstill or not math.isfinite(cs.vEgo) or not 0 <= cs.vEgo < 14 or
      instruction.maneuverType != 'turn' or not math.isfinite(instruction.distanceMeters) or
      not 0 <= instruction.distanceMeters <= min(90., max(35., cs.vEgo * 6.))):
    return current_desire
  if instruction.maneuverModifier in ('left', 'sharpLeft') and cs.leftBlinker and not cs.rightBlinker and not cs.leftBlindspot:
    return log.Desire.turnLeft
  if instruction.maneuverModifier in ('right', 'sharpRight') and cs.rightBlinker and not cs.leftBlinker and not cs.rightBlindspot:
    return log.Desire.turnRight
  return current_desire


def turn_speed(maneuver, min_steer_speed: float) -> float | None:
  kind, modifier = maneuver.maneuverType, maneuver.maneuverModifier
  target = TARGET_MPH.get(modifier) if kind == 'turn' else None
  if modifier == 'uturn' or 'uturn' in kind or 'u-turn' in kind:
    target = 5.
  elif 'roundabout' in kind or 'rotary' in kind:
    target = 12.
  if target is None or not math.isfinite(maneuver.distanceMeters) or maneuver.distanceMeters < 0:
    return None
  target = max(target * CV.MPH_TO_MS, min_steer_speed)
  return math.sqrt(target * target + 2 * .45 * max(0., maneuver.distanceMeters - 8.))


def cruise_ceiling(sm, CP, now_ns: int, cruise_mps: float) -> float | None:
  nav = current_instruction(sm, now_ns)
  if nav is None:
    return None
  cs, cc = sm['carState'], sm['carControl']
  if (not CP.openpilotLongitudinalControl or CP.passive or CP.dashcamOnly or not cc.longActive or
      cs.gasPressed or cs.brakePressed or not math.isfinite(cruise_mps) or cruise_mps <= 0):
    return None
  minimum = float(CP.minSteerSpeed)
  if not math.isfinite(minimum):
    return None
  for instruction in (nav.instruction, nav.nextManeuver):
    target = turn_speed(instruction, max(minimum, 0.))
    if target is not None and target + .25 < cruise_mps:
      return target
  return None


def matching_turn_signal(sm, now_ns: int, *, supported: bool) -> bool:
  nav = current_instruction(sm, now_ns) if supported else None
  if nav is None:
    return False
  cs, instruction = sm['carState'], nav.instruction
  matching = ((instruction.maneuverModifier in ('left', 'sharpLeft') and cs.leftBlinker and not cs.rightBlinker) or
              (instruction.maneuverModifier in ('right', 'sharpRight') and cs.rightBlinker and not cs.leftBlinker))
  return bool(instruction.maneuverType == 'turn' and matching and math.isfinite(cs.vEgo) and
              math.isfinite(instruction.distanceMeters) and
              0 <= instruction.distanceMeters <= min(250., max(30., 15. + max(0., cs.vEgo) * 12.)))


class TurnIntent:
  def __init__(self):
    self.key = None
    self.stop_hold = False

  def select(self, sm, now_ns: int, current_desire, *, supported: bool, model_stop: bool):
    nav = current_instruction(sm, now_ns) if supported else None
    key = (nav.sessionId, nav.startedMonoTime) if nav is not None else None
    if key != self.key:
      self.key, self.stop_hold = key, False
    if nav is None:
      return current_desire
    cs = sm['carState']
    try:
      stamp, plan = sm.logMonoTime['longitudinalPlan'], sm['longitudinalPlan']
      plan_valid = (sm.valid['longitudinalPlan'] and sm.alive['longitudinalPlan'] and
                    nav.startedMonoTime <= stamp <= now_ns <= stamp + 150_000_000 and
                    nav.startedMonoTime <= plan.modelMonoTime <= stamp)
    except (KeyError, AttributeError, TypeError):
      plan_valid = False
    if cs.standstill or cs.leftBlinker == cs.rightBlinker:
      self.stop_hold = False
    elif model_stop or (plan_valid and plan.shouldStop):
      self.stop_hold = True
    if self.stop_hold or not plan_valid:
      return current_desire
    return turn_desire(sm, now_ns, current_desire, supported=supported)
