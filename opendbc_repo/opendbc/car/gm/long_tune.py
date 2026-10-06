import math
from time import monotonic_ns
import numpy as np

from opendbc.car.gm.feature_capabilities import longitudinal_supported
from opendbc.car.gm.values import (CAR, NO_ACC_BOLT_CAR, ORDINARY_ASCM_CAR, ORDINARY_CAMERA_CAR, ORDINARY_SDGM_CAR,
                                 volt_cc_pedal_profile)
from opendbc.car.gm.aol import GM_BASE_GATEWAY_IDS


VOLT_TUNE_CARS = frozenset((CAR.CHEVROLET_VOLT, CAR.CHEVROLET_VOLT_2019,
                           CAR.CHEVROLET_VOLT_ASCM, CAR.CHEVROLET_VOLT_CAMERA, CAR.CHEVROLET_VOLT_CC))


CONFIGURABLE_ACC_TUNE_CARS = (ORDINARY_ASCM_CAR | ORDINARY_CAMERA_CAR | ORDINARY_SDGM_CAR |
                              GM_BASE_GATEWAY_IDS | NO_ACC_BOLT_CAR | frozenset((CAR.CHEVROLET_BOLT_EUV,
                                CAR.CHEVROLET_BOLT_ACC_2022_2023, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL)))

def tune_options(cp):
  if not longitudinal_supported(cp):
    return (0,)
  if cp.carFingerprint in VOLT_TUNE_CARS:
    return (0, 2)
  return (0, 1) if cp.carFingerprint in CONFIGURABLE_ACC_TUNE_CARS else (0,)


def acc_tune_limits(speed, accel_max, brake_switch, zero_gas):
  cap = min(accel_max, float(np.interp(speed, (0., 4., 12.), (1.25, 1.6, accel_max))))
  bias = int(round(np.interp(speed, (0., 6., 15., 30.), (40., 85., 130., 170.))))
  return cap, min(zero_gas, brake_switch + bias)


def volt_tune_kp(cp, installed):
  if cp.carFingerprint == CAR.CHEVROLET_VOLT_CC and volt_cc_pedal_profile(cp) is None:
    return installed
  return ((0., 4., 12., 35.), (.10, .072, .050, .040))


class VoltTuneStopPolicy:
  MAX_EVIDENCE_AGE_NS = 20_000_000

  def __init__(self, installed, starting_speed, evidence_type, *, clock=monotonic_ns):
    self.installed = installed
    self.starting_speed = max(starting_speed, .35)
    self.evidence_type = evidence_type
    self.clock = clock
    self.drive_id = 0
    self.last_ns = 0
    self.start_authorized = False
    self.pending_start = False

  def reset(self):
    self.installed.reset()
    self.drive_id = 0
    self.last_ns = 0
    self.start_authorized = False
    self.pending_start = False

  def transition(self, native, previous, active, cs, target, should_stop, evidence):
    from opendbc.car.structs import car
    states = car.CarControl.Actuators.LongControlState
    state = self.installed.transition(native, previous, active, cs, target, should_stop, evidence)
    self.start_authorized = False
    now = self.clock()
    valid = (active and not should_stop and isinstance(evidence, self.evidence_type) and
             cs.canValid and not cs.canTimeout and not cs.brakePressed and not cs.gasPressed and
             math.isfinite(target) and target > 0. and math.isfinite(cs.vEgo) and
             evidence.drive_id > 0 and evidence.observed_ns > evidence.drive_id and
             0 <= now - evidence.observed_ns <= self.MAX_EVIDENCE_AGE_NS and
             isinstance(evidence.has_lead, bool))
    advancing = (valid and evidence.drive_id == self.drive_id and
                 0 < evidence.observed_ns - self.last_ns <= self.MAX_EVIDENCE_AGE_NS)
    if valid:
      if not advancing:
        self.pending_start = previous in (states.off, states.stopping) and state == states.pid
      self.drive_id, self.last_ns = evidence.drive_id, evidence.observed_ns
    else:
      self.drive_id = self.last_ns = 0
      self.pending_start = False
    if not active or should_stop:
      return state
    if not advancing:
      return states.pid if state == states.starting or previous == states.starting else state
    if previous == states.starting:
      state = states.pid if cs.vEgo > self.starting_speed else states.starting
    elif state == states.pid and (previous in (states.off, states.stopping) or self.pending_start):
      state = states.starting
    self.pending_start = False
    self.start_authorized = state == states.starting
    return state

  def starting_output(self, target, accel_limits, context):
    # Current planner ownership requires continuing positive, fresh launch intent.
    if (not self.start_authorized or not math.isfinite(target) or target <= 0. or
        not 0 <= self.clock() - self.last_ns <= self.MAX_EVIDENCE_AGE_NS):
      return 0.
    if context.traffic_mode or context.custom_acceleration or (context.has_lead is True and target <= .25):
      output = float(np.clip(target, 0., 1.15))
    elif context.profile_max_accel is not None and context.profile_max_accel > 0.:
      output = min(1.15, context.profile_max_accel)
    else:
      output = 1.15
    return float(np.clip(output, *accel_limits))


class VoltTunePolicy:
  def __init__(self, cp, installed):
    self.installed = installed
    self.manual_cc = cp.carFingerprint == CAR.CHEVROLET_VOLT_CC and volt_cc_pedal_profile(cp) is None
    self.kp = volt_tune_kp(cp, installed.kp)
    self.ki = (None if cp.carFingerprint == CAR.CHEVROLET_VOLT_CC and volt_cc_pedal_profile(cp) is None
               else ((0., 4., 12., 35.), (.025, .030, .040, .055)))
    self.friction_variant = installed.friction_variant
    self.stopping_decel_rate = installed.stopping_decel_rate
    self.target = getattr(installed, "target", None)

  def reset(self):
    self.installed.reset()

  def stop_policy(self):
    from opendbc.car.gm.cc_longitudinal import VoltCcEvidence
    stop = self.installed.stop_policy()
    return (VoltTuneStopPolicy(stop, .75, VoltCcEvidence) if self.manual_cc
            else VoltTuneStopPolicy(stop, stop.starting_speed, stop.evidence_type))

  def stopping_output(self, *args, **kwargs):
    return self.installed.stopping_output(*args, **kwargs)

  def prepare_pid(self, *args, **kwargs):
    return self.installed.prepare_pid(*args, **kwargs)

  def shape_output(self, *args, **kwargs):
    return self.installed.shape_output(*args, **kwargs)

  def feedforward(self, *args, **kwargs):
    return self.installed.feedforward(*args, **kwargs)


def selected_policy(cp, installed, selection):
  return VoltTunePolicy(cp, installed) if installed is not None and selection == 2 and 2 in tune_options(cp) else installed
