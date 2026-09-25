"""Exact Volt admission through actual Controls and existing lane authority."""
import os
import unittest
from unittest.mock import patch

from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from opendbc.car import gen_empty_fingerprint
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR
from openpilot.starpilot.lateral.lane_runtime import runtime_supported
from openpilot.starpilot.lateral.tests.test_lane_runtime import feed


def configurations():
  cases = ((CAR.CHEVROLET_VOLT, False, False, False, True),
           (CAR.CHEVROLET_VOLT, False, False, True, True),
           (CAR.CHEVROLET_VOLT_ASCM, False, True, False, True),
           (CAR.CHEVROLET_VOLT_ASCM, True, True, False, True),
           (CAR.CHEVROLET_VOLT_CC, True, False, False, False),
           (CAR.CHEVROLET_VOLT_CAMERA, False, False, False, False),
           (CAR.CHEVROLET_VOLT_CAMERA, True, False, False, False))
  for identity, alpha, sascm, alternate, radar in cases:
    fp = gen_empty_fingerprint()
    if not alternate:
      fp[0][0xBE] = 6
    if sascm:
      fp[0][0x2FF] = 8
    if radar:
      fp[1][0x460] = 8
    if identity == CAR.CHEVROLET_VOLT_CC:
      fp[0].update({0xBE: 6, 0x3D1: 8, 0xC9: 8, 0x1E1: 7, 0x1F5: 8, 0x34A: 5, 0x1C4: 8, 0xBD: 7})
    if identity == CAR.CHEVROLET_VOLT_CAMERA:
      fp[2][0x320] = 6
    yield CarInterface.get_params(identity, fp, [], alpha, False, False)


class TestVoltLaneRuntime(unittest.TestCase):
  def test_exact_admission_and_default_off_actual_controls_equality(self):
    non_torque = next(configurations()).as_reader().as_builder()
    non_torque.steerControlType = 'angle'
    self.assertFalse(runtime_supported(non_torque))
    for cp in configurations():
      with self.subTest(identity=cp.carFingerprint), OpenpilotPrefix(), patch.dict(os.environ,
          {'SIMULATION': '1', 'REPLAY': '1', 'LANE_CENTERING_REPLAY_RUNTIME': '0', 'AOL_REPLAY_RUNTIME': '0'}):
        self.assertTrue(runtime_supported(cp), str(cp.carFingerprint))
        for field in ('passive', 'dashcamOnly', 'notCar'):
          denied = cp.as_reader().as_builder()
          setattr(denied, field, True)
          self.assertFalse(runtime_supported(denied))
        settings = Params()
        settings.put('CarParams', cp.as_reader().as_builder().to_bytes(), block=True)
        selected, reference = Controls(), Controls()
        assert selected.lane_centering_host is not None
        reference.lane_centering_host = None
        for tick in range(20):
          now = 1_000_000_000 + tick * 10_000_000
          feed(selected, now, tick)
          feed(reference, now, tick)
          actual, _ = selected.state_control()
          expected, _ = reference.state_control()
          self.assertEqual(actual.to_dict(), expected.to_dict())

  def test_enabled_actual_controls_response_and_authority_gates(self):
    gates = ({'signal': True}, {'override': True}, {'fault': True}, {'can_valid': False},
             {'can_timeout': True}, {'active': False, 'enabled': False}, {'model_age': 1_000_000_000})
    for cp in configurations():
      for gate in gates:
        with self.subTest(identity=cp.carFingerprint, gate=gate), OpenpilotPrefix(), patch.dict(os.environ,
            {'SIMULATION': '1', 'REPLAY': '1', 'LANE_CENTERING_REPLAY_RUNTIME': '0', 'AOL_REPLAY_RUNTIME': '0'}):
          settings = Params()
          settings.put('CarParams', cp.as_reader().as_builder().to_bytes(), block=True)
          settings.put_bool('LaneCentering', True, block=True)
          settings.put('LaneCenterOffset', .2, block=True)
          settings.put('LaneCenteringE2EAuthority', 0., block=True)
          controls = Controls()
          for tick in range(100):
            now = 1_000_000_000 + tick * 10_000_000
            feed(controls, now, tick)
            controls.state_control()
          warm_correction = abs(controls.lane_centering_applied)
          self.assertGreater(warm_correction, 0., str(cp.carFingerprint))
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
      assert state is not None


class TestVolt2019LaneRuntime(unittest.TestCase):
  @staticmethod
  def configurations():
    from opendbc.car.gm.tests.test_volt_sdgm_control import sdgm_params
    for alpha in (False, True):
      for c9 in (False, True):
        yield sdgm_params(alpha=alpha, brake_c9=c9)

  def test_default_off_actual_controls_and_exact_configuration(self):
    with patch(__name__ + ".configurations", side_effect=self.configurations):
      TestVoltLaneRuntime.test_exact_admission_and_default_off_actual_controls_equality(TestVoltLaneRuntime())

  def test_enabled_actual_controls_and_existing_authority_gates(self):
    with patch(__name__ + ".configurations", side_effect=self.configurations):
      TestVoltLaneRuntime.test_enabled_actual_controls_response_and_authority_gates(TestVoltLaneRuntime())
