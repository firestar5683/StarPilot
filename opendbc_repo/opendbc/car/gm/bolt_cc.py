"""Cruise button ownership for the exact Bolt profiles."""

from dataclasses import dataclass
import math

IDS = ('CHEVROLET_BOLT_CC_2017', 'CHEVROLET_BOLT_CC_2018_2021', 'CHEVROLET_BOLT_CC_2022_2023')
ACC_ID = 'CHEVROLET_BOLT_ACC_2022_2023_PEDAL'
MIN_SPEED = 24 * 0.44704


@dataclass(frozen=True)
class BoltCcProfile:
  identity: str
  camera_removed: bool = False

  def __post_init__(self):
    if self.identity not in (*IDS, ACC_ID):
      raise ValueError('not a supported Bolt CC identity')

  @property
  def adaptive_stock(self):
    return self.identity == ACC_ID

  @property
  def camera_required(self):
    return self.adaptive_stock and not self.camera_removed


def button_bytes(button, counter):
  if button not in (1, 2, 3, 6) or counter not in range(4):
    raise ValueError('invalid button tuple')
  checksum = 255 + counter * 0x4EF - (button - 1) * 16
  return bytes((0, 0, 0, 1, counter, (button << 4) | ((checksum >> 8) & 15), checksum & 255))


class BoltCcOwner:
  def __init__(self, profile):
    self.profile = profile
    self.frame = 0
    self.last_send = 0
    self.last_direction = 0
    self.last_direction_frame = -151
    self.pending = 0
    self.pending_frame = 0
    self.credit = None
    self.last_counter = None
    self.last_button_stamp = 0
    self.cruise_active = False
    self.cruise_stamp = 0
    self.camera_active = False
    self.camera_stamp = 0
    self.prev_enabled = False
    self.cancel_pending = False
    self.cancel_stamp = 0

  def cruise(self, raw, stamp):
    if len(raw) != 8 or stamp <= 0 or stamp <= self.cruise_stamp:
      return False
    self.cruise_active = bool(raw[4] & 128)
    self.cruise_stamp = stamp
    if not self.cruise_active:
      self.cancel_pending = False
    return True

  def camera(self, raw, stamp):
    if not self.profile.camera_required or len(raw) != 6 or stamp <= 0 or stamp <= self.camera_stamp:
      return False
    self.camera_active = bool(raw[2] & 128)
    self.camera_stamp = stamp
    if not self.camera_active:
      self.cancel_pending = False
    return True

  def button(self, raw, stamp):
    self.credit = None
    if len(raw) != 7 or stamp <= 0 or stamp <= self.last_button_stamp:
      return False
    self.last_button_stamp = stamp
    counter = raw[4]
    button = (raw[5] >> 4) & 7
    if counter not in range(4) or button not in (1, 2, 3, 6) or raw != button_bytes(button, counter):
      return False
    forward = self.last_counter is None or counter == (self.last_counter + 1) % 4
    self.last_counter = counter
    if not forward or button != 1:
      return False
    self.credit = (counter, stamp)
    return True

  def request(self, speed, stock_speed, accel, metric=False):
    if not all(math.isfinite(x) for x in (speed, stock_speed, accel)):
      return 0, math.inf
    convert = 3.6 if metric else 1 / 0.44704
    setpoint = int(round(stock_speed * convert))
    projected = (speed * 1.01 + 3 * accel) * convert
    desired = int(round(projected))
    deadband = 0.0 if self.profile.adaptive_stock else 0.75 * (1.609344 if metric else 1.0)
    comparison = desired if self.profile.adaptive_stock else projected
    rate = 1.0 if abs(accel) <= 0.15 else 0.2
    if MIN_SPEED - desired / convert > 3.25:
      button = 6
    elif comparison < setpoint - deadband and setpoint > MIN_SPEED * convert + 1:
      button = 3
    elif comparison > setpoint + deadband:
      button = 2
    else:
      button = 0
    if self.profile.adaptive_stock:
      return button, rate
    if button not in (2, 3):
      self.pending = 0
      return button, rate
    if self.last_direction == 3 and button == 2 and (self.frame - self.last_direction_frame) * 0.01 <= 1.5:
      if self.pending != button:
        self.pending = button
        self.pending_frame = self.frame
        return 0, rate
      if (self.frame - self.pending_frame) * 0.01 < 0.6:
        return 0, rate
    self.pending = 0
    return button, rate

  def update(
    self,
    now,
    speed,
    stock_speed,
    accel,
    *,
    enabled=True,
    long_active=True,
    drive=True,
    brake=False,
    gas=False,
    sources_current=True,
    metric=False,
    hud_speed=None,
  ):
    self.frame += 1
    stock_active = self.camera_active if self.profile.camera_required else self.cruise_active
    if self.prev_enabled and not enabled and stock_active:
      self.cancel_pending = True
      self.cancel_stamp = now
    if self.cancel_pending and not 0 <= now - self.cancel_stamp <= 100_000_000:
      self.cancel_pending = False
    if enabled:
      self.cancel_pending = False
    self.prev_enabled = enabled
    stock_ready = (
      self.credit is not None
      and self.cruise_active
      and self.cruise_stamp > 0
      and 0 <= now - self.cruise_stamp <= 300_000_000
      and 0 < now - self.credit[1] <= 100_000_000
      and sources_current
    )
    camera_ready = (not self.profile.camera_required or
                    (self.camera_active and self.camera_stamp > 0 and 0 <= now - self.camera_stamp <= 300_000_000))
    cancel_ready = (stock_ready if not self.profile.camera_required else
                    camera_ready and self.credit is not None and 0 < now - self.credit[1] <= 100_000_000 and sources_current)
    if self.cancel_pending and cancel_ready:
      counter, stamp = self.credit
      self.credit = None
      self.cancel_pending = False
      return (0x1E1, button_bytes(6, (counter + 1) % 4), 2 if self.profile.camera_required else 0)
    stock_ready = stock_ready and camera_ready
    helper_requested = long_active and speed >= MIN_SPEED
    if (
      not helper_requested
      and stock_ready
      and enabled
      and drive
      and not brake
      and gas
      and self.frame % 52 == 0
      and hud_speed is not None
      and all(math.isfinite(v) for v in (stock_speed, speed, hud_speed))
      and stock_speed < speed < hud_speed
    ):
      counter, stamp = self.credit
      self.credit = None
      self.last_send = self.frame
      return (0x1E1, button_bytes(3, (counter + 1) % 4), 0)
    valid = stock_ready and drive and not brake and not gas and enabled and speed >= MIN_SPEED
    if not valid or not long_active:
      self.credit = None
      self.last_send = self.frame
      return None
    if self.frame % 4:
      return None
    button, rate = self.request(speed, stock_speed, accel, metric)
    if not button or (self.frame - self.last_send) * 0.01 <= rate:
      return None
    # Helper CANCEL uses projected speed only after the actual-speed caller floor.
    if button != 6 and speed < MIN_SPEED:
      return None
    counter, stamp = self.credit
    self.credit = None
    self.last_send = self.frame
    if button in (2, 3):
      self.last_direction = button
      self.last_direction_frame = self.frame
    return (0x1E1, button_bytes(button, (counter + 1) % 4), 0)


