"""Observer records the ordinary caller's existing admission without changing it."""

import pytest
from opendbc.car.hyundai.tests.test_ioniq5pe_stock import params
from openpilot.cereal import messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.runtime import ordinary_axis_acknowledged
from openpilot.starpilot.aol.wire import SAFETY_SERVICE, SafetyState, encode_safety


@pytest.mark.parametrize('condition', ['valid', 'session', 'request', 'grant', 'missing', 'expired', 'observer_error'])
def test_existing_ordinary_admission_observer_preserves_boolean_and_original_lease(condition):
  cp = params()
  now = 10_000_000_000
  with OpenpilotPrefix():
    sm = messaging.SubMaster(['aolAxisState', SAFETY_SERVICE])
    axis = messaging.new_message('aolAxisState', valid=True, logMonoTime=now)
    axis.aolAxisState.qualified = True
    axis.aolAxisState.sessionId = 'current'
    axis.aolAxisState.observedMonoTime = now
    axis.aolAxisState.validUntilMonoTime = now + 30_000_000
    axis.aolAxisState.desiredLateral = True
    axis.aolAxisState.lateralActive = True
    axis.aolAxisState.nativeAcknowledged = True
    native = messaging.new_message(SAFETY_SERVICE, 0, valid=True, logMonoTime=now)
    native.aolSafetyWire = encode_safety(
      SafetyState(
        1,
        True,
        now,
        now + 200_000_000,
        int(cp.safetyConfigs[0].safetyModel.raw),
        cp.safetyConfigs[0].safetyParam,
        condition != 'request',
        False,
        condition != 'grant',
        False,
        'actual-ordinary-fixture',
        'old' if condition == 'session' else 'current',
      )
    )
    sm.update_msgs(now / 1e9, [axis.as_reader(), native.as_reader()])
    if condition == 'missing':
      sm.valid[SAFETY_SERVICE] = False
    decision_ns = now + 200_000_001 if condition == 'expired' else now
    captured = []

    def observer(value):
      captured.append(value)
      if condition == 'observer_error':
        raise ValueError('metadata only')

    expected = condition in ('valid', 'observer_error')
    assert ordinary_axis_acknowledged(sm, cp, now_ns=decision_ns) == expected
    assert ordinary_axis_acknowledged(sm, cp, now_ns=decision_ns, on_validated_native=observer) == expected
    assert len(captured) == int(expected)
    if captured:
      assert captured[0].observedMonoTime == now
      assert captured[0].validUntilMonoTime == now + 200_000_000
      assert captured[0].axisSessionId == 'current'
