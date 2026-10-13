"""Existing ordinary controls follow the normal soft-disable countdown."""
from contextlib import ExitStack, contextmanager
from dataclasses import replace
from unittest import mock

import pytest

from openpilot.cereal import log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.runtime import current_native
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE
from openpilot.starpilot.aol.tests.test_ordinary_source_availability import settings
from openpilot.starpilot.aol.wire import decode_safety, encode_safety

MODES = ['long_only', 'combined', 'combined_unarmed']


@contextmanager
def callers(mode):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    owners = case._ioniq_availability_callers(full_op=mode != 'lateral_only')
    sd, controls, drive, card, receive = owners
    old, state, command = drive(2, state_stamp=BASE, **settings(mode, BASE, 3))
    assert old.longitudinalActive == (mode != 'lateral_only')
    assert command.longActive == old.longitudinalActive
    assert old.lateralActive == (mode != 'long_only')
    if mode in ('combined', 'lateral_only'):
      assert receive(BASE, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    yield owners, old


def healthy_soft_checkpoint(sd, axis, state, stamp):
  assert sd.rk.lagging and log.OnroadEvent.EventName.selfdrivedLagging in sd.events.names
  assert sd.events.contains(fixture.ET.NO_ENTRY) and sd.events.contains(fixture.ET.SOFT_DISABLE)
  assert not sd.events.contains(fixture.ET.USER_DISABLE) and not sd.events.contains(fixture.ET.IMMEDIATE_DISABLE)
  assert state.enabled and state.active and state.state == log.SelfdriveState.OpenpilotState.softDisabling
  assert sd.state_machine.soft_disable_timer == 300
  assert axis.sourceCarStateMonoTime == stamp and sd.conditional_car_state_valid
  assert axis.observedMonoTime == stamp and axis.validUntilMonoTime == stamp + 30_000_000
  native = current_native(sd.sm, sd.CP, now_ns=stamp, axis_session_id=sd.aol_session_id)
  assert native is not None and native.requestedLongitudinal and native.longitudinalAllowed
  assert not sd.aol_authority_lost and not sd.events.contains(fixture.ET.ENABLE)




@pytest.mark.parametrize('mode', MODES)
def test_expected_established_ordinary_axes_follow_fresh_soft_disable_semantics(mode):
  with callers(mode) as ((sd, _, drive, _, _), _):
    stamp = BASE + 10_000_000
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      axis, state, command = drive(3, state_stamp=stamp, **settings(mode, stamp, 4))
      healthy_soft_checkpoint(sd, axis, state, stamp)
    assert axis.desiredLongitudinal and axis.longitudinalActive and command.longActive
    assert bool(axis.lateralActive) == bool(command.latActive) == (mode != 'long_only')


@pytest.mark.parametrize('mode', MODES)
def test_fresh_lag_countdown_disables_without_long_auto_enable(mode):
  with callers(mode) as ((sd, _, drive, _, _), old):
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      for tick in range(3, 304):
        stamp = BASE + (tick - 2) * 10_000_000
        axis, state, command = drive(tick, state_stamp=stamp, **settings(mode, stamp, tick + 1))
        assert axis.sourceCarStateMonoTime == stamp and axis.validUntilMonoTime == stamp + 30_000_000
        assert not sd.aol_authority_lost and not sd.events.contains(fixture.ET.ENABLE)
        assert sd.state_machine.soft_disable_timer == max(0, 303 - tick)
        assert state.enabled == (tick < 303) and state.active == (tick < 303)
    assert not state.enabled and not state.active and sd.state_machine.soft_disable_timer == 0
    stamp += 10_000_000
    axis, state, command = drive(304, state_stamp=stamp, **settings(mode, stamp, 305))
    assert not state.enabled and not state.active
    assert not axis.desiredLongitudinal and not axis.longitudinalActive and not command.longActive
    assert not sd.events.contains(fixture.ET.ENABLE) and old.validUntilMonoTime < stamp


@pytest.mark.parametrize('mode', MODES)
def test_lag_clear_before_timeout_requires_current_native_long_regrant(mode):
  with callers(mode) as ((sd, _, drive, _, _), old):
    stamp = BASE + 10_000_000
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      drive(3, state_stamp=stamp, **settings(mode, stamp, 4))
    stamp += 10_000_000
    options = settings(mode, stamp, 5)
    options.update(native_request_long=False, long_allowed=False)
    axis, state, command = drive(4, state_stamp=stamp, **options)
    assert state.enabled and state.active and state.state == log.SelfdriveState.OpenpilotState.enabled
    assert axis.desiredLongitudinal and not axis.longitudinalActive and not command.longActive
    assert not sd.events.contains(fixture.ET.ENABLE)
    stamp += 10_000_000
    axis, state, command = drive(5, state_stamp=stamp, **settings(mode, stamp, 6))
    assert state.enabled and axis.longitudinalActive and command.longActive
    assert not sd.events.contains(fixture.ET.ENABLE) and old.validUntilMonoTime <= stamp


def test_independent_lat_only_lag_stays_off_without_ordinary_enable_then_recovers():
  mode = 'lateral_only'
  with callers(mode) as ((sd, _, drive, card, receive), _):
    stamp = BASE + 10_000_000
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      axis, state, command = drive(3, state_stamp=stamp, **settings(mode, stamp, 4))
    assert not state.enabled and not state.active and not axis.lateralActive and not command.latActive
    assert not axis.longitudinalActive and not command.longActive
    assert receive(stamp, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    assert card.aol_card_intent.allowed_latch
    stamp += 10_000_000
    axis, state, command = drive(4, state_stamp=stamp, **settings(mode, stamp, 5))
    assert axis.lateralActive and command.latActive
    assert not state.enabled and not axis.longitudinalActive and not command.longActive
    assert not sd.events.contains(fixture.ET.ENABLE)


@pytest.mark.parametrize('fault', ['native_invalid', 'native_lat_denied', 'native_long_denied',
  'native_session', 'can_invalid', 'permanent_eps', 'dm_three', 'dm_lockout', 'mixed_immediate'])
def test_fresh_lag_does_not_waive_fault_dm_or_native_gates(fault):
  mode = 'combined'
  with callers(mode) as ((sd, _, drive, _, _), _):
    # DM delivery is intercepted at the actual20Hz envelope boundary before consumers run.
    for tick in (3, 4):
      stamp = BASE + (tick - 2) * 10_000_000
      drive(tick, state_stamp=stamp, **settings(mode, stamp, tick + 1))
    stamp = BASE + 30_000_000
    original_update = sd.sm.update_msgs
    delivered = []
    def update(timestamp, messages):
      frames = []
      for message in messages:
        if message.which() == 'driverMonitoringState' and fault in ('dm_three', 'dm_lockout'):
          message = message.as_builder()
          message.driverMonitoringState.activePolicy = 'vision'
          if fault == 'dm_three':
            message.driverMonitoringState.alertLevel = 'three'
          else:
            message.driverMonitoringState.lockout = True
          delivered.append(int(message.logMonoTime))
          message = message.as_reader()
        elif message.which() == 'aolSafetyWire' and fault == 'native_session':
          message = message.as_builder()
          message.aolSafetyWire = encode_safety(replace(decode_safety(message.aolSafetyWire), axisSessionId='other-session'))
          message = message.as_reader()
        frames.append(message)
      return original_update(timestamp, frames)
    observed = fixture.car_state()
    observed.canValid = fault != 'can_invalid'
    observed.steerFaultPermanent = fault == 'permanent_eps'
    options = settings(mode, stamp, 6)
    options.update(native_valid=fault != 'native_invalid', allowed=fault != 'native_lat_denied',
                   long_allowed=fault != 'native_long_denied')
    original_events = sd.update_events
    def events(cs):
      result = original_events(cs)
      if fault == 'mixed_immediate':
        sd.events.add(log.OnroadEvent.EventName.controlsMismatch)
      return result
    with mock.patch.object(sd.sm, 'update_msgs', side_effect=update), \
         mock.patch.object(sd, 'update_events', side_effect=events), \
         mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      axis, _, command = drive(5, state_stamp=stamp, observed_state=observed, **options)
    if fault in ('dm_three', 'dm_lockout'):
      assert delivered == [stamp] and sd.aol_dm_lateral_inhibit
    assert not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive
    assert not sd.events.contains(fixture.ET.ENABLE)
