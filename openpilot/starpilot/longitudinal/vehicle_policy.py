"""Select an admitted vehicle-owned longitudinal tuning policy."""

from opendbc.car.gm.conventional_pedal import policy_for as conventional_pedal_policy_for
from opendbc.car.gm.camera import policy_for as camera_policy_for
from opendbc.car.gm.hybrid_cc import policy_for as hybrid_policy_for
from opendbc.car.gm.ordinary_cc import policy_for as ordinary_cc_policy_for
from opendbc.car.gm.bolt_cc import policy_for as bolt_cc_policy_for
from opendbc.car.gm.longitudinal import policy_for as gm_pedal_policy_for, volt_policy_for, euv_policy_for, ascm_policy_for, sdgm_policy_for

from opendbc.car.gm.cc_longitudinal import policy_for as volt_cc_policy_for
from opendbc.car.gm.suburban import (policy_for as suburban_policy_for,
                                     stopping_decel_rate as gm_suburban_stopping_decel_rate)
from opendbc.car.hyundai.g90_longitudinal import (stopping_decel_rate as hyundai_stopping_decel_rate,
                                                 forecast_should_stop as hyundai_forecast_should_stop)


def installed_policy_for(cp):
  return (hybrid_policy_for(cp) or suburban_policy_for(cp) or conventional_pedal_policy_for(cp) or camera_policy_for(cp) or ordinary_cc_policy_for(cp) or
          sdgm_policy_for(cp) or ascm_policy_for(cp) or gm_pedal_policy_for(cp) or volt_policy_for(cp) or
          euv_policy_for(cp) or volt_cc_policy_for(cp) or bolt_cc_policy_for(cp))


def policy_for(cp, startup_preferences=None):
  from opendbc.car.gm.long_tune import selected_policy
  installed = installed_policy_for(cp)
  selection = getattr(startup_preferences, "gm_longitudinal_tune", 0)
  return selected_policy(cp, installed, selection)


def stopping_decel_rate(cp, policy):
  from opendbc.car.toyota.prius_longitudinal import stopping_decel_rate as prius_filter_stop_rate
  rate = prius_filter_stop_rate(cp)
  if rate is not None:
    return rate
  from opendbc.car.toyota.values import stopping_decel_rate as toyota_stopping_decel_rate
  rate = toyota_stopping_decel_rate(cp)
  if rate is not None:
    return rate
  from opendbc.car.honda.parameter_profiles import stopping_decel_rate as honda_stopping_decel_rate
  rate = honda_stopping_decel_rate(cp)
  if rate is not None:
    return rate
  rate = hyundai_stopping_decel_rate(cp)
  if rate is not None:
    return rate
  rate = gm_suburban_stopping_decel_rate(cp)
  if rate is not None:
    return rate
  return policy.stopping_decel_rate if policy is not None else 1.0


def stopping_policy_for(cp, dt):
  from opendbc.car.hyundai.blended_stopping import policy_for as blended_stopping_policy_for
  from opendbc.car.hyundai.ev9_stopping import policy_for as ev9_stopping_policy_for
  return ev9_stopping_policy_for(cp, dt) or blended_stopping_policy_for(cp, dt)


def forecast_should_stop(cp, speeds, time_indices, action_t, fallback):
  from opendbc.car.honda.parameter_profiles import forecast_should_stop as honda_forecast_should_stop
  decision = honda_forecast_should_stop(cp, speeds, time_indices, action_t)
  if decision is not None:
    return decision
  decision = hyundai_forecast_should_stop(cp, speeds, time_indices, action_t)
  return fallback if decision is None else decision


def tracked_lead_scale(cp):
  from opendbc.car.hyundai.gv70_longitudinal import tracked_lead_scale as hyundai_tracked_lead_scale
  return hyundai_tracked_lead_scale(cp)


def planner_cost_owner(cp):
  from opendbc.car.hyundai.gv70_costs import eligible
  if not eligible(cp):
    return None
  from openpilot.starpilot.longitudinal.gv70_cost_context import GV70CostContext
  return GV70CostContext()


def far_follow_owner(cp, dt):
  from openpilot.starpilot.longitudinal.niro_follow import eligible, NiroFarFollow
  return NiroFarFollow(dt) if eligible(cp) else None
