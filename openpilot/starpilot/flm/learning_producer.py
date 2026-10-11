"""Bounded 20 Hz physical linear-factor collection beside native TLS."""
from collections import deque
import math
import time
import uuid

import numpy as np
from opendbc.car.car_helpers import interfaces
from openpilot.cereal import messaging
from openpilot.common.constants import ACCELERATION_DUE_TO_GRAVITY
from openpilot.selfdrive.locationd.helpers import Pose, PoseCalibrator
from openpilot.starpilot.flm.automatic import EvidenceWindow, PhysicalPoint, evaluate_linear_factor, identity_digest, linear_policy
from openpilot.starpilot.flm.gm_evidence import FLMSample
from openpilot.starpilot.flm.learning_source import VERSION, conversion_identity, identity_for
from openpilot.starpilot.lateral.controller_selection import read_selection


class AutomaticLearningProducer:
  def __init__(self, CP, params):
    self.CP, self.params = CP, params
    try:
      self.CI = interfaces[CP.carFingerprint](CP)
    except Exception:
      self.CI = None
    self.session, self.sequence = uuid.uuid4().hex, 0
    self.identity = None
    self.refresh_ns = self.last_boot = self.anchor = None
    self.windows = deque(maxlen=24)
    self.pending = deque(maxlen=16)
    self.control_history = deque(maxlen=128)
    self.frozen_lag = None
    self.window_direction = self.window_band = None
    self.calibrator = PoseCalibrator()
    self.calibration_frozen = False
    self.torque_times, self.torques = deque(maxlen=128), deque(maxlen=128)
    self.speed_times, self.speeds = deque(maxlen=128), deque(maxlen=128)
    self.rows, self.points = [], []
    self.last_control = 0
    self.excluded_until = 0
    self.reason = 'initializing'
    self.block = 0
    self.active_since_ns = None
    self.optional_errors = 0
    self.sealed = False
    self.result = None
    self.result_bounds = None
    self.evaluated_blocks = 0
    self.last_evaluation_ns = None

  def split(self, reason, *, hard=False, eligibility=True):
    self.rows, self.points = [], []
    self.pending.clear()
    self.window_direction = self.window_band = None
    self.sealed = False
    if eligibility:
      self.active_since_ns = None
    if hard:
      self.result = None
      self.result_bounds = None
      self.evaluated_blocks = 0
      self.last_evaluation_ns = None
      self.control_history.clear()
      self.torque_times.clear()
      self.torques.clear()
      self.speed_times.clear()
      self.speeds.clear()
      self.frozen_lag = None
      self.calibration_frozen = False
      self.last_control = 0
      self.last_boot = None
    self.reason = reason

  def fail(self, reason):
    self.optional_errors = min(self.optional_errors + 1, 2 ** 31 - 1)
    self.identity = None
    self.windows.clear()
    self.split(reason, hard=True)

  def update(self, sm, estimator):
    # An optional learner must never prevent the existing TLS publication.
    try:
      self._update(sm)
    except Exception:
      self.fail('optional_source_error')

  def _update(self, sm):
    now = time.monotonic_ns()
    boot = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    offset = boot - now
    if self.anchor is None:
      self.anchor = offset
    if abs(offset - self.anchor) > 1_000_000:
      self.windows.clear()
      self.split('clock_discontinuity', hard=True)
      self.anchor = offset
      return
    if self.refresh_ns is None or now - self.refresh_ns >= 1_000_000_000:
      selection = read_selection(self.params, self.CP)
      conversion = conversion_identity(self.CP, self.CI, selection.mode) if self.CI is not None else None
      identity, enabled, manual = identity_for(self.CP, selection.mode, self.params, conversion)
      identity = identity if enabled and not manual else None
      if identity != self.identity:
        self.windows.clear()
        self.split('identity_or_preference_changed', hard=True)
      self.identity, self.refresh_ns = identity, now
    if self.identity is None:
      self.split('unavailable')
      return
    required = ['carState', 'carControl', 'carOutput', 'controlsState', 'deviceMotion', 'extrinsicsCalibration', 'lateralDelay']
    if not sm.all_checks(required):
      self.split('source_checks')
      return
    age_limits = {'carState': 100_000_000, 'carControl': 100_000_000, 'carOutput': 100_000_000,
                  'controlsState': 100_000_000, 'deviceMotion': 100_000_000, 'lateralDelay': 500_000_000}
    if any(not sm.seen[s] or not 0 <= boot - sm.logMonoTime[s] <= limit for s, limit in age_limits.items()):
      self.split('source_age')
      return
    cs, cc = sm['carState'], sm['carControl']
    dm = sm['deviceMotion']
    if not 0 < int(dm.timestamp) <= boot or boot - int(dm.timestamp) > 100_000_000:
      self.split('pose_source_age')
      return
    live_lag = float(sm['lateralDelay'].lateralDelay)
    if not math.isfinite(live_lag) or not 0 <= live_lag <= .5:
      self.split('alignment_lag_invalid')
      return
    if self.frozen_lag is None:
      self.frozen_lag = live_lag
    # Freeze the externally supplied delay for this evidence identity.
    # Never tune delay against training or held-out response.
    lag = self.frozen_lag
    if sm['extrinsicsCalibration'].calStatus != 'calibrated':
      self.windows.clear()
      self.split('calibration_invalid', hard=True)
      return
    if not self.calibration_frozen:
      self.calibrator.feed_extrinsics_calibration(sm['extrinsicsCalibration'])
      self.calibration_frozen = True
    if sm.updated['carOutput']:
      self.torque_times.append(sm.logMonoTime['carOutput'] * 1e-9 + lag)
      self.torques.append(-sm['carOutput'].actuatorsOutput.torque)
    if sm.updated['carState']:
      self.speed_times.append(sm.logMonoTime['carState'] * 1e-9 + lag)
      self.speeds.append(cs.vEgo)
    if cs.steeringPressed or cs.brakePressed or cs.gasPressed:
      self.excluded_until = boot + 1_000_000_000
      self.split('driver_override')
      return
    if boot < self.excluded_until or not cc.latActive or not cs.canValid or cs.canTimeout:
      self.split('inactive_or_override_buffer')
      return
    if sm['controlsState'].lateralControlState.which() != 'torqueState':
      self.split('non_torque_controller')
      return
    lc = sm['controlsState'].lateralControlState.torqueState
    stamp = sm.logMonoTime['controlsState']
    if lc.saturated or not math.isfinite(lag) or not 0 <= lag <= .5 or abs(lc.desiredLateralJerk) > 1:
      self.split('saturation_or_nonsteady')
      return
    if not (dm.angularVelocityDevice.valid and dm.orientationNED.valid and dm.inputsOK and dm.sensorsOK and dm.posenetOK):
      self.split('pose_invalid')
      return
    if self.active_since_ns is None:
      self.active_since_ns = boot - self.anchor
    if self.last_boot is not None and not 0 < boot - self.last_boot <= 100_000_000:
      self.split('sample_gap')
    self.last_boot = boot
    if stamp <= self.last_control:
      return
    self.last_control = stamp
    row_ns = stamp + round(lag * 1e9) - self.anchor
    control_row = FLMSample(self.session, self.block, row_ns / 1e9, cs.vEgo, True, False, False,
      lc.actualLateralAccel, lc.desiredLateralAccel, lc.desiredLateralJerk, lc.error, lc.errorRate,
      lc.p, lc.i, lc.d, lc.f, lc.output, cs.steeringAngleDeg, cs.steeringTorque,
      cc.actuators.torque, sm['carOutput'].actuatorsOutput.torque, None)
    self.control_history.append((row_ns, control_row))
    if len(self.torques) < 100 or len(self.speeds) < 100:
      self.reason = 'alignment_history'
      return
    pose = Pose.from_device_motion(dm)
    calibrated = self.calibrator.build_calibrated_pose(pose)
    response_t = dm.timestamp * 1e-9
    for times in (self.torque_times, self.speed_times):
      before = [t for t in times if t <= response_t]
      after = [t for t in times if t >= response_t]
      if not before or not after or response_t - before[-1] > .1 or after[0] - response_t > .1:
        self.split('physical_alignment_gap')
        return
    torque = float(np.interp(response_t, self.torque_times, self.torques))
    speed = float(np.interp(response_t, self.speed_times, self.speeds))
    accel = float(speed * calibrated.angular_velocity.yaw - np.sin(pose.orientation.roll) * ACCELERATION_DUE_TO_GRAVITY)
    point_ns = int(dm.timestamp) - self.anchor
    eligible = [(ns, row) for ns, row in self.control_history if ns <= point_ns]
    if not eligible:
      return
    row_ns, row = eligible[-1]
    if not 0 <= point_ns - row_ns <= 30_000_000 or not all(math.isfinite(v) for v in (torque, speed, accel)) or speed <= 15:
      self.split('response_join')
      return
    if abs(accel) > 1 or not (-.5 <= torque < .5 and abs(torque) > .02):
      self.split('physical_response_bounds')
      return
    if self.active_since_ns is None or point_ns - round(lag * 1e9) - self.active_since_ns < 2_000_000_000:
      self.reason = 'active_history'
      return
    if abs(row.desired_la) <= .25:
      self.split('response_direction_unexcited')
      return
    direction = torque > 0
    band = row.v_ego >= 25
    if self.window_direction is not None and (direction != self.window_direction or band != self.window_band):
      self.split('direction_or_speed_band_changed', eligibility=False)
      return
    self.window_direction, self.window_band = direction, band
    if self.sealed:
      self.reason = 'maneuver_sealed'
      self.evaluate(now)
      return
    if self.pending and (point_ns <= self.pending[-1][2].mono_ns or row.t <= self.pending[-1][1].t):
      return
    self.pending.append((boot, row, PhysicalPoint(point_ns, torque, accel)))
    while self.pending and boot - self.pending[0][0] >= 350_000_000:
      _, accepted, point = self.pending.popleft()
      self.rows.append(accepted)
      self.points.append(point)
      if len(self.points) == 240:
        self.windows.append(EvidenceWindow(identity_digest(self.identity), f'{self.session}:{self.block}',
          tuple(self.rows), tuple(self.points), self.active_since_ns, round(self.frozen_lag * 1e9)))
        self.block += 1
        self.rows, self.points = [], []
        self.pending.clear()
        self.sealed = True
        break
    self.reason = 'collecting_independent_response'
    self.evaluate(now)

  def evaluate(self, now):
    # Physical maneuvers, not adjacent slices, own blocks. Fit once per new
    # block and no more than once per minute; publication never fits.
    if self.identity is None or self.block == self.evaluated_blocks or sum(len(w.response) for w in self.windows) < 4000:
      return
    if self.last_evaluation_ns is not None and now - self.last_evaluation_ns < 60_000_000_000:
      return
    self.result = evaluate_linear_factor(self.identity, tuple(self.windows),
      baseline_factor=float(self.identity['basis'][0]), vehicle_factor=float(self.CP.lateralTuning.torque.latAccelFactor),
      linear_conversion_verified=True, policy=linear_policy())
    self.result_bounds = (self.windows[0].response[0].mono_ns, self.windows[-1].response[-1].mono_ns)
    self.evaluated_blocks, self.last_evaluation_ns = self.block, now

  def get_msg(self):
    try:
      return self._get_msg()
    except Exception:
      self.fail('optional_publication_error')
      return None

  def _get_msg(self):
    now = time.monotonic_ns()
    msg = messaging.new_message('autoSteeringLearning')
    value = msg.autoSteeringLearning
    value.version, value.session, value.sequence = VERSION, self.session, self.sequence
    self.sequence += 1
    value.observedMonoTime, value.validUntilMonoTime = now, now + 500_000_000
    value.status = 'collecting' if self.identity is not None else 'unavailable'
    value.reason, value.family = self.reason, 'linearFactor' if self.identity is not None else 'none'
    if self.identity is not None:
      value.identity = self.identity
      if self.windows:
        value.sourceWindowStartMonoTime = self.windows[0].response[0].mono_ns
        value.sourceWindowEndMonoTime = self.windows[-1].response[-1].mono_ns
      if self.result is not None and self.result_bounds is not None:
        result = self.result
        value.sourceWindowStartMonoTime, value.sourceWindowEndMonoTime = self.result_bounds
        value.status = 'qualifiedFit' if result.status == 'qualified_fit' else result.status
        value.reason = result.reason
        value.acceptancePolicyId = result.acceptance_policy_id
        candidate, metrics = dict(result.candidate), dict(result.metrics)
        if 'latAccelFactor' in candidate:
          value.latAccelFactor = candidate['latAccelFactor']
        for target, source in (('trainWindows', 'trainWindows'), ('heldoutWindows', 'heldoutWindows'),
                               ('trainBaselineLoss', 'trainBaselineMSE'), ('trainCandidateLoss', 'trainFitMSE'),
                               ('heldoutBaselineLoss', 'heldoutBaselineMSE'), ('heldoutCandidateLoss', 'heldoutFitMSE')):
          if source in metrics:
            setattr(value, target, int(metrics[source]) if target.endswith('Windows') else metrics[source])
    msg.valid = True
    return msg
