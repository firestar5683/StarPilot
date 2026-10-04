import unittest
from unittest.mock import patch

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.tests.test_bolt_cc import params, feed, control, setup, native
from opendbc.car.gm.tests.test_bolt_pedal import TestBoltPedalMessages
from opendbc.car.gm.bolt_cc import button_bytes
from opendbc.car.gm.values import CAR, DBC, is_bolt_pedal_profile
from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences, bolt_disable_supported

IDS = (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_CC_2018_2021,
       CAR.CHEVROLET_BOLT_CC_2022_2023, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL)


class TestBoltDisableActivePedal(unittest.TestCase):
  def test_exact_startup_authority_reduction_and_siblings(self):
    for identity in IDS:
      for alpha in (False, True):
        cp = params(identity, alpha=alpha, present=True, pedal=True)
        self.assertTrue(is_bolt_pedal_profile(cp))
        word, flags = cp.safetyConfigs[0].safetyParam, cp.flags
        self.assertTrue(bolt_disable_supported(cp))
        VehicleStartupPreferences(disable_bolt_long=True).prepare(cp, fingerprints={2: {0x180: 4}})
        self.assertFalse(cp.openpilotLongitudinalControl)
        self.assertTrue(cp.pcmCruise)
        self.assertTrue(is_bolt_pedal_profile(cp, stock_only=True))
        self.assertTrue(bolt_disable_supported(cp))
        self.assertEqual((cp.safetyConfigs[0].safetyParam, cp.flags),
                         (5 if identity == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL else word, flags))
        VehicleStartupPreferences(disable_bolt_long=True).finalize(cp)
        VehicleStartupPreferences().prepare(cp, fingerprints={2: {0x180: 4}})
        self.assertFalse(cp.openpilotLongitudinalControl)
    for identity in (CAR.CHEVROLET_BOLT_EUV, CAR.CHEVROLET_BOLT_ACC_2022_2023):
      cp = params(identity, alpha=True)
      before = cp.to_dict()
      self.assertFalse(bolt_disable_supported(cp))
      VehicleStartupPreferences(disable_bolt_long=True).prepare(cp, fingerprints={2: {0x180: 4}})
      self.assertEqual(cp.to_dict(), before)

  def test_actual_parser_stock_cruise_no_takeover_and_native_steering(self):
    for identity in IDS:
      for alpha in (False, True):
        cp = params(identity, alpha=alpha, present=True, pedal=True)
        VehicleStartupPreferences(disable_bolt_long=True).prepare(cp, fingerprints={2: {0x180: 4}})
        ci = CarInterface(cp)
        packer = CANPacker(DBC[identity][Bus.pt])
        setup(cp)
        original = ci.update
        for frame in range(16):
          now = 1_000_000_000 + frame * 10_000_000
          sensor = TestBoltPedalMessages.sensor(packer, 0, frame % 16)
          extra = [sensor]
          if identity == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL:
            extra += [packer.make_can_msg('AcceleratorPedal2', 0, {'CruiseState': 1}),
                      packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCruiseState': 2, 'ACCCmdActive': 1})]
          def update(packets, original=original, extra=extra):
            return original([(stamp, [*messages, *extra]) for stamp, messages in packets])
          with patch.object(ci, 'update', side_effect=update):
            out, messages = feed(ci, packer, now, counter=frame % 4)
          self.assertTrue(out.canValid, (identity, alpha, frame, is_bolt_pedal_profile(ci.CP, stock_only=True), cp.pcmCruise))
          self.assertTrue(out.cruiseState.enabled)
          self.assertFalse(out.cruiseState.nonAdaptive)
          if frame == 0:
            from openpilot.selfdrive.car.car_events import CarEvents, EventName
            from opendbc.car import structs
            events = CarEvents(cp).update(out, structs.CarState(), control())
            self.assertNotIn(EventName.wrongCruiseMode, events.names)
            self.assertIn(EventName.pcmEnable, events.names)
          for message in [*messages, *extra]:
            native('rx', message, now // 1000)
          if frame == 0:
            native('rx', (0x1E1, button_bytes(3, 1), 0), now // 1000 + 1)
            native('rx', (0x1E1, button_bytes(1, 2), 0), now // 1000 + 2)
          ci.CC.frame = frame
          # Even an erroneous active demand cannot acquire disabled startup ownership.
          cc = control()
          _, commands = ci.apply(cc.as_reader(), now + 3_000)
          self.assertFalse(any(m[0] in (0x200, 0x315, 0xBD, 0x1F5, 0x1E1, 0x370, 0x3D1) for m in commands))
          for message in commands:
            if message[0] == 0x180:
              self.assertTrue(native('tx', message, now // 1000 + 3))

  def test_actual_card_before_constructor_and_parked_owner(self):
    import os
    from types import SimpleNamespace
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.selfdrive.car.card import Car
    from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
    for identity in IDS:
      with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
        settings = Params()
        settings.put_bool('OpenpilotEnabledToggle', True, block=True)
        settings.put_bool('DisableOpenpilotLongitudinal', True, block=True)
        observed = []
        def get_car(*args, pre_create_hook, identity=identity, observed=observed, **kwargs):
          cp = params(identity, present=True, pedal=True)
          original_word = cp.safetyConfigs[0].safetyParam
          cp = pre_create_hook(cp, identity, {2: {0x180: 4}}, [])
          self.assertTrue(is_bolt_pedal_profile(cp, stock_only=True))
          self.assertEqual(cp.safetyConfigs[0].safetyParam,
                           5 if identity == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL else original_word)
          ci = CarInterface(cp)
          observed.append(ci.CP.to_dict())
          return ci
        with patch('openpilot.selfdrive.car.card.messaging.recv_one_retry', return_value=SimpleNamespace(can=[1])), \
             patch('openpilot.selfdrive.car.card.get_car', side_effect=get_car):
          card = Car()
        self.assertEqual(len(observed), 1)
        self.assertFalse(card.CP.openpilotLongitudinalControl)
        self.assertTrue(card.CP.pcmCruise)
        owner = FeatureSettingsOwner(settings, lambda group: True,
                                     vehicle_fingerprint=lambda identity=identity: identity, vehicle_params=lambda card=card: card.CP)
        self.assertIsNotNone(owner._bolt_disable_capability())
        before = card.CP.to_dict()
        settings.put_bool('DisableOpenpilotLongitudinal', False, block=True)
        self.assertEqual(card.CP.to_dict(), before)

  def test_parked_saved_owner_no_live_mutation(self):
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
    from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest
    for identity in IDS:
      with OpenpilotPrefix():
        settings = Params()
        cp = params(identity, present=True, pedal=True)
        allowed = [False]
        owner = FeatureSettingsOwner(settings, lambda group, allowed=allowed: allowed[0],
                                     vehicle_fingerprint=lambda identity=identity: identity, vehicle_params=lambda cp=cp: cp)
        request = FeatureSettingsRequest('DisableOpenpilotLongitudinal', None, 'On', confirmation=True,
                                         vehicle_fingerprint=identity, capability=owner._bolt_disable_capability())
        self.assertFalse(owner.apply(request))
        allowed[0] = True
        view = owner.snapshot('vehicle', parked=True, system_long=True, lateral_context=True, metric=False)
        row = next(row for row in view.rows if row.key == 'DisableOpenpilotLongitudinal')
        self.assertTrue(row.available)
        before = cp.to_dict()
        self.assertTrue(owner.apply(request))
        self.assertFalse(owner.apply(request))
        self.assertEqual(cp.to_dict(), before)

  def test_disabled_acc_native_stock_friction_forwarding(self):
    from opendbc.safety.tests.libsafety import libsafety_py
    cp = params(CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL, present=True, pedal=True)
    VehicleStartupPreferences(disable_bolt_long=True).prepare(cp, fingerprints={2: {0x180: 4}})
    setup(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    active = packer.make_can_msg('AcceleratorPedal2', 0, {'CruiseState': 1})
    native('rx', active, 1_000_000)
    self.assertEqual(libsafety_py.libsafety.safety_fwd_hook(2, 0x315), 0)
    inactive = packer.make_can_msg('AcceleratorPedal2', 0, {'CruiseState': 0})
    native('rx', inactive, 1_010_000)
    self.assertEqual(libsafety_py.libsafety.safety_fwd_hook(2, 0x315), 0)

  def test_missing_camera_denial_keeps_recovery_toggle_and_next_startup_off(self):
    import os
    from types import SimpleNamespace
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.selfdrive.car.card import Car
    from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
    from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest
    from opendbc.car import structs
    from opendbc.car.gm.values import is_bolt_pedal_stock_denied
    identity = CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL
    for fingerprint in ({}, {2: {0x180: 3}}, {0: {0x180: 4}}):
      with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
        settings = Params()
        settings.put_bool('OpenpilotEnabledToggle', True, block=True)
        settings.put_bool('DisableOpenpilotLongitudinal', True, block=True)
        def get_car(*args, pre_create_hook, fingerprint=fingerprint, **kwargs):
          cp = params(identity, present=True, pedal=True)
          cp = pre_create_hook(cp, identity, fingerprint, [])
          self.assertTrue(is_bolt_pedal_stock_denied(cp))
          return CarInterface(cp)
        with patch('openpilot.selfdrive.car.card.messaging.recv_one_retry', return_value=SimpleNamespace(can=[1])), \
             patch('openpilot.selfdrive.car.card.get_car', side_effect=get_car):
          card = Car()
        # Params destruction joins Card's asynchronous startup cache writes before the parked save.
        card.params = Params()
        self.assertTrue(is_bolt_pedal_stock_denied(card.CP))
        self.assertEqual(card.CP.safetyConfigs[0].safetyModel, structs.CarParams.SafetyModel.noOutput)
        owner = FeatureSettingsOwner(settings, lambda group: True,
                                     vehicle_fingerprint=lambda: identity, vehicle_params=lambda card=card: card.CP)
        view = owner.snapshot('vehicle', parked=True, system_long=True, lateral_context=True, metric=False)
        row = next(row for row in view.rows if row.key == 'DisableOpenpilotLongitudinal')
        self.assertTrue(row.available)
        self.assertIn('Factory camera not detected', row.reason)
        request = FeatureSettingsRequest('DisableOpenpilotLongitudinal', b'1', 'Off', confirmation=True,
                                         vehicle_fingerprint=identity, capability=owner._bolt_disable_capability())
        import fcntl
        from pathlib import Path
        lock = Path(settings.get_param_path('DisableOpenpilotLongitudinal')).parent.parent / '.lock'
        with lock.open('rb') as writer_lock:
          fcntl.flock(writer_lock, fcntl.LOCK_EX)
          self.assertFalse(owner.apply(request))
          self.assertTrue(settings.get_bool('DisableOpenpilotLongitudinal'))
        self.assertTrue(owner.apply(request))
        self.assertFalse(owner.apply(request))
        self.assertTrue(is_bolt_pedal_stock_denied(card.CP))
        next_cp = params(identity, present=True, pedal=True)
        VehicleStartupPreferences.read(settings, enabled=True).prepare(next_cp)
        self.assertTrue(is_bolt_pedal_profile(next_cp))
    cp = params(identity, present=True, pedal=True)
    VehicleStartupPreferences(disable_bolt_long=True).prepare(cp)
    self.assertTrue(is_bolt_pedal_stock_denied(cp))

  def test_reduced_acc_user_cancel_native_stock_forward_and_sources(self):
    from opendbc.safety.tests.libsafety import libsafety_py
    cp = params(CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL, present=True, pedal=True)
    VehicleStartupPreferences(disable_bolt_long=True).prepare(cp, fingerprints={2: {0x180: 4}})
    self.assertEqual(cp.safetyConfigs[0].safetyParam, 5)
    setup(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    active = packer.make_can_msg('AcceleratorPedal2', 0, {'CruiseState': 1})
    native('rx', active, 1_000_000)
    self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
    self.assertEqual(libsafety_py.libsafety.safety_fwd_hook(2, 0x315), 0)
    cancel = (0x1E1, button_bytes(6, 1), 2)
    self.assertTrue(native('tx', cancel, 1_001_000))
    for address, length in ((0x200, 6), (0x315, 5), (0xBD, 7), (0x1F5, 8), (0x370, 6)):
      self.assertFalse(native('tx', (address, bytes(length), 0), 1_001_001))
    native('rx', packer.make_can_msg('AcceleratorPedal2', 0, {'CruiseState': 0}), 1_010_000)
    self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
    self.assertEqual(libsafety_py.libsafety.safety_fwd_hook(2, 0x315), 0)
    self.assertFalse(native('tx', cancel, 1_011_000))

  def test_reduced_acc_missing_stale_pt_and_physical_regen_suppress_steering(self):
    identity = CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL
    for fault in ('missing_camera', 'stale', 'stale_pt', 'regen'):
      cp = params(identity, present=True, pedal=True)
      VehicleStartupPreferences(disable_bolt_long=True).prepare(cp, fingerprints={2: {0x180: 4}})
      ci = CarInterface(cp)
      packer = CANPacker(DBC[identity][Bus.pt])
      extra = [TestBoltPedalMessages.sensor(packer, 0, 0),
               packer.make_can_msg('AcceleratorPedal2', 0, {'CruiseState': 1})]
      if fault != 'missing_camera':
        extra.append(packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCruiseState': 2, 'ACCCmdActive': 1}))
      original = ci.update
      def update(packets, original=original, extra=extra):
        return original([(stamp, [*messages, *extra]) for stamp, messages in packets])
      with patch.object(ci, 'update', side_effect=update):
        out, _ = feed(ci, packer, 1_000_000_000)
      if fault == 'missing_camera':
        self.assertFalse(out.canValid)
      elif fault == 'stale_pt':
        for now in range(1_400_000_000, 1_461_000_000, 10_000_000):
          out = ci.update([(now, [packer.make_can_msg('ASCMActiveCruiseControlStatus', 2,
                                                    {'ACCCruiseState': 2, 'ACCCmdActive': 1})])])
        self.assertFalse(out.canValid)
      elif fault == 'regen':
        out = ci.update([(1_001_000_000, [packer.make_can_msg('EBCMRegenPaddle', 0, {'RegenPaddle': 1})])])
        self.assertTrue(out.regenBraking)
      now = 1_402_000_000 if fault in ('stale', 'stale_pt') else 1_002_000_000
      ci.CC.frame = 104
      _, messages = ci.apply(control().as_reader(), now)
      steering = next(m for m in messages if m[0] == 0x180)
      self.assertEqual(steering[1][0] & 8, 0, fault)
      self.assertFalse(any(m[0] in (0x200, 0x315, 0x1E1, 0xBD, 0x1F5) for m in messages))


  def test_vehicle_snapshot_provider_expiry_does_not_read_denial_twice(self):
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
    cp = params(CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL, present=True, pedal=True)
    VehicleStartupPreferences(disable_bolt_long=True).prepare(cp)
    for expired in (None, object()):
      with OpenpilotPrefix():
        samples = iter((cp, expired))
        reads = []
        def provider(reads=reads, samples=samples):
          reads.append(True)
          return next(samples)
        owner = FeatureSettingsOwner(Params(), lambda _: True, vehicle_fingerprint=lambda: cp.carFingerprint,
                                     vehicle_params=provider)
        view = owner.snapshot('vehicle', parked=True, system_long=True, lateral_context=True, metric=False)
        self.assertEqual(len(reads), 1)
        row = next(row for row in view.rows if row.key == 'DisableOpenpilotLongitudinal')
        self.assertTrue(row.available)
        self.assertIn('Factory camera not detected', row.reason)
        # A displayed recovery row is not retained commit authority.
        self.assertIsNone(owner._bolt_disable_capability())
        self.assertEqual(len(reads), 2)
        owner.vehicle_params = lambda: cp
        refreshed = owner.snapshot('vehicle', parked=True, system_long=True, lateral_context=True, metric=False)
        self.assertTrue(next(row for row in refreshed.rows if row.key == 'DisableOpenpilotLongitudinal').available)
