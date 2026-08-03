from opendbc.car import DT_CTRL
from opendbc.car.can_definitions import CanData
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.gm.values import CAR, CanBus, CruiseButtons, GMFlags

MALIBU_BUTTON_TABLE = {
  0: [0x10FF, 0x15EE, 0x1ADD, 0x1FCC],
  1: [0x55AE, 0x5F8C, 0x6F7C, 0x659E],
  4: [0x2ACD, 0x20EF, 0x1ADD, 0x10FF],
  5: [0x60AF, 0x659E, 0x6A8D, 0x6F7C],
}

MALIBU_BUTTON_MAP = {
  CruiseButtons.UNPRESS: 0,
  CruiseButtons.RES_ACCEL: 1,
  CruiseButtons.MAIN: 4,
  CruiseButtons.CANCEL: 5,
}

ACC_CRUISE_STATE_ADAPTIVE = 2
XT4_CC_BUTTON_BURST_FRAMES = 6
XT4_CC_BUTTON_COUNTER_DELAY_FRAMES = 1
BOLT_CC_BUTTON_CARS = {
  CAR.CHEVROLET_BOLT_CC_2017,
  CAR.CHEVROLET_BOLT_CC_2018_2021,
  CAR.CHEVROLET_BOLT_CC_2022_2023,
}
BOLT_CC_TARGET_DEADBAND_MPH = 0.75
BOLT_CC_REVERSE_CONFIRM_S = 0.6
BOLT_CC_DIRECTION_MEMORY_S = 1.5


def malibu_phase_map_for_button(button):
  key = MALIBU_BUTTON_MAP.get(button)
  if key is None or key not in MALIBU_BUTTON_TABLE:
    return None
  return {v: i for i, v in enumerate(MALIBU_BUTTON_TABLE[key])}


def malibu_phase_map_for_acc(acc_value):
  seq = MALIBU_BUTTON_TABLE.get(acc_value)
  if not seq:
    return None
  return {v: i for i, v in enumerate(seq)}


def create_buttons_malibu(packer, bus, button, phase, prefix=0x41):
  key = MALIBU_BUTTON_MAP.get(button)
  if key is None or key not in MALIBU_BUTTON_TABLE:
    return create_buttons(packer, bus, 0, button)

  values = {
    "ACCButtons": button,
    "RollingCounter": 0,
    "ACCAlwaysOne": 1,
    "DistanceButton": 0,
  }
  dat = packer.make_can_msg("ASCMSteeringButton", bus, values)[1]
  data = bytearray(dat)
  data[3] = prefix & 0xFF

  seq = MALIBU_BUTTON_TABLE[key]
  val = seq[phase % len(seq)]
  data[5] = (val >> 8) & 0xFF
  data[6] = val & 0xFF
  return CanData(0x1e1, bytes(data), bus)


def create_buttons_malibu_cancel(bus, phase, prefix=0x41):
  data = bytearray(7)
  data[3] = prefix & 0xFF
  data[4] = 0x00
  cancel_seq = MALIBU_BUTTON_TABLE[5]
  val = cancel_seq[phase % len(cancel_seq)]
  data[5] = (val >> 8) & 0xFF
  data[6] = val & 0xFF
  return CanData(0x1e1, bytes(data), bus)


def create_buttons(packer, bus, idx, button):
  values = {
    "ACCButtons": button,
    "RollingCounter": idx,
    "ACCAlwaysOne": 1,
    "DistanceButton": 0,
  }

  checksum = 240 + int(values["ACCAlwaysOne"] * 0xf)
  checksum += values["RollingCounter"] * (0x4ef if values["ACCAlwaysOne"] != 0 else 0x3f0)
  checksum -= int(values["ACCButtons"] - 1) << 4  # not correct if value is 0
  checksum -= 2 * values["DistanceButton"]

  values["SteeringButtonChecksum"] = checksum
  return packer.make_can_msg("ASCMSteeringButton", bus, values)


def create_pscm_status(packer, bus, pscm_status):
  values = {s: pscm_status[s] for s in [
    "HandsOffSWDetectionMode",
    "HandsOffSWlDetectionStatus",
    "LKATorqueDeliveredStatus",
    "LKADriverAppldTrq",
    "LKATorqueDelivered",
    "LKATotalTorqueDelivered",
    "RollingCounter",
    "PSCMStatusChecksum",
  ]}
  checksum_mod = int(1 - values["HandsOffSWlDetectionStatus"]) << 5
  values["HandsOffSWlDetectionStatus"] = 1
  values["PSCMStatusChecksum"] += checksum_mod
  return packer.make_can_msg("PSCMStatus", bus, values)


