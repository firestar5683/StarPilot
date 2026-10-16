"""Independent physical fit/replay into current bounded Controls learning stages."""
from dataclasses import replace
import json
import math
from pathlib import Path
import unittest

from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR
from openpilot.starpilot.flm.learning_wire import result_message
from openpilot.starpilot.flm.tests.test_registered_controls_global import controls_for
from openpilot.starpilot.flm.tests.test_registered_accepted_profile import computed_registered_fit
from openpilot.starpilot.flm.tests.test_live_calibration_paths import live_frame, BASE
from openpilot.starpilot.lateral.learning_preferences import KEY as PREFERENCE_KEY, replace_preference
from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY as TORQUE_KEY, replace_field, serialize_document


def current_fit(controls):
  for tick in range(30):
    live_frame(controls, tick, 'a' * 32)
  return computed_registered_fit(controls.CP, controls.global_learning, BASE + 300_000_000)


def apply_fit(controls, result, validation):
  command = None
  for tick in range(30, 71):
    command, _ = live_frame(controls, tick, 'a' * 32, result=result, validation=validation)
  return command


class TestAutomaticLearningIntegration(unittest.TestCase):
  def params(self):
    return interfaces[CAR.TOYOTA_RAV4_TSS2].get_non_essential_params(CAR.TOYOTA_RAV4_TSS2)

  def test_produced_fit_reaches_actual_controls_once_without_manual_document(self):
    with controls_for(self.params(), 'standard', True) as controls:
      before_cp = controls.CP.as_builder().to_bytes()
      tune = controls.LaC.torque_params.to_dict()
      result, validation = current_fit(controls)
      self.assertIsNotNone(result.profile)
      self.assertIsNotNone(validation)
      command = apply_fit(controls, result, validation)
      runtime = controls.global_learning
      self.assertTrue(command.latActive)
      self.assertTrue(runtime.used)
      self.assertEqual(runtime.reason, 'qualified')
      self.assertTrue(any(value != 0 for value in runtime.applied_coordinates))
      owner = runtime.torque_owner
      for tick in range(71, 80):
        live_frame(controls, tick, 'a' * 32, result=result, validation=validation)
      self.assertIs(runtime.torque_owner, owner, 'One stage owner survives subsequent receipts')
      self.assertEqual(controls.LaC.torque_params.to_dict(), tune)
      self.assertEqual(controls.CP.as_builder().to_bytes(), before_cp)
      self.assertIsNone(controls.params.get(TORQUE_KEY))
      self.assertFalse(controls.sm.simulation)
      self.assertTrue(controls.sm.all_checks(['autoSteeringLearning']))

  def test_actual_application_expires_and_reset_restart_or_manual_choice_falls_back(self):
    for reason in ('stale', 'restart', 'off', 'corrupt', 'reset', 'manual'):
      with self.subTest(reason=reason), controls_for(self.params(), 'standard', True) as controls:
        result, validation = current_fit(controls)
        self.assertIsNotNone(result.profile)
        apply_fit(controls, result, validation)
        runtime = controls.global_learning
        self.assertTrue(any(value != 0 for value in runtime.applied_coordinates))
        before_cp, tune = controls.CP.as_builder().to_bytes(), controls.LaC.torque_params.to_dict()
        if reason == 'off':
          controls.params.put(PREFERENCE_KEY, replace_preference(None, controls.CP, False), block=True)
        elif reason == 'corrupt':
          Path(controls.params.get_param_path(PREFERENCE_KEY)).write_bytes(b'malformed')
        elif reason == 'reset':
          controls.params.put('AutoSteeringLearningReset', 'c' * 32, block=True)
        elif reason == 'manual':
          basis = controls.CP.lateralTuning.torque
          profile = replace_field({}, str(controls.CP.carFingerprint),
            (basis.latAccelFactor, basis.latAccelOffset, basis.friction), 'factor', 'custom', basis.latAccelFactor * 1.2)
          controls.params.put(TORQUE_KEY, json.loads(serialize_document(profile)), block=True)
        for tick in range(71, 101):
          command, _ = live_frame(controls, tick, 'b' * 32 if reason == 'restart' else 'a' * 32,
            result=None if reason == 'restart' else result, validation=None if reason == 'restart' else validation,
            publish=False if reason == 'stale' else None)
        self.assertEqual(runtime.applied_coordinates, (0., 0.))
        self.assertTrue(command.latActive, 'Learning loss must not create a driving fault')
        self.assertEqual(controls.CP.as_builder().to_bytes(), before_cp)
        self.assertEqual(controls.LaC.torque_params.to_dict(), tune)
        if reason in ('reset', 'manual'):
          self.assertNotEqual(runtime.identity, result.profile.identity)

  def test_real_controller_bounds_and_authority_are_independent_of_qualified_wire(self):
    with controls_for(self.params(), 'standard', True) as controls:
      before_cp = controls.CP.as_builder().to_bytes()
      result, validation = current_fit(controls)
      command = apply_fit(controls, result, validation)
      self.assertTrue(command.latActive)
      self.assertLessEqual(abs(command.actuators.torque), controls.LaC.steer_max)
      runtime = controls.global_learning
      # A fitted correction never supplies a missing native authority witness.
      runtime.prepare(controls.sm, now_ns=BASE + 700_000_000, active=True, healthy=True,
                      native_required=True, native_witness=None)
      self.assertEqual(runtime.applied_coordinates, (0., 0.))
      inactive_integral = controls.LaC.pid.i
      for tick, health in enumerate(({'fault': True}, {'active': False, 'enabled': False}), 71):
        command, _ = live_frame(controls, tick, 'a' * 32, result=result, validation=validation, **health)
        self.assertFalse(command.latActive)
        self.assertEqual(command.actuators.torque, 0.)
        self.assertEqual(controls.LaC.pid.i, inactive_integral, 'Inactive baseline PID state must not advance')
      # A sender cannot escape stage bounds or validation identity.
      invalid = replace(result.profile, coefficients=(100., 100.))
      invalid_profiles = (
        invalid,
        replace(result.profile, coefficients=(math.nan, 0.)),
        *(replace(result.profile, parameters=(replace(result.profile.parameters[0], **changes),
                                             result.profile.parameters[1]))
          for changes in ({'low': math.inf}, {'low': 1., 'high': -1.}, {'max_step': 0.}, {'slew_per_s': 0.})),
      )
      for invalid in invalid_profiles:
        with self.subTest(invalid=invalid), self.assertRaises(ValueError):
          result_message(replace(result, profile=invalid), 'invalid-sender', 1, BASE + 750_000_000,
                         replay_validation=replace(validation, profile=invalid))

      def corrupt_wire(event):
        event.autoSteeringLearning.learning.runtimeProfile.coefficients = [100., 100.]

      for tick in range(73, 80):
        command, _ = live_frame(controls, tick, 'a' * 32, result=result,
                               validation=validation, publish=tick == 75, wire_mutator=corrupt_wire)
        self.assertTrue(math.isfinite(command.actuators.torque))
        self.assertLessEqual(abs(command.actuators.torque), controls.LaC.steer_max)
      self.assertEqual(runtime.applied_coordinates, (0., 0.))
      self.assertEqual(controls.CP.as_builder().to_bytes(), before_cp)
