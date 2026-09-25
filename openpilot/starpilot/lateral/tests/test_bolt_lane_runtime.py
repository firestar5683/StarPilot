"""Exact Bolt admission through actual Controls and existing lane authority."""
import os
from itertools import product
import unittest
from unittest.mock import patch

from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.lateral.bolt_policy import BOLT_GENERATIONS
from openpilot.starpilot.lateral.lane_runtime import runtime_supported
from openpilot.starpilot.lateral.tests.test_lane_runtime import feed
from openpilot.starpilot.longitudinal.tests.test_bolt_mode_transition import params


class TestBoltLaneRuntime(unittest.TestCase):
  def test_exact_admission_and_default_off_actual_controls_equality(self):
    for identity, alpha in product(BOLT_GENERATIONS, (False, True)):
      with self.subTest(identity=identity), OpenpilotPrefix(), patch.dict(os.environ,
          {'SIMULATION': '1', 'REPLAY': '1', 'LANE_CENTERING_REPLAY_RUNTIME': '0', 'AOL_REPLAY_RUNTIME': '0'}):
        cp = params(identity, alpha=alpha)
        self.assertTrue(runtime_supported(cp))
        for field in ('passive', 'dashcamOnly', 'notCar'):
          denied = cp.as_reader().as_builder()
          setattr(denied, field, True)
          self.assertFalse(runtime_supported(denied))
        settings = Params()
        settings.put('CarParams', cp.to_bytes(), block=True)
        selected, reference = Controls(), Controls()
        self.assertIsNotNone(selected.lane_centering_host)
        reference.lane_centering_host = None
        for tick in range(20):
          now = 1_000_000_000 + tick * 10_000_000
          feed(selected, now, tick)
          feed(reference, now, tick)
          actual, _ = selected.state_control()
          expected, _ = reference.state_control()
          self.assertEqual(actual.to_bytes(), expected.to_bytes())

  def test_enabled_actual_controls_response_and_authority_gates(self):
    gates = ({'signal': True}, {'override': True}, {'fault': True}, {'can_valid': False},
             {'can_timeout': True}, {'active': False, 'enabled': False}, {'model_age': 1_000_000_000})
    for identity, alpha in product(BOLT_GENERATIONS, (False, True)):
      for gate in gates:
        with self.subTest(identity=identity, gate=gate), OpenpilotPrefix(), patch.dict(os.environ,
            {'SIMULATION': '1', 'REPLAY': '1', 'LANE_CENTERING_REPLAY_RUNTIME': '0', 'AOL_REPLAY_RUNTIME': '0'}):
          cp = params(identity, alpha=alpha)
          settings = Params()
          settings.put('CarParams', cp.to_bytes(), block=True)
          settings.put_bool('LaneCentering', True, block=True)
          settings.put('LaneCenterOffset', .2, block=True)
          settings.put('LaneCenteringE2EAuthority', 0., block=True)
          controls = Controls()
          for tick in range(100):
            now = 1_000_000_000 + tick * 10_000_000
            feed(controls, now, tick)
            controls.state_control()
          warm_correction = abs(controls.lane_centering_applied)
          self.assertGreater(warm_correction, 0.)
          for tick in range(100, 140):
            now = 1_000_000_000 + tick * 10_000_000
            feed(controls, now, tick, **gate)
            command, _ = controls.state_control()
          if gate.get('signal'):
            self.assertLess(abs(controls.lane_centering_applied), warm_correction)
            self.assertEqual(controls.last_lane_centering_result.reason, 'signal_release')
          else:
            self.assertEqual(controls.lane_centering_applied, 0.)
          if any(key in gate for key in ('fault', 'active')):
            self.assertFalse(command.latActive)
            self.assertEqual(command.actuators.torque, 0.)

  def test_absent_cp_actual_lane_settings_page(self):
    with OpenpilotPrefix(), patch.dict(os.environ, {'LANE_CENTERING_REPLAY_RUNTIME': '0'}):
      self.assertFalse(runtime_supported(None))
      owner = FeatureSettingsOwner(Params(), lambda _: True, vehicle_fingerprint=lambda: None,
                                   vehicle_params=lambda: None)
      state = owner.snapshot('lane', parked=True, system_long=False, lateral_context=False, metric=False)
      self.assertIsNotNone(state)
