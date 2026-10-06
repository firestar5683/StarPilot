"""Native planner/MPC comparisons with real Cap'n Proto input messages."""

import unittest
from dataclasses import replace
from typing import Any, cast

from openpilot.cereal import log, messaging
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.selfdrive.controls.radard import _LEAD_ACCEL_TAU
from openpilot.starpilot.longitudinal.cruise_ceiling import CruiseCeiling, select_cruise_ceiling
from openpilot.starpilot.speed_limits.acceptance import Authority, LongitudinalOwner, Mode
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR

ACTIVE = Authority(Mode.LONGITUDINAL_ONLY, LongitudinalOwner.SYSTEM, False, True, False, False)
FRAMES = 40
TRANSITION = 12
V_EGO = 20.0


def messages(*, lead=False, e2e=False, force=False, unset=False, off=False, disabled=False, zero_cruise=False):
  radar = messaging.new_message("radarState")
  control = messaging.new_message("controlsState")
  selfdrive = messaging.new_message("selfdriveState")
  car_state = messaging.new_message("carState")
  vehicle = messaging.new_message("vehicleParameters")
  car_control = messaging.new_message("carControl")
  model = messaging.new_message("modelV2")
  lead_data = log.RadarState.LeadData.new_message()
  lead_data.dRel = 36.0 if lead else 200.0
  lead_data.vLead = 10.0 if lead else 30.0
  lead_data.vLeadK = lead_data.vLead
  lead_data.vRel = lead_data.vLead - V_EGO
  lead_data.aLeadK = 0.0
  lead_data.aLeadTau = float(_LEAD_ACCEL_TAU)
  lead_data.present = lead
  lead_data.modelProb = 1.0 if lead else 0.0
  lead_data.radar = True
  radar.radarState.leadOne = lead_data
  radar.radarState.leadTwo = lead_data
  control.controlsState.longControlState = LongCtrlState.off if off else LongCtrlState.pid
  control.controlsState.forceDecel = force
  selfdrive.selfdriveState.enabled = not (off or disabled)
  selfdrive.selfdriveState.experimentalMode = e2e
  selfdrive.selfdriveState.personality = log.LongitudinalPersonality.standard
  car_state.carState.vEgo = V_EGO
  car_state.carState.aEgo = 0.0
  car_state.carState.vCruise = 255.0 if unset else (0.0 if zero_cruise else 100.0)
  car_state.carState.standstill = False
  car_state.carState.steeringAngleDeg = 0.0
  car_control.carControl.orientationNED = [0.0, 0.0, 0.0]
  vehicle.vehicleParameters.angleOffsetDeg = 0.0
  model.modelV2.meta.disengagePredictions.gasPressProbs = [1.0] * 6
  model.modelV2.action.desiredAcceleration = -2.0 if e2e else 0.5
  model.modelV2.action.shouldStop = e2e
  envelopes = (radar, control, selfdrive, car_state, vehicle, car_control, model)
  sm = {"radarState": radar.radarState, "controlsState": control.controlsState,
        "selfdriveState": selfdrive.selfdriveState, "carState": car_state.carState,
        "vehicleParameters": vehicle.vehicleParameters, "carControl": car_control.carControl,
        "modelV2": model.modelV2}
  return sm, envelopes


def snapshot(planner):
  return (float(planner.output_a_target), float(planner.a_cruise), str(planner.mpc.source),
          bool(planner.output_should_stop), tuple(float(x) for x in planner.v_desired_trajectory[:4]))


def message_bytes(envelopes):
  out = []
  for msg in envelopes:
    out.append(msg.to_bytes())
    msg.clear_write_flag()
  return out


