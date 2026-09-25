"""Reached EV9 start/release behavior through actual shared LongControl."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.car import structs
from opendbc.car.hyundai.ev9_longitudinal import candidate
from opendbc.car.hyundai.ev9_stopping import START_ACCEL, policy_for
from opendbc.car.hyundai.tests.test_ioniq5pe_stock import params
from opendbc.car.hyundai.values import CAR
from openpilot.selfdrive.controls.lib.longcontrol import LongControl, LongCtrlState
from openpilot.starpilot.longitudinal.extension import LongitudinalContext
from openpilot.starpilot.longitudinal.inputs import LongitudinalInputs


def cp():
  return candidate(params(candidate=CAR.KIA_EV9), enabled=True, is_release=False)


def state(speed=0., *, standstill=True, brake=False):
  cs = structs.CarState(vEgo=speed, canValid=True, brakePressed=brake)
  cs.cruiseState.standstill = standstill
  return cs


def context(**fields):
  values = dict(has_lead=False, traffic_mode=False, custom_acceleration=False, profile_max_accel=0.)
  values.update(fields)
  return LongitudinalContext(**values)


class TestEV9Stopping(unittest.TestCase):
  def test_only_exact_long_profile_gets_policy_and_stock_siblings_stay_unmodified(self):
    self.assertIsNotNone(policy_for(cp(), .01))
    for identity in (CAR.KIA_EV9, CAR.HYUNDAI_IONIQ_5_PE, CAR.HYUNDAI_IONIQ_6):
      self.assertIsNone(policy_for(params(candidate=identity), .01))
    malformed = cp()
    malformed.alternativeExperience = 32
    self.assertIsNone(policy_for(malformed, .01))

  def test_actual_loop_release_hysteresis_reset_and_lead_fast_path(self):
    loop = LongControl(cp())
    loop.long_control_state = LongCtrlState.stopping
    cs = state()
    for _ in range(34):
      loop.update(True, cs, .2, False, (-4., 2.2), context=context())
      self.assertEqual(loop.long_control_state, LongCtrlState.stopping)
    loop.update(True, cs, .15, False, (-4., 2.2), context=context())
    self.assertEqual(loop.extension.stopping_policy.release_counter, 0)
    for _ in range(35):
      loop.update(True, cs, .2, False, (-4., 2.2), context=context())
    self.assertEqual(loop.long_control_state, LongCtrlState.starting)
    self.assertEqual(loop.extension.stopping_policy.release_counter, 0)
    loop.long_control_state = LongCtrlState.stopping
    loop.update(True, cs, .16, False, (-4., 2.2), context=context(has_lead=True))
    self.assertEqual(loop.long_control_state, LongCtrlState.starting)
    loop.update(True, cs, .5, True, (-4., 2.2), context=context())
    self.assertEqual(loop.long_control_state, LongCtrlState.stopping)

  def test_actual_loop_start_state_and_speed_boundary(self):
    loop = LongControl(cp())
    cs = state(standstill=False)
    self.assertAlmostEqual(loop.update(True, cs, .1, False, (-4., 2.2), context=context()), START_ACCEL)
    self.assertEqual(loop.long_control_state, LongCtrlState.starting)
    cs.vEgo = .5
    loop.update(True, cs, .1, False, (-4., 2.2), context=context())
    self.assertEqual(loop.long_control_state, LongCtrlState.starting)
    cs.vEgo = .5001
    loop.update(True, cs, .1, False, (-4., 2.2), context=context())
    self.assertEqual(loop.long_control_state, LongCtrlState.pid)
    loop.update(False, cs, .1, False, (-4., 2.2), context=context())
    self.assertEqual(loop.long_control_state, LongCtrlState.off)

  def test_actual_start_output_traffic_custom_lead_and_profile_cap(self):
    for fields, target, expected in (({'traffic_mode': True}, .1, .1), ({'custom_acceleration': True}, .1, .1),
                                     ({'has_lead': True}, .1, .1), ({'profile_max_accel': .12}, .1, .12),
                                     ({}, .1, START_ACCEL), ({'has_lead': True}, .26, START_ACCEL)):
      loop = LongControl(cp())
      loop.long_control_state = LongCtrlState.starting
      self.assertAlmostEqual(loop.update(True, state(), target, False, (-4., 2.2), context=context(**fields)), expected)

  def test_actual_stopping_ramp_and_moving_target_follow(self):
    loop = LongControl(cp())
    loop.long_control_state = LongCtrlState.stopping
    self.assertAlmostEqual(loop.update(True, state(), -1., True, (-4., 2.2), context=context()), -.004)
    loop.last_output_accel = -.1
    self.assertAlmostEqual(loop.update(True, state(6.), -1., True, (-4., 2.2), context=context()), -.154)

  def test_inputs_preserve_plan_lead_and_selected_profile_context(self):
    now = 2_000_000_000
    sm = {'carState': SimpleNamespace(vEgo=0.), 'selfdriveState': SimpleNamespace(personality=1, experimentalMode=False),
          'longitudinalPlan': SimpleNamespace(hasLead=True),
          'deviceState': SimpleNamespace(started=True, startedMonoTime=2)}
    class Messages(dict):
      seen = {'slcState': False, 'deviceState': True}
      alive = {'deviceState': True}
      valid = {'deviceState': True}
      logMonoTime = dict.fromkeys(('carState', 'selfdriveState', 'longitudinalPlan', 'deviceState'), now - 1)
      recv_time = dict.fromkeys(('carState', 'selfdriveState', 'longitudinalPlan', 'deviceState'), now / 1e9)
      def all_checks(self, names):
        return True
    messages = Messages(sm)
    inputs = LongitudinalInputs.__new__(LongitudinalInputs)
    inputs.CP = cp()
    inputs.messages = lambda: messages
    inputs.ev9_source_floor_ns = 1
    inputs.ev9_boot_offset_ns = 0
    inputs.ev9_traffic = SimpleNamespace(sample=lambda *args, **kwargs: False)
    inputs.ev9_profile = SimpleNamespace(selected_success_ns=now, disabled=True, selected_document=None,
                                         sample=lambda *args, **kwargs: None,
                                         sample_selected=lambda *args, **kwargs: SimpleNamespace(acceleration_max=.12))
    with patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now)):
      value = inputs._ev9_context(True)
    self.assertFalse(value.experimental_mode)
    self.assertTrue(value.has_lead)
    self.assertFalse(value.traffic_mode)
    self.assertFalse(value.custom_acceleration)
    self.assertEqual(value.profile_max_accel, .12)
    # Reproduce actual optional SubMaster all_checks ignoring validity.
    messages.valid['deviceState'] = False
    with patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now)):
      self.assertIsNone(inputs._ev9_context(True).profile_max_accel)
    messages.valid['deviceState'] = True
    messages.alive['deviceState'] = False
    with patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now)):
      self.assertIsNone(inputs._ev9_context(True).profile_max_accel)
    messages.alive['deviceState'] = True
    messages.logMonoTime['longitudinalPlan'] = 1
    with patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now)):
      self.assertIsNone(inputs._ev9_context(True).profile_max_accel)

  def test_actual_pid_acc_to_blended_original_numeric_trace(self):
    loop = LongControl(cp())
    loop.long_control_state = LongCtrlState.pid
    cs = state(10., standstill=False)
    ctx = context(experimental_mode=True)
    last = 0.
    urgency = abs(-1. / -4.) ** .4
    for frame in range(1, 101):
      blend = 1. - (1. - min(1., frame * .01)) * (1. - urgency)
      expected = last + (-1. - last) * blend
      actual = loop.update(True, cs, -1., False, (-3.5, 2.2), context=ctx)
      self.assertAlmostEqual(actual, expected, places=7)
      last = actual
    self.assertAlmostEqual(last, -1.)

  def test_actual_pid_blended_to_acc_original_numeric_trace(self):
    loop = LongControl(cp())
    loop.long_control_state = LongCtrlState.pid
    cs = state(10., standstill=False)
    # Enter blended and finish its original one-second transition.
    for _ in range(100):
      loop.update(True, cs, 0., False, (-3.5, 2.2), context=context(experimental_mode=True))
    last = 0.
    for frame in range(1, 101):
      expected = last + (.5 - last) * min(1., frame * .01)
      actual = loop.update(True, cs, .5, False, (-3.5, 2.2), context=context(experimental_mode=False))
      self.assertAlmostEqual(actual, expected, places=7)
      last = actual
    self.assertAlmostEqual(last, .5)
