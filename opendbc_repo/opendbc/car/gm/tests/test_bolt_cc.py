import unittest
from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR, DBC, BOLT_CC_WORDS, GMFlags, is_bolt_cc_profile
from opendbc.car.gm.bolt_cc import button_bytes
from opendbc.safety.tests.libsafety import libsafety_py

BOLT_CC_WORDS = {identity: words for identity, words in BOLT_CC_WORDS.items() if identity != CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL}


def setup(cp):
  safety = libsafety_py.libsafety
  safety.init_tests()
  assert safety.set_safety_hooks(int(structs.CarParams.SafetyModel.gm), cp.safetyConfigs[0].safetyParam) == 0


def native(direction, msg, us):
  address, data, bus = msg
  safety = libsafety_py.libsafety
  safety.set_timer(us)
  packet = libsafety_py.make_CANPacket(address, bus, data)
  return safety.safety_rx_hook(packet) if direction == "rx" else safety.safety_tx_hook(packet)


def params(identity, alpha=False, present=False, pedal=False, removed=False, metric=False):
  fp = gen_empty_fingerprint()
  if present:
    fp[0][0x201] = 6
  if removed and present:
    fp[0].update({0x184: 8, 0x34A: 5, 0x348: 5, 0xC9: 8, 0x1C4: 8, 0x1E1: 7,
                  0x1F5: 8, 0xBD: 7, 0x232: 8, 0x3D1: 8, 0xBE: 6})
  if not removed:
    fp[2][0x320] = 8
    fp[2][0x180] = 4
  cp = CarInterface.get_params(identity, fp, [], alpha, False, False)
  if not removed:
    assert not cp.flags & GMFlags.NO_CAMERA
  return cp


def fixture(identity, removed=False, metric=False, alpha=False, present=False):
  cp = params(identity, removed=removed, metric=metric, alpha=alpha, present=present)
  ci = CarInterface(cp)
  ci.CC.bolt_cc_metric = metric
  return cp, ci, CANPacker(DBC[identity][Bus.pt])


def feed(ci, packer, now, counter=0, gas=False, active=True, speed=20, stock=15, brake=False, regen=False, camera=True):
  vals = {
    'PSCMStatus': {},
    'ECMCruiseControl': {'CruiseActive': int(active), 'CruiseSetSpeed': stock * 3.6},
    'ECMEngineStatus': {'CruiseMainOn': 1, 'BrakePressed': int(brake)},
    'AcceleratorPedal2': {'AcceleratorPedal2': 30 if gas else 0},
    'ECMPRDNL2': {'PRNDL2': 4},
    'EBCMWheelSpdRear': {'RLWheelSpd': speed * 3.6, 'RRWheelSpd': speed * 3.6, 'RLWheelDir': 1, 'RRWheelDir': 1},
    'EBCMWheelSpdFront': {'FLWheelSpd': speed * 3.6, 'FRWheelSpd': speed * 3.6},
    'ESPStatus': {'TractionControlOn': 1},
    'BCMDoorBeltStatus': {'LeftSeatBelt': 1},
    'BCMGeneralPlatformStatus': {},
    'BCMTurnSignals': {},
    'PSCMSteeringAngle': {},
    'ECMAcceleratorPos': {},
    'EBCMFrictionBrakeStatus': {},
    'EBCMRegenPaddle': {'RegenPaddle': int(regen)},
  }
  msgs = [packer.make_can_msg(n, 0, v) for n, v in vals.items()]
  msgs.append((0x1E1, button_bytes(1, counter), 0))
  if camera:
    msgs.append(packer.make_can_msg('ASCMLKASteeringCmd', 2, {}))
    msgs.append(packer.make_can_msg('AEBCmd', 2, {}))
  # Prime lazy subscriptions, then prove actual CI's validity (no fabricated canValid).
  ci.update([(now - 1_000_000, msgs)])
  out = ci.update([(now, msgs)])
  return out, sorted(msgs, key=lambda m: m[0] == 0x3d1)