def create_steering_control(packer, bus, apply_torque, idx, lkas_active):
  values = {
    "LKASteeringCmdActive": lkas_active,
    "LKASteeringCmd": apply_torque,
    "RollingCounter": idx,
    "LKASteeringCmdChecksum": 0x1000 - (lkas_active << 11) - (apply_torque & 0x7ff) - idx
  }

  return packer.make_can_msg("ASCMLKASteeringCmd", bus, values)


def create_adas_keepalive(bus):
  dat = b"\x00\x00\x00\x00\x00\x00\x00"
  return [CanData(0x409, dat, bus), CanData(0x40a, dat, bus)]


def create_gas_regen_command(packer, bus, throttle, idx, enabled, at_full_stop, include_always_one3=False, use_volt_layout=False):
  gas_regen_msg = packer.dbc.name_to_msg.get("ASCMGasRegenCmd")
  has_legacy_volt_layout = gas_regen_msg is not None and {
    "GasRegenCmdActiveInv",
    "GasRegenAlwaysOne",
    "GasRegenAlwaysOne2",
  }.issubset(gas_regen_msg.sigs)

  if use_volt_layout and has_legacy_volt_layout:
    values = {
      "GasRegenCmdActive": enabled,
      "RollingCounter": idx,
      "GasRegenCmdActiveInv": 1 - enabled,
      "GasRegenCmd": throttle,
      "GasRegenFullStopActive": at_full_stop,
      "GasRegenAlwaysOne": 1,
      "GasRegenAlwaysOne2": 1,
    }
    if include_always_one3:
      values["GasRegenAlwaysOne3"] = 1

    dat = packer.make_can_msg("ASCMGasRegenCmd", bus, values)[1]
    values["GasRegenChecksum"] = (((0xff - dat[1]) & 0xff) << 16) | \
                                 (((0xff - dat[2]) & 0xff) << 8) | \
                                 ((0x100 - dat[3] - idx) & 0xff)

    return packer.make_can_msg("ASCMGasRegenCmd", bus, values)

  # Preserve the legacy GM Global A GasRegen wire layout when the DBC no longer
  # exposes the helper fields used by older ACC implementations.
  throttle = int(throttle)
  dat = bytearray(8)
  dat[0] = ((idx & 0x3) << 6) | int(enabled)
  dat[1] = 0x42 | (0x20 if at_full_stop else 0x00) | ((throttle >> 13) & 0x1)

  cmd = throttle << 3
  dat[2] = (cmd >> 8) & 0xFF
  dat[3] = cmd & 0xFF
  if include_always_one3:
    dat[2] |= 0x80

  dat[4] = 0x00 if enabled else 0x01
  dat[5] = (0xFF - dat[1]) & 0xFF
  dat[6] = (0xFF - dat[2]) & 0xFF
  dat[7] = (0x100 - dat[3] - idx) & 0xFF

  return CanData(0x2CB, bytes(dat), bus)


def create_ecm_cruise_control_command(packer, bus, enabled, target_speed_kph):
  dat = bytearray(8)
  dat[0] = 0x01
  dat[4] = 0x00

  set_speed_raw = 0
  if enabled:
    set_speed_raw = int(round(max(0., target_speed_kph) / 0.0625))
    set_speed_raw = max(0, min(set_speed_raw, 0x0FFF))

  dat[2] = (set_speed_raw >> 8) & 0xFF
  dat[3] = set_speed_raw & 0xFF
  return CanData(0x3D1, bytes(dat), bus)


def get_friction_brake_mode(apply_brake, enabled, near_stop, at_full_stop, CP, allow_near_stop_mode=False):
  mode = 0x1

  # TODO: Understand this better. Volts and ICE Camera ACC cars are 0x1 when enabled with no brake
  if enabled and CP.carFingerprint in (CAR.CHEVROLET_BOLT_ACC_2022_2023, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL):
    mode = 0x9

  if apply_brake > 0:
    mode = 0xa
    if at_full_stop:
      mode = 0xd
    elif allow_near_stop_mode and near_stop:
      # Stock Volt auto hold can run with cruise main on but ACC inactive, so
      # there is no stock STANDSTILL state to promote 0xa -> 0xd. Restore the
      # older near-stop hold mode only for that path.
      mode = 0xb

  return mode


