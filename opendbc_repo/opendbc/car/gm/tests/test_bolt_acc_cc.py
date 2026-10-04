"""ACC Bolt pedal-off conventional cruise has a distinct camera/PT owner."""
from openpilot.starpilot.longitudinal.tests.extension_helpers import extension_state
import unittest
from unittest.mock import patch
from opendbc.car.gm.tests.test_bolt_cc import params, fixture, feed, control, setup, native
from opendbc.car.gm.values import CAR, GMFlags, is_bolt_cc_profile
from opendbc.car.gm.bolt_cc import button_bytes
from opendbc.safety.tests.libsafety import libsafety_py

ID = CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL


def observe(ci, packer, now, *, camera_active=True, fcw=0, **kwargs):
  camera = packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCmdActive': int(camera_active), 'FCWAlert': fcw})
  original = ci.update
  with patch.object(ci, 'update', side_effect=lambda packets: original([(stamp, [*messages, camera]) for stamp, messages in packets])):
    out, messages = feed(ci, packer, now, **kwargs)
  return out, [*messages, camera]


class TestBoltAccCc(unittest.TestCase):
  def test_final_configuration_isolated_from_active_pedal_and_removed_camera(self):
    for alpha in (False, True):
      for present in (False, True):
        cp = params(ID, alpha=alpha, present=present)
        if present:
          self.assertTrue(cp.flags & GMFlags.PEDAL_LONG.value)
          self.assertFalse(is_bolt_cc_profile(cp))
          self.assertTrue(cp.openpilotLongitudinalControl)
          continue
        self.assertTrue(is_bolt_cc_profile(cp))
        self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xC140)
        self.assertFalse(cp.pcmCruise or cp.alphaLongitudinalAvailable)
        pedal = params(ID, alpha=alpha, present=True, pedal=True)
        self.assertTrue(pedal.flags & GMFlags.PEDAL_LONG.value)
        self.assertFalse(is_bolt_cc_profile(pedal))
        removed = params(ID, alpha=alpha, present=present, removed=True)
        self.assertTrue(is_bolt_cc_profile(removed))
        self.assertEqual(removed.safetyConfigs[0].safetyParam, 0xC141)

  def test_actual_parser_controller_registry_agreement_and_camera_cancel(self):
    for pt_active, camera_active in ((True, True), (False, True), (True, False)):
      with self.subTest(pt=pt_active, camera=camera_active):
        cp, ci, packer = fixture(ID)
        setup(cp)
        out, messages = observe(ci, packer, 1_000_000_000, active=pt_active, camera_active=camera_active)
        self.assertTrue(out.canValid)
        self.assertEqual(out.cruiseState.enabled, camera_active)
        self.assertFalse(out.cruiseState.nonAdaptive)
        for message in messages:
          native('rx', message, 1_000_000)
        self.assertEqual(libsafety_py.libsafety.get_controls_allowed(), pt_active)
        ci.CC.frame = 104
        _, commands = ci.apply(control().as_reader(), 1_001_000_000)
        buttons = [m for m in commands if m[0] == 0x1E1]
        self.assertEqual(bool(buttons), pt_active and camera_active)
        for message in buttons:
          self.assertEqual(message[2], 0)
          self.assertTrue(native('tx', message, 1_001_000))
        out, messages = observe(ci, packer, 1_010_000_000, counter=1, active=pt_active, camera_active=camera_active)
        for message in messages:
          native('rx', message, 1_010_000)
        ci.CC.frame = 105
        _, commands = ci.apply(control(enabled=False, long_active=False).as_reader(), 1_011_000_000)
        buttons = [m for m in commands if m[0] == 0x1E1]
        self.assertEqual(bool(buttons), camera_active)
        for message in buttons:
          self.assertEqual(message, (0x1E1, button_bytes(6, 2), 2))
          self.assertTrue(native('tx', message, 1_011_000))
        for address, length in ((0x200, 6), (0x315, 5), (0x370, 6), (0x3D1, 8)):
          self.assertFalse(native('tx', (address, bytes(length), 0), 1_012_000))

  def test_camera_raw_length_bus_and_staleness(self):
    cp, ci, packer = fixture(ID)
    setup(cp)
    out, messages = observe(ci, packer, 1_000_000_000, fcw=1)
    self.assertTrue(out.stockFcw)
    self.assertFalse(out.cruiseState.nonAdaptive)
    for message in messages:
      native('rx', message, 1_000_000)
    from opendbc.car.gm.values import AccState
    standstill = packer.make_can_msg('AcceleratorPedal2', 0, {'CruiseState': int(AccState.STANDSTILL)})
    self.assertTrue(ci.update([(1_001_000_000, [standstill])]).cruiseState.standstill)
    camera = packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCmdActive': 1})
    self.assertEqual(camera[0], 0x370)
    self.assertEqual(len(camera[1]), 6)
    self.assertEqual(camera[1][2] & 128, 128)
    out = ci.update([(1_002_000_000, [(0x370, bytes(3), 2), camera])])
    self.assertFalse(out.canValid)
    self.assertEqual(ci.CS.bolt_cc_camera_source[0], 0)
    self.assertFalse(ci.update([(1_003_000_000, [])]).canValid)
    self.assertFalse(ci.update([(1_004_000_000, [(0x370, camera[1], 0)])]).canValid)
    self.assertTrue(ci.update([(1_005_000_000, [camera])]).canValid)
    ci.CC.frame = 104
    _, commands = ci.apply(control().as_reader(), 1_400_000_000)
    self.assertFalse(any(m[0] == 0x1E1 for m in commands))
    self.assertFalse(native('tx', (0x1E1, button_bytes(2, 1), 0), 1_400_000))

  def test_gas_override_keeps_pt_lateral_and_literal_set_route(self):
    cp, ci, packer = fixture(ID)
    setup(cp)
    _, messages = observe(ci, packer, 1_000_000_000, gas=True, speed=20, stock=15)
    for message in messages:
      native('rx', message, 1_000_000)
    self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
    ci.CC.frame = 104
    command = control(long_active=False)
    command.hudControl.setSpeed = 25
    _, commands = ci.apply(command.as_reader(), 1_001_000_000)
    buttons = [m for m in commands if m[0] == 0x1E1]
    self.assertEqual(buttons, [(0x1E1, button_bytes(3, 1), 0)])
    self.assertTrue(native('tx', buttons[0], 1_001_000))
    self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
    _, messages = observe(ci, packer, 1_010_000_000, gas=False, counter=1)
    for message in messages:
      native('rx', message, 1_010_000)
    ci.CC.frame = 108
    ci.CC.bolt_cc_owner.last_send = 0
    _, commands = ci.apply(control().as_reader(), 1_011_000_000)
    button = next(m for m in commands if m[0] == 0x1E1)
    self.assertTrue(native('tx', button, 1_011_000))

  def test_brake_paddle_and_health_need_physical_rearm(self):
    from opendbc.safety.tests.test_gm_bolt_cc import ready, packet
    for address, data in ((0xC9, bytes((0, 0, 0, 0, 0, 1, 0, 0))), (0xBD, bytes((16, 0, 0, 0, 0, 0, 0)))):
      ready(0xC140)
      packet(0x370, bytes((0, 0, 128, 0, 0, 0)), 1_000_001, bus=2)
      packet(address, data, 1_002_000)
      self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
      packet(address, bytes(len(data)), 1_003_000)
      packet(0x1E1, button_bytes(1, 1), 1_004_000)
      self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
      packet(0x1E1, button_bytes(3, 2), 1_005_000)
      packet(0x1E1, button_bytes(1, 3), 1_006_000)
      self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
      self.assertTrue(packet(0x1E1, button_bytes(2, 0), 1_007_000, transmit=True))

    frames = ready(0xC140)
    packet(0x370, bytes((0, 0, 128, 0, 0, 0)), 1_000_001, bus=2)
    safety = libsafety_py.libsafety
    safety.set_timer(3_000_000)
    safety.safety_tick()
    self.assertFalse(safety.get_controls_allowed())
    for address, data in frames:
      packet(address, data, 3_001_000)
    packet(0x370, bytes((0, 0, 128, 0, 0, 0)), 3_001_001, bus=2)
    self.assertFalse(safety.get_controls_allowed())
    packet(0x1E1, button_bytes(2, 1), 3_002_000)
    self.assertTrue(safety.get_controls_allowed())

  def test_actual_longcontrol_uses_acc_specific_cc_owner(self):
    from openpilot.selfdrive.controls.lib.longcontrol import LongControl
    from opendbc.car.gm.bolt_cc import BoltCcLongitudinalPolicy
    cp = params(ID)
    controller = LongControl(cp)
    self.assertIsInstance(extension_state(controller, 'vehicle_policy'), BoltCcLongitudinalPolicy)
    self.assertEqual(controller.stopping_decel_rate, 11.18)
    self.assertIsNone(extension_state(controller, 'gm_start'))

  def test_actual_controls_mode_transition_freshness_and_reset(self):
    import os
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.common.params import Params
    from openpilot.cereal import messaging
    from openpilot.selfdrive.controls.controlsd import Controls
    with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
      cp, ci, packer = fixture(ID)
      state, _ = observe(ci, packer, 1_000_000_000)
      self.assertTrue(state.canValid)
      Params().put('CarParams', cp.to_bytes(), block=True)
      controls = Controls()
      controls.sm.simulation = False

      def publish(now, mode, valid=True):
        drive = messaging.new_message('selfdriveState', valid=valid)
        drive.selfdriveState.enabled = drive.selfdriveState.active = True
        drive.selfdriveState.experimentalMode = mode
        vehicle = messaging.new_message('carState', valid=True)
        vehicle.carState = state.as_reader()
        plan = messaging.new_message('longitudinalPlan', valid=True)
        plan.longitudinalPlan.aTarget = -.5
        controls.sm.update_msgs(now, [messaging.log_from_bytes(msg.to_bytes()) for msg in (drive, vehicle, plan)])
      publish(1.00, False)
      publish(1.01, False)
      controls.state_control()
      self.assertEqual(extension_state(controls.LoC, 'bolt_mode').current_mode, 'acc')
      publish(1.02, True)
      controls.state_control()
      self.assertEqual(extension_state(controls.LoC, 'bolt_mode').current_mode, 'blended')
      timer = extension_state(controls.LoC, 'bolt_mode').timer
      controls.LoC.reset()
      self.assertEqual(extension_state(controls.LoC, 'bolt_mode').timer, timer)
      publish(1.03, False, valid=False)
      controls.state_control()
      self.assertEqual(extension_state(controls.LoC, 'bolt_mode').current_mode, 'blended')
      controls.sm.update_msgs(1.20, [])
      self.assertFalse(controls.sm.all_checks(['selfdriveState']))
      controls.state_control()
      self.assertEqual(extension_state(controls.LoC, 'bolt_mode').current_mode, 'blended')
      for tick in range(110):
        publish(1.21 + tick * .01, False)
      self.assertTrue(controls.sm.all_checks(['selfdriveState']))
      controls.state_control()
      self.assertEqual(extension_state(controls.LoC, 'bolt_mode').current_mode, 'acc')
      self.assertTrue(extension_state(controls.LoC, 'bolt_mode').leaving_experimental)

  def test_saved_disable_actual_card_controller_and_parked_capability(self):
    import os
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.common.params import Params
    from openpilot.selfdrive.car.card import Car
    from opendbc.car.gm.radar_interface import RadarInterface
    from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
    from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest
    with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
      settings = Params()
      settings.put_bool('OpenpilotEnabledToggle', True, block=True)
      cp, ci, packer = fixture(ID)
      parked = [False]
      owner = FeatureSettingsOwner(settings, lambda group: parked[0],
                                   vehicle_fingerprint=lambda: cp.carFingerprint, vehicle_params=lambda: cp)
      capability = owner._bolt_disable_capability()
      self.assertIsNotNone(capability)
      request = FeatureSettingsRequest('DisableOpenpilotLongitudinal', None, 'On', confirmation=True,
                                       vehicle_fingerprint=cp.carFingerprint, capability=capability)
      self.assertFalse(owner.apply(request))
      parked[0] = True
      view = owner.snapshot('vehicle', parked=True, system_long=True, lateral_context=True, metric=False)
      self.assertTrue(next(row for row in view.rows if row.key == 'DisableOpenpilotLongitudinal').available)
      self.assertTrue(owner.apply(request))
      self.assertTrue(cp.openpilotLongitudinalControl)
      card = Car(CI=ci, RI=RadarInterface(cp))
      self.assertFalse(card.CP.openpilotLongitudinalControl)
      self.assertEqual(card.CP.safetyConfigs[0].safetyParam, 0xC140)
      self.assertFalse(card.CP.pcmCruise)
      for frame in (4, 52, 104, 108):
        now = 1_000_000_000 + frame * 10_000_000
        out, _ = observe(ci, packer, now, counter=frame % 4, gas=frame >= 52, speed=20, stock=15)
        self.assertTrue(out.canValid)
        ci.CC.frame = frame
        _, messages = ci.apply(control().as_reader(), now + 1_000_000)
        self.assertFalse(any(message[0] in (0x1E1, 0x200, 0x315, 0x2CB) for message in messages))
      removed = params(ID, removed=True)
      unavailable = FeatureSettingsOwner(settings, lambda group: True,
                                         vehicle_fingerprint=lambda: removed.carFingerprint, vehicle_params=lambda: removed)
      self.assertIsNotNone(unavailable._bolt_disable_capability())
      from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences
      VehicleStartupPreferences(disable_bolt_long=True).prepare(removed)
      self.assertFalse(removed.openpilotLongitudinalControl)
      self.assertEqual(removed.safetyConfigs[0].safetyParam, 0xC141)


