"""Live Auto evidence and optional typed status contract."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace
import time
import unittest

from openpilot.cereal import log
import openpilot.cereal.messaging as messaging
from openpilot.starpilot.lateral.adjacent_lane_evidence import adjacent_lane_available
from openpilot.starpilot.lateral.auto_lane_change import ClockEpochGuard, auto_evidence, session_policy, steering_capable
from openpilot.starpilot.lateral.lane_change_preferences import LaneChangePolicy, decode as decode_policy
from openpilot.selfdrive.modeld.constants import ModelConstants
from openpilot.starpilot.lateral.lane_change_status_wire import (
  Direction, LaneChangeStatus, Phase, alert_wording, decode, encode, encode_optional, fresh_for_model,
)


def line(y):
  return SimpleNamespace(x=ModelConstants.X_IDXS, y=[y] * ModelConstants.IDX_N)


def model():
  return SimpleNamespace(frameId=77, frameAge=0, timestampEof=10_000_000_000,
                         laneLines=[line(-5.5), line(-1.8), line(1.8), line(5.5)],
                         laneLineProbs=[0.95] * 4, laneLineStds=[0.1] * 4,
                         roadEdges=[line(-6.2), line(6.2)], roadEdgeStds=[0.1] * 2,
                         meta=SimpleNamespace(laneChangeDirection="left"))


def submaster(now):
  services = ("carState", "carControl", "extrinsicsCalibration")
  class FakeSubMaster(SimpleNamespace):
    def __getitem__(self, key):
      return self.values[key]
  return FakeSubMaster(seen=dict.fromkeys(services, True), alive=dict.fromkeys(services, True),
                       valid=dict.fromkeys(services, True), logMonoTime=dict.fromkeys(services, now - 10_000_000),
                       recv_time=dict.fromkeys(services, (now - 10_000_000) / 1e9),
                       values={"carState": SimpleNamespace(canValid=True, canTimeout=False),
                                 "carControl": SimpleNamespace(enabled=True, latActive=True),
                                 "extrinsicsCalibration": SimpleNamespace(calStatus=log.ExtrinsicsCalibration.Status.calibrated,
                                                                          rpyCalib=[0., 0., 0.])})


class TestAutoLaneChange(unittest.TestCase):
  def test_four_startup_modes(self):
    old = decode_policy(b'{"version":1,"enabled":true,"minimumSpeedMps":8.9408,"onePerSignal":false}')
    self.assertIsNotNone(old)
    assert old is not None
    self.assertFalse(session_policy(old, True).auto_lane_change)
    from opendbc.car.car_helpers import interfaces
    from opendbc.car.hyundai.values import CAR as HYUNDAI
    from opendbc.car.toyota.values import CAR as TOYOTA
    from opendbc.car import structs
    for car in (HYUNDAI.HYUNDAI_IONIQ_6, TOYOTA.TOYOTA_RAV4_TSS2_2023):
      cp = interfaces[car].get_non_essential_params(car)
      self.assertTrue(steering_capable(cp))
      for field in ('notCar', 'passive', 'dashcamOnly'):
        bad = cp.as_reader().as_builder()
        setattr(bad, field, True)
        self.assertFalse(steering_capable(bad))
      for config in cp.safetyConfigs:
        config.safetyModel = structs.CarParams.SafetyModel.noOutput
      self.assertFalse(steering_capable(cp))
    from opendbc.car.ford.values import CAR as FORD
    for car in (TOYOTA.TOYOTA_RAV4_TSS2_2023, FORD.FORD_ESCAPE_MK4):
      self.assertTrue(steering_capable(interfaces[car].get_non_essential_params(car)))
    cp = interfaces[HYUNDAI.HYUNDAI_IONIQ_6].get_non_essential_params(HYUNDAI.HYUNDAI_IONIQ_6)
    actual = cp.as_reader().as_builder().safetyConfigs[-1]
    placeholder = structs.CarParams.SafetyConfig()
    placeholder.safetyModel = structs.CarParams.SafetyModel.silent
    cp.safetyConfigs = [placeholder, actual]
    self.assertTrue(steering_capable(cp))
    placeholder.safetyModel = structs.CarParams.SafetyModel.noOutput
    cp.safetyConfigs = [placeholder, actual]
    self.assertTrue(steering_capable(cp))
    cp.safetyConfigs = [placeholder]
    self.assertFalse(steering_capable(cp))
    placeholder.safetyModel = structs.CarParams.SafetyModel.silent
    cp.safetyConfigs = [placeholder]
    self.assertFalse(steering_capable(cp))
    placeholder.safetyModel = structs.CarParams.SafetyModel.allOutput
    cp.safetyConfigs = [placeholder, actual]
    self.assertFalse(steering_capable(cp))
    self.assertFalse(steering_capable(None))
    self.assertFalse(steering_capable(SimpleNamespace()))
    requested = LaneChangePolicy(auto_lane_change=True)
    self.assertFalse(session_policy(requested, False).auto_lane_change)
    self.assertTrue(session_policy(requested, True).auto_lane_change)
    self.assertFalse(session_policy(LaneChangePolicy(enabled=False, auto_lane_change=True), True).enabled)

  def test_clock_domains_and_current_calibration(self):
    now_mono = 1_000_000_000
    now_boot = 10_050_000_000  # includes a long suspend offset from MONOTONIC
    sm, frame = submaster(now_mono), model()
    self.assertTrue(auto_evidence(sm, frame, -1, 3.0, now_mono_ns=now_mono, now_boot_ns=now_boot, model_valid=True, vehicle_capable=True))
    self.assertFalse(auto_evidence(sm, frame, -1, 3.0, now_mono_ns=now_mono, now_boot_ns=now_boot + 200_000_000, model_valid=True, vehicle_capable=True))
    sm.values["extrinsicsCalibration"].calStatus = log.ExtrinsicsCalibration.Status.uncalibrated
    self.assertFalse(auto_evidence(sm, frame, -1, 3.0, now_mono_ns=now_mono, now_boot_ns=now_boot, model_valid=True, vehicle_capable=True))
    sm.values["extrinsicsCalibration"].calStatus = log.ExtrinsicsCalibration.Status.calibrated
    sm.logMonoTime["extrinsicsCalibration"] = now_mono - 800_000_000
    self.assertFalse(auto_evidence(sm, frame, -1, 3.0, now_mono_ns=now_mono, now_boot_ns=now_boot, model_valid=True, vehicle_capable=True))

  def test_suspend_offset_requires_new_calibration_and_controls(self):
    before_mono, before_boot = 1_000_000_000, 10_000_000_000
    guard = ClockEpochGuard(before_mono, before_boot)
    sm = submaster(before_mono)
    self.assertTrue(guard.ready(sm, before_mono, before_boot))
    # MONOTONIC advanced a short interval; BOOTTIME includes a long suspend.
    resumed_mono, resumed_boot = 1_050_000_000, 15_050_000_000
    self.assertFalse(guard.ready(sm, resumed_mono, resumed_boot))
    self.assertFalse(guard.ready(sm, resumed_mono + 10_000_000, resumed_boot + 10_000_000))
    for name in ("carState", "carControl", "extrinsicsCalibration"):
      sm.logMonoTime[name] = resumed_mono + 11_000_000
      sm.recv_time[name] = (resumed_mono + 11_000_000) / 1e9
    self.assertTrue(guard.ready(sm, resumed_mono + 12_000_000, resumed_boot + 12_000_000))

    short_guard = ClockEpochGuard(1_000_000_000, 10_000_000_000)
    short_sm = submaster(1_020_000_000)
    for name in ("carState", "carControl", "extrinsicsCalibration"):
      short_sm.logMonoTime[name] = 1_000_000_000  # apparently only 20 ms old on MONOTONIC
      short_sm.recv_time[name] = 1.0
    fresh_camera = model()
    fresh_camera.timestampEof = 10_100_000_000
    self.assertTrue(auto_evidence(short_sm, fresh_camera, -1, 3.0, now_mono_ns=1_020_000_000,
                                  now_boot_ns=10_110_000_000, model_valid=True, vehicle_capable=True))
    self.assertFalse(short_guard.ready(short_sm, 1_020_000_000, 10_110_000_000))
    self.assertFalse(short_guard.ready(short_sm, 1_021_000_000, 10_111_000_000))
    self.assertFalse(short_guard.ready(short_sm, 1_021_000_000, 10_111_000_000, sample_skew_ns=2_000_000))

  def test_same_frame_geometry_and_engagement(self):
    now = 1_000_000_000
    sm, frame = submaster(now), model()
    self.assertTrue(auto_evidence(sm, frame, 1, 3.0, now_mono_ns=now, now_boot_ns=10_050_000_000, model_valid=True, vehicle_capable=True))
    frame.laneLineProbs[3] = 0.2
    self.assertTrue(auto_evidence(sm, frame, 1, 3.0, now_mono_ns=now, now_boot_ns=10_050_000_000, model_valid=True, vehicle_capable=True))
    frame.laneLineProbs[3] = 0.95
    sm.values["carControl"].enabled = False
    self.assertTrue(auto_evidence(sm, frame, 1, 3.0, now_mono_ns=now, now_boot_ns=10_050_000_000, model_valid=True, vehicle_capable=True))
    from openpilot.selfdrive.controls.lib.desire_helper import DesireHelper
    car = sm.values["carState"]
    car.vEgo, car.leftBlinker, car.rightBlinker = 15., False, False
    car.steeringPressed, car.steeringTorque = False, 0.
    car.leftBlindspot = car.rightBlindspot = False
    helper = DesireHelper(LaneChangePolicy(auto_lane_change=True, auto_delay_s=0.))
    evidence = auto_evidence(sm, frame, 1, 3.0, now_mono_ns=now, now_boot_ns=10_050_000_000, model_valid=True, vehicle_capable=True)
    helper.update(car, True, 1., engaged=sm.values["carControl"].latActive, auto_evidence=evidence)
    car.rightBlinker = True
    helper.update(car, True, 1., engaged=sm.values["carControl"].latActive, auto_evidence=evidence)
    helper.update(car, True, 1., engaged=sm.values["carControl"].latActive, auto_evidence=evidence)
    self.assertEqual(helper.lane_change_state, log.LaneChangeState.laneChangeStarting)
    sm.values["carControl"].latActive = False
    self.assertFalse(auto_evidence(sm, frame, 1, 3.0, now_mono_ns=now, now_boot_ns=10_050_000_000, model_valid=True, vehicle_capable=True))
    sm.values["carControl"].latActive = True
    sm.values["carControl"].enabled = True
    sm.values["carState"].canTimeout = True
    self.assertFalse(auto_evidence(sm, frame, 1, 3.0, now_mono_ns=now, now_boot_ns=10_050_000_000, model_valid=True, vehicle_capable=True))
    sm.values["carState"].canTimeout = False
    frame.laneLineProbs[3] = 1.2
    self.assertFalse(auto_evidence(sm, frame, 1, 3.0, now_mono_ns=now, now_boot_ns=10_050_000_000, model_valid=True, vehicle_capable=True))
    frame.laneLineProbs[3] = 0.95
    frame.frameAge = 2
    self.assertFalse(auto_evidence(sm, frame, 1, 3.0, now_mono_ns=now, now_boot_ns=10_050_000_000, model_valid=True, vehicle_capable=True))
    frame.frameAge = 0
    self.assertFalse(auto_evidence(sm, frame, 1, 3.0, now_mono_ns=now, now_boot_ns=10_050_000_000, model_valid=False, vehicle_capable=True))
    self.assertFalse(auto_evidence(sm, frame, 1, 3.0, now_mono_ns=now, now_boot_ns=10_050_000_000, model_valid=True, vehicle_capable=False))

  def test_recorded_geometry_with_uncertain_road_edge(self):
    saved = json.loads((Path(__file__).parent / "fixtures" / "adjacent_lane_geometry.json").read_text())
    values = saved["model"]
    frame = SimpleNamespace(**{key: value for key, value in values.items() if key not in ("laneLines", "roadEdges")},
                            laneLines=[SimpleNamespace(**value) for value in values["laneLines"]],
                            roadEdges=[SimpleNamespace(**value) for value in values["roadEdges"]])
    self.assertTrue(saved["model_valid"])
    self.assertGreater(frame.roadEdgeStds[0], 0.5)
    self.assertGreaterEqual(min(frame.laneLineProbs[:2]), 0.8)
    now = 1_000_000_000
    sm = submaster(now)
    self.assertTrue(auto_evidence(sm, frame, -1, 2.9, now_mono_ns=now,
                                  now_boot_ns=frame.timestampEof + 50_000_000, model_valid=True, vehicle_capable=True))
    self.assertFalse(adjacent_lane_available(frame, -1, 3.5))

  def test_nearer_road_edge_and_zero_width_configuration(self):
    frame = model()
    for direction, edge, y in ((-1, 0, -3.0), (1, 1, 3.0)):
      with self.subTest(direction=direction):
        frame.roadEdges[edge] = line(y)
        self.assertFalse(adjacent_lane_available(frame, direction, 3.0))
        self.assertTrue(adjacent_lane_available(frame, direction, 0.0))
    self.assertFalse(adjacent_lane_available(frame, 0, 0.0))
    self.assertFalse(adjacent_lane_available(frame, -1, -0.1))
    self.assertFalse(adjacent_lane_available(frame, -1, 4.573))

  def test_width_geometry_rejects_malformed_coordinates_and_metadata(self):
    for defect in ("nan", "infinite", "short", "reversed_x", "missing_edge", "bad_probability", "negative_std"):
      with self.subTest(defect=defect):
        frame = copy.deepcopy(model())
        frame.laneLines[0].x = list(frame.laneLines[0].x)
        if defect == "nan":
          frame.laneLines[0].y[0] = float("nan")
        elif defect == "infinite":
          frame.roadEdges[0].y[0] = float("inf")
        elif defect == "short":
          frame.laneLines[0].y.pop()
        elif defect == "reversed_x":
          frame.laneLines[0].x.reverse()
        elif defect == "missing_edge":
          frame.roadEdges.pop()
        elif defect == "bad_probability":
          frame.laneLineProbs[0] = 1.1
        else:
          frame.roadEdgeStds[0] = -1.0
        self.assertFalse(adjacent_lane_available(frame, -1, 0.0))

  def test_width_restoration_keeps_fresh_input_and_permission_gates(self):
    now = 1_000_000_000
    frame = model()
    frame.roadEdgeStds = [1.5, 1.5]
    for service in ("carState", "carControl", "extrinsicsCalibration"):
      with self.subTest(service=service):
        sm = submaster(now)
        self.assertTrue(auto_evidence(sm, frame, -1, 3.0, now_mono_ns=now,
                                      now_boot_ns=10_050_000_000, model_valid=True, vehicle_capable=True))
        sm.logMonoTime[service] = now - 800_000_000
        self.assertFalse(auto_evidence(sm, frame, -1, 3.0, now_mono_ns=now,
                                       now_boot_ns=10_050_000_000, model_valid=True, vehicle_capable=True))
    sm = submaster(now)
    sm.values["carControl"].latActive = False
    self.assertFalse(auto_evidence(sm, frame, -1, 3.0, now_mono_ns=now,
                                   now_boot_ns=10_050_000_000, model_valid=True, vehicle_capable=True))

  def test_typed_wire_arrival_order_and_neutral_fallback(self):
    frame = model()
    status = LaneChangeStatus("session", 2, 77, 10_000_000_000, 1_000_000_000, 1_150_000_000,
                              Phase.WAITING_FOR_DELAY, Direction.LEFT, True, True)
    raw = encode(status)
    self.assertEqual(decode(raw), status)
    zero_eof = LaneChangeStatus(status.producer_session_id, status.sequence, status.model_frame_id, 0,
                                status.observed_mono_time_ns, status.valid_until_mono_time_ns,
                                status.phase, status.direction, status.auto_configured, status.engaged)
    self.assertIsNone(encode_optional(zero_eof))
    self.assertTrue(fresh_for_model(decode(raw), frame, 1_050_000_000, 1_020_000_000))
    # Status-first and model-first delivery are neutral until both identify the same frame.
    self.assertFalse(fresh_for_model(decode(raw), replace_status_model(frame, 76), 1_050_000_000, 1_020_000_000))
    self.assertFalse(fresh_for_model(None, frame, 1_050_000_000, 1_020_000_000))
    self.assertFalse(fresh_for_model(decode(raw), frame, 1_400_000_000, 1_020_000_000))
    self.assertFalse(fresh_for_model(decode(raw), frame, 1_050_000_000, 1_020_000_000, 3, "session"))
    self.assertIsNone(decode(raw[:-8]))
    self.assertEqual(alert_wording(None, frame, 1_050_000_000, 1_020_000_000),
                     ("Lane Change Pending", "Check surroundings"))
    self.assertEqual(alert_wording(status, frame, 1_050_000_000, 1_020_000_000),
                     ("Automatic Lane Change Pending", "Check surroundings; steer to confirm now"))
    self.assertIsNone(alert_wording(replace_status_phase(status, Phase.MANUAL_REQUIRED),
                                    frame, 1_050_000_000, 1_020_000_000))
    aol_manual = LaneChangeStatus(status.producer_session_id, status.sequence, status.model_frame_id,
                                   status.model_timestamp_eof_ns, status.observed_mono_time_ns,
                                   status.valid_until_mono_time_ns, Phase.MANUAL_REQUIRED, status.direction, True, False)
    self.assertIsNone(alert_wording(aol_manual, frame, 1_050_000_000, 1_020_000_000))
    aol_auto = replace_status_phase(aol_manual, Phase.WAITING_FOR_DELAY)
    self.assertEqual(alert_wording(aol_auto, frame, 1_050_000_000, 1_020_000_000),
                     ("Lane Change Pending", "Check surroundings"))
    self.assertEqual(alert_wording(replace_status_phase(status, Phase.LANE_UNAVAILABLE),
                                   frame, 1_050_000_000, 1_020_000_000),
                     ("Automatic Change Unavailable", "Steer to confirm when safe"))
    self.assertEqual(alert_wording(status, frame, 1_050_000_000, 1_020_000_000,
                                   message_mono_ns=800_000_000), ("Lane Change Pending", "Check surroundings"))
    after_suspend = replace_status_model(frame, 78)
    after_suspend.timestampEof = 15_000_000_000
    self.assertEqual(alert_wording(status, after_suspend, 1_050_000_000, 1_020_000_000),
                     ("Lane Change Pending", "Check surroundings"))

  def test_real_optional_service_roundtrip(self):
    publisher = messaging.PubMaster(["laneChangeAssistWire", "modelV2"])
    subscriber = messaging.SubMaster(["laneChangeAssistWire", "modelV2"], ignore_alive=["laneChangeAssistWire"],
                                     ignore_valid=["laneChangeAssistWire"])
    self.assertTrue(subscriber.all_checks(["laneChangeAssistWire"]))  # optional status cannot hold stock engagement
    time.sleep(0.05)
    now = time.monotonic_ns()
    status = LaneChangeStatus("ipc-session", 1, 77, 10_000_000_000, now, now + 100_000_000,
                              Phase.MANUAL_REQUIRED, Direction.LEFT, False, True)
    msg = messaging.new_message("laneChangeAssistWire", 0)
    msg.valid = True
    msg.laneChangeAssistWire = encode(status)
    publisher.send("laneChangeAssistWire", msg)
    subscriber.update(100)
    self.assertTrue(subscriber.seen["laneChangeAssistWire"] and subscriber.valid["laneChangeAssistWire"])
    self.assertEqual(decode(subscriber["laneChangeAssistWire"]), status)
    self.assertEqual(alert_wording(status, subscriber["modelV2"], time.monotonic_ns(),
                                   int(subscriber.recv_time["laneChangeAssistWire"] * 1e9)),
                     ("Lane Change Pending", "Check surroundings"))  # status arrived first

    def send_model(frame_id):
      message = messaging.new_message("modelV2")
      message.valid = True
      message.modelV2.frameId = frame_id
      message.modelV2.timestampEof = 10_000_000_000
      message.modelV2.meta.laneChangeDirection = log.LaneChangeDirection.left
      publisher.send("modelV2", message)
      subscriber.update(100)

    send_model(77)
    self.assertIsNone(alert_wording(decode(subscriber["laneChangeAssistWire"]), subscriber["modelV2"],
                                    time.monotonic_ns(), int(subscriber.recv_time["laneChangeAssistWire"] * 1e9)))
    send_model(78)  # model arrived first; old wire must not describe it
    self.assertEqual(alert_wording(decode(subscriber["laneChangeAssistWire"]), subscriber["modelV2"],
                                   time.monotonic_ns(), int(subscriber.recv_time["laneChangeAssistWire"] * 1e9)),
                     ("Lane Change Pending", "Check surroundings"))
    next_status = LaneChangeStatus("ipc-session", 2, 78, 10_000_000_000, time.monotonic_ns(),
                                   time.monotonic_ns() + 100_000_000, Phase.MANUAL_REQUIRED, Direction.LEFT, False, True)
    next_msg = messaging.new_message("laneChangeAssistWire", 0)
    next_msg.valid = True
    next_msg.laneChangeAssistWire = encode(next_status)
    publisher.send("laneChangeAssistWire", next_msg)
    subscriber.update(100)
    self.assertIsNone(alert_wording(decode(subscriber["laneChangeAssistWire"]), subscriber["modelV2"],
                                    time.monotonic_ns(), int(subscriber.recv_time["laneChangeAssistWire"] * 1e9)))


def replace_status_model(frame, frame_id):
  return SimpleNamespace(frameId=frame_id, timestampEof=frame.timestampEof, meta=frame.meta)


def replace_status_phase(status, phase):
  return LaneChangeStatus(status.producer_session_id, status.sequence, status.model_frame_id,
                          status.model_timestamp_eof_ns, status.observed_mono_time_ns,
                          status.valid_until_mono_time_ns, phase, status.direction,
                          status.auto_configured, status.engaged)


if __name__ == "__main__":
  unittest.main()
