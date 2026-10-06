"""Actual host curvature selection, limiter and native controllers on supplied messages."""

import argparse
from dataclasses import asdict, replace
import json
import math
import os
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest

from openpilot.common.basedir import BASEDIR


def probe(output, reference_method=None):
  if not os.environ.get("OPENPILOT_PREFIX", "").startswith("lane-host-") or any(
    name in os.environ for name in ("CEREAL_FAKE", "CEREAL_FAKE_PREFIX", "SIMULATION")
  ):
    raise RuntimeError("Native lane-host probe requires isolated IPC without simulation flags")
  from openpilot.cereal import messaging
  from openpilot.common.realtime import DT_CTRL
  from openpilot.selfdrive.controls.controlsd import Controls
  from openpilot.selfdrive.controls.lib.drive_helpers import clip_curvature
  from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
  from openpilot.selfdrive.controls.lib.longcontrol import LongControl
  from openpilot.starpilot.longitudinal.ioniq6_start import eligible as ioniq6_start_eligible
  from openpilot.starpilot.longitudinal.tests.extension_helpers import attach_inputs
  from openpilot.starpilot.lateral.lane_centering import ControlMode, LaneCenteringController, LaneCenteringRequest, LaneCenteringSettings
  from openpilot.starpilot.lateral.tests.test_lane_centering import model
  from openpilot.starpilot.lateral.lane_change_preferences import LaneChangePolicy
  from openpilot.starpilot.lateral.lane_change_smoothing import LaneChangeSmoother
  from opendbc.car.car_helpers import interfaces
  from opendbc.car.toyota.values import CAR
  from opendbc.car.vehicle_model import VehicleModel

  def host():
    # Allocate just the state_control dependencies. Native controllers and SubMaster
    # are independent; Params, publication, pose calibration and manager are not run.
    control = Controls.__new__(Controls)
    from openpilot.starpilot.lateral.pause import LateralPause, PauseSettings
    control.lateral_pause = LateralPause(PauseSettings())
    attach_inputs(control)
    control.lateral_gain_owner = None
    control.aol_replay = False
    interface = interfaces[CAR.TOYOTA_COROLLA_TSS2]
    control.CP = interface.get_non_essential_params(CAR.TOYOTA_COROLLA_TSS2).as_reader()
    control.longitudinal_inputs.ioniq6_start_enabled = ioniq6_start_eligible(control.CP)
    control.CI = interface(control.CP)
    control.VM = VehicleModel(control.CP)
    control.LaC = LatControlTorque(control.CP, control.CI, DT_CTRL)
    control.LoC = LongControl(control.CP)
    control.sm = messaging.SubMaster(["vehicleParameters", "lateralTorqueParameters", "carState", "selfdriveState",
                                     "longitudinalPlan", "modelV2", "lateralManeuverPlan", "lateralDelay", "onroadEvents"],
                                    frequency=100)
    control.curvature = control.desired_curvature = 0.0
    control.steer_limited_by_safety = False
    control.lane_centering_controller = LaneCenteringController()
    control.lane_change_policy = LaneChangePolicy()
    control.lane_change_smoother = LaneChangeSmoother()
    control.torque_host = None  # Explicit feature-off state for the manually constructed Controls fixture.
    control.torque_learning_allowed = False
    control.longitudinal_inputs.gm_start_enabled = False
    control.longitudinal_inputs.gm_volt_enabled = False
    control.longitudinal_inputs.toyota_sienna_replay = False
    control.lane_centering_host = None
    control.last_lane_centering_result = None
    return control

  request = LaneCenteringRequest(ControlMode.COMBINED, LaneCenteringSettings(True, 0.0, 0.0, True), DT_CTRL)
  changes = ("disabled_setting", "off", "long_only", "lateral_only", "fault", "disabled_host", "override", "signal",
             "invalid_model", "stale_model", "clock_reset", "absent_request", "invalid_request", "maneuver")
  records = []

  def input_bytes(control):
    return {name: tuple(event.as_builder().to_bytes() for event in control.sm[name]) if name == "onroadEvents"
            else control.sm[name].as_builder().to_bytes() for name in control.sm.services}

  for change in changes:
    candidate, reference = host(), host()
    previous_correction = 0.0
    # Each gate starts with positive acquired state; absence/disabled equivalence
    # starts disabled from the beginning to compare all controller history exactly.
    for tick in range(140):
      phase = "warm" if tick < 80 else change
      timestamp = 1_000_000_000 + tick * 10_000_000
      inputs = []

      def message(service, size=None, valid=True, timestamp=timestamp, inputs=inputs):
        msg = messaging.new_message(service, size, valid=valid, logMonoTime=timestamp)
        inputs.append(msg)
        return getattr(msg, service)

      cs = message("carState")
      cs.vEgo = cs.vEgoRaw = 20.0
      cs.vCruise = cs.vCruiseCluster = 100.0
      cs.canValid = True
      cs.steerFaultTemporary = phase == "fault"
      cs.steeringPressed = phase == "override"
      cs.leftBlinker = phase == "signal"
      state = message("selfdriveState")
      state.enabled = state.active = phase != "disabled_host"
      state.state = "enabled" if state.enabled else "disabled"
      lp = message("vehicleParameters")
      lp.stiffnessFactor, lp.steerRatio = 1.0, candidate.CP.steerRatio
      message("longitudinalPlan").aTarget = 0.5
      message("lateralDelay").lateralDelay = 0.1
      message("onroadEvents", 0)
      if tick % 5 == 0 and phase != "stale_model":
        event = messaging.new_message("modelV2", valid=phase != "invalid_model", logMonoTime=timestamp)
        event.modelV2 = model()
        event.modelV2.action.desiredCurvature = 0.0002
        inputs.append(event)
      if phase == "maneuver":
        message("lateralManeuverPlan").desiredCurvature = -0.0004
      readers = [msg.as_reader() for msg in inputs]
      candidate.sm.update_msgs(timestamp / 1e9, readers)
      reference.sm.update_msgs(timestamp / 1e9, readers)
      before = input_bytes(candidate)
      configured = request
      if change == "disabled_setting":
        configured = replace(request, settings=replace(request.settings, enabled=False))
      elif phase == "off":
        configured = replace(request, mode=ControlMode.OFF)
      elif phase == "long_only":
        configured = replace(request, mode=ControlMode.LONGITUDINAL_ONLY)
      elif phase == "lateral_only":
        configured = replace(request, mode=ControlMode.LATERAL_ONLY)
      elif phase == "clock_reset":
        configured = replace(request, time_discontinuity=True)
      elif phase == "absent_request":
        configured = None
      elif phase == "invalid_request":
        configured = "invalid"
      prior_curvature = candidate.desired_curvature
      command, lateral = candidate.state_control(lane_centering=configured)
      base_command, _ = reference.state_control() if reference_method is None else reference_method(reference)
      after = input_bytes(candidate)
      if before != after:
        raise AssertionError("Host changed its supplied messages")
      result = candidate.last_lane_centering_result
      if result is not None and result.candidate_curvature is not None:
        expected, _ = clip_curvature(cs.vEgo, prior_curvature, result.candidate_curvature, lp.roll)
        published_precision = struct.unpack("f", struct.pack("f", expected))[0]
        if candidate.desired_curvature != expected or command.actuators.curvature != published_precision:
          raise AssertionError("Lane candidate bypassed native curvature limiting")
      if result is not None and result.correction != 0.0:
        baseline_input = result.candidate_curvature - result.correction
        without_lane, _ = clip_curvature(cs.vEgo, prior_curvature, baseline_input, lp.roll)
        if not math.isclose(candidate.lane_centering_applied, candidate.desired_curvature - without_lane, abs_tol=1e-12):
          raise AssertionError("Lane feedback did not reflect the final command limiter")
      elif candidate.lane_centering_applied != 0.0:
        raise AssertionError("Inactive lane contribution remained visible")
      records.append({"scenario": change, "phase": phase, "tick": tick,
                      "model_sample": candidate.sm.logMonoTime["modelV2"], "model_checks": candidate.sm.all_checks(["modelV2"]),
                      "result": asdict(result) if result is not None else None, "previous_correction": previous_correction,
                      "host": command.to_dict(), "reference": base_command.to_dict(), "controller_active": lateral.active})
      previous_correction = result.correction if result is not None else 0.0
  Path(output).write_text(json.dumps({"scope": "Native host/controller software composition; supplied authority, no vehicle qualification",
                                    "records": records}, indent=2) + "\n")