class TestBoltAccCcRemoved(unittest.TestCase):
  def test_actual_pt_parser_controller_cancel_and_native(self):
    for alpha in (False, True):
      for present in (False,):
        cp, ci, packer = fixture(ID, removed=True, alpha=alpha, present=present)
        self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xC141)
        setup(cp)
        out, messages = feed(ci, packer, 1_000_000_000)
        self.assertTrue(out.canValid)
        self.assertTrue(out.cruiseState.enabled)
        self.assertFalse(out.cruiseState.nonAdaptive)
        for message in messages:
          native('rx', message, 1_000_000)
        self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
        ci.CC.frame = 104
        _, commands = ci.apply(control().as_reader(), 1_001_000_000)
        buttons = [m for m in commands if m[0] == 0x1E1]
        self.assertTrue(buttons)
        for message in buttons:
          self.assertEqual(message[2], 0)
          self.assertTrue(native('tx', message, 1_001_000))
        _, messages = feed(ci, packer, 1_010_000_000, counter=1)
        for message in messages:
          native('rx', message, 1_010_000)
        ci.CC.frame = 105
        _, commands = ci.apply(control(enabled=False, long_active=False).as_reader(), 1_011_000_000)
        self.assertEqual([m for m in commands if m[0] == 0x1E1], [(0x1E1, button_bytes(6, 2), 0)])
        libsafety_py.libsafety.set_controls_allowed(False)
        self.assertTrue(native('tx', (0x1E1, button_bytes(6, 2), 0), 1_011_000))
        self.assertFalse(native('tx', (0x1E1, button_bytes(6, 2), 2), 1_012_000))
        self.assertFalse(native('tx', (0x1E1, button_bytes(6, 2), 0), 1_012_000))

  def test_pt_source_malformed_future_and_stock_inactive(self):
    for invalid in ('length', 'future', 'inactive'):
      cp, ci, packer = fixture(ID, removed=True)
      setup(cp)
      out, messages = feed(ci, packer, 1_000_000_000)
      self.assertTrue(out.canValid)
      if invalid == 'length':
        out = ci.update([(1_010_000_000, [(0x3D1, bytes(3), 0)])])
        self.assertFalse(out.canValid)
        self.assertFalse(ci.update([(1_011_000_000, [])]).canValid)
      elif invalid == 'future':
        feed(ci, packer, 2_000_000_000, counter=1)
      else:
        out, _ = feed(ci, packer, 1_010_000_000, counter=1, active=False)
        self.assertFalse(out.cruiseState.enabled)
      ci.CC.frame = 104
      _, commands = ci.apply(control().as_reader(), 1_020_000_000)
      self.assertFalse(any(m[0] == 0x1E1 for m in commands))

  def test_removed_topology_ignores_camera_and_preserves_rounded_acc_law(self):
    from opendbc.car.gm.bolt_cc import BoltCcOwner, BoltCcProfile
    present = BoltCcOwner(BoltCcProfile(ID))
    removed = BoltCcOwner(BoltCcProfile(ID, camera_removed=True))
    for metric in (False, True):
      for speed in (11.2, 15.0, 20.0):
        for target in (-1.5, -.15, 0., .15, 1.5):
          self.assertEqual(present.request(speed, 15, target, metric), removed.request(speed, 15, target, metric))
    cp, ci, packer = fixture(ID, removed=True)
    out, _ = feed(ci, packer, 1_000_000_000)
    self.assertTrue(out.canValid)
    out = ci.update([(1_001_000_000, [(0x370, bytes(3), 2)])])
    self.assertTrue(out.canValid)
    self.assertTrue(out.cruiseState.enabled)

  def test_removed_driver_counter_and_timeout_boundaries(self):
    from opendbc.safety.tests.test_gm_bolt_cc import ready, packet
    for cause in ('brake', 'gas', 'regen', 'park', 'duplicate', 'skip', 'timeout'):
      with self.subTest(cause=cause):
        ready(0xC141)
        if cause == 'brake':
          packet(0xC9, bytes((0, 0, 0, 0, 0, 1, 0, 0)), 1_002_000)
        elif cause == 'gas':
          packet(0x1C4, bytes((0, 0, 0, 0, 0, 1, 0, 0)), 1_002_000)
        elif cause == 'regen':
          packet(0xBD, bytes((16, 0, 0, 0, 0, 0, 0)), 1_002_000)
        elif cause == 'park':
          packet(0x1F5, bytes(8), 1_002_000)
        elif cause in ('duplicate', 'skip'):
          packet(0x1E1, button_bytes(1, 0 if cause == 'duplicate' else 2), 1_002_000)
        now = 1_400_000 if cause == 'timeout' else 1_003_000
        self.assertFalse(packet(0x1E1, button_bytes(2, 1), now, transmit=True))
        self.assertFalse(packet(0x1E1, button_bytes(6, 1), now, bus=2, transmit=True))
    cp, ci, packer = fixture(ID, removed=True)
    setup(cp)
    _, messages = feed(ci, packer, 1_000_000_000, gas=True, speed=20, stock=15)
    for message in messages:
      native('rx', message, 1_000_000)
    self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
    ci.CC.frame = 104
    command = control(long_active=False)
    command.hudControl.setSpeed = 25
    _, messages = ci.apply(command.as_reader(), 1_001_000_000)
    self.assertEqual([m for m in messages if m[0] == 0x1E1], [(0x1E1, button_bytes(3, 1), 0)])
    self.assertTrue(native('tx', (0x1E1, button_bytes(3, 1), 0), 1_001_000))
    self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
