"""GM pedal tuning through PID and actuator demand."""

from openpilot.starpilot.longitudinal.extension import LongitudinalContext
from openpilot.starpilot.longitudinal.tests.extension_helpers import extension_state
from openpilot.starpilot.longitudinal.tests.extension_helpers import attach_inputs
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from opendbc.car import structs
from opendbc.car.gm.carcontroller import CarController, bolt_pedal_fraction
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.longitudinal import PedalStartEvidence
from opendbc.car.gm.bolt_cc import BoltCcLongitudinalPolicy
from opendbc.car.gm.tests.test_bolt_pedal import params as bolt_params
from opendbc.car.gm.values import CAR, DBC, PEDAL_BOLT_CAR, CarControllerParams
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.selfdrive.controls.controlsd import Controls


ACC_PEDAL = CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL


def state(speed=12.0, accel=0.0):
  return SimpleNamespace(vEgo=speed, aEgo=accel, brakePressed=False, gasPressed=False,
                         canValid=True, canTimeout=False, cruiseState=SimpleNamespace(standstill=False))


def controller_step(cp, demand, *, frame=4, controller=None, stock_acc=False,
                    long_active=True, brake=False, available=True, speed=12.0, stopping=False):
  controller = controller or CarController(DBC[cp.carFingerprint], cp)
  controller.frame = frame
  controller.last_steer_frame = frame
  now_ns = 1_000_000_000 + (frame - 4) * 10_000_000
  control = structs.CarControl()
  control.enabled = long_active
  control.longActive = long_active
  control.actuators.accel = demand
  if stopping:
    control.actuators.longControlState = structs.CarControl.Actuators.LongControlState.stopping
  vehicle = structs.CarState()
  vehicle.vEgo = speed
  vehicle.aEgo = 0.0
  vehicle.brakePressed = brake
  vehicle.gearShifter = structs.CarState.GearShifter.low
  vehicle.cruiseState.available = available
  vehicle.cruiseState.enabled = stock_acc
  cs = SimpleNamespace(out=vehicle.as_reader(), pedal_sensor_healthy=True, pedal_sensor_ts_nanos=now_ns - 50_000_000,
                       stock_acc_status_ts_nanos=now_ns - 50_000_000, cam_lka_steering_cmd_counter=0,
                       loopback_lka_steering_cmd_updated=False, loopback_lka_steering_cmd_ts_nanos=now_ns,
                       pt_lka_steering_cmd_counter=0, buttons_counter=0,
                       pscm_status=dict.fromkeys(('HandsOffSWDetectionMode', 'HandsOffSWlDetectionStatus',
                                                  'LKATorqueDeliveredStatus', 'LKADriverAppldTrq',
                                                  'LKATorqueDelivered', 'LKATotalTorqueDelivered',
                                                  'RollingCounter', 'PSCMStatusChecksum'), 0))
  _, messages = controller.update(control.as_reader(), cs, now_ns)
  return controller, messages


