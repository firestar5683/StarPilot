from contextlib import ExitStack
import os
from unittest import mock

import pytest

from openpilot.cereal import log
from openpilot.selfdrive.selfdrived.events import EVENTS, ET, EventName
from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import callers
from openpilot.starpilot.aol.tests.test_ioniq_availability import car_state


@pytest.mark.parametrize('family', ['gm', 'toyota'])
@pytest.mark.parametrize('full', [False, True])
@pytest.mark.parametrize('vision', [False, True])
def test_actual_armed_dm_escalation_retains_lateral_and_drops_long(family, full, vision):
  with ExitStack() as cleanup:
    sd, _, drive, card, receive = callers(cleanup, family, not full)
    values = {'level': 'three', 'lockout': False}
    original = sd.update_events

    def dm_events(state):
      dm = sd.sm['driverMonitoringState'].as_builder()
      dm.alertLevel = values['level']
      dm.activePolicy = 'vision' if vision else 'wheeltouch'
      dm.lockout = values['lockout']
      sd.sm.data['driverMonitoringState'] = dm.as_reader()
      return original(state)

    cleanup.enter_context(mock.patch.object(sd, 'update_events', side_effect=dm_events))
    for tick, level, locked in ((2, 'one', False), (3, 'two', False), (4, 'three', False),
                                (5, 'three', True), (6, 'none', False)):
      values.update(level=level, lockout=locked)
      axis, _, command = drive(tick, native_request_long=full if tick < 4 else False)
      assert axis.lateralActive and command.latActive
      assert receive(10_000_000_000 + tick * 10_000_000)
      assert card.aol_card_intent.allowed_latch
      if tick >= 4:
        assert not axis.desiredLongitudinal and not command.longActive and not sd.enabled
      if level == 'three':
        event = EventName.driverDistracted3 if vision else EventName.driverUnresponsive3
        assert event in sd.events.names
        alert = EVENTS[event][ET.PERMANENT]
        assert alert.audible_alert == log.SelfdriveState.AudibleAlert.warningImmediate
        assert alert.alert_status == log.SelfdriveState.AlertStatus.critical
    assert not sd.enabled and not command.longActive


@pytest.mark.parametrize('fault', ['unarmed', 'native_denied', 'permanent', 'stale_source'])
def test_dm_does_not_grant_lateral_to_otherwise_ineligible_callers(fault):
  with ExitStack() as cleanup:
    sd, _, drive, _, _ = callers(cleanup, 'toyota', True)
    original = sd.update_events

    def red_events(state):
      dm = sd.sm['driverMonitoringState'].as_builder()
      dm.alertLevel = 'three'
      sd.sm.data['driverMonitoringState'] = dm.as_reader()
      return original(state)

    cleanup.enter_context(mock.patch.object(sd, 'update_events', side_effect=red_events))
    state = car_state()
    if fault == 'permanent':
      state.steerFaultPermanent = True
    options = {'observed_state': state, 'native_request_long': False}
    if fault == 'unarmed':
      options['latched'] = False
    elif fault == 'native_denied':
      options['allowed'] = False
    elif fault == 'stale_source':
      options['state_stamp'] = 10_000_000_000
    axis, _, command = drive(5, **options)
    assert not axis.lateralActive and not command.latActive and not command.longActive


@pytest.mark.parametrize('always_only', [False, True])
def test_dm_lockout_alone_keeps_prior_lateral_but_requires_new_long_engagement(always_only):
  with ExitStack() as cleanup:
    sd, _, drive, _, _ = callers(cleanup, 'gm', False)
    original = sd.update_events
    locked = [True]

    def events(state):
      dm = sd.sm['driverMonitoringState'].as_builder()
      dm.alertLevel = 'none'
      dm.lockout = locked[0] and not always_only
      dm.alwaysOnLockout = locked[0] and always_only
      sd.sm.data['driverMonitoringState'] = dm.as_reader()
      return original(state)

    cleanup.enter_context(mock.patch.object(sd, 'update_events', side_effect=events))
    axis, _, command = drive(2)
    assert axis.lateralActive and command.latActive
    assert not sd.enabled and not axis.desiredLongitudinal and not command.longActive
    assert EventName.tooDistracted in sd.events.names
    locked[0] = False
    axis, _, command = drive(3, native_request_long=False)
    assert axis.lateralActive and not sd.enabled and not command.longActive


def test_first_red_admission_cannot_start_previously_unaccepted_lateral():
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import honda_family_case
  with ExitStack() as cleanup:
    cleanup.enter_context(OpenpilotPrefix())
    cleanup.enter_context(mock.patch.dict(os.environ, {'SIMULATION': '0', 'AOL_REPLAY_RUNTIME': '1'}))
    family = honda_family_case('honda', True)
    cleanup.callback(family.doCleanups)
    sd, _, drive = family._authority_callers(False, cp=family.family_cp.as_builder(), genuine_events=True)
    original = sd.update_events

    def events(state):
      dm = sd.sm['driverMonitoringState'].as_builder()
      dm.alertLevel = 'three'
      sd.sm.data['driverMonitoringState'] = dm.as_reader()
      return original(state)

    cleanup.enter_context(mock.patch.object(sd, 'update_events', side_effect=events))
    axis, _, command = drive(0, latched=True, native_request_long=False)
    assert not axis.lateralActive and not command.latActive and not command.longActive
    assert not getattr(sd, 'aol_dm_retained_owner', None)
