"""Fresh ordinary lag renews only a newly admitted source after an old lease expires."""
from contextlib import ExitStack
from unittest import mock

import pytest

from openpilot.cereal import log
from openpilot.starpilot.aol.tests.test_fresh_lag_continuity import callers
from openpilot.starpilot.aol.tests.test_ordinary_source_availability import settings
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture


@pytest.mark.parametrize('mode', ['combined', 'combined_unarmed', 'long_only'])
def test_new_fresh_lag_source_after_old_deadline_preserves_normal_countdown(mode):
  with callers(mode) as ((sd, controls, drive, card, receive), old):
    stamp = BASE + 40000000
    assert old.validUntilMonoTime < stamp
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      axis, state, command = drive(6, state_stamp=stamp, **settings(mode, stamp, 7))
    assert axis.faultReason == 'none' and (not sd.aol_authority_lost)
    assert axis.sourceCarStateMonoTime == stamp
    assert axis.validUntilMonoTime == stamp + 30000000
    assert state.enabled and state.active and (state.state == log.SelfdriveState.OpenpilotState.softDisabling)
    assert sd.state_machine.soft_disable_timer == 300
    assert axis.longitudinalActive and command.longActive
    assert axis.lateralActive == command.latActive == (mode != 'long_only')
    assert log.OnroadEvent.EventName.selfdrivedLagging in sd.events.names
    assert not sd.events.contains(fixture.ET.ENABLE)
    assert old.validUntilMonoTime < stamp


@pytest.mark.parametrize('fault', ['immediate', 'native_denied', 'missing_pair', 'dm', 'invalid_cs'])
def test_old_deadline_new_frame_never_excuses_other_faults(fault):
  with callers('combined') as ((sd, controls, drive, card, receive), old):
    stamp = BASE + 40000000
    options = settings('combined', stamp, 7)
    if fault == 'immediate':
      options['critical_event'] = log.OnroadEvent.EventName.controlsMismatch
    elif fault == 'native_denied':
      options.update(allowed=False, long_allowed=False)
    elif fault == 'invalid_cs':
      options['timeout'] = True
    actual = sd.sm.update_msgs
    delivered_intents = []
    companion = sd.aol_intent_companion
    assert companion.samples.get(BASE) is not None

    def red(t, rows):
      for row in rows:
        if row.which() == 'aolIntentWire':
          if fault == 'missing_pair':
            continue
          delivered_intents.append(int(row.logMonoTime))
        if fault == 'dm' and row.which() == 'driverMonitoringState':
          row = row.as_builder()
          row.driverMonitoringState.alertLevel = 'three'
          row = row.as_reader()
        yield row
    with ExitStack() as interception:
      if fault == 'missing_pair':
        original_receive = fixture.messaging.recv_one_or_none
        interception.enter_context(mock.patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none',
                                               side_effect=lambda sock: None if sock is companion.sock else original_receive(sock)))
      interception.enter_context(mock.patch.object(sd.sm, 'update_msgs', side_effect=lambda t, rows: actual(t, list(red(t, rows)))))
      interception.enter_context(mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02))
      axis, _, command = drive(6, state_stamp=stamp, **options)
    if fault == 'missing_pair':
      assert not delivered_intents
      assert stamp not in companion.samples and stamp not in companion.raw_projections
      assert sd.sm.logMonoTime['aolIntentWire'] < stamp
      assert companion.last_rejection is not None
    assert not axis.longitudinalActive and (not command.longActive)
    assert not axis.lateralActive and (not command.latActive)
    assert not sd.events.contains(fixture.ET.ENABLE)
