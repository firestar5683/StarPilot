import math
import numpy as np
from opendbc.car import Bus, create_gas_interceptor_command, make_tester_present_msg, rate_limit, structs, ACCELERATION_DUE_TO_GRAVITY, DT_CTRL
from opendbc.car.lateral import apply_meas_steer_torque_limits, apply_std_steer_angle_limits, common_fault_avoidance
from opendbc.car.can_definitions import CanData
from opendbc.car.carlog import carlog
from opendbc.car.common.filter_simple import FirstOrderFilter, HighPassFilter
from opendbc.car.common.pid import PIDController
from opendbc.car.secoc import add_mac, build_sync_mac
from opendbc.car.interfaces import CarControllerBase
from opendbc.car.toyota import toyotacan
from opendbc.car.toyota.values import CAR, MIN_ACC_SPEED, NO_STOP_TIMER_CAR, PEDAL_TRANSITION, TSS2_CAR, \
                                        CarControllerParams, ToyotaFlags, \
                                        UNSUPPORTED_DSU_CAR
from opendbc.can import CANPacker

Ecu = structs.CarParams.Ecu
LongCtrlState = structs.CarControl.Actuators.LongControlState
SteerControlType = structs.CarParams.SteerControlType
VisualAlert = structs.CarControl.HUDControl.VisualAlert

# The up limit allows the brakes/gas to unwind quickly leaving a stop,
# the down limit roughly matches the rate of ACCEL_NET, reducing PCM compensation windup
ACCEL_WINDUP_LIMIT = 4.0 * DT_CTRL * 3  # m/s^2 / frame
ACCEL_WINDDOWN_LIMIT = -4.0 * DT_CTRL * 3  # m/s^2 / frame
ACCEL_PID_UNWIND = 0.03 * DT_CTRL * 3  # m/s^2 / frame
PRIUS_INTEGRAL_MISMATCH_UNWIND = 8.0
PRIUS_POSITIVE_FEEDFORWARD_SCALE = 0.7

MAX_PITCH_COMPENSATION = 1.5  # m/s^2
TOYOTA_COAST_BRAKE_MIN_SPEED = 15.0  # m/s
TOYOTA_COAST_BRAKE_ENABLE_ACCEL = -0.10  # m/s^2
TOYOTA_COAST_BRAKE_DISABLE_ACCEL = -0.06  # m/s^2
TOYOTA_NO_LEAD_COAST_BRAKE_ACCEL = -0.30  # m/s^2
TOYOTA_INTERCEPTOR_COMFORT_TARGET_ACCEL = 2.0  # m/s^2

# LKA limits
# EPS faults if you apply torque while the steering rate is above 100 deg/s for too long
MAX_STEER_RATE = 100  # deg/s
MAX_STEER_RATE_FRAMES = 18  # tx control frames needed before torque can be cut

# EPS allows user torque above threshold for 50 frames before permanently faulting
MAX_USER_TORQUE = 500

PARK = structs.CarState.GearShifter.park

# Lock / unlock door commands - Credit goes to AlexandreSato!
LOCK_CMD = b"\x40\x05\x30\x11\x00\x80\x00\x00"
UNLOCK_CMD = b"\x40\x05\x30\x11\x00\x40\x00\x00"


def get_long_tune(CP, params):
  kiBP = [2., 5.]
  kiV = [0.5, 0.25]
  k_f = 1.0

  if CP.carFingerprint == CAR.TOYOTA_PRIUS:
    k_f = 0.8
  elif CP.carFingerprint not in TSS2_CAR:
    kiBP = [0., 5., 35.]
    kiV = [3.6, 2.4, 1.5]

  return PIDController(0.0, (kiBP, kiV), k_f=k_f,
                       pos_limit=params.ACCEL_MAX, neg_limit=params.ACCEL_MIN,
                       rate=1 / (DT_CTRL * 3))


