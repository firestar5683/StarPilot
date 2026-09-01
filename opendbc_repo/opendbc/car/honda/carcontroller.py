import math
import numpy as np

from opendbc.can import CANPacker
from opendbc.car import ACCELERATION_DUE_TO_GRAVITY, Bus, DT_CTRL, create_gas_interceptor_command, rate_limit, make_tester_present_msg, structs
from opendbc.car.honda import hondacan
from opendbc.car.honda.values import (
  CAR,
  CruiseButtons,
  CruiseSettings,
  HONDA_BOSCH,
  HONDA_BOSCH_CANFD,
  HONDA_BOSCH_RADARLESS,
  HONDA_BOSCH_TJA_CONTROL,
  HONDA_NIDEC_ALT_PCM_ACCEL,
  CarControllerParams,
  HondaFlags,
)
from opendbc.car.interfaces import CarControllerBase
from opendbc.car.common.pid import PIDController
from openpilot.common.params import Params

VisualAlert = structs.CarControl.HUDControl.VisualAlert
LongCtrlState = structs.CarControl.Actuators.LongControlState


ACCORD11G_BRAKE_PID_MIN_SPEED = 1e-3
ACCORD11G_BRAKE_PID_MAX_SPEED = 3.0
ACCORD11G_BRAKE_PID_RELEASE_PER_UPDATE = 0.02


def get_civic_bosch_modified_torque_lpf_tau(torque_cmd: float, prev_torque_cmd: float, v_ego: float) -> float:
  torque_delta = abs(float(torque_cmd) - float(prev_torque_cmd))
  torque_cmd_abs = abs(float(torque_cmd))
  sign_change = (float(torque_cmd) * float(prev_torque_cmd)) < 0.0
  highway = v_ego > (50.0 * 0.44704)
  low_speed = v_ego < (30.0 * 0.44704)

  if highway:
    if torque_cmd_abs < 0.12:
      return 0.18 if sign_change else 0.16
    if sign_change and torque_delta > 0.15:
      return 0.10
    return 0.12

  if sign_change and torque_cmd_abs < 0.25:
    return 0.28 if low_speed else 0.22

  # Extra damping for the tiny near-center commands where both modified EPS
  # firmwares still show hunting and escalating sway.
  if torque_cmd_abs < 0.12:
    return 0.28 if low_speed else 0.20

  if low_speed:
    if torque_delta > 0.50:
      return 0.14
    elif torque_delta > 0.20:
      return 0.16
    elif torque_delta > 0.05:
      return 0.18
    else:
      return 0.22

  if torque_delta > 0.50:
    return 0.12
  elif torque_delta > 0.20:
    return 0.13
  elif torque_delta > 0.05:
    return 0.15
  else:
    return 0.18


def get_civic_bosch_modified_steering_pressed(
  raw_pressed: bool, steering_torque: float, torque_cmd: float, filter_s: float, was_pressed: bool
) -> tuple[float, bool]:
  torque_product = steering_torque * torque_cmd
  torque_cmd_abs = abs(torque_cmd)

  if raw_pressed:
    if torque_product < 0.0:
      trigger_s = 0.08 if was_pressed else 0.10
      rise_rate = 1.0
    elif torque_cmd_abs < 0.10:
      trigger_s = 0.20 if was_pressed else 0.24
      rise_rate = 0.75
    else:
      trigger_s = 0.70 if was_pressed else 0.80
      rise_rate = 0.50

    filter_s = min(1.0, filter_s + (rise_rate * DT_CTRL))
    steering_pressed = filter_s >= trigger_s
  else:
    filter_s = max(0.0, filter_s - 8.0 * DT_CTRL)
    steering_pressed = filter_s > 0.04 and was_pressed

  return filter_s, steering_pressed


def get_honda_bosch_wind_brake_mps2(v_ego: float) -> float:
  return float(np.interp(v_ego, [0.0, 13.4, 22.4, 31.3, 40.2], [0.000, 0.049, 0.136, 0.267, 0.441]))