def pscm_passthrough(data):
  if len(data) != 8:
    raise ValueError('invalid PSCM length')
  masks = (0x3F, 0xFF, 0x3F, 0xFF, 0x7B, 0xFF, 7, 0xFF)
  out = bytearray(d & m for d, m in zip(data, masks, strict=True))
  mod = 32 if not (data[2] & 32) else 0
  checksum = (((data[4] & 3) << 8) | data[5]) + mod
  out[2] |= 32
  out[4] = (out[4] & 0xFC) | ((checksum >> 8) & 3)
  out[5] = checksum & 255
  return bytes(out)


def auxiliary_messages(owner, pscm, source_stamp, now):
  result = []
  if owner.frame % 10 == 0 and source_stamp > 0 and 0 <= now - source_stamp <= 100_000_000:
    result.append((0x184, pscm_passthrough(pscm), 2))
  if owner.profile.camera_removed and owner.frame % 100 == 0:
    result.extend([(0x409, bytes(7), 0), (0x40A, bytes(7), 0)])
  return result


class BoltCcLongitudinalPolicy:
  """Literal conventional-Bolt PID calibration; no Volt stop/regen shaping."""

  friction_variant = False
  stopping_decel_rate = 11.18
  kp = ((10.7, 10.8, 28.0), (0.0, 5.0, 2.0))

  def reset(self):
    pass

  def prepare_pid(self, pid, target, error, speed, last_output, accel_limits, **kwargs):
    if pid.i > 0.0 and target < -0.05 and error < -0.25 and not (speed <= 0.35 and target > -0.40):
      magnitude = abs(error)
      if magnitude < 0.75:
        bleed = 0.55 - 0.30 * (magnitude - 0.25) / 0.50
      elif magnitude < 1.5:
        bleed = 0.25 * (1.5 - magnitude) / 0.75
      else:
        bleed = 0.0
      pid.i *= bleed
    return False

  def feedforward(self, target, speed, last_output):
    return target

  def shape_output(self, output, target, error, speed):
    if output > 0.0 and target < -0.10 and error < -0.35 and not (speed <= 0.35 and target > -0.40):
      positive_cap = 0.0 if target <= -0.6 else 0.05 * (target + 0.6) / 0.5
      output = min(output, positive_cap)
    return output


def policy_for(cp):
  from opendbc.car.gm.values import is_bolt_cc_profile

  return BoltCcLongitudinalPolicy() if is_bolt_cc_profile(cp) and cp.openpilotLongitudinalControl else None