def update_permit_braking(current: bool, net_acceleration_request_min: float, stopping: bool,
                          long_active: bool, v_ego: float, lead_visible: bool) -> bool:
  if stopping or not long_active:
    return True

  if not lead_visible and v_ego >= TOYOTA_COAST_BRAKE_MIN_SPEED:
    return net_acceleration_request_min <= TOYOTA_NO_LEAD_COAST_BRAKE_ACCEL

  # At cruising speeds, some Toyota platforms turn tiny negative accel corrections
  # into noticeable brake taps. Keep a small coast-only band so mild follow/cruise
  # trims stay off the brakes while still allowing real negative requests through.
  if v_ego >= TOYOTA_COAST_BRAKE_MIN_SPEED:
    if net_acceleration_request_min <= TOYOTA_COAST_BRAKE_ENABLE_ACCEL:
      return True
    if net_acceleration_request_min >= TOYOTA_COAST_BRAKE_DISABLE_ACCEL:
      return False
    return current

  if net_acceleration_request_min < 0.2:
    return True
  if net_acceleration_request_min > 0.3:
    return False
  return current


def limit_interceptor_pcm_accel(pcm_accel_cmd: float, target_accel: float, stopping: bool, v_ego: float) -> float:
  if stopping:
    return pcm_accel_cmd

  # The Toyota long path should not cross the accel sign against a strong planner
  # request on pedal/SDSU cars during ordinary driving.
  if target_accel > 0.15 and pcm_accel_cmd < 0.0:
    positive_floor = float(np.interp(v_ego, [0.0, 5.0, 15.0], [0.12, 0.08, 0.0]))
    pcm_accel_cmd = max(pcm_accel_cmd, positive_floor)
  elif target_accel < -0.15 and pcm_accel_cmd > 0.0:
    negative_floor = float(np.interp(v_ego, [0.0, 5.0, 15.0], [-0.12, -0.08, 0.0]))
    pcm_accel_cmd = min(pcm_accel_cmd, negative_floor)

  if target_accel <= -1.6:
    return pcm_accel_cmd

  if abs(target_accel) > TOYOTA_INTERCEPTOR_COMFORT_TARGET_ACCEL:
    return pcm_accel_cmd

  lower_delta = float(np.interp(v_ego, [0.0, 5.0, 15.0], [0.20, 0.25, 0.35]))
  upper_delta = float(np.interp(v_ego, [0.0, 5.0, 15.0], [0.25, 0.30, 0.40]))
  limited = float(np.clip(pcm_accel_cmd, target_accel - lower_delta, target_accel + upper_delta))

  # Pedal/SDSU cars can feel especially surgey if the Toyota longitudinal controller
  # swings far away from the planner target. Bias comfort-zone requests back toward
  # the planner while still allowing some controller correction.
  target_weight = float(np.interp(v_ego, [0.0, 5.0, 15.0], [0.8, 0.65, 0.5]))
  limited = (target_weight * target_accel) + ((1.0 - target_weight) * limited)

  if target_accel > 0.15:
    limited = max(limited, float(np.interp(v_ego, [0.0, 5.0, 15.0], [0.10, 0.05, 0.0])))
  elif target_accel < -0.15:
    limited = min(limited, float(np.interp(v_ego, [0.0, 5.0, 15.0], [-0.10, -0.05, 0.0])))

  return limited


def limit_interceptor_stopping_accel(pcm_accel_cmd: float, target_accel: float, stopping: bool, v_ego: float, lead_visible: bool) -> float:
  if not stopping or lead_visible or pcm_accel_cmd >= 0.0 or v_ego >= 2.5:
    return pcm_accel_cmd

  # Pedal/SDSU Toyotas can feel abrupt in the last few feet of a no-lead stop
  # because stopping state can hold onto a stale strong negative command even
  # after the planner target has already softened. Keep real lead stops
  # untouched, but let the last 2-3 mph of a no-lead stop unwind toward the
  # current planner target instead of shoving through zero.
  stop_floor = float(np.interp(v_ego, [0.0, 0.2, 0.5, 0.9, 1.5, 2.5], [-0.72, -0.76, -0.82, -0.92, -1.05, -1.20]))
  target_buffer = float(np.interp(v_ego, [0.0, 0.5, 1.5, 2.5], [0.08, 0.10, 0.15, 0.20]))
  planner_floor = float(target_accel) - target_buffer
  return max(pcm_accel_cmd, max(stop_floor, planner_floor))


