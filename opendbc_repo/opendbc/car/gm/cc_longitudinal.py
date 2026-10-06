"""Exact Volt conventional-cruise owner; physical ECU retains propulsion."""
from dataclasses import dataclass
import math

from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.gm.values import CruiseButtons, is_volt_cc_longitudinal
from opendbc.car.gm.longitudinal import GMVoltLongitudinalPolicy
from opendbc.car.structs import car


def volt_cc_forward_gear(gear) -> bool:
  return gear in (car.CarState.GearShifter.drive, car.CarState.GearShifter.low)


@dataclass(frozen=True)
class VoltCcEvidence:
  drive_id: int
  observed_ns: int
  has_lead: bool


@dataclass(frozen=True)
class VoltCcPhysical:
  observed_ns: int
  source_ns: tuple[int, ...]
  neutral_button: bool
  forward_wheels: bool
  button_credit_ns: int

  def sources_current(self, now_ns: int) -> bool:
    return (len(self.source_ns) == 7 and self.observed_ns > 0 and 0 <= now_ns - self.observed_ns <= 150_000_000 and
            all(source > 0 and 0 <= now_ns - source <= limit for source, limit in
                zip(self.source_ns, (300_000_000, 100_000_000, 100_000_000, 100_000_000, 300_000_000,
                                     100_000_000, 100_000_000), strict=True)))

  def current(self, now_ns: int) -> bool:
    return self.neutral_button and self.forward_wheels and self.sources_current(now_ns)


def button_request(speed: float, stock_speed: float, target: float, cruise_kph: float,
                   has_lead: bool, metric: bool) -> tuple[int, float]:
  """Original Volt request law, equal physical acceleration, no raw gas conversion."""
  if not all(math.isfinite(value) for value in (speed, stock_speed, target, cruise_kph)):
    return CruiseButtons.INIT, math.inf
  convert = CV.MS_TO_KPH if metric else CV.MS_TO_MPH
  stock = int(round(stock_speed * convert))
  ego = speed * convert
  requested = (speed * 1.01 + 3 * target) * convert
  deadband = (2. if has_lead else 5.) * (CV.MPH_TO_KPH if metric else 1.)
  cap = int(round(cruise_kph if metric else cruise_kph * CV.KPH_TO_MPH)) if 0. < cruise_kph < 255. else None
  toward = cap is not None and ((target > 0 and stock < cap) or (target < 0 and stock > cap))
  if cap is not None and ((target > 0 and stock >= cap) or (target < 0 and stock <= cap and not has_lead)):
    return CruiseButtons.INIT, math.inf
  if target == 0 or (not toward and abs(requested - stock) <= deadband):
    return CruiseButtons.INIT, math.inf
  if target < 0:
    return CruiseButtons.DECEL_SET, .2 if stock > ego + 3. else max(1. / (-target * convert), .2)
  return CruiseButtons.RES_ACCEL, .2 if stock < ego - 3. else max(1. / (target * convert), .2)


class VoltCcStopPolicy:
  evidence_type = VoltCcEvidence

  def __init__(self):
    self.reset()

  def reset(self):
    self.drive_id = self.last_ns = self.release_since_ns = None

  def transition(self, native, previous, active, cs, target, should_stop, evidence):
    states = car.CarControl.Actuators.LongControlState
    if not active:
      self.reset()
      return states.off
    valid = (isinstance(evidence, VoltCcEvidence) and cs.canValid and not cs.canTimeout and
             not cs.brakePressed and not cs.gasPressed and math.isfinite(target) and math.isfinite(cs.vEgo) and
             evidence.drive_id > 0 and evidence.observed_ns > evidence.drive_id and type(evidence.has_lead) is bool)
    if not valid:
      self.reset()
      return states.stopping if previous == states.stopping else native
    if self.drive_id != evidence.drive_id or self.last_ns is None or not 0 < evidence.observed_ns - self.last_ns <= 20_000_000:
      self.release_since_ns = None
    self.drive_id, self.last_ns = evidence.drive_id, evidence.observed_ns
    if should_stop:
      self.release_since_ns = None
      return states.stopping
    if previous != states.stopping:
      self.release_since_ns = None
      return native
    immediate = cs.vEgo > .75 or (evidence.has_lead and target > .15) or (target >= .45 and not cs.cruiseState.standstill)
    if target > .15:
      if self.release_since_ns is None:
        self.release_since_ns = evidence.observed_ns
    else:
      self.release_since_ns = None
    settled = self.release_since_ns is not None and evidence.observed_ns - self.release_since_ns >= 340_000_000
    return states.pid if immediate or settled else states.stopping


class VoltCcLongitudinalPolicy(GMVoltLongitudinalPolicy):
  stopping_decel_rate = 11.18
  kp = ((10.7, 10.8, 28.), (0., 5., 2.))
  stop_policy = VoltCcStopPolicy

  def stopping_output(self, output, target, should_stop, cs):
    speed = cs.vEgo
    if should_stop and not cs.brakePressed and speed > 1.75 and target < output - .25:
      points, values = (1.75, 3., 6., 10.), (.02, .03, .05, .07)
      step = values[-1]
      for low, high, a, b in zip(points[:-1], points[1:], values[:-1], values[1:], strict=True):
        if low <= speed <= high:
          step = a + (b - a) * (speed - low) / (high - low)
          break
      return max(target, output - step)
    return output


def policy_for(cp):
  return VoltCcLongitudinalPolicy() if is_volt_cc_longitudinal(cp) else None