def update_accord11g_low_speed_brake_pid(
  brake_pid: PIDController,
  accel: float,
  actual_accel: float,
  v_ego: float,
  active_accel_threshold: float,
  long_active: bool,
) -> float:
  if not long_active:
    brake_pid.reset()
    return accel

  if accel < active_accel_threshold and ACCORD11G_BRAKE_PID_MIN_SPEED < v_ego < ACCORD11G_BRAKE_PID_MAX_SPEED:
    brake_addon = brake_pid.update(error=accel - actual_accel, speed=v_ego)
  else:
    if brake_pid.i < 0.0:
      brake_pid.i = min(0.0, brake_pid.i + ACCORD11G_BRAKE_PID_RELEASE_PER_UPDATE)
    else:
      brake_pid.reset()
    brake_addon = brake_pid.i

  return min(accel, accel + brake_addon)


def update_honda_bosch_live_learning(
  gas_factor: float,
  wind_factor: float,
  wind_factor_before_brake: float,
  desired_accel: float,
  actual_accel: float,
  gas_pedal_force: float,
  wind_brake_mps2: float,
  brake_pressed: bool,
  v_ego: float,
) -> tuple[float, float, float]:
  accel_error = desired_accel - actual_accel

  if accel_error != 0.0 and gas_pedal_force > 0.0:
    gas_factor = float(np.clip(gas_factor + accel_error / 50.0 * gas_pedal_force, 0.1, 3.0))

  if accel_error != 0.0 and not brake_pressed and v_ego > 0.0:
    wind_adjust = 1.0 + wind_brake_mps2 / 1000.0
    if accel_error > 0.0:
      wind_factor = float(np.clip(wind_factor * wind_adjust, 0.1, 3.0))
    else:
      wind_factor = float(np.clip(wind_factor / wind_adjust, 0.1, 3.0))

  if gas_pedal_force <= 0.0:
    wind_factor = max(wind_factor, wind_factor_before_brake)
  else:
    wind_factor_before_brake = wind_factor

  return gas_factor, wind_factor, wind_factor_before_brake


def compute_gb_honda_bosch(accel, speed):
  # TODO returns 0s, is unused
  return 0.0, 0.0


def compute_gb_honda_nidec(accel, speed):
  creep_brake = 0.0
  creep_speed = 2.3
  creep_brake_value = 0.15
  if speed < creep_speed:
    creep_brake = (creep_speed - speed) / creep_speed * creep_brake_value
  gb = float(accel) / 4.8 - creep_brake
  return np.clip(gb, 0.0, 1.0), np.clip(-gb, 0.0, 1.0)


def compute_gas_brake(accel, speed, fingerprint):
  if fingerprint in HONDA_BOSCH:
    return compute_gb_honda_bosch(accel, speed)
  else:
    return compute_gb_honda_nidec(accel, speed)


# TODO not clear this does anything useful
def actuator_hysteresis(brake, braking, brake_steady, v_ego, car_fingerprint):
  # hyst params
  brake_hyst_on = 0.02  # to activate brakes exceed this value
  brake_hyst_off = 0.005  # to deactivate brakes below this value
  brake_hyst_gap = 0.01  # don't change brake command for small oscillations within this value

  # *** hysteresis logic to avoid brake blinking. go above 0.1 to trigger
  if (brake < brake_hyst_on and not braking) or brake < brake_hyst_off:
    brake = 0.0
  braking = brake > 0.0

  # for small brake oscillations within brake_hyst_gap, don't change the brake command
  if brake == 0.0:
    brake_steady = 0.0
  elif brake > brake_steady + brake_hyst_gap:
    brake_steady = brake - brake_hyst_gap
  elif brake < brake_steady - brake_hyst_gap:
    brake_steady = brake + brake_hyst_gap
  brake = brake_steady

  return brake, braking, brake_steady


def brake_pump_hysteresis(apply_brake, apply_brake_last, last_pump_ts, ts):
  pump_on = False

  # reset pump timer if:
  # - there is an increment in brake request
  # - we are applying steady state brakes and we haven't been running the pump
  #   for more than 20s (to prevent pressure bleeding)
  if apply_brake > apply_brake_last or (ts - last_pump_ts > 20.0 and apply_brake > 0):
    last_pump_ts = ts

  # once the pump is on, run it for at least 0.2s
  if ts - last_pump_ts < 0.2 and apply_brake > 0:
    pump_on = True

  return pump_on, last_pump_ts