class NativePlannerCeilingTests(unittest.TestCase):
  def setUp(self):
    self.cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    self.assertTrue(self.cp.openpilotLongitudinalControl)

  def compare(self, *, case="ordinary", ceiling=(), expected_status="applied"):
    default = LongitudinalPlanner(self.cp, init_v=V_EGO)
    opt_in = LongitudinalPlanner(self.cp, init_v=V_EGO)
    resets = {"default": [], "opt_in": []}
    for name, planner in (("default", default), ("opt_in", opt_in)):
      original = planner.mpc.reset

      def record_reset(original=original, planner=planner, name=name):
        resets[name].append(int(planner.mpc.solution_status))
        return original()

      cast(Any, planner.mpc).reset = record_reset
    differences = []
    final = None
    for frame in range(FRAMES):
      active = frame >= TRANSITION
      conditions = {"lead": case == "lead" and active, "e2e": case == "e2e" and active,
                    "force": case == "force" and active, "unset": case == "unset" and active,
                    "off": case == "off" and active, "disabled": case == "disabled" and active,
                    "zero_cruise": case == "zero_cruise" and active}
      left, left_envelopes = messages(**conditions)
      right, right_envelopes = messages(**conditions)
      before = message_bytes((*left_envelopes, *right_envelopes))
      default.update(left)
      actual_ceiling = None if not active or ceiling == () else ceiling
      opt_in.update(right, cruise_ceiling=actual_ceiling)
      after = message_bytes((*left_envelopes, *right_envelopes))
      self.assertEqual(before, after, "planner mutated a supplied Cap'n Proto message")
      self.assertEqual(default.last_cruise_ceiling_status, "absent")
      self.assertEqual(default.mpc.solution_status, 0)
      self.assertEqual(opt_in.mpc.solution_status, 0)
      if snapshot(default) != snapshot(opt_in):
        differences.append(frame)
      final = (snapshot(default), snapshot(opt_in))
      if active:
        self.assertEqual(opt_in.last_cruise_ceiling_status, expected_status)
    self.assertEqual(resets, {"default": [], "opt_in": []})
    return differences, final

  def test_default_and_explicit_absence_are_identical(self):
    differences, _ = self.compare(ceiling=None, expected_status="absent")
    self.assertEqual(differences, [])

  def test_valid_lower_cap_changes_cruise_without_mutating_driver_message(self):
    differences, final = self.compare(ceiling=CruiseCeiling(60.0 / 3.6, ACTIVE))
    self.assertEqual(differences[0], TRANSITION)
    self.assertLess(final[1][0], final[0][0])

  def test_above_driver_cap_leaves_native_path_equal(self):
    differences, _ = self.compare(ceiling=CruiseCeiling(40.0, ACTIVE), expected_status="above_driver")
    self.assertEqual(differences, [])

  def test_lead_and_e2e_braking_remain_lower_candidates(self):
    for case, source in (("lead", "1"), ("e2e", "4")):
      with self.subTest(case=case):
        _, final = self.compare(case=case, ceiling=CruiseCeiling(60.0 / 3.6, ACTIVE))
        self.assertEqual(final[0][0], final[1][0])
        self.assertEqual(final[0][2], source)
        self.assertEqual(final[1][2], source)

  def test_force_decel_unset_and_off_do_not_apply_cap(self):
    for case, status in (("force", "force_decel"), ("unset", "driver_cruise_unavailable"),
                         ("zero_cruise", "driver_cruise_unavailable"), ("off", "inactive"), ("disabled", "inactive")):
      with self.subTest(case=case):
        differences, _ = self.compare(case=case, ceiling=CruiseCeiling(60.0 / 3.6, ACTIVE), expected_status=status)
        self.assertEqual(differences, [])

  def test_host_without_system_long_does_not_apply_cap(self):
    self.cp.openpilotLongitudinalControl = False
    differences, _ = self.compare(ceiling=CruiseCeiling(60.0 / 3.6, ACTIVE), expected_status="inactive")
    self.assertEqual(differences, [])

  def test_pure_boundary_rejects_coerced_host_flags(self):
    kwargs = {"driver_v_cruise_kph": 100.0, "driver_cruise_mps": 100.0 / 3.6,
              "system_long_available": True, "long_control_active": True,
              "selfdrive_enabled": True, "force_decel": False}
    for name in ("system_long_available", "long_control_active", "selfdrive_enabled", "force_decel"):
      with self.subTest(name=name):
        invalid = {**kwargs, name: "false"}
        result = select_cruise_ceiling(CruiseCeiling(10.0, ACTIVE), **cast(Any, invalid))
        self.assertEqual(result.status, "invalid")
        self.assertIsNone(result.effective_mps)

  def test_pure_boundary_rejects_unavailable_driver_speed(self):
    for driver_kph in (-1.0, 0.0, 255.0, float("nan")):
      with self.subTest(driver_kph=driver_kph):
        result = select_cruise_ceiling(
          CruiseCeiling(10.0, ACTIVE), driver_v_cruise_kph=driver_kph, driver_cruise_mps=20.0,
          system_long_available=True, long_control_active=True, selfdrive_enabled=True, force_decel=False)
        self.assertEqual(result.status, "driver_cruise_unavailable")
        self.assertIsNone(result.effective_mps)

  def test_invalid_and_contradictory_authority_leave_native_path_equal(self):
    bad = (
      CruiseCeiling(0.0, ACTIVE), CruiseCeiling(-1.0, ACTIVE), CruiseCeiling(float("nan"), ACTIVE),
      CruiseCeiling(cast(Any, True), ACTIVE),
      CruiseCeiling(10.0, replace(ACTIVE, stock_acc_active=True)),
      CruiseCeiling(10.0, replace(ACTIVE, fully_disengaged=True)),
      CruiseCeiling(10.0, replace(ACTIVE, owner=LongitudinalOwner.STOCK, longitudinal_active=False)),
    )
    for ceiling in bad:
      with self.subTest(ceiling=ceiling):
        status = "inactive" if ceiling.authority.owner is LongitudinalOwner.STOCK else "invalid"
        differences, _ = self.compare(ceiling=ceiling, expected_status=status)
        self.assertEqual(differences, [])


