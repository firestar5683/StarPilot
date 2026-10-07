"""Acceleration tuning for conventional-cruise GM pedal configurations."""

import numpy as np

from opendbc.car.gm.values import CAR, is_conventional_cc_pedal_profile, is_silverado_cc_pedal_profile
from opendbc.car.gm.longitudinal import GMPedalLongitudinalPolicy, _GMDefaultStopPolicy, _moving_stop_target_follow
from opendbc.car.gm.cc_longitudinal import VoltCcEvidence


def stop_start_speed(malibu: bool) -> float:
  """Default stop/start speed for the conventional-cruise pedal policy."""
  return .75 if malibu else .5


class GMConventionalPedalPolicy(GMPedalLongitudinalPolicy):
  def __init__(self, malibu: bool):
    super().__init__(friction_variant=False)
    # The reached original default reads this rate through Float32 CarParams storage.
    self.stopping_decel_rate = float(np.float32(.8))
    self.kp = (((0.0, 5.0, 35.0), (0.06, 0.05, 0.04)) if malibu else
               ((0.0, 5.0, 15.0, 35.0), (0.09, 0.08, 0.06, 0.045)))
    self.kp = (self.kp[0], tuple(float(np.float32(value)) for value in self.kp[1]))
    self.starting_speed = stop_start_speed(malibu)
    self.feedforward_gain = float(np.float32(0.15 if malibu else 0.25))

  def stop_policy(self):
    return _GMDefaultStopPolicy(self.starting_speed, VoltCcEvidence)

  def stopping_output(self, output, target, should_stop, cs):
    return _moving_stop_target_follow(output, target, should_stop, cs, max(1.5, self.starting_speed + 1.))

  def feedforward(self, target: float, speed: float, last_output: float) -> float:
    return target * self.feedforward_gain


def policy_for(cp):
  if not is_conventional_cc_pedal_profile(cp) or not cp.openpilotLongitudinalControl:
    return None
  return GMConventionalPedalPolicy(cp.carFingerprint == CAR.CHEVROLET_MALIBU_CC)


class CancelCredit:
  DRIVER_OVERRIDE_LENGTHS = {0xBD: 7, 0xC9: 8, 0x1C4: 8, 0x1F5: 8}

  """One cancellation per sequential, byte-valid neutral wheel-button packet."""

  def __init__(self, *, neutral_interval_ns=300_000_000):
    self.neutral_interval_ns = neutral_interval_ns
    self.counter = None
    self.packet_ns = self.source_ns = self.credit_ns = 0
    self.main_ns = self.stock_ns = 0
    self.gear_ns = self.gear_packet_ns = 0
    self.main = self.stock_active = False
    self.override_ns = {}

  def observe(self, can_packets, *, clear_on_main_off=False, clear_on_driver_override=False, observe_gear=False):
    # Decoded signals omit reserved bits. Observe ordered physical packets so
    # the sender cannot grant credit for a button frame Panda would reject.
    for stamp, packets in can_packets:
      for address, raw, bus in packets:
        if bus != 0:
          continue
        if observe_gear and address == 0x1F5:
          if len(raw) == 8 and stamp > max(0, self.gear_packet_ns):
            self.gear_ns = stamp
          elif len(raw) != 8 or stamp != self.gear_ns or stamp <= 0:
            # Same-event valid observations retain a qualified clock, never refresh it.
            self.gear_ns = 0
          self.gear_packet_ns = max(self.gear_packet_ns, stamp)
          if not self.gear_ns:
            self.credit_ns = 0
        if clear_on_driver_override and stamp > self.override_ns.get(address, 0):
          if address in self.DRIVER_OVERRIDE_LENGTHS and len(raw) == self.DRIVER_OVERRIDE_LENGTHS[address]:
            self.override_ns[address] = stamp
            override = ((address == 0xBD and raw[0] >> 4 != 0) or
                        (address == 0xC9 and raw[5] & 1 != 0) or
                        (address == 0x1C4 and raw[5] != 0) or
                        (address == 0x1F5 and (raw[3] & 15 not in (4, 6) or raw[5] & 2 != 0)))
            if override:
              self.credit_ns = 0
        if address == 0xC9:
          self.main_ns = stamp if len(raw) == 8 and stamp > 0 else 0
          self.main = bool(self.main_ns and raw[3] & 0x20)
          if clear_on_main_off and not self.main:
            self.credit_ns = 0
        elif address == 0x3D1:
          self.stock_ns = stamp if len(raw) == 8 and stamp > 0 else 0
          self.stock_active = bool(self.stock_ns and raw[4] & 0x80)
          if not self.stock_active:
            self.credit_ns = 0
        elif address == 0x1E1:
          self._observe_button(raw, stamp)

  def _observe_button(self, raw, stamp):
    if len(raw) != 7:
      self.credit_ns = 0
      return
    counter = raw[4] & 3
    if stamp <= 0 or stamp < self.packet_ns:
      # Panda still observes the physical counter even if its host timestamp is unusable.
      self.counter = counter
      self.credit_ns = self.source_ns = 0
      return
    checksum = 0xFF + counter * 0x4EF
    neutral = raw == bytes((0, 0, 0, 1, counter, 0x10 | (checksum >> 8), checksum & 0xFF))
    first = self.counter is None
    timely = self.source_ns > 0 and 0 <= stamp - self.source_ns <= self.neutral_interval_ns
    if neutral and (first or timely and counter == (self.counter + 1) % 4):
      self.credit_ns = stamp
      self.source_ns = stamp
    elif not neutral or not timely or counter != self.counter:
      self.credit_ns = 0
    if first or counter != self.counter:
      self.source_ns = stamp
    self.counter, self.packet_ns = counter, stamp

  def available(self, now_ns, used_ns):
    return (self.credit_ns > used_ns and self.main and self.stock_active and
            all(stamp > 0 and 0 <= now_ns - stamp <= 300_000_000
                for stamp in (self.main_ns, self.stock_ns, self.source_ns)))


def cancel_sources_current(cs, now_ns):
  """Keep the parser's process-health checks alongside raw cancellation credit."""
  return cs.out.canValid and not cs.out.canTimeout


def sources_current(cs, now_ns):
  if is_silverado_cc_pedal_profile(cs.CP):
    stamps = cs.silverado_pedal_sources
    limits = (300_000_000, 100_000_000, 300_000_000, 300_000_000,
              100_000_000, 100_000_000, 300_000_000, 100_000_000)
    return (len(stamps) == len(limits) and cs.out.canValid and not cs.out.canTimeout and
            all(stamp > 0 and 0 <= now_ns - stamp <= limit for stamp, limit in zip(stamps, limits, strict=True)))
  stamps = cs.conventional_pedal_sources
  limits = (300_000_000, 300_000_000, 300_000_000, 300_000_000,
            300_000_000, 100_000_000, 300_000_000, 100_000_000)
  if len(stamps) == 9:
    limits += (100_000_000,)
  return (len(stamps) == len(limits) and cs.out.canValid and not cs.out.canTimeout and
          all(stamp > 0 and 0 <= now_ns - stamp <= limit for stamp, limit in zip(stamps, limits, strict=True)))
