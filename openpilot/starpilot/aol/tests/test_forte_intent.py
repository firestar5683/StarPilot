import unittest
from unittest.mock import patch

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.forte_aol import FORTE_IDS, FORTE_AOL_MARKER, FORTE_AOL_EXPERIENCE, ForteLkasSources
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags
from openpilot.starpilot.aol.intent import AolSettings
from openpilot.starpilot.aol.runtime import decide_axes
from openpilot.starpilot.car.hyundai.aol import policy_for, create_intent, native_profile_supported, native_accepts_cp
from types import SimpleNamespace

Button = structs.CarState.ButtonEvent.Type


def params(car=CAR.KIA_FORTE_2019_NON_SCC, source=0x391):
  fp = gen_empty_fingerprint()
  if source:
    fp[0][source] = 8
  return CarInterface.get_params(car, fp, [], False, False, False)


def settings(lkas=9, main=0):
  return AolSettings(True, 0., lkas, main, (0, 0, 0), (0, 0, 0))


def state(main=False, cruise=False, events=()):
  cs = structs.CarState()
  cs.canValid = True
  cs.gearShifter = 'drive'
  cs.cruiseState.available, cs.cruiseState.enabled = main, cruise
  cs.buttonEvents = [structs.CarState.ButtonEvent(type=button, pressed=pressed) for button, pressed in events]
  return cs