def control(long_active=True, enabled=True, gas=False):
  cc = structs.CarControl()
  cc.enabled = enabled
  cc.latActive = True
  cc.longActive = long_active
  cc.actuators.accel = 1
  cc.actuators.torque = 0.02
  cc.hudControl.setSpeed = 30
  return cc


class Production(unittest.TestCase):
  def test_removed_camera_never_becomes_lazy_required_source(self):
    for identity in BOLT_CC_WORDS:
      for removed in (False, True):
        with self.subTest(identity=identity, removed=removed):
          cp, ci, packer = fixture(identity, removed=removed)
          for tick in range(40):
            out, frames = feed(ci, packer, 1_000_000_000 + tick * 10_000_000,
                               counter=tick % 4, camera=not removed)
          self.assertTrue(out.canValid)
          self.assertFalse(out.canTimeout)
          if removed:
            self.assertFalse(any(frame[2] == 2 for frame in frames))
          for tick in range(40, 170):
            out, _ = feed(ci, packer, 1_000_000_000 + tick * 10_000_000,
                          counter=tick % 4, camera=False)
          self.assertEqual(out.canValid, removed)
          for tick in range(170, 210):
            out, _ = feed(ci, packer, 1_000_000_000 + tick * 10_000_000,
                          counter=tick % 4, camera=not removed)
          self.assertTrue(out.canValid)

  def test_final_params_matrix_and_pedal_separation(self):
    for identity, words in BOLT_CC_WORDS.items():
      for alpha in (False, True):
        for present in (False, True):
          for setting in (False, True):
            for removed in (False, True):
              cp = params(identity, alpha=alpha, present=present, pedal=setting, removed=removed)
              if present:
                self.assertFalse(is_bolt_cc_profile(cp))
                self.assertTrue(cp.flags & GMFlags.PEDAL_LONG.value)
              else:
                self.assertTrue(is_bolt_cc_profile(cp))
                self.assertEqual(cp.safetyConfigs[0].safetyParam, words[removed])
                self.assertTrue(cp.openpilotLongitudinalControl)
                self.assertFalse(cp.pcmCruise or cp.alphaLongitudinalAvailable)
                self.assertAlmostEqual(cp.minEnableSpeed, 24 * 0.44704, places=5)

  def test_exact_profile_rejects_wrong_model_extra_configs_and_side_owner(self):
    cp = params(CAR.CHEVROLET_BOLT_CC_2017)
    for field, value in (("passive", True), ("dashcamOnly", True), ("notCar", True),
                         ("pcmCruise", True), ("alphaLongitudinalAvailable", True),
                         ("networkLocation", structs.CarParams.NetworkLocation.gateway)):
      altered = cp.as_reader().as_builder()
      setattr(altered, field, value)
      self.assertFalse(is_bolt_cc_profile(altered), field)
    altered = cp.as_reader().as_builder()
    altered.safetyConfigs[0].safetyModel = structs.CarParams.SafetyModel.toyota
    self.assertFalse(is_bolt_cc_profile(altered))
    altered = cp.as_reader().as_builder()
    altered.safetyConfigs = [cp.safetyConfigs[0].to_dict(), cp.safetyConfigs[0].to_dict()]
    self.assertFalse(is_bolt_cc_profile(altered))

  def test_actual_parser_controller_native_all_generation_routes(self):
    for identity in BOLT_CC_WORDS:
      for removed in (False, True):
        for alpha, present in ((False, False), (True, False)):
          cp, ci, packer = fixture(identity, removed, alpha=alpha, present=present)
          out, msgs = feed(ci, packer, 1_000_000_000)
          self.assertTrue(out.canValid)
          self.assertFalse(out.canTimeout)
          self.assertTrue(out.cruiseState.enabled)
          self.assertFalse(out.cruiseState.nonAdaptive)
          self.assertAlmostEqual(out.cruiseState.speed, 15, places=2)
          setup(cp)
          for msg in msgs:
            if msg[0] in (0x184, 0x3D1, 0x1E1, 0xC9, 0x1C4, 0x1F5, 0x34A):
              self.assertTrue(native('rx', msg, 1_000_000))
          ci.CC.frame = 104
          _, commands = ci.apply(control().as_reader(), 1_001_000_000)
          button = next(m for m in commands if m[0] == 0x1E1)
          self.assertEqual(button[1], button_bytes(2, 1))
          self.assertTrue(native('tx', button, 1_001_000))
          self.assertFalse(any(m[0] in (0x200, 0x315, 0x2CB, 0xBD, 0x3D1) for m in commands))

  def test_gas_preserves_lateral_and_set_exception_then_release(self):
    for identity in BOLT_CC_WORDS:
      cp, ci, packer = fixture(identity)
      out, msgs = feed(ci, packer, 1_000_000_000, gas=True)
      self.assertTrue(out.gasPressed)
      setup(cp)
      for msg in msgs:
        if msg[0] in (0x184, 0x3D1, 0x1E1, 0xC9, 0x1C4, 0x1F5, 0x34A):
          native('rx', msg, 1_000_000)
      self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
      ci.CC.frame = 104
      _, commands = ci.apply(control(False).as_reader(), 1_001_000_000)
      button = next(m for m in commands if m[0] == 0x1E1)
      self.assertEqual(button[1], button_bytes(3, 1))
      self.assertTrue(native('tx', button, 1_001_000))
      steer = next(m for m in commands if m[0] == 0x180)
      self.assertTrue(native('tx', steer, 1_001_001))
      self.assertFalse(native('tx', (0x1E1, button_bytes(2, 1), 0), 1_001_002))
      # Release gas, still-active PCM; a new physical neutral counter restores ordinary long.
      out, msgs = feed(ci, packer, 1_010_000_000, counter=1, gas=False)
      for msg in msgs:
        if msg[0] in (0x184, 0x3D1, 0x1E1, 0xC9, 0x1C4, 0x1F5, 0x34A):
          native('rx', msg, 1_010_000)
      self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
      ci.CC.frame = 128
      _, commands = ci.apply(control().as_reader(), 1_011_000_000)
      button = next(m for m in commands if m[0] == 0x1E1)
      self.assertEqual(button[1], button_bytes(2, 2))
      self.assertTrue(native('tx', button, 1_011_000))

  def test_actual_controller_metric_boundary_and_disable_long(self):
    identity = CAR.CHEVROLET_BOLT_CC_2018_2021
    for metric in (False, True):
      cp, ci, packer = fixture(identity, metric=metric)
      out, _ = feed(ci, packer, 1_000_000_000, speed=12, stock=12)
      self.assertTrue(out.canValid)
      ci.CC.frame = 104
      cc = control()
      cc.actuators.accel = -0.17
      _, commands = ci.apply(cc.as_reader(), 1_001_000_000)
      buttons = [m for m in commands if m[0] == 0x1E1]
      self.assertEqual(len(buttons), 0 if metric else 1)
      if buttons:
        self.assertEqual(buttons[0][1], button_bytes(3, 1))
    cp = params(identity)
    cp.openpilotLongitudinalControl = False
    ci = CarInterface(cp)
    packer = CANPacker(DBC[identity][Bus.pt])
    out, _ = feed(ci, packer, 1_000_000_000)
    self.assertTrue(out.canValid)
    ci.CC.frame = 104
    _, commands = ci.apply(control().as_reader(), 1_001_000_000)
    self.assertFalse(any(m[0] in (0x1E1, 0x200, 0x315, 0x2CB, 0xBD) for m in commands))

  def test_real_paddle_disengagement_and_physical_button_rearm(self):
    cp, ci, packer = fixture(CAR.CHEVROLET_BOLT_CC_2017)
    out, msgs = feed(ci, packer, 1_000_000_000, regen=True)
    self.assertTrue(out.regenBraking)
    setup(cp)
    for msg in msgs:
      if msg[0] in (0x184, 0x3D1, 0x1E1, 0xC9, 0x1C4, 0x1F5, 0x34A, 0xBD):
        native('rx', msg, 1_000_000)
    self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
    ci.CC.frame = 104
    _, commands = ci.apply(control().as_reader(), 1_001_000_000)
    self.assertFalse(any(m[0] == 0x1E1 for m in commands))
    self.assertFalse(native('tx', (0x1E1, button_bytes(2, 1), 0), 1_001_000))
    self.assertTrue(native('rx', packer.make_can_msg('EBCMRegenPaddle', 0, {}), 1_002_000))
    self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
    self.assertTrue(native('rx', (0x1E1, button_bytes(3, 1), 0), 1_003_000))
    self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
    self.assertTrue(native('rx', (0x1E1, button_bytes(1, 2), 0), 1_004_000))
    self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
    self.assertTrue(native('tx', (0x1E1, button_bytes(2, 3), 0), 1_005_000))

  def test_wrong_length_sources_cannot_create_fresh_raw_credit(self):
    for bad_length in (3, 9):
      cp, ci, packer = fixture(CAR.CHEVROLET_BOLT_CC_2018_2021)
      out, _ = feed(ci, packer, 1_000_000_000)
      self.assertTrue(out.canValid)
      bad = (0x1E1, bytes(bad_length), 0)
      good = (0x1E1, button_bytes(1, 1), 0)
      out = ci.update([(1_010_000_000, [bad, good])])
      self.assertFalse(out.canValid)
      self.assertEqual(ci.CS.bolt_cc_sources[2], (0, b""))
      ci.CC.frame = 104
      _, commands = ci.apply(control().as_reader(), 1_011_000_000)
      self.assertFalse(any(m[0] == 0x1E1 for m in commands))
      ci.update([(1_012_000_000, [good])])
      self.assertEqual(ci.CS.bolt_cc_sources[2], (1_012_000_000, good[1]))

  def test_invalid_optional_paddle_source_stays_not_ready_until_new_valid_packet(self):
    cp, ci, packer = fixture(CAR.CHEVROLET_BOLT_CC_2018_2021)
    out, _ = feed(ci, packer, 1_000_000_000)
    self.assertTrue(out.canValid)
    out = ci.update([(1_010_000_000, [(0xbd, bytes(3), 0)])])
    self.assertFalse(out.canValid)
    out = ci.update([(1_011_000_000, [])])
    self.assertFalse(out.canValid)
    out = ci.update([(1_012_000_000, [(0xbd, bytes(7), 0)])])
    self.assertTrue(out.canValid)

  def test_global_health_revocation_does_not_auto_rearm_on_fresh_sources(self):
    cp, ci, packer = fixture(CAR.CHEVROLET_BOLT_CC_2018_2021)
    _, msgs = feed(ci, packer, 1_000_000_000)
    setup(cp)
    for msg in msgs:
      if msg[0] in (0x184, 0x3D1, 0x1E1, 0xC9, 0x1C4, 0x1F5, 0x34A, 0xBD):
        native('rx', msg, 1_000_000)
    self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
    libsafety_py.libsafety.set_timer(3_000_000)
    libsafety_py.libsafety.safety_tick()
    self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
    _, msgs = feed(ci, packer, 3_001_000_000, counter=1)
    for msg in msgs:
      if msg[0] in (0x184, 0x3D1, 0x1E1, 0xC9, 0x1C4, 0x1F5, 0x34A, 0xBD):
        native('rx', msg, 3_001_000)
    self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
    self.assertTrue(native('rx', (0x1E1, button_bytes(2, 2), 0), 3_002_000))
    self.assertTrue(libsafety_py.libsafety.get_controls_allowed())


if __name__ == '__main__':
  unittest.main()
