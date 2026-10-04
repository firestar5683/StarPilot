"""EV9 ordinary transport has no independent engagement authority."""
import unittest
from unittest.mock import patch

from opendbc.car.hyundai.values import CAR
from opendbc.car.hyundai.tests.test_ioniq5pe_stock import params
from openpilot.starpilot.aol.tests import test_ordinary_axis as ordinary_axis_fixture


class TestEV9OrdinaryAxis(unittest.TestCase):
  def test_actual_controls_requires_ev9_native_ack(self):
    # Reuse actual Controls/typed Params fixture, replacing only its vehicle CP.
    ev9 = params(candidate=CAR.KIA_EV9)
    self.assertEqual(ev9.safetyConfigs[0].safetyParam, 0x5c91)
    with patch('opendbc.car.hyundai.tests.test_ioniq5pe_stock.params', return_value=ev9):
      ordinary_axis_fixture.TestOrdinaryAxis().test_actual_controls_intersects_baseline_without_changing_enabled_or_long()

  def test_current_ev9_session_rejects_pe_native_word_and_independent_long(self):
    from openpilot.cereal import messaging
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.starpilot.aol.runtime import current_native, decide_ordinary_axis
    from openpilot.starpilot.aol.vehicle import policy_for
    from openpilot.starpilot.aol.wire import SAFETY_SERVICE, SafetyState, encode_safety, decode_safety

    cp = params(candidate=CAR.KIA_EV9)
    policy = policy_for(cp)
    self.assertTrue(policy.ordinary_axis_ack_required)
    self.assertTrue(policy.explicit_latch and policy.runtime_supported and policy.settings_supported)
    self.assertEqual(cp.alternativeExperience, 0)
    with OpenpilotPrefix():
      sm = messaging.SubMaster([SAFETY_SERVICE])
      for tick, (word, session, long_request, expected) in enumerate((
          (0x5c91, 'ev9-current', False, True), (0x5491, 'ev9-current', False, False),
          (0x5c91, 'old-session', False, False), (0x5c91, 'ev9-current', True, False))):
        with self.subTest(word=word, session=session, long_request=long_request):
          now = 1_000_000_000 + tick * 10_000_000
          message = messaging.new_message(SAFETY_SERVICE, 0, valid=True, logMonoTime=now)
          message.aolSafetyWire = encode_safety(SafetyState(
            protocolVersion=1, compatible=True, observedMonoTime=now, validUntilMonoTime=now + 200_000_000,
            safetyModel=int(cp.safetyConfigs[0].safetyModel.raw), safetyParam=word,
            lateralAllowed=True, longitudinalAllowed=False, requestedLateral=True,
            requestedLongitudinal=long_request, pandaSerial='synthetic-transport-only', axisSessionId=session))
          decoded = decode_safety(message.aolSafetyWire)
          assert decoded is not None
          self.assertEqual(decoded.requestedLongitudinal, long_request)
          sm.update_msgs(now / 1e9, [message.as_reader()])
          native = current_native(sm, cp, now_ns=now, axis_session_id='ev9-current')
          result = decide_ordinary_axis(requested=True, native=native)
          self.assertEqual(result.lateral_active, expected)
          self.assertFalse(result.desired_longitudinal or result.longitudinal_active)
          self.assertFalse(decide_ordinary_axis(requested=False, native=native).lateral_active)
