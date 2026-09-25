import os
from pathlib import Path
import subprocess
import sys
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.car.gm.tests.test_bolt_cc import fixture, feed, control, params as bolt_params
from opendbc.car.gm.values import CAR
from openpilot.common.params import Params, ParamKeyFlag
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.state_migration import prepare_manager_start, MigrationRequired
from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest


SUPPORTED_NON_ACC = (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_CC_2018_2021, CAR.CHEVROLET_BOLT_CC_2022_2023)


class TestBoltDisableLongitudinal(unittest.TestCase):
  def test_prepare_exact_cp_before_construction_and_positional_compatibility(self):
    self.assertTrue(VehicleStartupPreferences(False, False, False, True).disable_bolt_long)
    for identity in SUPPORTED_NON_ACC:
      for removed in (False, True):
        for raw in (None, b'0', b'1', b'bad'):
          with OpenpilotPrefix():
            params = Params()
            if raw is not None:
              Path(params.get_param_path('DisableOpenpilotLongitudinal')).write_bytes(raw)
            params.put_bool('SafeMode', True, block=True)
            cp, _, _ = fixture(identity, removed=removed)
            before = (cp.pcmCruise, cp.flags, cp.safetyConfigs[0].safetyParam)
            prefs = VehicleStartupPreferences.read(params, enabled=True)
            self.assertIs(prefs.prepare(cp), cp)
            self.assertEqual(cp.openpilotLongitudinalControl, raw in (None, b'0'))
            self.assertEqual((cp.pcmCruise, cp.flags, cp.safetyConfigs[0].safetyParam), before)
    for identity, pedal in ((CAR.CHEVROLET_BOLT_EUV, False), (CAR.CHEVROLET_BOLT_ACC_2022_2023, False)):
      cp = bolt_params(identity, pedal=pedal, present=pedal)
      before = cp.to_dict()
      VehicleStartupPreferences(disable_bolt_long=True).prepare(cp)
      self.assertEqual(cp.to_dict(), before)

  def test_actual_card_explicit_ci_startup_disables_all_long_commands(self):
    from openpilot.selfdrive.car.card import Car
    from opendbc.car.gm.radar_interface import RadarInterface
    for identity in SUPPORTED_NON_ACC:
      with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
        params = Params()
        params.put_bool('OpenpilotEnabledToggle', True, block=True)
        params.put_bool('DisableOpenpilotLongitudinal', True, block=True)
        cp, ci, packer = fixture(identity)
        word = cp.safetyConfigs[0].safetyParam
        card = Car(CI=ci, RI=RadarInterface(cp))
        self.assertFalse(card.CP.openpilotLongitudinalControl)
        self.assertFalse(card.CP.pcmCruise)
        self.assertEqual(card.CP.safetyConfigs[0].safetyParam, word)
        command = control()
        for frame in range(1, 109):
          now = 1_000_000_000 + frame * 10_000_000
          out, _ = feed(ci, packer, now, gas=frame >= 52, speed=12, stock=11)
          self.assertTrue(out.canValid)
          ci.CC.frame = frame
          _, messages = ci.apply(command.as_reader(), now + 1_000_000)
          self.assertNotIn(0x1E1, [message[0] for message in messages])
        # Saving a different preference does not mutate the running drive CP.
        params.put_bool('DisableOpenpilotLongitudinal', False, block=True)
        self.assertFalse(card.CP.openpilotLongitudinalControl)

  def test_registered_preference_second_process_and_unknown_guard(self):
    with OpenpilotPrefix():
      params = Params()
      temporary = tempfile.TemporaryDirectory()
      self.addCleanup(temporary.cleanup)
      storage = Path(temporary.name) / 'recovery'
      prepare_manager_start(params, storage)
      self.assertIs(params.get_default_value('DisableOpenpilotLongitudinal'), False)
      params.put_bool('DisableOpenpilotLongitudinal', True, block=True)
      for flag in (ParamKeyFlag.CLEAR_ON_MANAGER_START, ParamKeyFlag.CLEAR_ON_ONROAD_TRANSITION,
                   ParamKeyFlag.CLEAR_ON_OFFROAD_TRANSITION, ParamKeyFlag.CLEAR_ON_IGNITION_ON, ParamKeyFlag.DEVELOPMENT_ONLY):
        params.clear_all(flag)
        self.assertEqual(Path(params.get_param_path('DisableOpenpilotLongitudinal')).read_bytes(), b'1')
      code = """
from pathlib import Path
import sys
from openpilot.common.params import Params
from openpilot.starpilot.state_migration import prepare_manager_start
p = Params()
assert p.get_bool('DisableOpenpilotLongitudinal')
prepare_manager_start(p, Path(sys.argv[1]), dry_run=True)
"""
      subprocess.run([sys.executable, '-c', code, str(storage)], check=True)
      unknown = Path(params.get_param_path()) / 'UnregisteredDisableOwner'
      unknown.write_bytes(b'keep')
      with self.assertRaises(MigrationRequired):
        prepare_manager_start(params, storage, dry_run=True)
      self.assertEqual(unknown.read_bytes(), b'keep')

  def test_ui_exact_parked_save_does_not_mutate_cp(self):
    with OpenpilotPrefix():
      params = Params()
      cp, _, _ = fixture(CAR.CHEVROLET_BOLT_CC_2018_2021)
      allowed = [False]
      owner = FeatureSettingsOwner(params, lambda group: allowed[0],
                                   vehicle_fingerprint=lambda cp=cp: cp.carFingerprint, vehicle_params=lambda cp=cp: cp)
      view = owner.snapshot('vehicle', parked=False, system_long=True, lateral_context=True, metric=False)
      row = next(row for row in view.rows if row.key == 'DisableOpenpilotLongitudinal')
      self.assertEqual(row.label, 'Disable StarPilot Speed Control')
      self.assertFalse(row.available)
      capability = owner._bolt_disable_capability()
      request = FeatureSettingsRequest('DisableOpenpilotLongitudinal', None, 'On', confirmation=True,
                                       vehicle_fingerprint=cp.carFingerprint, capability=capability)
      self.assertFalse(owner.apply(request))
      allowed[0] = True
      view = owner.snapshot('vehicle', parked=True, system_long=True, lateral_context=True, metric=False)
      row = next(row for row in view.rows if row.key == 'DisableOpenpilotLongitudinal')
      self.assertTrue(row.available)
      self.assertTrue(owner.apply(request))
      self.assertEqual(Path(params.get_param_path('DisableOpenpilotLongitudinal')).read_bytes(), b'1')
      self.assertTrue(cp.openpilotLongitudinalControl)
      self.assertFalse(owner.apply(request))

  def test_actual_card_get_car_hook_reduces_before_interface_construction(self):
    from openpilot.selfdrive.car.card import Car
    from opendbc.car.gm.interface import CarInterface
    for identity in SUPPORTED_NON_ACC:
      with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
        settings = Params()
        settings.put_bool('OpenpilotEnabledToggle', True, block=True)
        settings.put_bool('DisableOpenpilotLongitudinal', True, block=True)
        observed = []
        def get_car(*args, pre_create_hook, identity=identity, observed=observed, **kwargs):
          cp = bolt_params(identity)
          cp = pre_create_hook(cp, identity, {}, [])
          observed.append(cp.openpilotLongitudinalControl)
          ci = CarInterface(cp)
          self.assertFalse(ci.CP.openpilotLongitudinalControl)
          return ci
        with patch('openpilot.selfdrive.car.card.messaging.recv_one_retry', return_value=SimpleNamespace(can=[1])), \
             patch('openpilot.selfdrive.car.card.get_car', side_effect=get_car):
          card = Car()
        self.assertEqual(observed, [False])
        self.assertFalse(card.CP.openpilotLongitudinalControl)

  def test_ui_sibling_capability_unavailable(self):
    with OpenpilotPrefix():
      settings = Params()
      for cp in (bolt_params(CAR.CHEVROLET_BOLT_ACC_2022_2023), bolt_params(CAR.CHEVROLET_BOLT_EUV)):
        owner = FeatureSettingsOwner(settings, lambda group: True,
                                     vehicle_fingerprint=lambda cp=cp: cp.carFingerprint, vehicle_params=lambda cp=cp: cp)
        self.assertIsNone(owner._bolt_disable_capability())
        view = owner.snapshot('vehicle', parked=True, system_long=True, lateral_context=True, metric=False)
        self.assertFalse(any(row.key == 'DisableOpenpilotLongitudinal' for row in view.rows))
