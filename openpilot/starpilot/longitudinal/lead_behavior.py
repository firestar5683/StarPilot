"""Lead departure and inside-gap responses, bounded by the native planner."""

import math

from openpilot.starpilot.longitudinal.experimental_release import valid_key, SOURCES, MAX_SOURCE_AGE_NS


def current_leads(sm, cp, now_ns, key):
  try:
    if not valid_key(key):
      return None
    if not all(sm.valid[name] and sm.alive[name] and key[2] <= sm.logMonoTime[name] <= now_ns and
               now_ns - sm.logMonoTime[name] <= MAX_SOURCE_AGE_NS for name in SOURCES):
      return None
    car = sm['carState']
    if (not cp.openpilotLongitudinalControl or cp.passive or cp.dashcamOnly or cp.notCar or
        not sm['carControl'].longActive or not sm['selfdriveState'].enabled or
        not car.canValid or car.canTimeout or car.brakePressed or car.gasPressed or sm['controlsState'].forceDecel):
      return None
    leads = tuple(lead for lead in (sm['radarState'].leadOne, sm['radarState'].leadTwo) if lead.present)
    for lead in leads:
      if not all(math.isfinite(float(getattr(lead, field))) for field in ('dRel', 'vLead', 'aLeadK', 'yRel', 'modelProb')):
        return None
    return leads
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return None


def inside_gap_cap(lead, speed, follow_seconds, accel_min):
  """Dom's modest closing-speed response once inside the selected following gap."""
  if (speed < 8.0 or lead.vLead < 5.0 or abs(lead.yRel) > 1.75 or
      not lead.radar and lead.modelProb < .95 or speed - lead.vLead < .5):
    return None
  desired_gap = speed * follow_seconds + 6.0 + (speed ** 2 - max(lead.vLead, 0.) ** 2) / 5.0
  deficit = desired_gap - lead.dRel
  if deficit <= max(3.0, .15 * desired_gap):
    return None
  brake_deficit = .25 * desired_gap
  deficit_factor = max(0., min(1., (deficit - brake_deficit) / max(brake_deficit, 1.)))
  closing_factor = max(0., min(1., (speed - lead.vLead - 1.) / 1.5))
  return max(accel_min, -min(.65, .45 * deficit_factor + .20 * closing_factor))


def departure_floor(lead, speed, model_accel):
  """Dom's positive-model departure assist; native lead/braking targets still win."""
  if (speed > 2.0 or lead.vLead < .6 or lead.vLead - speed < .5 or lead.dRel < 3.5 or
      lead.aLeadK < -.2 or model_accel < .12 or abs(lead.yRel) > 1.75 or
      not lead.radar and lead.modelProb < .85):
    return None
  gap_factor = max(0., min(1., (lead.dRel - 3.5) / 2.5))
  lead_factor = max(0., min(1., (lead.vLead - .6) / 1.6))
  cap = .25 + .30 * max(0., min(1., .55 * lead_factor + .45 * gap_factor))
  return min(cap, max(model_accel + .10, .25))


def adjust(*, target, sm, cp, now_ns, key, follow_seconds, mpc_target, cruise_target, model_target,
           stopping, force_stop, traffic_mode, accel_min):
  leads = current_leads(sm, cp, now_ns, key)
  if not leads or traffic_mode is not False or force_stop or stopping or not .5 <= follow_seconds <= 3.:
    return target
  speed = float(sm['carState'].vEgo)
  if not all(math.isfinite(float(value)) for value in
             (target, speed, follow_seconds, mpc_target, cruise_target, model_target, accel_min)):
    return target
  # A departure may only recover a conservative model acceleration. It cannot
  # override either native MPC lead braking, cruise limits, stop or another lead.
  if (sm['selfdriveState'].experimentalMode and not stopping and
      not sm['modelV2'].action.shouldStop and all(lead.vLead > speed and lead.dRel >= 3.5 for lead in leads)):
    floors = [floor for lead in leads if (floor := departure_floor(lead, speed, model_target)) is not None]
    if floors:
      target = max(target, min(min(floors), mpc_target, cruise_target))
  caps = [cap for lead in leads if (cap := inside_gap_cap(lead, speed, follow_seconds, accel_min)) is not None]
  return min(target, min(caps)) if caps else target