def process_hud_alert(hud_alert):
  alert_fcw = False
  alert_steer_required = False

  # Make sure FCW is prioritized over steering required
  # TODO: implement separate available LDW alert
  if hud_alert == VisualAlert.fcw:
    alert_fcw = True
  elif hud_alert in (VisualAlert.steerRequired, VisualAlert.ldw):
    alert_steer_required = True

  return alert_fcw, alert_steer_required


def persist_honda_learned_params_nonblocking(params, gas_factor, wind_factor):
  # Persist gas and wind factors asynchronously using put_nonblocking
  params.put_nonblocking("HondaGasFactorParams", float(gas_factor))
  params.put_nonblocking("HondaWindFactorParams", float(wind_factor))


LKAS_STATE_CHANGE_PULSE_FRAMES = 30


def update_accord11g_lkas_state_change(last_key, remaining_frames, hud_key):
  if hud_key != last_key:
    last_key = hud_key
    remaining_frames = LKAS_STATE_CHANGE_PULSE_FRAMES

  state_change = remaining_frames > 0
  remaining_frames = max(0, remaining_frames - 1)

  return last_key, remaining_frames, state_change


class CarController(CarControllerBase):
  def __init__(self, dbc_names, CP):
    super().__init__(dbc_names, CP)
    self.packer = CANPacker(dbc_names[Bus.pt])
    self.params = CarControllerParams(CP)
    self.param_store = Params()
    self.CAN = hondacan.CanBus(CP)
    self.tja_control = CP.carFingerprint in HONDA_BOSCH_TJA_CONTROL

    # MVL CAN-FD ownership state. These do not affect non-CANFD vehicles.
    self.radar_disable_counter = 0
    self.radar_mux = 0
    self.radar_hud_pulse = 0
    self.last_acc_enabled = False
    self.lkas_button_send_remaining = 0
    self.last_lkas_button_frame = 0

    # Accord 11G stock-style cluster state-change pulse.
    # Inactive for every other Honda.
    self.lkas_hud_key = None
    self.lkas_state_change_frames = 0

    self.braking = False
    self.brake_steady = 0.0
    self.brake_last = 0.0
    self.apply_brake_last = 0
    self.last_pump_ts = 0.0
    self.stopping_counter = 0

    self.accel = 0.0
    self.speed = 0.0
    self.gas = 0.0
    self.brake = 0.0
    self.last_torque = 0.0
    self.torque_lpf = 0.0
    self.prev_torque_cmd = 0.0
    self.steering_pressed_filter_s = 0.0
    self.steering_pressed_robust_prev = False
    self.bosch_last_gas = 0.0
    self.bosch_gas_factor = self.param_store.get_float("HondaGasFactorParams", default=1.0)
    self.bosch_wind_factor = self.param_store.get_float("HondaWindFactorParams", default=1.0)
    self.bosch_wind_factor_before_brake = self.bosch_wind_factor
    self.bosch_gas_factor_before_gasmax = self.bosch_gas_factor
    self.bosch_wind_factor_before_gasmax = self.bosch_wind_factor
    self.pitch = 0.0
    self.mvl_accord_mode = CP.carFingerprint == CAR.HONDA_ACCORD_11G
    # MVL Bosch low-speed extra-brake integrator. Active only for Accord 11G MVL mode.
    self.mvl_brake_pid = PIDController(k_p=0.0, k_i=1.0, pos_limit=0.0, neg_limit=-2.0, rate=50)
    self.mvl_brake_pid.reset()

  def _modified_civic_standard_active(self) -> bool:
    return self.CP.carFingerprint == CAR.HONDA_CIVIC_BOSCH and bool(self.CP.flags & HondaFlags.EPS_MODIFIED)

  def _filtered_steering_pressed(self, CS, torque_cmd: float) -> bool:
    self.steering_pressed_filter_s, steering_pressed = get_civic_bosch_modified_steering_pressed(
      bool(CS.out.steeringPressed),
      float(getattr(CS.out, "steeringTorque", 0.0)),
      float(torque_cmd),
      self.steering_pressed_filter_s,
      self.steering_pressed_robust_prev,
    )
    self.steering_pressed_robust_prev = steering_pressed
    return steering_pressed

  def update(self, CC, CS, now_nanos, starpilot_toggles):
    actuators = CC.actuators
    hud_control = CC.hudControl
    hud_v_cruise = hud_control.setSpeed / CS.v_cruise_factor if hud_control.speedVisible else 255
    pcm_cancel_cmd = CC.cruiseControl.cancel
    gas_interceptor_command = 0.0
    min_gas = self.params.BOSCH_GAS_LOOKUP_BP[0]
    if len(CC.orientationNED) == 3:
      self.pitch = CC.orientationNED[1]
    hill_brake = math.sin(self.pitch) * ACCELERATION_DUE_TO_GRAVITY

    if CC.longActive:
      accel = actuators.accel
      gas, brake = compute_gas_brake(actuators.accel, CS.out.vEgo, self.CP.carFingerprint)
    else:
      accel = 0.0
      gas, brake = 0.0, 0.0

    torque_cmd = float(actuators.torque)
    filtered_steering_pressed = bool(CS.out.steeringPressed)
    if self._modified_civic_standard_active():
      if CC.latActive:
        filtered_steering_pressed = self._filtered_steering_pressed(CS, torque_cmd)
        if filtered_steering_pressed:
          self.torque_lpf = 0.0
          self.prev_torque_cmd = 0.0
          torque_cmd = 0.0
        else:
          tau = get_civic_bosch_modified_torque_lpf_tau(torque_cmd, self.prev_torque_cmd, CS.out.vEgo)
          alpha = DT_CTRL / (tau + DT_CTRL)
          self.torque_lpf = alpha * torque_cmd + ((1.0 - alpha) * self.torque_lpf)
          self.prev_torque_cmd = torque_cmd
          torque_cmd = self.torque_lpf
      else:
        self.torque_lpf = 0.0
        self.prev_torque_cmd = 0.0
        self.steering_pressed_filter_s = 0.0
        self.steering_pressed_robust_prev = False

    # *** rate limit steer ***
    limited_torque = rate_limit(torque_cmd, self.last_torque, -self.params.STEER_DELTA_DOWN * DT_CTRL, self.params.STEER_DELTA_UP * DT_CTRL)
    self.last_torque = limited_torque

    # *** apply brake hysteresis ***
    pre_limit_brake, self.braking, self.brake_steady = actuator_hysteresis(brake, self.braking, self.brake_steady, CS.out.vEgo, self.CP.carFingerprint)

    # *** rate limit after the enable check ***
    self.brake_last = rate_limit(pre_limit_brake, self.brake_last, -2.0, DT_CTRL)

    # vehicle hud display, wait for one update from 10Hz 0x304 msg
    alert_fcw, alert_steer_required = process_hud_alert(hud_control.visualAlert)

    # **** process the car messages ****

    # steer torque is converted back to CAN reference (positive when steering right)
    apply_torque = int(np.interp(-limited_torque * self.params.STEER_MAX, self.params.STEER_LOOKUP_BP, self.params.STEER_LOOKUP_V))

    # Send CAN commands
    can_sends = []

    # Bosch radar ownership. On CAN-FD, leave the stock radar active until the comma relay is open,
    # then enter extended diagnostics and disable radar RX/TX. This prevents a gap between stock
    # ACC_CONTROL disappearing and panda permitting openpilot's replacement stream.
    if self.CP.carFingerprint in (HONDA_BOSCH - HONDA_BOSCH_RADARLESS) and self.CP.openpilotLongitudinalControl:
      if self.mvl_accord_mode and CS.stock_acc_alive:
        if CS.canfd_relay_open:
          if self.radar_disable_counter % 50 == 0:
            can_sends.append((0x18DAB0F1, b'\x02\x10\x03\x00\x00\x00\x00\x00', self.CAN.pt))
          elif self.radar_disable_counter % 50 == 5:
            can_sends.append((0x18DAB0F1, b'\x03\x28\x83\x03\x00\x00\x00\x00', self.CAN.pt))
          self.radar_disable_counter += 1
      elif self.frame % 10 == 0:
        can_sends.append(make_tester_present_msg(0x18DAB0F1, self.CAN.pt, suppress_response=True))

    # After the stock CAN-FD radar is silent, reproduce its low-rate/tick-aligned messages on both
    # the PT and camera sides of the open relay. Pack once and mirror identical bytes so counters and
    # checksums stay synchronized. v3 deliberately uses an idle lane/object payload first; model-based
    # cluster rendering is deferred until the ownership/DTC handover is proven.
    mvl_radar_owned = self.mvl_accord_mode and CS.canfd_relay_open and not CS.stock_acc_alive
    if mvl_radar_owned and self.CP.openpilotLongitudinalControl:
      if CC.enabled and not self.last_acc_enabled:
        self.radar_hud_pulse = 30
      self.last_acc_enabled = CC.enabled

      radar_msgs = []
      if CS.hud_tick:
        radar_msgs.append(hondacan.create_radar_hud_canfd(self.packer, self.CAN.pt, CC.enabled, self.radar_hud_pulse > 0))
        if self.radar_hud_pulse > 0:
          self.radar_hud_pulse -= 1
      if CS.supp_tick:
        radar_msgs.append(hondacan.create_canfd_supplemental(self.packer, self.CAN.pt))
      if CS.radar_50hz_tick:
        if self.radar_mux >= 58:
          self.radar_mux = 1
        elif self.radar_mux == 10:
          self.radar_mux = 17
        elif self.radar_mux == 26:
          self.radar_mux = 33
        elif self.radar_mux == 42:
          self.radar_mux = 49
        else:
          self.radar_mux += 1
        radar_msgs.extend(hondacan.create_canfd_50hz_radar_messages(self.packer, self.CAN.pt, self.radar_mux))
      if CS.radar_5hz_tick:
        radar_msgs.extend(hondacan.create_canfd_5hz_radar_messages(self.packer, self.CAN.pt, CS.radar_ref_counter))

      for addr, dat, _ in radar_msgs:
        can_sends.append((addr, dat, self.CAN.pt))
        can_sends.append((addr, dat, self.CAN.camera))

    # Send steering command.
    can_sends.append(hondacan.create_steering_control(self.packer, self.CAN, apply_torque, CC.latActive, self.tja_control))

    # wind brake from air resistance decel at high speed
    wind_brake = float(np.interp(CS.out.vEgo, [0.0, 2.3, 35.0], [0.001, 0.002, 0.15]))
    wind_brake_mps2 = get_honda_bosch_wind_brake_mps2(CS.out.vEgo)
    # all of this is only relevant for HONDA NIDEC
    max_accel = np.interp(CS.out.vEgo, self.params.NIDEC_MAX_ACCEL_BP, self.params.NIDEC_MAX_ACCEL_V)
    # TODO this 1.44 is just to maintain previous behavior
    pcm_speed_BP = [-wind_brake, -wind_brake * (3 / 4), 0.0, 0.5]
    # The Honda ODYSSEY seems to have different PCM_ACCEL
    # msgs, is it other cars too?
    if self.CP.enableGasInterceptorDEPRECATED or not CC.longActive:
      pcm_speed = 0.0
      pcm_accel = int(0.0)
    elif self.CP.carFingerprint in HONDA_NIDEC_ALT_PCM_ACCEL:
      pcm_speed_V = [0.0, np.clip(CS.out.vEgo - 3.0, 0.0, 100.0), np.clip(CS.out.vEgo + 0.0, 0.0, 100.0), np.clip(CS.out.vEgo + 5.0, 0.0, 100.0)]
      pcm_speed = float(np.interp(gas - brake, pcm_speed_BP, pcm_speed_V))
      pcm_accel = int(1.0 * self.params.NIDEC_GAS_MAX)
    else:
      pcm_speed_V = [0.0, np.clip(CS.out.vEgo - 2.0, 0.0, 100.0), np.clip(CS.out.vEgo + 2.0, 0.0, 100.0), np.clip(CS.out.vEgo + 5.0, 0.0, 100.0)]
      pcm_speed = float(np.interp(gas - brake, pcm_speed_BP, pcm_speed_V))
      pcm_accel = int(np.clip((accel / 1.44) / max_accel, 0.0, 1.0) * self.params.NIDEC_GAS_MAX)

    if not self.CP.openpilotLongitudinalControl:
      if self.frame % 2 == 0 and self.CP.carFingerprint not in HONDA_BOSCH_RADARLESS | HONDA_BOSCH_CANFD:
        can_sends.append(hondacan.create_bosch_supplemental_1(self.packer, self.CAN))
      # If using stock ACC, spam cancel command to kill gas when OP disengages.
      if pcm_cancel_cmd:
        can_sends.append(hondacan.spam_buttons_command(self.packer, self.CAN, CruiseButtons.CANCEL, self.CP.carFingerprint))
      elif CC.cruiseControl.resume:
        can_sends.append(hondacan.spam_buttons_command(self.packer, self.CAN, CruiseButtons.RES_ACCEL, self.CP.carFingerprint))

    else:
      # Send gas and brake commands.
      if self.frame % 2 == 0:
        ts = self.frame * DT_CTRL

        if self.CP.carFingerprint in HONDA_BOSCH:
          target_accel = update_accord11g_low_speed_brake_pid(
            self.mvl_brake_pid,
            accel,
            CS.out.aEgo,
            CS.out.vEgo,
            min_gas,
            CC.longActive,
          ) if self.mvl_accord_mode else accel

          self.accel = float(np.clip(target_accel, self.params.BOSCH_ACCEL_MIN, self.params.BOSCH_ACCEL_MAX))
          # Keep propulsion inhibited while the Accord's extra-brake integrator releases.
          gas_pedal_force = (target_accel if self.mvl_accord_mode else self.accel) + hill_brake

          if self.CP.carFingerprint not in HONDA_BOSCH_RADARLESS:
            gas_pedal_force += wind_brake_mps2 * self.bosch_wind_factor

            if actuators.longControlState == LongCtrlState.pid and not CS.out.gasPressed:
              gas_error = (accel if self.mvl_accord_mode else self.accel) - CS.out.aEgo

              if gas_error != 0.0 and gas_pedal_force > min_gas:
                if self.CP.carFingerprint == CAR.HONDA_INSIGHT:
                  gas_learn_speed = 150.0
                elif self.CP.carFingerprint in (CAR.ACURA_RDX_3G, CAR.ACURA_RDX_3G_MMR):
                  gas_learn_speed = 300.0
                else:
                  gas_learn_speed = 50.0
                gas_factor_floor = 0.01 if self.mvl_accord_mode else 0.1
                gas_learn_force = (gas_pedal_force - min_gas) if self.mvl_accord_mode else gas_pedal_force
                self.bosch_gas_factor = float(np.clip(
                  self.bosch_gas_factor + gas_error / gas_learn_speed * gas_learn_force,
                  gas_factor_floor, 3.0,
                ))

              if gas_error != 0.0 and not CS.out.brakePressed and CS.out.vEgo > 0.0:
                wind_learn_speed = 100.0 if self.CP.carFingerprint in (CAR.ACURA_RDX_3G, CAR.ACURA_RDX_3G_MMR) else 1000.0
                wind_adjust = 1.0 + wind_brake_mps2 / wind_learn_speed
                if gas_error > 0.0:
                  self.bosch_wind_factor = float(np.clip(self.bosch_wind_factor * wind_adjust, 0.1, 3.0))
                else:
                  self.bosch_wind_factor = float(np.clip(self.bosch_wind_factor / wind_adjust, 0.1, 3.0))

              wind_brake_threshold = min_gas if self.mvl_accord_mode else 0.0
              if gas_pedal_force <= wind_brake_threshold:
                self.bosch_wind_factor = max(self.bosch_wind_factor, self.bosch_wind_factor_before_brake)
              else:
                self.bosch_wind_factor_before_brake = self.bosch_wind_factor

              if gas_pedal_force >= self.params.BOSCH_ACCEL_MAX:
                self.bosch_gas_factor = min(self.bosch_gas_factor, self.bosch_gas_factor_before_gasmax)
                self.bosch_wind_factor = min(self.bosch_wind_factor, self.bosch_wind_factor_before_gasmax)
              else:
                self.bosch_gas_factor_before_gasmax = self.bosch_gas_factor
                self.bosch_wind_factor_before_gasmax = self.bosch_wind_factor

          gas_lookup_input = ((gas_pedal_force - min_gas) * self.bosch_gas_factor + min_gas) if self.mvl_accord_mode else \
                             gas_pedal_force * self.bosch_gas_factor
          self.gas = float(np.interp(gas_lookup_input, self.params.BOSCH_GAS_LOOKUP_BP, self.params.BOSCH_GAS_LOOKUP_V))
          self.gas = min(self.gas, max(60.0, self.bosch_last_gas + 60.0))
          self.bosch_last_gas = self.gas

          stopping = actuators.longControlState == LongCtrlState.stopping
          self.stopping_counter = self.stopping_counter + 1 if stopping else 0
          if not self.mvl_accord_mode or mvl_radar_owned:
            can_sends.extend(
              hondacan.create_acc_commands(
                self.packer, self.CAN, CC.enabled, CC.longActive, self.accel, self.gas, self.stopping_counter, self.CP,
                gas_force=gas_pedal_force if self.mvl_accord_mode else None,
              )
            )
        else:
          apply_brake = np.clip(self.brake_last - wind_brake, 0.0, 1.0)
          apply_brake = int(np.clip(apply_brake * self.params.NIDEC_BRAKE_MAX, 0, self.params.NIDEC_BRAKE_MAX - 1))
          pump_on, self.last_pump_ts = brake_pump_hysteresis(apply_brake, self.apply_brake_last, self.last_pump_ts, ts)

          pcm_override = True
          can_sends.append(
            hondacan.create_brake_command(
              self.packer, self.CAN, apply_brake, pump_on, pcm_override, pcm_cancel_cmd, alert_fcw, self.CP.carFingerprint, CS.stock_brake
            )
          )
          self.apply_brake_last = apply_brake
          self.brake = apply_brake / self.params.NIDEC_BRAKE_MAX

          if self.CP.enableGasInterceptorDEPRECATED:
            gas_error = actuators.accel - CS.out.aEgo

            if not CS.out.gasPressed and actuators.longControlState == LongCtrlState.pid:
              if gas_error != 0.0 and gas > 0.0:
                self.bosch_gas_factor = float(np.clip(self.bosch_gas_factor + gas_error / 150.0 * (gas * 4.8), 0.1, 3.0))
              if gas_error != 0.0 and not CS.out.brakePressed and CS.out.vEgo > 0.0:
                wind_adjust = 1.0 + (wind_brake * 4.8) / 1000.0
                if gas_error > 0.0:
                  self.bosch_wind_factor = float(np.clip(self.bosch_wind_factor * wind_adjust, 0.1, 5.0))
                else:
                  self.bosch_wind_factor = float(np.clip(self.bosch_wind_factor / wind_adjust, 0.1, 5.0))
              if gas <= 0.0:
                self.bosch_wind_factor = max(self.bosch_wind_factor, self.bosch_wind_factor_before_brake)
              else:
                self.bosch_wind_factor_before_brake = self.bosch_wind_factor

            gas_mult = float(np.interp(CS.out.vEgo, [0.0, 10.0], [0.4, 1.0]))
            if CC.longActive:
              gas_interceptor_command = float(np.clip(
                gas_mult * ((gas * self.bosch_gas_factor) - brake + (wind_brake * self.bosch_wind_factor * 3.0 / 4.0)),
                0.0,
                1.0,
              ))
            idx = (self.frame // 2) % 0x10
            can_sends.append(create_gas_interceptor_command(self.packer, gas_interceptor_command, idx))

    # Send dashboard UI commands. On CAN-FD, ACC_HUD is owned by the radar and must only start
    # after the handover, aligned to the radar's 10 Hz HUD tick.
    if (mvl_radar_owned and CS.hud_tick and self.CP.openpilotLongitudinalControl):
      can_sends.append(
        hondacan.create_acc_hud(self.packer, self.CAN.pt, self.CP, CC.enabled, pcm_speed, actuators.accel,
                                hud_control, hud_v_cruise, CS.is_metric, CS.acc_hud)
      )

    if self.frame % 10 == 0:
      if self.CP.openpilotLongitudinalControl and not self.mvl_accord_mode:
        # On Nidec, this also controls longitudinal positive acceleration
        can_sends.append(
          hondacan.create_acc_hud(self.packer, self.CAN.pt, self.CP, CC.enabled, pcm_speed, pcm_accel, hud_control, hud_v_cruise, CS.is_metric, CS.acc_hud)
        )

      steering_available = CS.out.cruiseState.available and CS.out.vEgo > self.CP.minSteerSpeed
      reduced_steering = filtered_steering_pressed

      lkas_state_change = None

      if self.mvl_accord_mode:
        lanes_visible = bool(hud_control.lanesVisible or CC.latActive)

        hud_key = (
          lanes_visible,
          bool(alert_steer_required),
        )

        (
          self.lkas_hud_key,
          self.lkas_state_change_frames,
          lkas_state_change,
        ) = update_accord11g_lkas_state_change(
          self.lkas_hud_key,
          self.lkas_state_change_frames,
          hud_key,
        )

      can_sends.extend(
        hondacan.create_lkas_hud(
          self.packer, self.CAN.lkas, self.CP, hud_control, CC.latActive,
          steering_available, reduced_steering, alert_steer_required,
          CS.lkas_hud, lkas_state_change=lkas_state_change,
        )
      )

      if self.CP.openpilotLongitudinalControl:
        # TODO: combining with create_acc_hud block above will change message order and will need replay logs regenerated
        if self.CP.carFingerprint in (HONDA_BOSCH - HONDA_BOSCH_RADARLESS - {CAR.HONDA_ACCORD_11G}):
          can_sends.append(hondacan.create_radar_hud(self.packer, self.CAN.pt))
        if self.CP.carFingerprint == CAR.HONDA_CIVIC_BOSCH:
          can_sends.append(hondacan.create_legacy_brake_command(self.packer, self.CAN.pt))
        if self.CP.carFingerprint not in HONDA_BOSCH:
          self.speed = pcm_speed
          if self.CP.enableGasInterceptorDEPRECATED:
            self.gas = gas_interceptor_command
          else:
            self.gas = pcm_accel / self.params.NIDEC_GAS_MAX

    # CAN-FD: while engaged, the camera still needs a valid SCM_BUTTONS stream behind the open relay.
    # Take over that stream, echoing the live ambient-light byte. Also send a short LKAS-setting pulse
    # when stock LKAS is ready, matching MVL's workaround for the Honda touch-steering-wheel timer.
    if (self.mvl_accord_mode and CC.enabled and self.frame % 4 == 0
        and not pcm_cancel_cmd and not CC.cruiseControl.resume):
      if (self.lkas_button_send_remaining == 0 and CS.lkas_hud["LKAS_READY"]
          and self.frame >= self.last_lkas_button_frame + 500):
        self.lkas_button_send_remaining = 3

      if self.lkas_button_send_remaining > 0:
        self.last_lkas_button_frame = self.frame
        self.lkas_button_send_remaining -= 1
        cruise_setting = CruiseSettings.LKAS
      elif CS.cruise_setting == CruiseSettings.LKAS:
        cruise_setting = 0
      else:
        cruise_setting = CS.cruise_setting

      can_sends.append(hondacan.spam_buttons_command(
        self.packer, self.CAN, CS.cruise_buttons, self.CP.carFingerprint,
        cruise_setting=cruise_setting, ambient_light=CS.scm_ambient_light, bus=self.CAN.camera,
      ))

    if self.frame > 0 and self.frame % 6000 == 0:
      persist_honda_learned_params_nonblocking(self.param_store, self.bosch_gas_factor, self.bosch_wind_factor)

    new_actuators = actuators.as_builder()
    new_actuators.speed = self.speed
    new_actuators.accel = self.accel
    new_actuators.gas = self.gas
    new_actuators.brake = self.brake
    new_actuators.torque = self.last_torque
    new_actuators.torqueOutputCan = apply_torque

    self.frame += 1
    return new_actuators, can_sends
