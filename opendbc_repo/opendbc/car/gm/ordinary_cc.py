"""Ordinary conventional-cruise button law and observed-counter cadence."""

from dataclasses import dataclass

from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.gm.values import CAR, CruiseButtons, is_ordinary_cc_profile, is_volt_cc_longitudinal, malibu_hybrid_profile
from opendbc.car.gm.longitudinal import GMOrdinaryLongitudinalPolicy, _GMDefaultStopPolicy
from opendbc.car.gm.cc_longitudinal import VoltCcEvidence


def button_request(speed, stock_speed, accel, min_enable, metric):
  units = CV.MS_TO_KPH if metric else CV.MS_TO_MPH
  stock = int(round(stock_speed * units))
  desired = int(round((speed * 1.01 + 3 * accel) * units))
  rate = 1.0 if abs(accel) <= .15 else .2
  if min_enable - desired / units > 3.25:
    return CruiseButtons.CANCEL, rate, 0
  if desired < stock and stock > min_enable * units + 1:
    return CruiseButtons.DECEL_SET, rate, stock - 1
  if desired > stock:
    return CruiseButtons.RES_ACCEL, rate, stock + 1
  return CruiseButtons.INIT, rate, stock


class ButtonCadence:
  def __init__(self, burst):
    self.burst = burst
    self.last_frame = 0
    self.observed_counter = -1
    self.observed_frame = 0
    self.remaining = 0
    self.button = CruiseButtons.INIT
    self.last_counter = -1
    self.last_direction_frame = None
    self.last_cancel_frame = None

  def reset_burst(self):
    self.remaining = 0
    self.button = CruiseButtons.INIT
    self.last_counter = -1
    self.observed_counter = -1

  def can_send(self, frame, button):
    last_sent = self.last_cancel_frame if button == CruiseButtons.CANCEL else self.last_direction_frame
    return last_sent is None or frame - last_sent > 2

  def note_sent(self, frame, button):
    if button == CruiseButtons.CANCEL:
      self.last_cancel_frame = frame
    else:
      self.last_direction_frame = frame

  def ready(self, frame, counter, button, rate):
    if not self.burst:
      if button != CruiseButtons.INIT and (frame - self.last_frame) * .01 > rate and self.can_send(frame, button):
        self.last_frame = frame
        self.note_sent(frame, button)
        return True
      return False
    if self.observed_counter != counter:
      self.observed_counter = counter
      self.observed_frame = frame
    if button == CruiseButtons.INIT:
      self.remaining = 0
      self.button = CruiseButtons.INIT
      return False
    if self.remaining > 0 and self.button != button:
      self.remaining = 0
    if self.remaining == 0:
      if (frame - self.last_frame) * .01 <= rate:
        return False
      self.last_frame = frame
      self.button = button
      self.remaining = 6
      self.last_counter = -1
    if frame - self.observed_frame < 1 or self.last_counter == counter:
      return False
    # All ordinary-CC writers share the native direction/CANCEL clocks.
    if not self.can_send(frame, button):
      return False
    self.note_sent(frame, button)
    self.last_counter = counter
    self.remaining -= 1
    return True


@dataclass(frozen=True)
class PhysicalObservation:
  observed_ns: int
  source_ns: tuple[int, ...]
  neutral_button: bool
  forward_wheels: bool
  button_credit_ns: int

  def sources_current(self, now_ns):
    limits = (300_000_000, 100_000_000, 100_000_000, 100_000_000, 300_000_000, 100_000_000)
    return (len(self.source_ns) == 6 and self.observed_ns > 0 and 0 <= now_ns - self.observed_ns <= 150_000_000 and
            all(source > 0 and 0 <= now_ns - source <= limit for source, limit in zip(self.source_ns, limits, strict=True)))

  def current(self, now_ns):
    return self.neutral_button and self.forward_wheels and self.sources_current(now_ns)


class LongitudinalPolicy(GMOrdinaryLongitudinalPolicy):
  stopping_decel_rate = 11.18

  def __init__(self, malibu):
    self.kp = ((10.7, 10.8, 28.0), (0.0, 20.0, 20.0) if malibu else (0.0, 5.0, 2.0))
    self.starting_speed = .75 if malibu else .5

  def stop_policy(self):
    return _GMDefaultStopPolicy(self.starting_speed, VoltCcEvidence)

def policy_for(cp):
  return LongitudinalPolicy(cp.carFingerprint == CAR.CHEVROLET_MALIBU_CC) if is_ordinary_cc_profile(cp) and cp.openpilotLongitudinalControl else None


def control_transport_required(cp):
  return is_ordinary_cc_profile(cp) or is_volt_cc_longitudinal(cp) or malibu_hybrid_profile(cp) is not None