def limit_prius_stopping_accel(pcm_accel_cmd: float, target_accel: float, stopping: bool, v_ego: float, lead_visible: bool) -> float:
  if not stopping or pcm_accel_cmd >= 0.0 or v_ego >= 1.5:
    return pcm_accel_cmd

  # Prius can hold onto a stale full negative stop command at standstill even after the
  # planner has already softened. Keep enough brake to hold the stop, but let the command
  # unwind toward the live planner target so launches are not delayed and stop transitions
  # are less abrupt.
  if target_accel <= -1.8:
    return pcm_accel_cmd

  stop_floor = float(np.interp(v_ego,
                               [0.0, 0.2, 0.5, 0.9, 1.5],
                               [-0.96, -1.00, -1.08, -1.18, -1.35] if lead_visible else [-0.84, -0.88, -0.96, -1.08, -1.24]))
  target_buffer = float(np.interp(v_ego, [0.0, 0.5, 1.5], [0.06, 0.10, 0.16]))
  planner_floor = float(target_accel) - target_buffer
  return max(pcm_accel_cmd, max(stop_floor, planner_floor))


class CarController(CarControllerBase):
  def __init__(self, dbc_names, CP):
    super().__init__(dbc_names, CP)
    self.params = CarControllerParams(self.CP)
    self.last_torque = 0
    self.last_angle = 0
    self.alert_active = False
    self.last_standstill = False
    self.standstill_req = False
    self.permit_braking = True
    self.steer_rate_counter = 0
    self.distance_button = 0

    # *** start long control state ***
    self.long_pid = get_long_tune(self.CP, self.params)
    self.aego = FirstOrderFilter(0.0, 0.25, DT_CTRL * 3)
    self.pitch = FirstOrderFilter(0, 0.5, DT_CTRL)
    self.pitch_hp = HighPassFilter(0.0, 0.25, 1.5, DT_CTRL)

    self.accel = 0
    self.prev_accel = 0
    # *** end long control state ***

    self.packer = CANPacker(dbc_names[Bus.pt])

    self.secoc_lka_message_counter = 0
    self.secoc_lta_message_counter = 0
    self.secoc_acc_message_counter = 0
    self.secoc_prev_reset_counter = 0

    self.doors_locked = False

  def _compute_interceptor_gas_cmd(self, CC, CS):
    if not (self.CP.enableGasInterceptorDEPRECATED and self.CP.openpilotLongitudinalControl and CC.longActive):
      return 0.0

    if self.CP.minEnableSpeed < 0.0:
      return 0.12 if CS.out.standstill and self.accel > 0.0 else 0.0

    max_interceptor_gas = 0.5
    if self.CP.carFingerprint == CAR.TOYOTA_RAV4:
      pedal_scale = float(np.interp(CS.out.vEgo, [0.0, MIN_ACC_SPEED, MIN_ACC_SPEED + PEDAL_TRANSITION], [0.15, 0.3, 0.0]))
    elif self.CP.carFingerprint == CAR.TOYOTA_COROLLA:
      pedal_scale = float(np.interp(CS.out.vEgo, [0.0, MIN_ACC_SPEED, MIN_ACC_SPEED + PEDAL_TRANSITION], [0.3, 0.4, 0.0]))
    else:
      pedal_scale = float(np.interp(CS.out.vEgo, [0.0, MIN_ACC_SPEED, MIN_ACC_SPEED + PEDAL_TRANSITION], [0.4, 0.5, 0.0]))

    pedal_offset = float(np.interp(CS.out.vEgo, [0.0, 2.3, MIN_ACC_SPEED + PEDAL_TRANSITION], [-0.4, 0.0, 0.2]))
    pedal_command = pedal_scale * (self.accel + pedal_offset)
    return float(np.clip(pedal_command, 0.0, max_interceptor_gas))

  def _update_standstill_request(self, CC, CS, actuators, starpilot_toggles):
    # Older TSS-P platforms need a standstill latch pulse, then an explicit release to move again.
    if self.CP.carFingerprint not in NO_STOP_TIMER_CAR:
      if CS.out.standstill and not self.last_standstill and not starpilot_toggles.sng_hack:
        self.standstill_req = True

      if CS.pcm_acc_status != 8 or CC.cruiseControl.resume or starpilot_toggles.sng_hack:
        # Clear once the PCM has latched the stop, when planner wants to move,
        # or when the SNG hack is forcing the latch open.
        self.standstill_req = False

    else:
      # if user engages at a stop with foot on brake, PCM starts in a special cruise standstill mode. on resume press,
      # brakes can take a while to ramp up causing a lurch forward. prevent resume press until planner wants to move.
      # don't use CC.cruiseControl.resume since it is gated on CS.cruiseState.standstill which goes false for 3s after resume press
      # TODO: hybrids do not have this issue and can stay stopped after resume press, whitelist them
      should_resume = actuators.accel > 0 or starpilot_toggles.sng_hack
      if should_resume:
        self.standstill_req = False

      if not should_resume and CS.out.cruiseState.standstill:
        self.standstill_req = True

    self.last_standstill = CS.out.standstill

  def update(self, CC, CS, now_nanos, starpilot_toggles):
    actuators = CC.actuators
    stopping = actuators.longControlState == LongCtrlState.stopping
    hud_control = CC.hudControl
    pcm_cancel_cmd = CC.cruiseControl.cancel
    lat_active = CC.latActive and abs(CS.out.steeringTorque) < MAX_USER_TORQUE

    if len(CC.orientationNED) == 3:
      self.pitch.update(CC.orientationNED[1])
      self.pitch_hp.update(CC.orientationNED[1])

    # *** control msgs ***
    can_sends = []

    # *** handle secoc reset counter increase ***
    if self.CP.flags & ToyotaFlags.SECOC.value:
      if CS.secoc_synchronization['RESET_CNT'] != self.secoc_prev_reset_counter:
        self.secoc_lka_message_counter = 0
        self.secoc_lta_message_counter = 0
        self.secoc_acc_message_counter = 0
        self.secoc_prev_reset_counter = CS.secoc_synchronization['RESET_CNT']

        expected_mac = build_sync_mac(self.secoc_key, int(CS.secoc_synchronization['TRIP_CNT']), int(CS.secoc_synchronization['RESET_CNT']))
        if int(CS.secoc_synchronization['AUTHENTICATOR']) != expected_mac:
          carlog.error("SecOC synchronization MAC mismatch, wrong key?")

    # *** steer torque ***
    new_torque = int(round(actuators.torque * self.params.STEER_MAX))
    apply_torque = apply_meas_steer_torque_limits(new_torque, self.last_torque, CS.out.steeringTorqueEps, self.params)

    # >100 degree/sec steering fault prevention
    self.steer_rate_counter, apply_steer_req = common_fault_avoidance(abs(CS.out.steeringRateDeg) >= MAX_STEER_RATE, lat_active,
                                                                      self.steer_rate_counter, MAX_STEER_RATE_FRAMES)

    if not lat_active:
      apply_torque = 0

    # *** steer angle ***
    if self.CP.steerControlType == SteerControlType.angle:
      # If using LTA control, disable LKA and set steering angle command
      apply_torque = 0
      apply_steer_req = False
      if self.frame % 2 == 0:
        # EPS uses the torque sensor angle to control with, offset to compensate
        apply_angle = actuators.steeringAngleDeg + CS.out.steeringAngleOffsetDeg

        # Angular rate limit based on speed
        self.last_angle = apply_std_steer_angle_limits(apply_angle, self.last_angle, CS.out.vEgoRaw,
                                                       CS.out.steeringAngleDeg + CS.out.steeringAngleOffsetDeg,
                                                       CC.latActive, self.params.ANGLE_LIMITS)

    self.last_torque = apply_torque

    # toyota can trace shows STEERING_LKA at 42Hz, with counter adding alternatively 1 and 2;
    # sending it at 100Hz seem to allow a higher rate limit, as the rate limit seems imposed
    # on consecutive messages
    steer_command = toyotacan.create_steer_command(self.packer, apply_torque, apply_steer_req)
    if self.CP.flags & ToyotaFlags.SECOC.value:
      # TODO: check if this slow and needs to be done by the CANPacker
      steer_command = add_mac(self.secoc_key,
                              int(CS.secoc_synchronization['TRIP_CNT']),
                              int(CS.secoc_synchronization['RESET_CNT']),
                              self.secoc_lka_message_counter,
                              steer_command)
      self.secoc_lka_message_counter += 1
    can_sends.append(steer_command)

    # STEERING_LTA does not seem to allow more rate by sending faster, and may wind up easier
    if self.frame % 2 == 0 and self.CP.carFingerprint in TSS2_CAR:
      lta_active = lat_active and self.CP.steerControlType == SteerControlType.angle
      # cut steering torque with TORQUE_WIND_DOWN when either EPS torque or driver torque is above
      # the threshold, to limit max lateral acceleration and for driver torque blending respectively.
      full_torque_condition = (abs(CS.out.steeringTorqueEps) < self.params.STEER_MAX and
                               abs(CS.out.steeringTorque) < self.params.MAX_LTA_DRIVER_TORQUE_ALLOWANCE)

      # TORQUE_WIND_DOWN at 0 ramps down torque at roughly the max down rate of 1500 units/sec
      torque_wind_down = 100 if lta_active and full_torque_condition else 0
      can_sends.append(toyotacan.create_lta_steer_command(self.packer, self.CP.steerControlType, self.last_angle,
                                                          lta_active, self.frame // 2, torque_wind_down))

      if self.CP.flags & ToyotaFlags.SECOC.value:
        lta_steer_2 = toyotacan.create_lta_steer_command_2(self.packer, self.frame // 2)
        lta_steer_2 = add_mac(self.secoc_key,
                              int(CS.secoc_synchronization['TRIP_CNT']),
                              int(CS.secoc_synchronization['RESET_CNT']),
                              self.secoc_lta_message_counter,
                              lta_steer_2)
        self.secoc_lta_message_counter += 1
        can_sends.append(lta_steer_2)

    # *** gas and brake ***

    self._update_standstill_request(CC, CS, actuators, starpilot_toggles)
    interceptor_gas_cmd = self._compute_interceptor_gas_cmd(CC, CS)

    # handle UI messages
    fcw_alert = hud_control.visualAlert == VisualAlert.fcw
    steer_alert = hud_control.visualAlert in (VisualAlert.steerRequired, VisualAlert.ldw)
    lead = hud_control.leadVisible or CS.out.vEgo < 12.  # at low speed we always assume the lead is present so ACC can be engaged

    if self.frame % 2 == 0 and self.CP.enableGasInterceptorDEPRECATED and self.CP.openpilotLongitudinalControl:
      # Send an explicit zero when off so the interceptor does not rescale around a stale command.
      can_sends.append(create_gas_interceptor_command(self.packer, interceptor_gas_cmd, self.frame // 2))

    if self.CP.openpilotLongitudinalControl:
      if self.frame % 3 == 0:
        # Press distance button until we are at the correct bar length. Only change while enabled to avoid skipping startup popup
        if self.frame % 6 == 0 and self.CP.openpilotLongitudinalControl:
          desired_distance = 4 - hud_control.leadDistanceBars
          if CS.out.cruiseState.enabled and CS.pcm_follow_distance != desired_distance:
            self.distance_button = not self.distance_button
          else:
            self.distance_button = 0

        # internal PCM gas command can get stuck unwinding from negative accel so we apply a generous rate limit
        pcm_accel_cmd = actuators.accel
        if CC.longActive:
          pcm_accel_cmd = rate_limit(pcm_accel_cmd, self.prev_accel, ACCEL_WINDDOWN_LIMIT, ACCEL_WINDUP_LIMIT)
        self.prev_accel = pcm_accel_cmd

        # calculate amount of acceleration PCM should apply to reach target, given pitch.
        # clipped to only include downhill angles, avoids erroneously unsetting PERMIT_BRAKING when stopping on uphills
        accel_due_to_pitch = math.sin(min(self.pitch.x, 0.0)) * ACCELERATION_DUE_TO_GRAVITY
        # TODO: on uphills this sometimes sets PERMIT_BRAKING low not considering the creep force
        net_acceleration_request = pcm_accel_cmd + accel_due_to_pitch

        # GVC does not overshoot ego acceleration when starting from stop, but still has a similar delay
        if not self.CP.flags & ToyotaFlags.SECOC.value:
          a_ego_blended = float(np.interp(CS.out.vEgo, [1.0, 2.0], [CS.gvc, CS.out.aEgo]))
        else:
          a_ego_blended = CS.out.aEgo

        # wind down integral when approaching target for step changes and smooth ramps to reduce overshoot
        prev_aego = self.aego.x
        self.aego.update(a_ego_blended)
        j_ego = (self.aego.x - prev_aego) / (DT_CTRL * 3)

        if starpilot_toggles.frogsgomoo_tweak:
          future_t = float(np.interp(CS.out.vEgo, [2., 5.], [0.35, 1.0]))
        else:
          future_t = float(np.interp(CS.out.vEgo, [2., 5.], [0.25, 0.5]))
        a_ego_future = a_ego_blended + j_ego * future_t

        if CC.longActive:
          if self.CP.enableGasInterceptorDEPRECATED:
            # Pedal/SDSU Toyotas have shown better behavior when we trust the planner
            # target directly instead of letting the Toyota longitudinal PID swing it
            # around. Keep the shared rate limits above, but bypass the extra
            # correction layer that causes rev/release oscillation.
            self.long_pid.reset()
          else:
            # constantly slowly unwind integral to recover from large temporary errors
            unwind_rate = ACCEL_PID_UNWIND
            if self.CP.carFingerprint == CAR.TOYOTA_PRIUS and pcm_accel_cmd * self.long_pid.i < 0.0:
              unwind_rate *= PRIUS_INTEGRAL_MISMATCH_UNWIND
            self.long_pid.i -= unwind_rate * float(np.sign(self.long_pid.i))

            error_future = pcm_accel_cmd - a_ego_future

            if not stopping:
              # Toyota's PCM slowly responds to changes in pitch. On change, we amplify our
              # acceleration request to compensate for the undershoot and following overshoot
              pitch_compensation = float(np.clip(math.sin(self.pitch_hp.x) * ACCELERATION_DUE_TO_GRAVITY,
                                                 -MAX_PITCH_COMPENSATION, MAX_PITCH_COMPENSATION))
              pcm_accel_cmd += pitch_compensation

            feedforward = pcm_accel_cmd
            if self.CP.carFingerprint == CAR.TOYOTA_PRIUS:
              # Keep Prius positive handoffs softer than the stock tune, while restoring some launch authority.
              if feedforward > 0.0:
                feedforward *= PRIUS_POSITIVE_FEEDFORWARD_SCALE

            pcm_accel_cmd = self.long_pid.update(error_future,
                                                 speed=CS.out.vEgo,
                                                 feedforward=feedforward,
                                                 freeze_integrator=actuators.longControlState != LongCtrlState.pid)
        else:
          self.long_pid.reset()

        # Along with rate limiting positive jerk above, this greatly improves gas response time
        # Consider the net acceleration request that the PCM should be applying (pitch included)
        net_acceleration_request_min = min(actuators.accel + accel_due_to_pitch, net_acceleration_request)
        self.permit_braking = update_permit_braking(self.permit_braking,
                                                    net_acceleration_request_min,
                                                    stopping,
                                                    CC.longActive,
                                                    CS.out.vEgo,
                                                    lead)

        if self.CP.enableGasInterceptorDEPRECATED:
          pcm_accel_cmd = limit_interceptor_pcm_accel(pcm_accel_cmd, actuators.accel, stopping, CS.out.vEgo)
          pcm_accel_cmd = limit_interceptor_stopping_accel(pcm_accel_cmd, actuators.accel, stopping, CS.out.vEgo, bool(hud_control.leadVisible))
        elif self.CP.carFingerprint == CAR.TOYOTA_PRIUS:
          pcm_accel_cmd = limit_prius_stopping_accel(pcm_accel_cmd, actuators.accel, stopping, CS.out.vEgo, lead)

        pcm_accel_cmd = float(np.clip(pcm_accel_cmd, self.params.ACCEL_MIN, self.params.ACCEL_MAX))

        main_accel_cmd = 0. if self.CP.flags & ToyotaFlags.SECOC.value else pcm_accel_cmd
        can_sends.append(toyotacan.create_accel_command(self.packer, main_accel_cmd, pcm_cancel_cmd, self.permit_braking, self.standstill_req, lead,
                                                        CS.acc_type, fcw_alert, self.distance_button, starpilot_toggles.reverse_cruise_increase))
        if self.CP.flags & ToyotaFlags.SECOC.value:
          acc_cmd_2 = toyotacan.create_accel_command_2(self.packer, pcm_accel_cmd)
          acc_cmd_2 = add_mac(self.secoc_key,
                              int(CS.secoc_synchronization['TRIP_CNT']),
                              int(CS.secoc_synchronization['RESET_CNT']),
                              self.secoc_acc_message_counter,
                              acc_cmd_2)
          self.secoc_acc_message_counter += 1
          can_sends.append(acc_cmd_2)

        self.accel = pcm_accel_cmd

    else:
      # we can spam can to cancel the system even if we are using lat only control
      if pcm_cancel_cmd:
        if self.CP.carFingerprint in UNSUPPORTED_DSU_CAR:
          can_sends.append(toyotacan.create_acc_cancel_command(self.packer))
        else:
          can_sends.append(toyotacan.create_accel_command(self.packer, 0, pcm_cancel_cmd, True, False, lead, CS.acc_type, False, self.distance_button, starpilot_toggles.reverse_cruise_increase))

    # *** hud ui ***
    if self.CP.carFingerprint != CAR.TOYOTA_PRIUS_V:
      # ui mesg is at 1Hz but we send asap if:
      # - there is something to display
      # - there is something to stop displaying
      send_ui = False
      if ((fcw_alert or steer_alert) and not self.alert_active) or \
         (not (fcw_alert or steer_alert) and self.alert_active):
        send_ui = True
        self.alert_active = not self.alert_active
      elif pcm_cancel_cmd:
        # forcing the pcm to disengage causes a bad fault sound so play a good sound instead
        send_ui = True

      if self.frame % 20 == 0 or send_ui:
        can_sends.append(toyotacan.create_ui_command(self.packer, steer_alert, pcm_cancel_cmd, hud_control.leftLaneVisible,
                                                     hud_control.rightLaneVisible, hud_control.leftLaneDepart,
                                                     hud_control.rightLaneDepart, CS.lkas_hud, lat_active))

      if (self.frame % 100 == 0 or send_ui) and self.CP.flags & ToyotaFlags.DISABLE_RADAR.value:
        can_sends.append(toyotacan.create_fcw_command(self.packer, fcw_alert))

    # keep radar disabled
    if self.frame % 20 == 0 and self.CP.flags & ToyotaFlags.DISABLE_RADAR.value:
      can_sends.append(make_tester_present_msg(0x750, 0, 0xF))

    new_actuators = actuators.as_builder()
    new_actuators.torque = apply_torque / self.params.STEER_MAX
    new_actuators.torqueOutputCan = apply_torque
    new_actuators.steeringAngleDeg = self.last_angle
    new_actuators.accel = self.accel

    self.frame += 1

    if not self.doors_locked and CS.out.gearShifter != PARK:
      if starpilot_toggles.lock_doors:
        can_sends.append(CanData(0x750, LOCK_CMD, 0))
      self.doors_locked = True
    elif self.doors_locked and CS.out.gearShifter == PARK:
      if starpilot_toggles.unlock_doors:
        can_sends.append(CanData(0x750, UNLOCK_CMD, 0))
      self.doors_locked = False

    return new_actuators, can_sends
