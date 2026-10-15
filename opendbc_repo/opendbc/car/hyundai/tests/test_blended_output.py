import unittest
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.car.structs import car
from opendbc.car.hyundai.blended_longitudinal import candidate_from_stock
from opendbc.car.hyundai.tests.test_palisade_2023 import params
from opendbc.car.hyundai.values import CarControllerParams, CAR
from opendbc.car.hyundai.interface import CarInterface
from openpilot.starpilot.longitudinal.output_max import final_output
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.starpilot.longitudinal.extension import LongitudinalContext
from openpilot.starpilot.longitudinal.inputs import LongitudinalInputs
from openpilot.starpilot.longitudinal.tests.extension_helpers import empty_params

State = car.CarControl.Actuators.LongControlState


class TestBlendedOutput(unittest.TestCase):
  def setUp(self):
    self.scope = patch('opendbc.car.hyundai.blended_longitudinal.hdai_startup_qualified', return_value=True)
    self.scope.start()
    self.addCleanup(self.scope.stop)
    self.cp = candidate_from_stock(params(), alpha_requested=True, native_qualified=True)
    self.cs = car.CarState()
    self.cs.canValid = True
    self.cs.vEgo = 3.

  def update(self, control, target, *, stop=False, mode=False):
    return control.update(True, self.cs, target, stop, (-3.5, 2.),
                          context=LongitudinalContext(experimental_mode=mode))

  def test_actual_loop_moving_stop_follow_and_bypass(self):
    for speed, brake, target, expected in [(3., False, -1., -.1335),
                                           (1.5, False, -1., -.1035),
                                           (3., True, -1., -.1035),
                                           (3., False, -.2, -.1035)]:
      with self.subTest(speed=speed, brake=brake, target=target):
        control = LongControl(self.cp)
        control.last_output_accel = -.1
        self.cs.vEgo = speed
        self.cs.brakePressed = brake
        self.assertAlmostEqual(self.update(control, target, stop=True), expected, places=6)

  def test_actual_pid_default_and_original_negative_target_guards(self):
    control = LongControl(self.cp)
    self.assertAlmostEqual(self.update(control, .6), .6)
    control.pid.i = .5
    self.cs.aEgo = .5
    self.assertAlmostEqual(self.update(control, -.25), -.125, places=6)
    self.assertAlmostEqual(control.pid.i, .125, places=6)
    control.pid.i = 2.
    self.assertAlmostEqual(self.update(control, -.25), .035, places=6)
    self.assertAlmostEqual(control.pid.i, .5, places=6)
    control = LongControl(self.cp)
    control.pid.i = .5
    self.cs.vEgo = .35
    self.cs.aEgo = .5
    self.assertAlmostEqual(self.update(control, -.25), .25, places=6)
    self.assertAlmostEqual(control.pid.i, .5, places=6)

  def test_actual_loop_mode_transition_and_integrator_freeze(self):
    control = LongControl(self.cp)
    self.update(control, 0.)
    expected = -1. * (1. - .99 * (1. - .25 ** .4))
    self.assertAlmostEqual(self.update(control, -1., mode=True), expected, places=6)
    previous = control.last_output_accel
    self.assertAlmostEqual(self.update(control, .5, mode=False), previous + (.5 - previous) * .01, places=6)
    with patch.object(control.pid, 'update', wraps=control.pid.update) as update:
      self.update(control, .5, mode=False)
    self.assertTrue(update.call_args.kwargs['freeze_integrator'])

  def test_actual_inputs_use_plan_lead_and_checked_mode(self):
    class Messages(dict):
      fresh = True

      def all_checks(self, services):
        return self.fresh

    messages = Messages(longitudinalPlan=SimpleNamespace(hasLead=True),
                        selfdriveState=SimpleNamespace(experimentalMode=True))
    owner = LongitudinalInputs(self.cp, empty_params(self), lambda: messages)
    self.assertEqual(owner.optional_services, ['radarState', 'deviceState'])
    context = owner.context(True)
    self.assertTrue(context.has_lead)
    self.assertTrue(context.experimental_mode)
    self.assertFalse(context.faster_takeoffs)
    self.assertIsNone(context.start_evidence)
    messages.fresh = False
    context = owner.context(True)
    self.assertIsNone(context.has_lead)
    self.assertIsNone(context.experimental_mode)

  def test_unseen_optional_takeoff_sources_keep_native_context_but_cannot_start(self):
    from openpilot.cereal import messaging

    optional = ['radarState', 'deviceState']
    required = ['carState', 'longitudinalPlan', 'selfdriveState']
    messages = messaging.SubMaster(required + optional, ignore_alive=optional,
                                  ignore_valid=optional, ignore_avg_freq=optional)
    plan = messaging.new_message('longitudinalPlan', valid=True, logMonoTime=5_020_000_000)
    plan.longitudinalPlan.hasLead = True
    state = messaging.new_message('selfdriveState', valid=True, logMonoTime=5_020_000_000)
    state.selfdriveState.experimentalMode = True
    car_state = messaging.new_message('carState', valid=True, logMonoTime=5_020_000_000)
    messages.update_msgs(5.02, [plan.as_reader(), state.as_reader(), car_state.as_reader()])
    for name in required:
      messages.alive[name] = messages.valid[name] = messages.freq_ok[name] = True
    params = empty_params(self)
    owner = LongitudinalInputs(self.cp, params, lambda: messages)
    self.assertEqual(owner.optional_services, optional)
    self.assertFalse(any(messages.seen[name] for name in optional))
    self.assertTrue(messages.all_checks())
    baseline = owner.context(True)
    self.assertTrue(baseline.has_lead and baseline.experimental_mode)
    self.assertFalse(baseline.faster_takeoffs)
    self.assertIsNone(baseline.start_evidence)
    params.put_bool('FasterLeadTakeoff', True, block=True)
    assert owner.takeoff_preferences is not None
    owner.takeoff_preferences.next_ns = 0
    with patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', side_effect=[
      (5_000_000_000, 5_500_000_000), (5_050_000_000, 5_550_000_000)]):
      for _ in range(2):
        context = owner.context(True)
        self.assertTrue(messages.all_checks())
        self.assertTrue(context.has_lead and context.experimental_mode and context.faster_takeoffs)
        self.assertFalse(context.start_evidence.car_fresh or context.start_evidence.plan_fresh)
        self.assertIsNone(context.start_evidence.lead_clear)
        control = LongControl(self.cp)
        self.cs.vEgo = 0.
        control.update(True, self.cs, 1.8, False, (-3.5, 2.), context=context)
        self.assertFalse(control.takeoff_starting)
    messages.valid['longitudinalPlan'] = False
    self.assertFalse(messages.all_checks())
    self.assertIsNone(owner.context(True).has_lead)

  def test_cp_selected_alpha_limits_and_shared_default_output_ceiling(self):
    for topology in ('hdai', 'hdaii'):
      stock = params(topology)
      candidate = candidate_from_stock(stock, alpha_requested=True, native_qualified=True)
      limits = CarControllerParams(candidate)
      self.assertEqual((limits.STEER_MAX, limits.STEER_DELTA_UP, limits.STEER_DELTA_DOWN),
                       (384, 3, 7) if topology == 'hdaii' else (404, 2, 3))
      self.assertEqual((limits.ACCEL_MIN, limits.ACCEL_MAX), (-3.5, 3.5))
      self.assertEqual(CarInterface.get_pid_accel_limits(candidate, 0., 0.), (-3.5, 3.5))
      control = LongControl(candidate)
      output = control.update(True, self.cs, 3.5, False, CarInterface.get_pid_accel_limits(candidate, 0., 0.),
                              context=LongitudinalContext(experimental_mode=False))
      self.assertAlmostEqual(output, 3.5)
      self.assertAlmostEqual(final_output(output), 3.5)
      self.assertAlmostEqual(final_output(5.), 4.)
      self.assertAlmostEqual(final_output(-3.5), -3.5)
      self.assertEqual(CarControllerParams(stock).ACCEL_MAX, 2.)
      self.assertEqual(CarInterface.get_pid_accel_limits(stock, 0., 0.), (-3.5, 2.))
    sibling = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, {0: {}, 1: {}, 2: {}}, [], False, False, False)
    self.assertEqual(CarControllerParams(sibling).ACCEL_MAX, 2.)
    self.assertEqual(CarInterface.get_pid_accel_limits(sibling, 0., 0.), (-3.5, 2.))
