"""Opt-in, read-only Stinger object logging. Never publishes control or radar data."""

import math
import time
from collections import deque
from dataclasses import asdict

from openpilot.tools.car_porting.stinger_object_tracks import MAX_EGO_AGE_NS, SLOT_COUNT, StingerObjectDecoder


PLATFORM = "KIA_STINGER_2022"
LOG_INTERVAL_NS = 500_000_000
MAX_OBJECT_AGE_NS = 100_000_000


class StingerObjectShadow:
  def __init__(self, openpilot_longitudinal: bool):
    self.openpilot_longitudinal = openpilot_longitudinal
    self.decoder = StingerObjectDecoder()
    self.ego_history = deque(maxlen=128)
    self.objects: dict[int, dict] = {}
    self.scc = None
    self.object_count = 0
    self.last_log_ns = None

  def update_ego(self, timestamp_ns: int, speed: float, cruise_enabled: bool, brake_pressed: bool, steering_angle: float):
    if not math.isfinite(speed) or not math.isfinite(steering_angle):
      return
    if self.ego_history and timestamp_ns <= self.ego_history[-1]["timestamp_ns"]:
      return
    self.ego_history.append({"timestamp_ns": timestamp_ns, "speed": speed, "cruise_enabled": cruise_enabled,
                             "brake_pressed": brake_pressed, "steering_angle": steering_angle})

  def update_can(self, timestamp_ns: int, address: int, dat: bytes, bus: int):
    if bus == 0 and address == 0x420 and len(dat) == 8:
      raw = int.from_bytes(dat, "little")
      self.scc = {"timestamp_ns": timestamp_ns, "payload": dat.hex(), "main_mode": bool(raw & 1),
                  "object_valid": bool((raw >> 16) & 1), "object_status": (raw >> 22) & 3,
                  "distance": ((raw >> 33) & 0x7ff) * 0.1,
                  "relative_speed": ((raw >> 44) & 0xfff) * 0.1 - 170.0}

    obj = self.decoder.update(timestamp_ns, address, dat, bus)
    if obj is None:
      return
    ego = next((sample for sample in reversed(self.ego_history)
                if 0 <= timestamp_ns - sample["timestamp_ns"] <= MAX_EGO_AGE_NS), None)
    self.objects[obj.slot] = {"timestamp_ns": timestamp_ns, **asdict(obj),
                              "ego_timestamp_ns": ego["timestamp_ns"] if ego else None,
                              "ego_speed": ego["speed"] if ego else None,
                              "relative_speed": obj.relative_speed(ego["speed"]) if ego else None}
    self.object_count += 1

  def snapshot(self, timestamp_ns: int) -> dict | None:
    if self.last_log_ns is not None and timestamp_ns - self.last_log_ns < LOG_INTERVAL_NS:
      return None
    self.last_log_ns = timestamp_ns
    self.objects = {slot: obj for slot, obj in self.objects.items()
                    if 0 <= timestamp_ns - obj["timestamp_ns"] <= MAX_OBJECT_AGE_NS}
    assert len(self.objects) <= SLOT_COUNT
    scc = self.scc if self.scc and 0 <= timestamp_ns - self.scc["timestamp_ns"] <= MAX_OBJECT_AGE_NS else None
    ego = self.ego_history[-1] if self.ego_history else None
    if ego and not 0 <= timestamp_ns - ego["timestamp_ns"] <= MAX_EGO_AGE_NS:
      ego = None
    return {"timestamp_ns": timestamp_ns, "platform": PLATFORM, "shadow_only": True,
            "openpilot_longitudinal": self.openpilot_longitudinal, "decoded_objects_total": self.object_count,
            "objects": [self.objects[slot] for slot in sorted(self.objects)], "car_state": ego,
            "scc11": scc, "scc11_independent_reference": scc is not None and not self.openpilot_longitudinal}


def main():
  from cereal import car, messaging
  from openpilot.common.params import Params
  from openpilot.common.swaglog import cloudlog

  params = Params()
  cp_bytes = params.get("CarParams")
  if cp_bytes is None or not params.get_bool("StingerObjectShadow") or params.get_bool("DisableLogging"):
    return
  with car.CarParams.from_bytes(cp_bytes) as CP:
    if CP.carFingerprint != PLATFORM or CP.notCar:
      return
    collector = StingerObjectShadow(CP.openpilotLongitudinalControl)

  can_sock = messaging.sub_sock("can", timeout=100)
  sm = messaging.SubMaster(["carState"])
  cloudlog.event("stinger_object_shadow_start", platform=PLATFORM, shadow_only=True)
  while True:
    sm.update(0)
    if sm.updated["carState"] and sm.valid["carState"]:
      CS = sm["carState"]
      collector.update_ego(sm.logMonoTime["carState"], CS.vEgo, CS.cruiseState.enabled, CS.brakePressed, CS.steeringAngleDeg)
    for event in messaging.drain_sock(can_sock, wait_for_one=True):
      if event.which() == "can" and event.valid:
        for msg in event.can:
          collector.update_can(event.logMonoTime, msg.address, bytes(msg.dat), msg.src)
    snapshot = collector.snapshot(time.monotonic_ns())
    if snapshot is not None:
      if not params.get_bool("StingerObjectShadow") or params.get_bool("DisableLogging"):
        return
      cloudlog.event("stinger_object_shadow", **snapshot)


if __name__ == "__main__":
  main()
