from opendbc.car import DT_CTRL


def get_civic_bosch_modified_torque_lpf_tau(torque_cmd: float, prev_torque_cmd: float, v_ego: float) -> float:
  torque_delta = abs(float(torque_cmd) - float(prev_torque_cmd))
  torque_cmd_abs = abs(float(torque_cmd))
  sign_change = float(torque_cmd) * float(prev_torque_cmd) < 0.0
  highway = v_ego > 50.0 * 0.44704
  low_speed = v_ego < 30.0 * 0.44704
  if highway:
    if torque_cmd_abs < 0.12:
      return 0.18 if sign_change else 0.16
    if sign_change and torque_delta > 0.15:
      return 0.1
    return 0.12
  if sign_change and torque_cmd_abs < 0.25:
    return 0.28 if low_speed else 0.22
  if torque_cmd_abs < 0.12:
    return 0.28 if low_speed else 0.2
  if low_speed:
    if torque_delta > 0.5:
      return 0.14
    elif torque_delta > 0.2:
      return 0.16
    elif torque_delta > 0.05:
      return 0.18
    else:
      return 0.22
  if torque_delta > 0.5:
    return 0.12
  elif torque_delta > 0.2:
    return 0.13
  elif torque_delta > 0.05:
    return 0.15
  else:
    return 0.18

def get_civic_bosch_modified_steering_pressed(raw_pressed: bool, steering_torque: float, torque_cmd: float,
                                               filter_s: float, was_pressed: bool) -> tuple[float, bool]:
  torque_product = steering_torque * torque_cmd
  torque_cmd_abs = abs(torque_cmd)
  if raw_pressed:
    if torque_product < 0.0:
      trigger_s = 0.08 if was_pressed else 0.1
      rise_rate = 1.0
    elif torque_cmd_abs < 0.1:
      trigger_s = 0.2 if was_pressed else 0.24
      rise_rate = 0.75
    else:
      trigger_s = 0.7 if was_pressed else 0.8
      rise_rate = 0.5
    filter_s = min(1.0, filter_s + rise_rate * DT_CTRL)
    steering_pressed = filter_s >= trigger_s
  else:
    filter_s = max(0.0, filter_s - 8.0 * DT_CTRL)
    steering_pressed = filter_s > 0.04 and was_pressed
  return (filter_s, steering_pressed)


class ModifiedCivicSteering:
  def __init__(self):
    self.reset()

  def reset(self):
    self.torque_lpf = 0.0
    self.prev_torque_cmd = 0.0
    self.steering_pressed_filter_s = 0.0
    self.steering_pressed_robust_prev = False

  def update(self, CC, CS):
    torque_cmd = float(CC.actuators.torque)
    if not CC.latActive:
      self.reset()
      return torque_cmd
    self.steering_pressed_filter_s, pressed = get_civic_bosch_modified_steering_pressed(
      bool(CS.out.steeringPressed), float(CS.out.steeringTorque), torque_cmd,
      self.steering_pressed_filter_s, self.steering_pressed_robust_prev)
    self.steering_pressed_robust_prev = pressed
    if pressed:
      self.torque_lpf = 0.0
      self.prev_torque_cmd = 0.0
      return 0.0
    tau = get_civic_bosch_modified_torque_lpf_tau(torque_cmd, self.prev_torque_cmd, CS.out.vEgo)
    alpha = DT_CTRL / (tau + DT_CTRL)
    self.torque_lpf = alpha * torque_cmd + (1.0 - alpha) * self.torque_lpf
    self.prev_torque_cmd = torque_cmd
    return self.torque_lpf
