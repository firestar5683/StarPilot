"""Exact Ioniq admission avoids unrelated profiles, without caching authority."""
import unittest
from contextlib import ExitStack
from dataclasses import replace
from unittest import mock

from openpilot.cereal import messaging
from openpilot.selfdrive.car.tests.test_hyundai_aol import candidate
from openpilot.starpilot.aol.runtime import current_native
from openpilot.starpilot.aol.vehicle import native_matches_cp
from openpilot.starpilot.aol.wire import PandaSlot, SafetyState, encode_safety
from openpilot.starpilot.car.hyundai import aol
from opendbc.car.hyundai.values import HyundaiFlags
from opendbc.car.structs import car


class TestIoniqNativeDispatch(unittest.TestCase):
  def profiles(self):
    for alternate in (False, True):
      for cp in candidate(alternate):
        cp.safetyConfigs[0].safetyParam |= 0x0800
        yield cp

  def test_exact_profile_revalidates_without_visiting_unrelated_owners(self):
    unrelated = ('qualified_blended_alpha', 'qualified_blended_stock', 'qualified_angle_aol',
                 'qualified_classic_long', 'qualified_classic_scc', 'qualified_canfd_long',
                 'qualified_canfd_stock', 'qualified_non_scc', 'qualified_ccnc_ev_stock')
    for cp in self.profiles():
      with self.subTest(word=cp.safetyConfigs[0].safetyParam), ExitStack() as stack:
        for name in unrelated:
          stack.enter_context(mock.patch.object(aol, name, side_effect=AssertionError(name)))
        qualifier = stack.enter_context(mock.patch.object(aol, 'qualified_ioniq6', wraps=aol.qualified_ioniq6))
        model, param = int(cp.safetyConfigs[0].safetyModel.raw), cp.safetyConfigs[0].safetyParam
        self.assertTrue(native_matches_cp(cp, model, param))
        cp.radarUnavailable = True
        self.assertFalse(native_matches_cp(cp, model, param))
        cp.radarUnavailable = False
        self.assertTrue(native_matches_cp(cp, model, param))
        self.assertEqual(qualifier.call_count, 3)

  def test_exact_qualifier_contract_and_outer_native_word_check_are_preserved(self):
    changes = (('brand', 'mock'), ('radarUnavailable', True), ('passive', True),
               ('dashcamOnly', True), ('notCar', True), ('openpilotLongitudinalControl', None),
               ('pcmCruise', None), ('alternativeExperience', 32),
               ('steerControlType', car.CarParams.SteerControlType.angle))
    for original in self.profiles():
      mutations = [original]
      for field, value in changes:
        cp = original.as_reader().as_builder()
        setattr(cp, field, not getattr(cp, field) if value is None else value)
        mutations.append(cp)
      for flag in (HyundaiFlags.CANFD, HyundaiFlags.EV, HyundaiFlags.CANFD_LKA_STEER_MSG,
                   HyundaiFlags.CANFD_LKA_STEER_MSG_ALT, HyundaiFlags.CANFD_ALT_BUTTONS,
                   HyundaiFlags.CANFD_ANGLE_STEERING, HyundaiFlags.CANFD_CAMERA_SCC):
        cp = original.as_reader().as_builder()
        cp.flags ^= int(flag)
        mutations.append(cp)
      for cp in mutations:
        model, param = int(cp.safetyConfigs[0].safetyModel.raw), cp.safetyConfigs[0].safetyParam
        with self.subTest(word=param, flags=cp.flags, profile=cp.to_dict()):
          expected = aol.qualified_ioniq6(cp)
          self.assertEqual(aol.native_accepts_cp(cp, model, param), expected)
          # Preserve the direct port API; exact native words are checked by dispatch.
          self.assertEqual(aol.native_accepts_cp(cp, model + 1, param ^ 1), expected)
          self.assertEqual(native_matches_cp(cp, model, param), expected)
          self.assertFalse(native_matches_cp(cp, model + 1, param))
          self.assertFalse(native_matches_cp(cp, model, param ^ 1))
      for configs in ([], [original.safetyConfigs[0], original.safetyConfigs[0]]):
        cp = original.as_reader().as_builder()
        cp.safetyConfigs = configs
        self.assertFalse(native_matches_cp(cp, int(car.CarParams.SafetyModel.hyundaiCanfd), 0x8895))

  def test_native_payload_health_session_validity_and_original_lease_still_apply(self):
    _, cp = candidate(True)
    cp.safetyConfigs[0].safetyParam |= 0x0800
    now = 1_000_000_000
    model, param = int(cp.safetyConfigs[0].safetyModel.raw), cp.safetyConfigs[0].safetyParam
    slot = PandaSlot(0, 'panda', model, param, cp.alternativeExperience, True)
    good = SafetyState(1, True, now, now + 200_000_000, model, param,
                       True, True, True, True, 'panda', 'axis', now, (slot,))
    sm = messaging.SubMaster(['aolSafetyWire'])

    def receive(value, *, valid=True, stamp=now):
      nonlocal sm
      sm = messaging.SubMaster(['aolSafetyWire'])
      envelope = messaging.new_message('aolSafetyWire', 0, valid=valid, logMonoTime=stamp)
      envelope.aolSafetyWire = encode_safety(value)
      sm.update_msgs(now / 1e9, [envelope.as_reader()])

    receive(good)
    self.assertIsNotNone(current_native(sm, cp, now_ns=now, axis_session_id='axis'))
    self.assertIsNotNone(current_native(sm, cp, now_ns=now + 200_000_000, axis_session_id='axis'))
    self.assertIsNone(current_native(sm, cp, now_ns=now + 200_000_001, axis_session_id='axis'))
    self.assertIsNone(current_native(sm, cp, now_ns=now, axis_session_id='different'))
    receive(good, valid=False)
    self.assertIsNone(current_native(sm, cp, now_ns=now, axis_session_id='axis'))
    for bad in (replace(good, compatible=False), replace(good, protocolVersion=2),
                replace(good, safetyParam=param ^ 1), replace(good, safetyModel=model + 1),
                replace(good, observedMonoTime=now + 1),
                replace(good, pandaInventory=(replace(slot, heartbeatLost=True),)),
                replace(good, pandaInventory=(replace(slot, safetyRxChecksInvalid=True),)),
                replace(good, pandaInventory=(replace(slot, faults=1),)),
                replace(good, pandaInventory=(replace(slot, alternativeExperience=32),))):
      with self.subTest(native=bad):
        receive(bad)
        self.assertIsNone(current_native(sm, cp, now_ns=now, axis_session_id='axis'))
    # A changed permission is observed immediately; no previous grant is reused.
    receive(replace(good, lateralAllowed=False, longitudinalAllowed=False))
    denied = current_native(sm, cp, now_ns=now, axis_session_id='axis')
    self.assertIsNotNone(denied)
    assert denied is not None
    self.assertFalse(denied.lateralAllowed or denied.longitudinalAllowed)
