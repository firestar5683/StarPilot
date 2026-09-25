"""Stationary Toyota door commands on actual observed gear transitions.

Command payloads from Dom StarPilot, credited there to AlexandreSato.
This owner never changes Panda safety mode or sends diagnostics directly.
"""

import math

from opendbc.car.structs import CarState

# Credit: AlexandreSato (original Dom Toyota controller).
LOCK_CMD = b"\x40\x05\x30\x11\x00\x80\x00\x00"
UNLOCK_CMD = b"\x40\x05\x30\x11\x00\x40\x00\x00"
Gear = CarState.GearShifter


class DoorLocks:
  def __init__(self):
    self.lock = self.unlock = False
    self.previous_gear = None

  def update(self, state):
    gear = state.gearShifter
    if not state.canValid or state.canTimeout or gear not in (Gear.park, Gear.drive, Gear.reverse, Gear.neutral):
      self.previous_gear = None
      return None
    previous, self.previous_gear = self.previous_gear, gear
    if (previous is None or previous == gear or not state.standstill or not math.isfinite(state.vEgoRaw) or
        abs(state.vEgoRaw) > .01 or state.doorOpen or state.gasPressed or state.vehicleSensorsInvalid):
      return None
    if previous == Gear.park and gear != Gear.park and self.lock:
      return LOCK_CMD
    if previous != Gear.park and gear == Gear.park and self.unlock:
      return UNLOCK_CMD
    return None