def create_friction_brake_command(packer, bus, apply_brake, idx, enabled, near_stop, at_full_stop, CP, allow_near_stop_mode=False):
  mode = get_friction_brake_mode(apply_brake, enabled, near_stop, at_full_stop, CP, allow_near_stop_mode)

  brake = (0x1000 - apply_brake) & 0xfff
  checksum = (0x10000 - (mode << 12) - brake - idx) & 0xffff

  values = {
    "RollingCounter": idx,
    "FrictionBrakeMode": mode,
    "FrictionBrakeChecksum": checksum,
    "FrictionBrakeCmd": -apply_brake
  }

  return packer.make_can_msg("EBCMFrictionBrakeCmd", bus, values)


def create_acc_2cd_command(bus, idx):
  dat = bytearray([0x00, 0x2c, 0x03, 0xd3, 0x00])
  dat[0] = (idx & 0x3) << 6
  dat[4] = (0xfd - (idx & 0x3)) & 0xff
  return CanData(0x2CD, bytes(dat), bus)


def create_acc_dashboard_command(packer, bus, enabled, target_speed_kph, hud_control, fcw_alert, acc_always_one=1):
  target_speed = min(target_speed_kph, 255)

  values = {
    "ACCAlwaysOne": acc_always_one,
    "ACCCruiseState": ACC_CRUISE_STATE_ADAPTIVE,
    "ACCResumeButton": 0,
    "ACCSpeedSetpoint": target_speed,
    "ACCGapLevel": hud_control.leadDistanceBars * enabled,  # 3 "far", 0 "inactive"
    "ACCCmdActive": enabled,
    "ACCAlwaysOne2": acc_always_one,
    "ACCLeadCar": hud_control.leadVisible,
    "FCWAlert": int(fcw_alert) & 0x3,
  }

  return packer.make_can_msg("ASCMActiveCruiseControlStatus", bus, values)


def create_adas_time_status(bus, tt, idx):
  dat = [(tt >> 20) & 0xff, (tt >> 12) & 0xff, (tt >> 4) & 0xff,
         ((tt & 0xf) << 4) + (idx << 2)]
  chksum = 0x1000 - dat[0] - dat[1] - dat[2] - dat[3]
  chksum = chksum & 0xfff
  dat += [0x40 + (chksum >> 8), chksum & 0xff, 0x12]
  return CanData(0xa1, bytes(dat), bus)


def create_adas_steering_status(bus, idx):
  dat = [idx << 6, 0xf0, 0x20, 0, 0, 0]
  chksum = 0x60 + sum(dat)
  dat += [chksum >> 8, chksum & 0xff]
  return CanData(0x306, bytes(dat), bus)


def create_adas_accelerometer_speed_status(bus, speed_ms, idx):
  spd = int(speed_ms * 16) & 0xfff
  accel = 0 & 0xfff
  # 0 if in park/neutral, 0x10 if in reverse, 0x08 for D/L
  #stick = 0x08
  near_range_cutoff = 0x27
  near_range_mode = 1 if spd <= near_range_cutoff else 0
  far_range_mode = 1 - near_range_mode
  dat = [0x08, spd >> 4, ((spd & 0xf) << 4) | (accel >> 8), accel & 0xff, 0]
  chksum = 0x62 + far_range_mode + (idx << 2) + dat[0] + dat[1] + dat[2] + dat[3] + dat[4]
  dat += [(idx << 5) + (far_range_mode << 4) + (near_range_mode << 3) + (chksum >> 8), chksum & 0xff]
  return CanData(0x308, bytes(dat), bus)


def create_adas_headlights_status(packer, bus):
  values = {
    "Always42": 0x42,
    "Always4": 0x4,
  }
  return packer.make_can_msg("ASCMHeadlight", bus, values)


def create_lka_icon_command(bus, active, critical, steer):
  if active and steer == 1:
    if critical:
      dat = b"\x50\xc0\x14"
    else:
      dat = b"\x50\x40\x18"
  elif active:
    if critical:
      dat = b"\x40\xc0\x14"
    else:
      dat = b"\x40\x40\x18"
  else:
    dat = b"\x00\x00\x00"
  return CanData(0x104c006c, dat, bus)


