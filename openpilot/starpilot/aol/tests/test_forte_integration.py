"""Synthetic parsed CAN and native axis/controller projection, not vehicle replay."""
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import DBC
from opendbc.safety.tests.common import make_msg
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests.test_hyundai import checksum
from openpilot.starpilot.aol.tests.test_forte_intent import params, settings
from openpilot.starpilot.car.hyundai.aol import create_intent, policy_for
from openpilot.starpilot.aol.runtime import current_native, decide_axes
from openpilot.starpilot.aol.wire import SAFETY_SERVICE, SafetyState, encode_safety


class Samples(dict):
  def __init__(self, native, stamp):
    super().__init__({SAFETY_SERVICE: encode_safety(native)})
    self.valid = self.alive = self.seen = {SAFETY_SERVICE: True}
    self.logMonoTime = {SAFETY_SERVICE: stamp}


class ForteStream:
  def __init__(self, *, main_action=0, source=0x391, aol=True):
    self.source = source
    self.cp = params(source=source)
    policy = policy_for(self.cp)
    if aol:
      self.cp.safetyConfigs[0].safetyParam |= policy.safety_param_addition
      self.cp.alternativeExperience |= policy.alternative_experience_addition
    self.ci = CarInterface(self.cp)
    self.ci.update([])
    self.packer = CANPacker(DBC[self.cp.carFingerprint][Bus.pt])
    self.intent = create_intent(self.cp, settings(main=main_action))
    self.intent.settings = replace(self.intent.settings, enabled=aol)
    self.safety = libsafety_py.libsafety  # Harness preloads the qualified candidate.
    self.now = 1_000_000_000
    self.count = 0
    self.reset()

  def reset(self):
    self.safety.init_tests()
    self.safety.set_alternative_experience(self.cp.alternativeExperience)
    assert self.safety.set_safety_hooks(int(self.cp.safetyConfigs[0].safetyModel.raw),
                                      self.cp.safetyConfigs[0].safetyParam) == 0
    self.safety.set_timer(self.now // 1000)
    self.safety.set_aol_test_heartbeat(True)  # Synthetic transport envelope only.

  def tick(self, *, main=False, cruise=False, bcm=False, clu=False, gear='D', eps=False,
           fatal=False, rejection=0, cruise_button=0):
    self.now += 10_000_000
    n = self.count
    self.count += 1
    gears = self.ci.CS.shifter_values
    gear_code = next(code for code, name in gears.items() if name == gear)
    values: dict[str, dict[str, float]] = {
      'EMS16': {'CRUISE_LAMP_M': int(main), 'CRUISE_LAMP_S': int(cruise), 'AliveCounter': n % 4},
      'WHL_SPD11': {'WHL_SPD_FL': 72, 'WHL_SPD_FR': 72, 'WHL_SPD_RL': 72, 'WHL_SPD_RR': 72,
                    'WHL_SPD_AliveCounter_LSB': n % 4, 'WHL_SPD_AliveCounter_MSB': (n // 4) % 4},
      'TCS13': {'AliveCounterTCS': n % 8}, 'MDPS12': {'CF_Mdps_ToiUnavail': int(eps)},
      'CLU11': {'CF_Clu_AliveCnt1': n % 16, 'CF_Clu_CruiseSwState': cruise_button}, 'LVR12': {'CF_Lvr_Gear': gear_code},
      'BCM_PO_11': {'LDA_BTN': int(bcm)}, 'CLU13': {'CF_Clu_LdwsLkasSW': int(clu)},
      'CGW1': {'CF_Gway_DrvSeatBeltSw': 1},
    }
    if self.source == 0x50c:
      del values['BCM_PO_11']
    frames = []
    for name in ('EMS12', 'TCS11', 'TCS15', 'CLU15', 'ESP12', 'SAS11', 'CGW2', *values):
      frame = self.packer.make_can_msg(name, 0, values.get(name, {}))
      if name in ('EMS16', 'WHL_SPD11', 'TCS13'):
        frame = checksum(frame)
      frames.append(frame)
    frames.append(self.packer.make_can_msg('LKAS11', 2, {'CF_Lkas_MsgCount': n % 16}))
    self.safety.set_timer(self.now // 1000)
    for address, data, bus in frames:
      self.safety.safety_rx_hook(make_msg(bus, address, len(data), data))
    self.safety.safety_tick()
    with patch('opendbc.car.hyundai.non_scc_aol.time.CLOCK_BOOTTIME', 7, create=True), \
         patch('opendbc.car.hyundai.non_scc_aol.time.clock_gettime_ns', return_value=self.now):
      self.cs = self.ci.update([(self.now, frames)])
    self.intent.update(self.cs, now_ns=self.now, fault_active=fatal, native_rejection_ns=rejection)
    return self.axis()

  def axis(self, receipt=None):
    intent = SimpleNamespace(allowedLatch=self.intent.allowed_latch, pauseLateral=self.intent.pause_lateral,
                             pauseLongitudinal=self.intent.pause_longitudinal)
    kwargs: dict = {'standard_lateral': False, 'standard_longitudinal': False, 'intent': intent,
              'car_state': self.cs, 'initialized': True, 'model_ready': True, 'no_entry': False,
              'immediate_disable': False, 'dm_lockout': False, 'pause_brake_mps': 0.}
    desired = decide_axes(native=None, **kwargs)
    self.safety.aol_set_host_request(int(desired.desired_lateral))
    permission = self.safety.aol_get_permission_mask()
    native = SafetyState(1, True, self.now, self.now + 30_000_000,
                         int(self.cp.safetyConfigs[0].safetyModel.raw), self.cp.safetyConfigs[0].safetyParam,
                         bool(permission & 1), False, bool(self.safety.aol_get_request_mask() & 1), False, 'synthetic-panda', 'session')
    if receipt is not None:
      native = receipt(native)
    acknowledged = current_native(Samples(native, self.now), self.cp, now_ns=self.now, axis_session_id='session')
    decision = decide_axes(native=acknowledged, **kwargs)
    command = structs.CarControl()
    command.latActive = decision.lateral_active
    command.actuators.torque = 0.01 if decision.lateral_active else 0.
    _, packets = self.ci.apply(command.as_reader(), self.now)
    lkas = [packet for packet in packets if packet[0] == 0x340]
    assert lkas, 'Actual controller must emit LKAS'
    for address, data, bus in lkas:
      assert self.safety.safety_tx_hook(make_msg(bus, address, len(data), data)), 'Actual LKAS rejected'
    return decision


class TestForteIntegration(unittest.TestCase):
  def tearDown(self):
    libsafety_py.libsafety.set_alternative_experience(0)

  def warm(self, stream, **kwargs):
    for _ in range(12):
      result = stream.tick(**kwargs)
    self.assertTrue(stream.cs.canValid)
    return result

  def test_native_reset_requires_neutral_and_new_physical_gesture(self):
    s = ForteStream()
    self.warm(s)
    self.assertTrue(s.tick(bcm=True).lateral_active)
    s.reset()
    self.assertFalse(self.warm(s, bcm=True).lateral_active)
    s.tick(bcm=True, rejection=s.now + 10_000_000)
    self.assertFalse(s.tick(bcm=True).lateral_active)
    s.tick()
    self.assertTrue(s.tick(bcm=True).lateral_active)

  def test_main_boot_both_button_orders_and_combined_sources(self):
    s = ForteStream(main_action=9)
    self.assertTrue(self.warm(s, main=True).lateral_active)
    self.assertFalse(s.tick(main=True, cruise=True, bcm=True).lateral_active)
    s.tick(main=True, cruise=True)
    self.assertTrue(s.tick(main=True, cruise=True, clu=True).lateral_active)
    t = ForteStream()
    self.warm(t)
    self.assertTrue(t.tick(bcm=True).lateral_active)
    self.assertTrue(t.tick(bcm=True, clu=False).lateral_active)
    self.assertTrue(t.tick(bcm=True, clu=False).lateral_active)
    t.tick()
    self.assertFalse(t.tick(clu=True).lateral_active)

  def test_wrong_session_stale_receipt_and_output_pause(self):
    s = ForteStream(main_action=9)
    self.assertTrue(self.warm(s, main=True).lateral_active)
    self.assertFalse(s.axis(lambda n: replace(n, axisSessionId='old')).lateral_active)
    self.assertFalse(s.axis(lambda n: replace(n, validUntilMonoTime=s.now - 1)).lateral_active)
    self.assertFalse(s.tick(main=True, eps=True).lateral_active)
    self.assertTrue(s.intent.allowed_latch)
    self.assertFalse(s.tick(main=True, gear='R').lateral_active)
    self.assertTrue(s.tick(main=True).lateral_active)
    self.assertFalse(s.tick(main=True, fatal=True).lateral_active)
    self.assertFalse(s.tick(main=True).lateral_active)
    s.tick(main=False)
    self.assertTrue(s.tick(main=True).lateral_active)

  def test_50c_only_ordinary_profile_does_not_require_absent_bcm(self):
    s = ForteStream(source=0x50c, aol=False)
    self.assertEqual(s.cp.safetyConfigs[0].safetyParam, 0x1000)
    self.assertEqual(s.cp.alternativeExperience, 0)
    self.assertFalse(self.warm(s, main=True).lateral_active)
    s.tick(main=True, cruise_button=2)  # Actual SET interaction precedes cruise rising.
    self.assertFalse(s.tick(main=True, cruise=True).lateral_active)
    self.assertTrue(s.cs.cruiseState.available)
    self.assertTrue(s.cs.cruiseState.enabled)
    self.assertTrue(s.safety.get_controls_allowed())
    self.assertEqual(s.safety.aol_get_permission_mask(), 0)

  def test_invalid_main_off_cannot_rearm_and_old_denial_preserves_new_edge(self):
    s = ForteStream(main_action=9)
    self.warm(s, main=True)
    s.tick(main=True, fatal=True)
    # A malformed/unhealthy state envelope is not confirmed main-OFF evidence.
    # Parsed CAN remains the source; the health failure is explicitly injected.
    s.cs.canValid = False
    s.cs.cruiseState.available = False
    s.intent.update(s.cs, now_ns=s.now + 1, fault_active=False)
    self.assertFalse(s.tick(main=True).lateral_active)
    s.tick(main=False)
    self.assertTrue(s.tick(main=True).lateral_active)
    t = ForteStream()
    self.warm(t)
    old_denial = t.now
    self.assertTrue(t.tick(bcm=True).lateral_active)
    self.assertTrue(t.tick(bcm=True, rejection=old_denial).lateral_active)

  def test_unselected_clu_source_grants_only_after_its_own_fresh_neutral(self):
    s = ForteStream()
    # BCM arrives first and remains the required native-health alternative.
    # CLU's independent neutral and press must still reach the port owner.
    self.warm(s)
    self.assertFalse(s.safety.get_controls_allowed())
    self.assertTrue(s.tick(clu=True).lateral_active)
    self.assertTrue(s.intent.allowed_latch)
    self.assertEqual(s.safety.aol_get_permission_mask(), 1)
    self.assertFalse(s.safety.get_controls_allowed())
    self.assertTrue(s.tick(clu=True, bcm=False).lateral_active)
    s.tick()
    self.assertFalse(s.tick(clu=True).lateral_active)
