from contextlib import ExitStack
from unittest import mock

import pytest

from openpilot.starpilot.aol import dm as owner
from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import callers


@pytest.mark.parametrize('family', ['gm', 'toyota'])
@pytest.mark.parametrize('restriction', ['healthy', 'red', 'lockout', 'always_lockout', 'invalid', 'native_denied'])
def test_actual_dm_proof_is_lazy_only_without_an_exception(family, restriction):
  with ExitStack() as cleanup:
    sd, _, drive, _, _ = callers(cleanup, family, True)
    original = sd.update_events

    def events(state):
      value = sd.sm['driverMonitoringState'].as_builder()
      value.alertLevel = 'three' if restriction in ('red', 'native_denied') else 'none'
      value.lockout = restriction == 'lockout'
      value.alwaysOnLockout = restriction == 'always_lockout'
      sd.sm.data['driverMonitoringState'] = value.as_reader()
      if restriction == 'invalid':
        sd.sm.valid['driverMonitoringState'] = False
      return original(state)

    cleanup.enter_context(mock.patch.object(sd, 'update_events', side_effect=events))
    with mock.patch.object(owner, 'armed_lateral_current', wraps=owner.armed_lateral_current) as proof:
      axis, _, command = drive(2, native_request_long=False, allowed=restriction != 'native_denied')
    if restriction in ('healthy', 'invalid'):
      proof.assert_not_called()
    else:
      assert proof.call_count > 0
    if restriction in ('invalid', 'native_denied'):
      assert not axis.lateralActive and not command.latActive
    else:
      assert axis.lateralActive and command.latActive
    assert not axis.longitudinalActive and not command.longActive
