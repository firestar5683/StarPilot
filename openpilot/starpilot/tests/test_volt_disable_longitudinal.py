"""Saved speed choice retains exact Volt physical and lateral ownership."""
from pathlib import Path
import unittest

from opendbc.car import gen_empty_fingerprint
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.lateral import lane_centering_supported
from opendbc.car.gm.startup_preferences import disable_long_supported
from opendbc.car.gm.tests.test_bolt_volt_configurations import ordinary_params
from opendbc.car.gm.values import CAR, is_volt_gateway_alternate_brake
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest


def volt_cc_params(*, release=False):
  fingerprint = gen_empty_fingerprint()
  fingerprint[0].update({0xBE: 6, 0x3D1: 8, 0xC9: 8, 0x1E1: 7, 0x1F5: 8, 0x34A: 5, 0x1C4: 8, 0xBD: 7})
  return CarInterface.get_params(CAR.CHEVROLET_VOLT_CC, fingerprint, [], False, release, False)


def configured(variant):
  if variant == 'cc':
    return volt_cc_params()
  return ordinary_params(CAR.CHEVROLET_VOLT, radar=True, accelerator=variant == 'be')


class TestVoltDisableLongitudinal(unittest.TestCase):
  def test_actual_registered_preference_finalized_cp_and_idempotence(self):
    for variant in ('be', 'f1', 'cc'):
      for raw in (None, b'0', b'1', b'corrupt'):
        with self.subTest(variant=variant, raw=raw), OpenpilotPrefix():
          params = Params()
          if raw is not None:
            Path(params.get_param_path('DisableOpenpilotLongitudinal')).write_bytes(raw)
          cp = configured(variant)
          self.assertTrue(cp.openpilotLongitudinalControl)
          before = (cp.pcmCruise, int(cp.flags), cp.safetyConfigs[0].safetyModel, cp.safetyConfigs[0].safetyParam)
          preferences = VehicleStartupPreferences.read(params, enabled=True)
          preferences.prepare(cp)
          preferences.finalize(cp)
          preferences.prepare(cp)
          self.assertEqual(cp.openpilotLongitudinalControl, raw in (None, b'0'))
          self.assertEqual((cp.pcmCruise, int(cp.flags), cp.safetyConfigs[0].safetyModel, cp.safetyConfigs[0].safetyParam), before)
          self.assertFalse(cp.pcmCruise)
          self.assertTrue(disable_long_supported(cp))
          self.assertTrue(lane_centering_supported(cp))
          self.assertEqual(is_volt_gateway_alternate_brake(cp), variant == 'f1')

  def test_unqualified_and_sibling_configs_unchanged(self):
    candidates = [volt_cc_params(release=True), ordinary_params(CAR.CHEVROLET_VOLT, radar=False),
                  ordinary_params(CAR.CHEVROLET_VOLT_CAMERA), ordinary_params(CAR.CHEVROLET_VOLT_2019),
                  ordinary_params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True)]
    for cp in candidates:
      before = cp.to_dict()
      self.assertFalse(disable_long_supported(cp))
      VehicleStartupPreferences(disable_bolt_long=True).prepare(cp)
      self.assertEqual(cp.to_dict(), before)
    for field in ('passive', 'dashcamOnly', 'notCar'):
      cp = configured('be')
      setattr(cp, field, True)
      self.assertFalse(disable_long_supported(cp))

  def test_parked_ui_recovery_changes_only_next_startup(self):
    for variant in ('be', 'f1', 'cc'):
      with self.subTest(variant=variant), OpenpilotPrefix():
        params = Params()
        cp = configured(variant)
        owner = FeatureSettingsOwner(params, lambda group: True, vehicle_fingerprint=lambda cp=cp: cp.carFingerprint,
                                     vehicle_params=lambda cp=cp: cp)
        view = owner.snapshot('vehicle', parked=True, system_long=True, lateral_context=True, metric=False)
        row = next(row for row in view.rows if row.key == 'DisableOpenpilotLongitudinal')
        self.assertTrue(row.available)
        capability = owner._bolt_disable_capability()
        request = FeatureSettingsRequest('DisableOpenpilotLongitudinal', None, 'On', confirmation=True,
                                         vehicle_fingerprint=cp.carFingerprint, capability=capability)
        self.assertTrue(owner.apply(request))
        self.assertTrue(cp.openpilotLongitudinalControl)
        VehicleStartupPreferences.read(params, enabled=True).prepare(cp)
        self.assertFalse(cp.openpilotLongitudinalControl)
        recovery = owner._bolt_disable_capability()
        request = FeatureSettingsRequest('DisableOpenpilotLongitudinal', b'1', 'Off', confirmation=True,
                                         vehicle_fingerprint=cp.carFingerprint, capability=recovery)
        self.assertTrue(owner.apply(request))
        self.assertFalse(cp.openpilotLongitudinalControl)
        next_cp = configured(variant)
        VehicleStartupPreferences.read(params, enabled=True).prepare(next_cp)
        self.assertTrue(next_cp.openpilotLongitudinalControl)

  def test_actual_card_and_packed_sources_suppress_host_longitudinal(self):
    import os
    from unittest.mock import patch
    from opendbc.can import CANPacker
    from opendbc.car import Bus, structs
    from opendbc.car.gm import gmcan
    from opendbc.car.gm.radar_interface import RadarInterface
    from opendbc.car.gm.tests.test_bolt_cc import control, feed, setup, native
    from opendbc.car.gm.values import DBC, CruiseButtons
    from opendbc.safety.tests.libsafety import libsafety_py
    from openpilot.selfdrive.car.card import Car

    for variant in ('be', 'f1', 'cc'):
      with self.subTest(variant=variant), OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
        params = Params()
        params.put_bool('OpenpilotEnabledToggle', True, block=True)
        params.put_bool('DisableOpenpilotLongitudinal', True, block=True)
        safety = libsafety_py.libsafety
        release = safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0
        if variant == 'cc' and release:
          cp = volt_cc_params(release=True)
          self.assertTrue(cp.dashcamOnly)
          self.assertFalse(disable_long_supported(cp))
          continue
        cp = configured(variant)
        ci = CarInterface(cp)
        word = cp.safetyConfigs[0].safetyParam
        card = Car(CI=ci, RI=RadarInterface(cp))
        self.assertFalse(card.CP.openpilotLongitudinalControl)
        self.assertEqual(card.CP.safetyConfigs[0].safetyParam, word)
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        setup(cp)
        steering = []
        command = control(long_active=True)
        # Actual Card finalized the same CI after parser/controller construction.
        # Every physical source is packed and observed; no fabricated canValid.
        for tick in range(60):
          now = 1_000_000_000 + tick * 10_000_000
          _, sources = feed(ci, packer, now, counter=tick % 4)
          selected = packer.make_can_msg('AcceleratorPedal2', 0, {'CruiseState': 2})
          sources = [source for source in sources if source[0] != selected[0]] + [selected]
          button = CruiseButtons.RES_ACCEL if tick == 5 else CruiseButtons.UNPRESS
          selected = gmcan.create_buttons(packer, 0, tick % 4, button)
          sources = [source for source in sources if source[0] != selected[0]] + [selected]
          if variant == 'f1':
            sources = [source for source in sources if source[0] != 0xBE]
            sources.append(packer.make_can_msg('EBCMBrakePedalPosition', 0, {'BrakePedalPosition': 0}))
          out = ci.update([(now + 1, sources)])
          for source in sources:
            native('rx', source, now // 1000)
          if tick < 10:
            continue
          self.assertTrue(out.canValid)
          self.assertFalse(out.brakePressed)
          ci.CC.frame = tick
          command.actuators.accel = -3. if tick % 2 else 2.
          command.cruiseControl.cancel = tick >= 30
          _, messages = ci.apply(command.as_reader(), now + 2)
          self.assertFalse(any(message[0] in (0x2CB, 0x315, 0x370, 0x409, 0x40A, 0xA1, 0x306, 0x308, 0x310) for message in messages))
          if variant != 'cc':
            self.assertFalse(any(message[0] == 0x1E1 for message in messages))
          for message in messages:
            if message[0] == 0x180:
              steering.append(message)
              self.assertTrue(native('tx', message, now // 1000))
        self.assertTrue(steering)
        self.assertTrue(any(message[1][0] & 8 for message in steering))
        # The positive complete feed above is required before this expiry check.
        ci.CC.frame = 72
        _, expired = ci.apply(command.as_reader(), now + 400_000_000)
        expired_steering = [message for message in expired if message[0] == 0x180]
        self.assertTrue(expired_steering)
        self.assertFalse(any(message[1][0] & 8 for message in expired_steering))
        # Physical brake is observed on the selected source, then native authority
        # withdraws without relying on an updated Controls command.
        now += 410_000_000
        brake_name, brake_signal, pressed = (('EBCMBrakePedalPosition', 'BrakePedalPosition', 6)
                                            if variant == 'f1' else ('ECMAcceleratorPos', 'BrakePedalPos', 12))
        brake_message = packer.make_can_msg(brake_name, 0, {brake_signal: pressed})
        sources = [source for source in sources if source[0] != brake_message[0]] + [brake_message]
        out = ci.update([(now, sources)])
        self.assertTrue(out.brakePressed)
        for source in sources:
          native('rx', source, now // 1000)
        self.assertFalse(safety.get_controls_allowed())
