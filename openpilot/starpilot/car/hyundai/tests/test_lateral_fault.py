import os
import unittest
from unittest.mock import patch

from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.starpilot.car.hyundai.lateral_fault import LateralFaultLatch
from openpilot.starpilot.lateral.tests.test_lane_runtime import feed


class TestHyundaiLateralFault(unittest.TestCase):
  def test_actual_controls_requires_rearm_after_elantra_hybrid_fault(self):
    for model in (CAR.HYUNDAI_ELANTRA_HEV_2024, CAR.HYUNDAI_ELANTRA_2024, CAR.HYUNDAI_IONIQ_6):
      with self.subTest(model=model), OpenpilotPrefix(), \
           patch.dict(os.environ, {'REPLAY': '1', 'AOL_REPLAY_RUNTIME': '0'}), \
           patch('openpilot.selfdrive.controls.controlsd.messaging.PubMaster'):
        cp = interfaces[model].get_non_essential_params(model)
        Params().put('CarParams', cp.to_bytes(), block=True)
        controls = Controls()
        latched_model = model == CAR.HYUNDAI_ELANTRA_HEV_2024
        cases = [(True, False, False, False, True),
                 (True, True, False, False, False),
                 (True, False, False, False, not latched_model),
                 (True, False, True, False, True),
                 (True, True, True, False, False),
                 (False, False, False, False, False),
                 (True, False, False, False, True),
                 (True, False, False, True, False)]
        for tick, (requested, temporary, cruise, permanent, expected) in enumerate(cases):
          now_ns = 1_000_000_000 + tick * 10_000_000
          feed(controls, now_ns, tick, active=requested, enabled=requested, fault=temporary)
          event = messaging.new_message('carState', valid=True, logMonoTime=now_ns)
          event.carState = controls.sm['carState']
          event.carState.cruiseState.enabled = cruise
          event.carState.steerFaultPermanent = permanent
          controls.sm.data['carState'] = event.carState.as_reader()
          command, _ = controls.state_control()
          self.assertEqual(command.latActive, expected)
          self.assertEqual(command.enabled, requested)
          if not expected:
            self.assertEqual(command.actuators.torque, 0.0)

  def test_actual_axis_intent_survives_fault_and_missing_permission_without_admission(self):
    from openpilot.starpilot.aol.runtime import current_axis, current_native

    with OpenpilotPrefix(), patch.dict(os.environ, {'REPLAY': '1', 'AOL_REPLAY_RUNTIME': '0'}), \
         patch('openpilot.selfdrive.controls.controlsd.messaging.PubMaster'):
      cp = interfaces[CAR.HYUNDAI_ELANTRA_HEV_2024].get_non_essential_params(CAR.HYUNDAI_ELANTRA_HEV_2024)
      Params().put('CarParams', cp.to_bytes(), block=True)
      controls = Controls()
      self.assertFalse(controls.aol_replay)
      # Exercise the reader boundary without granting this vehicle AOL safety.
      controls.aol_replay = True
      controls.sm = messaging.SubMaster([*controls.sm.services, 'aolAxisState', 'aolSafetyWire'], frequency=100)
      for tick, (desired, active, fault, fresh, expected_latch) in enumerate(
        ((True, True, True, True, True), (True, False, False, True, True),
         (True, False, False, False, True), (False, False, False, True, False))):
        now_ns = 1_000_000_000 + tick * 10_000_000
        feed(controls, now_ns, tick, fault=fault, aol_lat_only=True)
        event = messaging.new_message('aolAxisState', valid=True, logMonoTime=now_ns)
        event.aolAxisState = controls.sm['aolAxisState']
        event.aolAxisState.desiredLateral = desired
        event.aolAxisState.lateralActive = active
        controls.sm.data['aolAxisState'] = event.aolAxisState.as_reader()
        controls.sm.valid['aolAxisState'] = fresh
        axis = current_axis(controls.sm, now_ns=now_ns)
        self.assertEqual(axis is not None, fresh)
        self.assertIsNone(current_native(controls.sm, cp, now_ns=now_ns))
        command, _ = controls.state_control()
        self.assertEqual(controls.hyundai_lateral_fault.faulted, expected_latch)
        self.assertFalse(command.latActive)
        self.assertEqual(command.actuators.torque, 0.0)

  def test_fault_at_cruise_rising_edge_still_suppresses_output(self):
    latch = LateralFaultLatch(CAR.HYUNDAI_ELANTRA_HEV_2024)
    self.assertFalse(latch.update(requested=True, temporary_fault=True, cruise_enabled=True))
    self.assertTrue(latch.update(requested=True, temporary_fault=True, cruise_enabled=True))
    self.assertTrue(latch.update(requested=True, temporary_fault=False, cruise_enabled=True))
    self.assertFalse(latch.update(requested=False, temporary_fault=False, cruise_enabled=True))


if __name__ == '__main__':
  unittest.main()