class TestForteIntent(unittest.TestCase):
  def test_actual_cp_profile_additions_and_exact_family_isolation(self):
    for car in FORTE_IDS:
      for source in (0, 0x391, 0x50c):
        cp = params(car, source)
        policy = policy_for(cp)
        self.assertTrue(policy.intent_supported)
        self.assertEqual(policy.safety_param_addition, FORTE_AOL_MARKER | (0x800 if source else 0))
        self.assertEqual(cp.safetyConfigs[0].safetyParam, 0x1800 if source == 0x391 else 0x1000)
        self.assertEqual(policy.alternative_experience_addition, FORTE_AOL_EXPERIENCE)
        cp.safetyConfigs[0].safetyParam |= policy.safety_param_addition
        cp.alternativeExperience |= policy.alternative_experience_addition
        self.assertTrue(native_profile_supported(int(cp.safetyConfigs[0].safetyModel.raw), cp.safetyConfigs[0].safetyParam))
        self.assertTrue(native_accepts_cp(cp, int(cp.safetyConfigs[0].safetyModel.raw), cp.safetyConfigs[0].safetyParam))
        bad = cp.as_reader().as_builder()
        bad.safetyConfigs[0].safetyParam ^= 0x800
        self.assertFalse(policy_for(bad).intent_supported)
        for flag in (HyundaiFlags.LEGACY, HyundaiFlags.CAMERA_SCC, HyundaiFlags.CANFD, HyundaiFlags.FCEV, HyundaiFlags.CCNC):
          bad = cp.as_reader().as_builder()
          bad.flags |= int(flag)
          self.assertFalse(policy_for(bad).intent_supported)
        for field in ('passive', 'dashcamOnly', 'notCar'):
          bad = cp.as_reader().as_builder()
          setattr(bad, field, True)
          self.assertFalse(policy_for(bad).intent_supported)
    self.assertFalse(policy_for(params(CAR.KIA_FORTE)).intent_supported)
    self.assertFalse(native_profile_supported(int(structs.CarParams.SafetyModel.hyundai), 0x1000))

  def test_main_boot_and_assignment_defaults_and_symmetric_combined_pause(self):
    for car in FORTE_IDS:
      managed = create_intent(params(car), settings(main=9))
      managed.update(state(main=True), now_ns=1)
      self.assertTrue(managed.allowed_latch)
      managed.update(state(main=True, cruise=True, events=((Button.lkas, False),)), now_ns=2)
      for tick in (3, 5):
        managed.update(state(main=True, cruise=True, events=((Button.lkas, True),)), now_ns=tick)
        self.assertEqual(managed.pause_lateral, tick == 3)
        self.assertTrue(managed.allowed_latch)
        managed.update(state(main=True, cruise=True, events=((Button.lkas, False),)), now_ns=tick + 1)
      for source, expected in ((0, True), (0x391, False), (0x50c, False)):
        implicit = create_intent(params(car, source), settings(lkas=0))
        implicit.update(state(main=True), now_ns=1)
        self.assertEqual(implicit.allowed_latch, expected)
      managed.settings = settings(lkas=0, main=0)
      managed.update(state(main=True), now_ns=8)
      self.assertFalse(managed.allowed_latch)
      managed.settings = settings(lkas=0, main=9)
      managed.update(state(main=True), now_ns=9)
      self.assertTrue(managed.allowed_latch)

  def test_lkas_native_denial_fatal_rearm_and_temporary_output_pause(self):
    intent = create_intent(params(), settings())
    intent.update(state(events=((Button.lkas, False),)), now_ns=1)
    intent.update(state(events=((Button.lkas, True),)), now_ns=2)
    self.assertTrue(intent.allowed_latch)
    cs = state()
    cs.steerFaultTemporary = True
    intent.update(cs, now_ns=3)
    self.assertTrue(intent.allowed_latch)
    cs.gearShifter = 'reverse'
    intent.update(cs, now_ns=4)
    self.assertTrue(intent.allowed_latch)
    self.assertFalse(intent.output(cs)[0])
    intent.update(state(), now_ns=5, native_rejection_ns=5)
    self.assertFalse(intent.allowed_latch)
    intent.update(state(events=((Button.lkas, True),)), now_ns=6)
    self.assertFalse(intent.allowed_latch)
    intent.update(state(events=((Button.lkas, False),)), now_ns=7)
    intent.update(state(events=((Button.lkas, True),)), now_ns=8)
    self.assertTrue(intent.allowed_latch)
    intent.update(state(), now_ns=9, fault_active=True)
    self.assertFalse(intent.allowed_latch)
    intent.update(state(), now_ns=10)
    self.assertFalse(intent.allowed_latch)

    intent.update(state(events=((Button.lkas, False),)), now_ns=11)
    intent.update(state(events=((Button.lkas, True),)), now_ns=20)
    self.assertTrue(intent.allowed_latch)
    intent.update(state(), now_ns=21, native_rejection_ns=19)
    self.assertTrue(intent.allowed_latch)  # Older denial cannot revoke a newer physical gesture.
    managed = create_intent(params(), settings(main=9))
    managed.update(state(main=True), now_ns=1)
    managed.update(state(main=True), now_ns=2, fault_active=True)
    bad = state(main=False)
    bad.canValid = False
    managed.update(bad, now_ns=3)
    managed.update(state(main=True), now_ns=4)
    self.assertFalse(managed.allowed_latch)
    managed.settings = settings(lkas=0, main=9)
    managed.update(state(main=True, events=((Button.lkas, False),)), now_ns=5)
    managed.update(state(main=True, events=((Button.lkas, True),)), now_ns=6)
    self.assertFalse(managed.allowed_latch)
    managed.update(state(main=False), now_ns=7)
    managed.update(state(main=True), now_ns=8)
    self.assertTrue(managed.allowed_latch)

  def test_actual_ci_ordered_physical_or_and_held_initialization(self):
    for car in FORTE_IDS:
      cp = params(car)
      ci = CarInterface(cp)
      packer = CANPacker(DBC[car][Bus.pt])
      ci.update([])
      def packet(address, pressed, packer=packer):
        return packer.make_can_msg('BCM_PO_11' if address == 0x391 else 'CLU13', 0,
                                   {'LDA_BTN' if address == 0x391 else 'CF_Clu_LdwsLkasSW': int(pressed)})
      clock = 1_000_000_000
      def update(samples, ci=ci, packet=packet):
        nonlocal clock
        packets = []
        for address, pressed in samples:
          clock += 1_000_000
          packets.append((clock, [packet(address, pressed)]))
        with patch('opendbc.car.hyundai.non_scc_aol.time.CLOCK_BOOTTIME', 7, create=True), \
             patch('opendbc.car.hyundai.non_scc_aol.time.clock_gettime_ns', return_value=clock):
          ret = ci.update(packets)
        return [event.pressed for event in ret.buttonEvents if event.type == Button.lkas]
      self.assertEqual(update(((0x391, True), (0x50c, False))), [])
      self.assertEqual(update(((0x391, False),)), [False])
      self.assertEqual(update(((0x391, True), (0x50c, False), (0x391, True))), [True])
      self.assertEqual(update(((0x391, False),)), [False])
      self.assertEqual(update(((0x50c, True), (0x50c, False))), [True, False])
      clock += 300_000_001
      self.assertEqual(update(((0x391, True),)), [])
      self.assertEqual(update(((0x391, True),)), [])
      self.assertEqual(update(((0x391, False), (0x391, True), (0x391, False))), [False, True, False])

  def test_new_or_expired_source_must_show_own_neutral_without_phantom_edges(self):
    owner = ForteLkasSources()
    clock = 1_000_000_000
    def update(samples):
      nonlocal clock
      packets = []
      for address, pressed in samples:
        clock += 1_000_000
        data = bytearray(8)
        data[0 if address == 0x391 else 7] = 0x10 if address == 0x391 and pressed else int(pressed)
        packets.append((clock, [(address, bytes(data), 0)]))
      with patch('opendbc.car.hyundai.non_scc_aol.time.CLOCK_BOOTTIME', 7, create=True), \
           patch('opendbc.car.hyundai.non_scc_aol.time.clock_gettime_ns', return_value=clock):
        owner.update(packets)
      return owner.edges
    self.assertEqual(update(((0x391, False),)), [False])
    self.assertEqual(update(((0x50c, True),)), [])
    self.assertEqual(update(((0x50c, False),)), [False])
    self.assertEqual(update(((0x50c, True), (0x50c, False))), [True, False])
    self.assertEqual(update(((0x391, True),)), [True])
    clock += 300_000_001  # Lost release: expiry cannot fabricate a replacement gesture.
    self.assertEqual(update(((0x391, True), (0x50c, False))), [])
    self.assertEqual(update(((0x391, False), (0x391, True))), [False, True])

  def test_unacknowledged_native_denial_and_wrong_request_remain_neutral(self):
    cs = state(main=True)
    intent = SimpleNamespace(pauseLateral=False, pauseLongitudinal=False, allowedLatch=True)
    common = {'standard_lateral': False, 'standard_longitudinal': False, 'intent': intent, 'car_state': cs,
              'initialized': True, 'model_ready': True, 'no_entry': False, 'immediate_disable': False, 'dm_lockout': False, 'pause_brake_mps': 0.}
    for native in (None, SimpleNamespace(requestedLateral=True, requestedLongitudinal=False, lateralAllowed=False),
                   SimpleNamespace(requestedLateral=False, requestedLongitudinal=False, lateralAllowed=True)):
      result = decide_axes(native=native, **common)
      self.assertTrue(result.desired_lateral)
      self.assertFalse(result.lateral_active)
    native = SimpleNamespace(requestedLateral=True, requestedLongitudinal=False, lateralAllowed=True)
    self.assertTrue(decide_axes(native=native, **common).lateral_active)
    cs.steerFaultTemporary = True
    self.assertFalse(decide_axes(native=native, **common).lateral_active)