def stabilize_bolt_cc_button(controller, CP, requested_button):
  if CP.carFingerprint not in BOLT_CC_BUTTON_CARS:
    return requested_button

  direction_buttons = (CruiseButtons.RES_ACCEL, CruiseButtons.DECEL_SET)
  if requested_button not in direction_buttons:
    controller.gm_cc_pending_reverse_button = CruiseButtons.INIT
    return requested_button

  last_button = getattr(controller, "gm_cc_last_direction_button", CruiseButtons.INIT)
  last_frame = getattr(controller, "gm_cc_last_direction_frame", -int(BOLT_CC_DIRECTION_MEMORY_S / DT_CTRL) - 1)
  recently_sent = (controller.frame - last_frame) * DT_CTRL <= BOLT_CC_DIRECTION_MEMORY_S
  reversing_to_accel = (last_button == CruiseButtons.DECEL_SET and
                        requested_button == CruiseButtons.RES_ACCEL and recently_sent)

  if reversing_to_accel:
    pending_button = getattr(controller, "gm_cc_pending_reverse_button", CruiseButtons.INIT)
    if pending_button != requested_button:
      controller.gm_cc_pending_reverse_button = requested_button
      controller.gm_cc_pending_reverse_frame = controller.frame
      return CruiseButtons.INIT

    pending_frame = getattr(controller, "gm_cc_pending_reverse_frame", controller.frame)
    if (controller.frame - pending_frame) * DT_CTRL < BOLT_CC_REVERSE_CONFIRM_S:
      return CruiseButtons.INIT

  controller.gm_cc_pending_reverse_button = CruiseButtons.INIT
  return requested_button