if __name__ == "__main__":
  unittest.main()


class GasOverrideBoostTests(unittest.TestCase):
  def setUp(self):
    self.cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)

  def overridden_plan(self):
    planner = LongitudinalPlanner(self.cp, init_v=V_EGO, init_a=1.)
    payloads, _ = messages(e2e=True)
    class Frame(dict):
      logMonoTime = dict.fromkeys(payloads, 1_000_000_000)
      valid = dict.fromkeys(payloads, True)
      alive = dict.fromkeys(payloads, True)
    sm = Frame(payloads)
    sm['modelV2'].action.shouldStop = False
    sm['modelV2'].action.desiredAcceleration = -.4
    sm['carControl'].longActive = True
    planner.update(sm)
    self.assertTrue(planner.accel_boost.boost_eligible)
    sm['carState'].gasPressed = True
    for _ in range(80):
      planner.update(sm)
    self.assertAlmostEqual(planner.accel_boost.total_boost, .05)
    self.assertAlmostEqual(float(planner.output_a_target), -.35, places=6)
    return planner, sm

  def test_real_gas_override_budget_release_and_disable(self):
    planner, sm = self.overridden_plan()
    # Holding one press cannot accumulate more than the original .05 override budget.
    for _ in range(80):
      planner.update(sm)
    self.assertAlmostEqual(planner.accel_boost.total_boost, .05)
    sm['carState'].gasPressed = False
    planner.update(sm)
    sm['carState'].gasPressed = True
    for _ in range(80):
      planner.update(sm)
    self.assertAlmostEqual(planner.accel_boost.total_boost, .1)
    sm['selfdriveState'].enabled = False
    planner.update(sm)
    self.assertEqual(planner.accel_boost.total_boost, 0.)

  def test_boost_cannot_replace_lower_lead_or_cruise_candidates(self):
    planner, sm = self.overridden_plan()
    sm['carState'].gasPressed = False
    sm['carState'].vCruise = 0.
    for _ in range(80):
      planner.update(sm)
    self.assertLess(float(planner.output_a_target), -.35)
    self.assertEqual(planner.mpc.source, log.LongitudinalPlan.LongitudinalPlanSource.cruise)
    lead, _ = messages(lead=True, e2e=True)
    lead['modelV2'].action.shouldStop = False
    lead['modelV2'].action.desiredAcceleration = -.4
    for _ in range(80):
      planner.update(lead)
    self.assertLess(float(planner.output_a_target), -.35)
    self.assertIn(planner.mpc.source, (1, 2))

  def test_boost_retains_model_stop_and_committed_force_stop(self):
    from openpilot.starpilot.longitudinal.force_stop import StopPlan
    planner, sm = self.overridden_plan()
    sm['carState'].gasPressed = False
    sm['modelV2'].action.shouldStop = True
    planner.update(sm)
    self.assertTrue(planner.output_should_stop)
    from openpilot.selfdrive.controls.lib.longcontrol import LongControl
    receiver = LongControl(self.cp)
    actual = receiver.update(True, sm['carState'], planner.output_a_target,
                             planner.output_should_stop, (-3.5, 2.))
    self.assertEqual(receiver.long_control_state, LongCtrlState.stopping)
    self.assertLessEqual(actual, 0.)
    sm['modelV2'].action.shouldStop = False
    hold = StopPlan(model_ns=1_000_000_000, forcing=True, should_stop=True, manual_hold=True,
                    speed_ceiling_mps=0., obstacle_m=6.)
    for _ in range(10):
      planner.update(sm, force_stop_provider=lambda _: hold)
    self.assertTrue(planner.output_should_stop)
    self.assertTrue(planner.force_stop_plan.manual_hold)
    self.assertLessEqual(float(planner.output_a_target), 0.)