class GMPedalLongPolicyTests(unittest.TestCase):
  def test_start_branch_order_and_profile_sentinels(self):
    from opendbc.car.gm.longitudinal import GMPedalStartPolicy
    for ceiling in (None, -0.2, 0.0, 0.1, 0.8):
      for traffic, custom, lead, target in ((True, False, False, 0.4), (False, True, False, 0.4),
                                            (False, False, True, 0.2), (False, False, False, 0.4)):
        expected = (min(max(target, 0.0), 0.55) if traffic or custom or (lead and target <= 0.25)
                    else min(0.55, ceiling) if ceiling is not None and ceiling > 0 else 0.55)
        evidence = PedalStartEvidence(1, 10, lead, traffic, custom, ceiling)
        self.assertEqual(GMPedalStartPolicy.output(target, evidence), expected)

  def test_launch_handoff_recurrence_and_release_boundaries(self):
    states = structs.CarControl.Actuators.LongControlState
    for alpha in (False, True):
      long = LongControl(bolt_params(ACC_PEDAL, setting=True, pedal=True, alpha_long=alpha))
      cs = state(0.0)
      tick = 0

      def step(target=0.5, stop=False, lead=True, active=True, evidence=True, long=long, cs=cs):
        nonlocal tick
        tick += 1
        observed = PedalStartEvidence(1, 1_000_000_000 + tick * 10_000_000, lead) if evidence else None
        return long.update(active, cs, target, stop, (-4., 2.), context=LongitudinalContext(gm_start_evidence=observed))

      cs.cruiseState.standstill = True
      self.assertEqual(step(), 0.55)  # Interceptor ignores OEM standstill on engagement.
      self.assertEqual(long.long_control_state, states.starting)
      cs.vEgo = 0.35
      step()
      self.assertEqual(long.long_control_state, states.starting)
      cs.vEgo = 0.35001
      previous = 0.55
      with patch.object(long.pid, 'update', return_value=0.01):
        for frame in range(76):
          expected = max(0.01, min(previous, min(float(np.interp(cs.vEgo, [0., .5, 1.25], [.22, .18, .10])), .4 * .5))) if frame < 75 else 0.01
          self.assertAlmostEqual(step(), expected)
          self.assertEqual(long.long_control_state, states.pid)
          previous = expected
      step(stop=True)
      self.assertEqual(long.long_control_state, states.stopping)
      cs.vEgo = 0.0
      step(lead=False)  # Strong request alone cannot immediately release OEM standstill.
      self.assertEqual(long.long_control_state, states.stopping)
      cs.cruiseState.standstill = False
      step(lead=False)
      self.assertEqual(long.long_control_state, states.starting)
      cs.vEgo = 0.36
      with patch.object(long.pid, 'update', return_value=0.01):
        self.assertGreater(step(), 0.01)
        self.assertEqual(step(lead=False), 0.01)
      self.assertEqual(extension_state(long, 'gm_start').handoff_frames, 0)
      self.assertEqual(step(active=False), 0.0)
      self.assertEqual(long.long_control_state, states.off)
      step()
      cs.vEgo = 0.4
      with patch.object(long.pid, 'update', return_value=0.01):
        self.assertEqual(step(evidence=False), 0.01)
      self.assertEqual(extension_state(long, 'gm_start').handoff_frames, 0)

  def test_controlsd_start_evidence_rejects_stale_plan_and_preserves_custom_branch(self):
    now = 1_050_000_000
    controls = Controls.__new__(Controls)
    attach_inputs(controls)
    controls.CP = bolt_params(ACC_PEDAL, setting=True, pedal=True)
    controls.longitudinal_inputs.CP = controls.CP
    controls.longitudinal_inputs.gm_source_floor_ns = 900_000_000
    controls.longitudinal_inputs.gm_profile_host = SimpleNamespace(sample=lambda *args: SimpleNamespace(acceleration_max=0.12, custom_acceleration=True))

    class SubMaster(SimpleNamespace):
      def __getitem__(self, name):
        return {'carState': state(0.0), 'selfdriveState': SimpleNamespace(personality=1)}[name]

    names = ('carState', 'longitudinalPlan', 'selfdriveState')
    controls.sm = SubMaster(logMonoTime=dict.fromkeys(names, now - 20_000_000),
                             recv_time=dict.fromkeys(names, (now - 10_000_000) / 1e9), all_checks=lambda names: True)
    with patch.object(controls.longitudinal_inputs, '_qualified_radar_leads', return_value=((SimpleNamespace(present=True),), now, 900_000_000)):
      evidence = controls.longitudinal_inputs._gm_start_evidence()
      self.assertTrue(evidence.has_lead)
      self.assertTrue(evidence.custom_acceleration)
      long = LongControl(controls.CP)
      self.assertAlmostEqual(long.update(True, state(0.0), 0.3, False, (-4.0, 2.0), context=LongitudinalContext(gm_start_evidence=evidence)), 0.3)
      controls.sm.logMonoTime['longitudinalPlan'] = now - 160_000_000
      self.assertIsNone(controls.longitudinal_inputs._gm_start_evidence())
      controls.sm.logMonoTime['longitudinalPlan'] = now - 20_000_000
      controls.sm.recv_time['longitudinalPlan'] = (now + 1_000_000) / 1e9
      self.assertIsNone(controls.longitudinal_inputs._gm_start_evidence())
    controls.sm.recv_time['longitudinalPlan'] = (now - 10_000_000) / 1e9
    with patch.object(controls.longitudinal_inputs, '_qualified_radar_leads', return_value=((SimpleNamespace(present=False),), now, 900_000_000)):
      controls.longitudinal_inputs.gm_profile_host = SimpleNamespace(sample=lambda *args: SimpleNamespace(acceleration_max=0.4, custom_acceleration=False))
      evidence = controls.longitudinal_inputs._gm_start_evidence()
      self.assertFalse(evidence.custom_acceleration)
      self.assertAlmostEqual(LongControl(controls.CP).update(True, state(0.0), 0.2, False, (-4.0, 2.0),
        context=LongitudinalContext(gm_start_evidence=evidence)), 0.4)
      controls.longitudinal_inputs.gm_profile_host = SimpleNamespace(sample=lambda *args: None, disabled=True)
      evidence = controls.longitudinal_inputs._gm_start_evidence()
      self.assertIsNotNone(evidence)
      self.assertAlmostEqual(LongControl(controls.CP).update(True, state(0.0), 0.2, False, (-4.0, 2.0),
        context=LongitudinalContext(gm_start_evidence=evidence)), 0.55)
      controls.longitudinal_inputs.gm_profile_host.disabled = False
      self.assertIsNone(controls.longitudinal_inputs._gm_start_evidence())
      controls.longitudinal_inputs.gm_profile_host = None
      controls.longitudinal_inputs.gm_boot_offset_ns = 0
      controls.longitudinal_inputs.gm_traffic_state = SimpleNamespace(sample=lambda *args, **kwargs: True)
      evidence = controls.longitudinal_inputs._gm_start_evidence()
      self.assertTrue(evidence.traffic_mode)
      self.assertAlmostEqual(LongControl(controls.CP).update(True, state(0.0), 0.1, False, (-4.0, 2.0),
        context=LongitudinalContext(gm_start_evidence=evidence)), 0.1)
      controls.longitudinal_inputs.gm_traffic_state = SimpleNamespace(sample=lambda *args, **kwargs: None)
      self.assertIsNone(controls.longitudinal_inputs._gm_start_evidence())
    with patch.object(controls.longitudinal_inputs, '_qualified_radar_leads', return_value=None):
      self.assertIsNone(controls.longitudinal_inputs._gm_start_evidence())

  def test_dedicated_start_release_hysteresis_and_profile_caps(self):
    states = structs.CarControl.Actuators.LongControlState
    for alpha in (False, True):
      cp = bolt_params(ACC_PEDAL, setting=True, pedal=True, alpha_long=alpha)
      long = LongControl(cp)
      cs = state(0.0)
      long.update(True, cs, -1.0, True, (-4.0, 2.0))
      for tick in range(35):
        evidence = PedalStartEvidence(1, 1_000_000_000 + tick * 10_000_000, False)
        output = long.update(True, cs, 0.2, False, (-4.0, 2.0), context=LongitudinalContext(gm_start_evidence=evidence))
        self.assertEqual(long.long_control_state, states.stopping if tick < 34 else states.starting)
      self.assertAlmostEqual(output, 0.55)
      for evidence, target, expected in (
        (PedalStartEvidence(1, 1_350_000_000, True), 0.2, 0.2),
        (PedalStartEvidence(1, 1_360_000_000, False, traffic_mode=True), 0.1, 0.1),
        (PedalStartEvidence(1, 1_370_000_000, False, custom_acceleration=True), 0.3, 0.3),
        (PedalStartEvidence(1, 1_380_000_000, False, profile_max_accel=0.4), 0.7, 0.4),
      ):
        self.assertAlmostEqual(long.update(True, cs, target, False, (-4.0, 2.0), context=LongitudinalContext(gm_start_evidence=evidence)), expected)
      cs.vEgo = 0.36
      long.update(True, cs, 0.3, False, (-4.0, 2.0), context=LongitudinalContext(gm_start_evidence=PedalStartEvidence(1, 1_390_000_000, False)))
      self.assertEqual(long.long_control_state, states.pid)

  def test_start_missing_evidence_and_drive_change_never_carry_release_counter(self):
    cp = bolt_params(ACC_PEDAL, setting=True, pedal=True)
    long = LongControl(cp)
    cs = state(0.0)
    long.update(True, cs, -1.0, True, (-4.0, 2.0))
    for tick in range(34):
      long.update(True, cs, 0.2, False, (-4.0, 2.0),
                  context=LongitudinalContext(gm_start_evidence=PedalStartEvidence(1, 1_000_000_000 + tick * 10_000_000, False)))
    long.update(True, cs, 0.2, False, (-4.0, 2.0), context=LongitudinalContext(gm_start_evidence=PedalStartEvidence(2, 1_340_000_000, False)))
    self.assertEqual(long.long_control_state, structs.CarControl.Actuators.LongControlState.stopping)
    # Missing evidence follows the pre-existing state machine and cannot retain a launch kick.
    reference = LongControl(cp)
    reference.long_control_state = long.long_control_state
    reference.last_output_accel = long.last_output_accel
    self.assertEqual(long.update(True, cs, 0.2, False, (-4.0, 2.0)),
                     reference.update(True, cs, 0.2, False, (-4.0, 2.0)))
    self.assertIsNone(extension_state(long, 'gm_start').release_since_ns)

  def test_start_override_and_unadmitted_variants_keep_native_path(self):
    evidence = PedalStartEvidence(1, 1_000_000_000, True)
    for candidate in PEDAL_BOLT_CAR:
      for alpha in (False, True):
        cp = bolt_params(candidate, setting=True, pedal=True, alpha_long=alpha)
        if candidate != ACC_PEDAL:
          self.assertIsNone(extension_state(LongControl(cp), 'gm_start'))
        for field in ('brakePressed', 'gasPressed', 'canTimeout'):
          cs = state(0.0)
          setattr(cs, field, True)
          actual, reference = LongControl(cp), LongControl(cp)
          self.assertEqual(actual.update(True, cs, 0.3, False, (-4.0, 2.0), context=LongitudinalContext(gm_start_evidence=evidence)),
                           reference.update(True, cs, 0.3, False, (-4.0, 2.0)))
    self.assertIsNone(extension_state(LongControl(bolt_params(ACC_PEDAL, setting=False, pedal=True)), 'gm_start'))

  def test_original_speed_based_pid_limits_for_every_pedal_bolt(self):
    original_ceiling = ((0.0, 0.54), (1.5, 0.74), (4.0, 1.03), (8.0, 1.46),
                        (15.0, CarControllerParams.ACCEL_MAX))
    for candidate in PEDAL_BOLT_CAR:
      for alpha in (False, True):
        cp = bolt_params(candidate, setting=True, pedal=True, alpha_long=alpha)
        for speed, ceiling in original_ceiling:
          with self.subTest(candidate=candidate, alpha=alpha, speed=speed):
            floor, maximum = CarInterface.get_pid_accel_limits(cp, speed, 30.0)
            self.assertAlmostEqual(maximum, ceiling)
            expected_floor = (CarControllerParams.ACCEL_MIN if candidate == ACC_PEDAL else
                              float(np.interp(speed, (0.0, 1.5, 4.0, 8.0, 15.0, 30.0),
                                              (-0.93, -1.28, -1.98, -2.58, -2.86, -2.95))))
            self.assertAlmostEqual(floor, expected_floor)
    stock = bolt_params(CAR.CHEVROLET_BOLT_ACC_2022_2023, setting=True, pedal=True)
    self.assertEqual(CarInterface.get_pid_accel_limits(stock, 0.0, 30.0),
                     (CarControllerParams.ACCEL_MIN, CarControllerParams.ACCEL_MAX))

  def test_admission_and_original_positive_pid_for_each_exact_bolt_alpha_mode(self):
    for candidate in PEDAL_BOLT_CAR:
      for alpha in (False, True):
        with self.subTest(candidate=candidate, alpha=alpha):
          cp = bolt_params(candidate, setting=True, pedal=True, alpha_long=alpha)
          longitudinal = LongControl(cp)
          self.assertIsNotNone(extension_state(longitudinal, 'vehicle_policy'))
          limits = CarInterface.get_pid_accel_limits(cp, 12.0, 30.0)
          output = float(longitudinal.update(True, state(), 1.0, False, limits))
          self.assertAlmostEqual(float(longitudinal.pid.f), 0.2)
          self.assertTrue(0.25 < output < 0.30)
          self.assertTrue(limits[0] <= output <= limits[1])
          fallback = LongControl(bolt_params(candidate, setting=False, pedal=True, alpha_long=alpha))
          self.assertIsInstance(extension_state(fallback, 'vehicle_policy'), BoltCcLongitudinalPolicy)
          self.assertIsNone(extension_state(fallback, 'gm_start'))
    stock = LongControl(bolt_params(CAR.CHEVROLET_BOLT_ACC_2022_2023, setting=True, pedal=True))
    self.assertIsNone(extension_state(stock, 'vehicle_policy'))
    self.assertGreater(float(stock.update(True, state(), 1.0, False, (-4.0, 2.0))), 1.0)
    self.assertEqual(float(stock.pid.f), 1.0)

  def test_acc_pedal_startup_stock_handoff_override_and_disengage(self):
    for alpha in (False, True):
      with self.subTest(alpha=alpha):
        cp = bolt_params(ACC_PEDAL, setting=True, pedal=True, alpha_long=alpha)
        longitudinal = LongControl(cp)
        launch_limits = CarInterface.get_pid_accel_limits(cp, 0.0, 30.0)
        launch = float(longitudinal.update(True, state(0.0), 1.0, False, launch_limits))
        self.assertLessEqual(launch, 0.54)
        self.assertLessEqual(bolt_pedal_fraction(launch, 0.0, False), 0.20)
        cruising = float(longitudinal.update(True, state(), 1.0, False,
                                             CarInterface.get_pid_accel_limits(cp, 12.0, 30.0)))
        controller, messages = controller_step(cp, cruising, frame=8, stock_acc=True)
        self.assertEqual(controller.pedal_steady, 0.0)
        self.assertIn(0x1E1, [message[0] for message in messages])
        controller, messages = controller_step(cp, cruising, frame=12, controller=controller)
        self.assertTrue(0.0 < controller.pedal_steady < 0.50)
        self.assertIn(0x200, [message[0] for message in messages])
        controller, _ = controller_step(cp, cruising, frame=16, controller=controller, brake=True)
        self.assertEqual(controller.pedal_steady, 0.0)
        self.assertEqual(float(longitudinal.update(False, state(), 1.0, False, (-4.0, 2.0))), 0.0)
        controller, _ = controller_step(cp, 0.0, frame=20, controller=controller, long_active=False)
        self.assertEqual(controller.pedal_steady, 0.0)

  def test_zero_regen_and_friction_crossover_keep_distinct_demand(self):
    for alpha in (False, True):
      cp = bolt_params(ACC_PEDAL, setting=True, pedal=True, alpha_long=alpha)
      for target, expected_range, friction in ((0.0, (-0.01, 0.01), False),
                                               (-0.5, (-0.2, 0.0), False),
                                               (-3.5, (-4.0, -2.0), True)):
        with self.subTest(alpha=alpha, target=target):
          longitudinal = LongControl(cp)
          output = float(longitudinal.update(True, state(), target, False, (-4.0, 2.0)))
          self.assertTrue(expected_range[0] <= output <= expected_range[1])
          controller, messages = controller_step(cp, output)
          self.assertTrue(any(message[0] == 0x315 for message in messages))
          self.assertEqual(controller.apply_brake > 0, friction)
          self.assertTrue(0.0 <= controller.pedal_steady <= 1.0)
    for candidate in PEDAL_BOLT_CAR - {ACC_PEDAL}:
      policy = extension_state(LongControl(bolt_params(candidate, setting=True, pedal=True)), 'vehicle_policy')
      self.assertIsNotNone(policy)
      self.assertAlmostEqual(policy.feedforward(-3.0, 12.0, 0.0), -0.6)

  def test_stopping_resets_pid_and_respects_existing_limits(self):
    for alpha in (False, True):
      with self.subTest(alpha=alpha):
        cp = bolt_params(ACC_PEDAL, setting=True, pedal=True, alpha_long=alpha)
        longitudinal = LongControl(cp)
        self.assertGreater(longitudinal.update(True, state(), 0.5, False, (-4.0, 2.0)), 0.0)
        stopping = longitudinal.update(True, state(), -1.0, True, (-4.0, 2.0))
        self.assertTrue(-4.0 <= stopping <= 0.0)
        self.assertEqual(longitudinal.pid.i, 0.0)
        self.assertEqual(longitudinal.update(False, state(), 0.0, False, (-4.0, 2.0)), 0.0)

  def test_pedal_stopping_ramp_matches_original_demand_and_can_in_both_alpha_modes(self):
    for candidate in PEDAL_BOLT_CAR:
      for alpha in (False, True):
        with self.subTest(candidate=candidate, alpha=alpha):
          cp = bolt_params(candidate, setting=True, pedal=True, alpha_long=alpha)
          longitudinal = LongControl(cp)
          expected = 0.0
          actual_controller = reference_controller = None
          self.assertAlmostEqual(cp.stopAccel, -0.25)
          for tick in range(100):
            if expected > -0.25:
              expected = min(expected, 0.0) - 0.8 * 0.01
            expected = float(np.clip(expected, -4.0, 2.0))
            actual = float(longitudinal.update(True, state(0.5), -1.0, True, (-4.0, 2.0)))
            self.assertAlmostEqual(actual, expected)
            if tick % 4 == 0:
              actual_controller, messages = controller_step(cp, actual, frame=tick + 4,
                                                            controller=actual_controller, speed=0.5, stopping=True)
              reference_controller, reference = controller_step(cp, expected, frame=tick + 4,
                                                                 controller=reference_controller, speed=0.5, stopping=True)
              self.assertEqual(messages, reference)
          self.assertAlmostEqual(expected, -0.256)
          self.assertEqual(longitudinal.pid.i, 0.0)
          self.assertEqual(longitudinal.update(False, state(0.5), 0.0, False, (-4.0, 2.0)), 0.0)

    cp = bolt_params(ACC_PEDAL, setting=False, pedal=True)
    self.assertAlmostEqual(LongControl(cp).update(True, state(), -1.0, True, (-4.0, 2.0)), -0.1118)

  def test_original_target_step_and_saturation_freeze_integrator(self):
    for candidate in PEDAL_BOLT_CAR:
      for alpha in (False, True):
        with self.subTest(candidate=candidate, alpha=alpha):
          cp = bolt_params(candidate, setting=True, pedal=True, alpha_long=alpha)
          longitudinal = LongControl(cp)
          limits = (-4.0, 0.30)
          longitudinal.update(True, state(), 1.0, False, limits)
          self.assertEqual(extension_state(longitudinal, 'vehicle_policy').integrator_hold_frames, 13)
          self.assertEqual(longitudinal.pid.i, 0.0)
          for _ in range(12):
            longitudinal.update(True, state(), 1.0, False, limits)
          self.assertEqual(longitudinal.pid.i, 0.0)
          self.assertEqual(extension_state(longitudinal, 'vehicle_policy').integrator_hold_frames, 1)
          longitudinal.update(True, state(), 1.0, False, limits)
          self.assertEqual(extension_state(longitudinal, 'vehicle_policy').integrator_hold_frames, 0)
          self.assertEqual(longitudinal.pid.i, 0.0)  # positive saturation still freezes I
          longitudinal.update(True, state(), 0.0, False, (-4.0, 2.0))
          self.assertEqual(extension_state(longitudinal, 'vehicle_policy').integrator_hold_frames, 13)
          longitudinal.update(False, state(), 0.0, False, (-4.0, 2.0))
          self.assertEqual(extension_state(longitudinal, 'vehicle_policy').integrator_hold_frames, 0)
          self.assertEqual(extension_state(longitudinal, 'vehicle_policy').last_a_target, 0.0)

          unsaturated = LongControl(cp)
          for _ in range(13):
            unsaturated.update(True, state(), 1.0, False, (-4.0, 2.0))
          self.assertEqual(unsaturated.pid.i, 0.0)
          unsaturated.update(True, state(), 1.0, False, (-4.0, 2.0))
          self.assertGreater(unsaturated.pid.i, 0.0)

  def test_negative_target_bleeds_stale_positive_i_and_caps_drive_output(self):
    for candidate in PEDAL_BOLT_CAR:
      for alpha in (False, True):
        with self.subTest(candidate=candidate, alpha=alpha):
          cp = bolt_params(candidate, setting=True, pedal=True, alpha_long=alpha)
          longitudinal = LongControl(cp)
          longitudinal.pid.i = 1.0
          output = longitudinal.update(True, state(accel=-0.4), -0.8, False, (-4.0, 2.0))
          self.assertAlmostEqual(longitudinal.pid.i, 0.46)
          self.assertEqual(output, 0.0)
          self.assertEqual(extension_state(longitudinal, 'vehicle_policy').integrator_hold_frames, 13)


if __name__ == '__main__':
  unittest.main()
