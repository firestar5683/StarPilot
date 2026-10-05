import unittest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR, ToyotaFlags
from openpilot.starpilot.aol.intent import AolSettings
from openpilot.starpilot.aol.vehicle import policy_for
from openpilot.starpilot.car.toyota.aol import qualified, ToyotaCardIntent
from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences


class TestHighlanderAol(unittest.TestCase):
  def test_actual_factory_gas_hybrid_and_hold_composition(self):
    for hybrid in (False, True):
      for hold in (False, True):
        with self.subTest(hybrid=hybrid, hold=hold):
          firmware = [structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.hybrid)] if hybrid else []
          cp = CarInterface.get_params(CAR.TOYOTA_HIGHLANDER_TSS2, gen_empty_fingerprint(), firmware, False, False, False)
          self.assertEqual(cp.safetyConfigs[0].safetyParam, 73)
          self.assertEqual(bool(cp.flags & ToyotaFlags.HYBRID), hybrid)
          self.assertTrue(cp.openpilotLongitudinalControl)
          preferences = VehicleStartupPreferences(toyota_auto_hold=hold)
          preferences.prepare(cp)
          self.assertTrue(qualified(cp))
          policy = policy_for(cp)
          self.assertTrue(policy.full_axis_runtime_required)
          cp.alternativeExperience |= policy.alternative_experience_addition
          preferences.finalize(cp)
          self.assertEqual(cp.alternativeExperience, 160 if hold else 32)
          self.assertTrue(qualified(cp, marked_only=True))
          cp.safetyConfigs[0].safetyParam = 585
          cp.openpilotLongitudinalControl = False
          self.assertFalse(qualified(cp))

  def test_main_derived_intent_does_not_use_unreached_lkas_mapping(self):
    settings = AolSettings(True, 0., 9, 9, (0, 0, 0), (0, 0, 0))
    owner = ToyotaCardIntent(settings)
    state = structs.CarState(canValid=True, gearShifter=structs.CarState.GearShifter.drive)
    state.cruiseState.available = False
    state.buttonEvents = [structs.CarState.ButtonEvent(type=structs.CarState.ButtonEvent.Type.lkas, pressed=True)]
    owner.update(state.as_reader())
    self.assertFalse(owner.allowed_latch)
    state.buttonEvents = []
    state.cruiseState.available = True
    owner.update(state.as_reader())
    self.assertTrue(owner.allowed_latch)
    state.cruiseState.available = False
    owner.update(state.as_reader())
    self.assertFalse(owner.allowed_latch)

  def test_actual_card_hold_and_master_off_preserve_full_axis_transport(self):
    import os
    from types import SimpleNamespace
    from unittest.mock import patch
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.selfdrive.car.card import Car
    from openpilot.selfdrive.controls.controlsd import Controls
    from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
    for hold in (False, True):
      for enabled in (False, True):
        with self.subTest(hold=hold, enabled=enabled), OpenpilotPrefix(), \
             patch.dict(os.environ, {'SIMULATION': '1', 'AOL_REPLAY_RUNTIME': '0'}):
          saved = Params()
          for key, value in (('OpenpilotEnabledToggle', True), ('AlwaysOnLateral', enabled),
                             ('ToyotaAutoHold', hold), ('SafeMode', False)):
            saved.put_bool(key, value, block=True)
          cp = CarInterface.get_params(CAR.TOYOTA_HIGHLANDER_TSS2, gen_empty_fingerprint(), [], False, False, False)

          def discover(*args, pre_create_hook, cp=cp, **kwargs):
            return CarInterface(pre_create_hook(cp.as_reader().as_builder(), cp.carFingerprint, {}, []))
          with patch('openpilot.selfdrive.car.card.messaging.recv_one_retry', return_value=SimpleNamespace(can=[1])), \
               patch('openpilot.selfdrive.car.card.get_car', side_effect=discover):
            selected = Car()
          self.assertEqual(selected.CP.alternativeExperience, 160 if hold else 32)
          self.assertEqual(bool(selected.CP.flags & ToyotaFlags.AUTO_BRAKE_HOLD), hold)
          self.assertTrue(qualified(selected.CP, marked_only=True))
          with structs.CarParams.from_bytes(saved.get('CarParams')) as published:
            self.assertEqual(published.to_dict(), selected.CP.to_dict())
          controls = Controls()
          with patch('openpilot.selfdrive.selfdrived.selfdrived.REPLAY', False):
            sd = SelfdriveD(CP=selected.CP)
          self.assertTrue(controls.aol_replay)
          self.assertTrue(sd.aol_replay)
          state = structs.CarState(canValid=True, gearShifter=structs.CarState.GearShifter.drive)
          state.cruiseState.available = True
          selected.aol_card_intent.update(state.as_reader())
          self.assertEqual(selected.aol_card_intent.allowed_latch, enabled)
          del controls, sd, selected