def create_gm_cc_spam_command(packer, controller, CS, actuators, starpilot_toggles):
  accel = actuators.accel
  v_ego = CS.out.vEgo
  cruise_btn = CruiseButtons.INIT
  rate = 1 if abs(accel) <= 0.15 else 0.2
  is_metric = getattr(starpilot_toggles, "is_metric", False)
  ms_convert = CV.MS_TO_KPH if is_metric else CV.MS_TO_MPH
  speed_setpoint = int(round(CS.out.cruiseState.speed * ms_convert))
  projected_setpoint = (v_ego * 1.01 + 3 * accel) * ms_convert
  desired_setpoint = int(round(projected_setpoint))
  bolt_cc = CS.CP.carFingerprint in BOLT_CC_BUTTON_CARS
  target_deadband = BOLT_CC_TARGET_DEADBAND_MPH * (CV.MPH_TO_KPH if is_metric else 1.0) if bolt_cc else 0.0
  comparison_setpoint = projected_setpoint if bolt_cc else desired_setpoint

  if CS.CP.minEnableSpeed - (desired_setpoint / ms_convert) > 3.25:
    cruise_btn = CruiseButtons.CANCEL
  elif comparison_setpoint < speed_setpoint - target_deadband and speed_setpoint > CS.CP.minEnableSpeed * ms_convert + 1:
    cruise_btn = CruiseButtons.DECEL_SET
  elif comparison_setpoint > speed_setpoint + target_deadband:
    cruise_btn = CruiseButtons.RES_ACCEL

  cruise_btn = stabilize_bolt_cc_button(controller, CS.CP, cruise_btn)
  if cruise_btn == CruiseButtons.CANCEL:
    controller.apply_speed = 0
  elif cruise_btn == CruiseButtons.DECEL_SET:
    controller.apply_speed = speed_setpoint - 1
  elif cruise_btn == CruiseButtons.RES_ACCEL:
    controller.apply_speed = speed_setpoint + 1
  else:
    controller.apply_speed = speed_setpoint

  if CS.CP.carFingerprint == CAR.CADILLAC_XT4_CC:
    if controller.xt4_cc_button_observed_counter != CS.buttons_counter:
      controller.xt4_cc_button_observed_counter = CS.buttons_counter
      controller.xt4_cc_button_counter_frame = controller.frame

    if cruise_btn == CruiseButtons.INIT:
      controller.xt4_cc_button_burst_remaining = 0
      controller.xt4_cc_button_burst_button = CruiseButtons.INIT
      return []

    if (controller.xt4_cc_button_burst_remaining > 0 and
        controller.xt4_cc_button_burst_button != cruise_btn):
      controller.xt4_cc_button_burst_remaining = 0

    if controller.xt4_cc_button_burst_remaining == 0:
      if (controller.frame - controller.last_button_frame) * DT_CTRL <= rate:
        return []
      controller.last_button_frame = controller.frame
      controller.xt4_cc_button_burst_button = cruise_btn
      controller.xt4_cc_button_burst_remaining = XT4_CC_BUTTON_BURST_FRAMES
      controller.xt4_cc_button_burst_last_counter = -1

    # XT4 physical taps hold the button for 5-7 consecutive 33 Hz frames.
    # Sending immediately after the stock frame is too early for the receiving ECU.
    if controller.frame - controller.xt4_cc_button_counter_frame < XT4_CC_BUTTON_COUNTER_DELAY_FRAMES:
      return []

    # Send once per observed stock counter so the injected sequence has the same cadence.
    if controller.xt4_cc_button_burst_last_counter == CS.buttons_counter:
      return []

    controller.xt4_cc_button_burst_last_counter = CS.buttons_counter
    controller.xt4_cc_button_burst_remaining -= 1
    idx = (CS.buttons_counter + 1) % 4
    return [create_buttons(packer, CanBus.POWERTRAIN, idx, controller.xt4_cc_button_burst_button)]

  # Check rlogs closely - our message shouldn't show up on the pt bus for us
  # Or bus 2, since we're forwarding... but I think it does
  if (cruise_btn != CruiseButtons.INIT) and ((controller.frame - controller.last_button_frame) * DT_CTRL > rate):
    controller.last_button_frame = controller.frame
    if bolt_cc and cruise_btn in (CruiseButtons.RES_ACCEL, CruiseButtons.DECEL_SET):
      controller.gm_cc_last_direction_button = cruise_btn
      controller.gm_cc_last_direction_frame = controller.frame
    if CS.CP.carFingerprint == CAR.CHEVROLET_MALIBU_HYBRID_CC:
      phase_map = malibu_phase_map_for_button(cruise_btn)
      if phase_map:
        msgs = [create_buttons_malibu(packer, CanBus.POWERTRAIN, cruise_btn, controller.malibu_button_phase,
                                      CS.steering_button_prefix)]
        controller.malibu_button_phase = (controller.malibu_button_phase + 1) % 4
        return msgs
    idx = (CS.buttons_counter + 1) % 4  # Need to predict the next idx for '22-23 EUV
    msgs = [create_buttons(packer, CanBus.POWERTRAIN, idx, cruise_btn)]

    # Flashed camera-forward Volt CC installs also need the button spoof on the
    # camera side. Removed-camera installs set NO_CAMERA and keep this PT-only.
    if CS.CP.carFingerprint == CAR.CHEVROLET_VOLT_CC and not (CS.CP.flags & GMFlags.NO_CAMERA.value):
      msgs.append(create_buttons(packer, CanBus.CAMERA, idx, cruise_btn))
    return msgs
  else:
    return []


def create_prndl2_command(packer, bus, press_regen_paddle, CP):
  # Gen2 Bolt uses PRNDL2=5 during regen paddle spoof, Gen1 uses 7.
  gen2_bolts = {
    CAR.CHEVROLET_BOLT_ACC_2022_2023,
    CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
    CAR.CHEVROLET_BOLT_CC_2022_2023,
  }

  if CP.carFingerprint in gen2_bolts:
    prndl2_value = 5 if press_regen_paddle else 6
  else:
    prndl2_value = 7 if press_regen_paddle else 6
  manual_mode = 1 if press_regen_paddle else 0
  values = {
    "Byte0": 0x0C,
    "Byte1": 0x0C,
    "Byte2": 0x00,
    "PRNDL2": prndl2_value,
    "Byte4": 0x00,
    "ManualMode": manual_mode,
    "TransmissionState": 1,
    "Byte7": 0x00,
  }
  return packer.make_can_msg("ECMPRDNL2", bus, values)


def create_regen_paddle_command(packer, bus, press_regen_paddle):
  values = {
    "RegenPaddle": 2 if press_regen_paddle else 0,
    "Byte1": 0,
    "Byte2": 0,
    "Byte3": 0,
    "Byte4": 0,
    "Byte5": 0,
    "Byte6": 0,
  }
  return packer.make_can_msg("EBCMRegenPaddle", bus, values)