class TestLaneHost(unittest.TestCase):
  def test_native_host_gates_limiter_and_unchanged_longitudinal_path(self):
    ipc_root = "/tmp" if sys.platform == "darwin" else "/dev/shm"
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory(prefix="msgq_lane-host-", dir=ipc_root) as ipc:
      output = Path(tmp) / "observations.json"
      env = dict(os.environ, OPENPILOT_PREFIX=Path(ipc).name.removeprefix("msgq_"))
      for name in ("CEREAL_FAKE", "CEREAL_FAKE_PREFIX", "SIMULATION"):
        env.pop(name, None)
      run = subprocess.run([sys.executable, "-m", "openpilot.starpilot.lateral.tests.test_lane_host", "--probe", str(output)],
                           cwd=BASEDIR, env=env, capture_output=True, text=True, timeout=30)
      self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
      records = json.loads(output.read_text())["records"]
    self.assertEqual(len(records), 1960)
    for row in records:
      phase, result, command, reference = row["phase"], row["result"], row["host"], row["reference"]
      with self.subTest(scenario=row["scenario"], tick=row["tick"]):
        for field in ("enabled", "latActive", "longActive"):
          self.assertEqual(command[field], reference[field])
        self.assertEqual(command["actuators"]["accel"], reference["actuators"]["accel"])
        self.assertTrue(math.isfinite(command["actuators"]["torque"]))
        if row["scenario"] == "disabled_setting":
          self.assertEqual(command, reference)
        elif phase == "warm" and row["tick"] >= 20:
          self.assertGreater(result["correction"], 0.0)
          self.assertGreater(result["correction"], row["previous_correction"])
        elif phase in ("off", "long_only", "fault", "disabled_host", "override", "invalid_model", "clock_reset", "invalid_request"):
          self.assertEqual(result["correction"], 0.0)
        elif phase == "absent_request":
          self.assertIsNone(result)
        elif phase == "signal":
          self.assertLess(result["correction"], row["previous_correction"])
        elif phase == "stale_model" and not row["model_checks"]:
          self.assertEqual(result["correction"], 0.0)
        elif phase == "maneuver":
          self.assertAlmostEqual(result["candidate_curvature"] - result["correction"], -0.0004, places=9)
        if phase in ("fault", "disabled_host"):
          self.assertFalse(command["latActive"])
          self.assertEqual(command["actuators"]["torque"], 0.0)
    stale = [row for row in records if row["phase"] == "stale_model"]
    self.assertTrue(any(row["model_checks"] for row in stale))
    self.assertTrue(any(not row["model_checks"] for row in stale))
    held = [row for row in records if row["scenario"] == "lateral_only" and row["tick"] in (21, 22)]
    self.assertEqual(held[0]["model_sample"], held[1]["model_sample"])
    self.assertGreater(held[1]["result"]["correction"], held[0]["result"]["correction"])


if __name__ == "__main__":
  if "--probe" in sys.argv:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, required=True)
    probe(parser.parse_args().probe)
  else:
    unittest.main()
