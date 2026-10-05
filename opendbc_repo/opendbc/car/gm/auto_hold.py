from dataclasses import dataclass
import math

import numpy as np

from opendbc.car import structs


FORWARD_GEARS = (structs.CarState.GearShifter.drive, structs.CarState.GearShifter.low,
                 structs.CarState.GearShifter.manumatic)


@dataclass(frozen=True)
class AutoHoldConfig:
  minimum_brake: int = 80
  continued_stop_speed: float = .02


def config_for(cp) -> AutoHoldConfig:
  from opendbc.car.gm.values import is_gm_auto_hold, is_volt_sdgm_profile, camera_acc_pedal_profile
  if is_gm_auto_hold(cp) and is_volt_sdgm_profile(cp, longitudinal=True):
    profile = camera_acc_pedal_profile(cp)
    solo = (profile.one_pedal and not profile.auto_hold if profile is not None else
            0xD100 <= int(cp.safetyConfigs[0].safetyParam) <= 0xD10A)
    return AutoHoldConfig(100, .02 if solo else .25)
  return AutoHoldConfig()


def stopped_for_hold(cs, config: AutoHoldConfig, sent_hold: bool) -> bool:
  if config.continued_stop_speed == .02:
    return cs.standstill or cs.vEgo < .02
  if not math.isfinite(cs.wheelSpeeds.rl) or not math.isfinite(cs.wheelSpeeds.rr):
    return False
  # Physical GM wheel quantization puts raw28 below .25m/s and raw29 above it.
  # This bound tolerates Float32 rounding without borrowing filtered-speed authority.
  return cs.standstill or (sent_hold and cs.vEgo < config.continued_stop_speed and
                          abs(cs.wheelSpeeds.rl) < .25 and abs(cs.wheelSpeeds.rr) < .25)


def hold_brake(driver_brake: float, controller_brake: float, minimum: int = 80) -> int:
  driver_hold = float(np.interp(driver_brake, (8., 20., 40., 80.), (80., 110., 150., 220.)))
  return int(round(np.clip(max(controller_brake, driver_hold), minimum, 240)))


@dataclass
class AutoHold:
  config: AutoHoldConfig = AutoHoldConfig()
  drive_ns: int = 0
  wheel_ns: int = 0
  regen_release_ns: int = 0
  previous_regen: bool = False
  previous_forward: bool = False
  armed: bool = False
  engaged: bool = False
  brake: int = 0

  def reset(self):
    self.drive_ns = self.wheel_ns = 0
    self.regen_release_ns = 0
    self.previous_regen = self.armed = self.engaged = False
    self.previous_forward = False
    self.brake = 0

  def update(self, cs, *, enabled: bool, sources_current: bool, long_active: bool,
             driver_brake: float, controller_brake: int, wheel_ns: int, now_ns: int,
             physical_forward: bool, moving: bool, sent_hold: bool = False) -> int | None:
    if (not enabled or not sources_current or not cs.canValid or cs.canTimeout or
        not all(math.isfinite(value) for value in (cs.vEgo, driver_brake, controller_brake))):
      self.reset()
      return None

    forward = cs.gearShifter in FORWARD_GEARS and physical_forward
    if not forward:
      self.drive_ns = 0
      self.armed = self.engaged = False
    elif self.previous_forward and moving and self.wheel_ns > 0 and 0 < wheel_ns - self.wheel_ns <= 300_000_000:
      self.drive_ns = min(self.drive_ns + wheel_ns - self.wheel_ns, 3_000_000_000)
    self.previous_forward = forward
    self.wheel_ns = wheel_ns

    if self.previous_regen and not cs.regenBraking:
      self.regen_release_ns = now_ns
    self.previous_regen = cs.regenBraking
    cooldown = self.regen_release_ns > 0 and now_ns - self.regen_release_ns < 1_000_000_000

    ready = cs.cruiseState.available and forward and self.drive_ns >= 3_000_000_000
    if not ready or cs.gasPressed:
      self.armed = False
      if cs.gasPressed:
        self.engaged = False
    elif cooldown:
      self.armed = False
    elif cs.vEgo > 0.03 or ((cs.standstill or cs.vEgo < 0.02) and cs.brakePressed):
      self.armed = True

    if cs.vEgo > 0.1 or cs.gasPressed or not forward:
      self.brake = 0
    elif cs.brakePressed or controller_brake > 0:
      self.brake = hold_brake(driver_brake, controller_brake, self.config.minimum_brake)

    active = (ready and (self.armed or self.engaged or cs.brakePressed) and not cs.gasPressed and
              stopped_for_hold(cs, self.config, sent_hold) and not long_active and not cs.regenBraking and not cooldown)
    self.engaged = active
    if active:
      return self.brake or hold_brake(driver_brake, controller_brake, self.config.minimum_brake)
    return None
