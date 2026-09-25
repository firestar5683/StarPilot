from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from opendbc.car.structs import car
from openpilot.cereal import messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car.card import Car
from openpilot.selfdrive.ui.soundd import Soundd
from openpilot.starpilot.aol.intent import AOL_TOGGLE, AolCardIntent, AolSettings
from openpilot.starpilot.aol.runtime import decide_axes
from openpilot.starpilot.aol.wire import INTENT_SERVICE, IntentState, decode_intent, encode_intent
from openpilot.starpilot.audio.axis_alerts import AudibleAlert, AxisAlerts


class AudioFixture:
  def __init__(self):
    self.sm = messaging.SubMaster(['selfdriveState', 'aolAxisState', INTENT_SERVICE])
    self.sound = Soundd.__new__(Soundd)
    self.sound.axis_alerts = AxisAlerts()
    self.sound.update_alert = Mock()
    self.now = 1_000_000_000
    self.sequence = 0

  def publish(self, armed=False, lateral=False, longitudinal=False, native=AudibleAlert.none,
              *, age_ns=0, valid=True, session='card', sequence=None, acknowledged=True, payload=None,
              intent_message=None, enabled=None, pause_longitudinal=False, pause_lateral=False,
              active=False, state_age_ns=0, state_valid=True):
    self.now += 50_000_000
    self.sequence += 1
    stamp = self.now - age_ns
    if intent_message is None:
      intent_message = messaging.new_message(INTENT_SERVICE, 0, valid=valid)
      intent_message.logMonoTime = stamp
      intent_message.aolIntentWire = payload if payload is not None else encode_intent(IntentState(
        session, self.sequence if sequence is None else sequence, stamp, stamp, stamp + 200_000_000,
        False, pause_lateral, pause_longitudinal, True, lateralArmed=armed))
    else:
      self.now = intent_message.logMonoTime + 1_000_000
      stamp = self.now
    message = messaging.new_message('aolAxisState', valid=True)
    message.logMonoTime = stamp
    axis = message.aolAxisState
    axis.sessionId = 'selfdrived'
    axis.sequence = self.sequence
    axis.qualified = True
    axis.nativeAcknowledged = acknowledged
    axis.lateralActive, axis.longitudinalActive = lateral, longitudinal
    axis.desiredLateral, axis.desiredLongitudinal = lateral, longitudinal
    axis.observedMonoTime = stamp
    axis.validUntilMonoTime = stamp + 30_000_000
    state = messaging.new_message('selfdriveState', valid=state_valid)
    state.logMonoTime = self.now - state_age_ns
    state.selfdriveState.alertSound = native
    state.selfdriveState.enabled = longitudinal if enabled is None else enabled
    state.selfdriveState.active = active
    self.sm.update_msgs(self.now / 1e9, [message.as_reader(), state.as_reader(), intent_message.as_reader()])
    with patch('openpilot.selfdrive.ui.soundd.time.monotonic_ns', return_value=self.now):
      self.sound.get_audible_alert(self.sm)
    return self.sound.update_alert.call_args.args[0]


@pytest.fixture
def audio():
  with OpenpilotPrefix():
    yield AudioFixture()


def test_park_lkas_producer_wire_and_sound(audio):
  owner = AolCardIntent(AolSettings(True, 0.0, AOL_TOGGLE, 0, (0, 0, 0), (0, 0, 0)), explicit_latch=True)
  published = {}
  fields = SimpleNamespace(sm=SimpleNamespace(frame=1, all_checks=lambda _: True),
                         pm=SimpleNamespace(send=lambda service, message: published.__setitem__(service, message)),
                         CP=car.CarParams.new_message(), car_params_published=True,
                         slc_replay=False, curve_replay=False, conditional_replay=False,
                         last_actuators_output=car.CarControl.Actuators.new_message(), can_rcv_cum_timeout_counter=0,
                         rk=SimpleNamespace(remaining=0), aol_replay=True, aol_qualified=True, aol_sequence=0,
                         slc_producer_session='card', aol_card_intent=owner, v_cruise_helper=SimpleNamespace(slc_cruise_change=None))
  card = Car.__new__(Car)
  card.__dict__.update(vars(fields))
  cs = car.CarState.new_message(canValid=True, gearShifter=car.CarState.GearShifter.park, standstill=True)
  for pressed, gear, expected in ((None, 'park', AudibleAlert.none), (True, 'park', AudibleAlert.engage),
                                  (True, 'park', AudibleAlert.none), (False, 'park', AudibleAlert.none),
                                  (None, 'drive', AudibleAlert.none), (None, 'park', AudibleAlert.none),
                                  (True, 'park', AudibleAlert.disengage)):
    cs.gearShifter = gear
    cs.buttonEvents = [] if pressed is None else [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=pressed)]
    owner.update(cs)
    Car.state_publish(card, cs, None)
    decoded = decode_intent(published[INTENT_SERVICE].aolIntentWire)
    assert decoded is not None
    assert decoded.lateralArmed == owner.allowed_latch
    assert decoded.allowedLatch == (owner.allowed_latch and gear == 'drive')
    assert audio.publish(intent_message=published[INTENT_SERVICE]) == expected


def test_lateral_activation_without_latch_change_is_silent(audio):
  assert audio.publish() == AudibleAlert.none
  assert audio.publish(armed=True) == AudibleAlert.engage
  for lateral in (True, False, True, False):
    assert audio.publish(armed=True, lateral=lateral) == AudibleAlert.none
  assert audio.publish() == AudibleAlert.disengage


def test_native_latch_revocation_and_one_lkas_rearm_sound(audio):
  owner = AolCardIntent(AolSettings(True, 0, 0, 0, (0, 0, 0), (0, 0, 0)), explicit_latch=True)
  state = car.CarState.new_message(canValid=True, gearShifter=car.CarState.GearShifter.drive)
  owner.update(state, now_ns=100)
  assert audio.publish(armed=owner.allowed_latch) == AudibleAlert.none
  state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
  owner.update(state, now_ns=200)
  assert audio.publish(armed=owner.allowed_latch) == AudibleAlert.engage
  state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=False)]
  owner.update(state, now_ns=300)
  audio.publish(armed=owner.allowed_latch)
  state.buttonEvents = []
  owner.update(state, now_ns=400, native_rejection_ns=350)
  assert audio.publish(armed=owner.allowed_latch) == AudibleAlert.disengage
  state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
  owner.update(state, now_ns=500, native_rejection_ns=350)
  assert owner.allowed_latch
  assert audio.publish(armed=owner.allowed_latch) == AudibleAlert.engage


def test_longitudinal_transitions_without_aol(audio):
  assert audio.publish() == AudibleAlert.none
  assert audio.publish(longitudinal=True) == AudibleAlert.engage
  assert audio.publish(longitudinal=True) == AudibleAlert.none
  assert audio.publish() == AudibleAlert.disengage


@pytest.mark.parametrize('native', [AudibleAlert.warningImmediate, AudibleAlert.warningSoft, AudibleAlert.refuse,
                                   AudibleAlert.prompt, AudibleAlert.engage, AudibleAlert.disengage])
def test_native_alert_wins_without_queued_chime(audio, native):
  audio.publish()
  assert audio.publish(armed=True, native=native) == native
  assert audio.publish(armed=True) == AudibleAlert.none


def test_native_then_axis_ack_is_one_engagement(audio):
  audio.publish()
  assert audio.publish(native=AudibleAlert.engage) == AudibleAlert.engage
  assert audio.publish(longitudinal=True) == AudibleAlert.none
  assert audio.publish(armed=True, longitudinal=True) == AudibleAlert.none


@pytest.mark.parametrize('invalid', [{'age_ns': 31_000_000}, {'age_ns': -1}, {'valid': False}, {'payload': b'invalid'}])
def test_invalid_latch_is_silent_and_recovery_does_not_replay(audio, invalid):
  audio.publish()
  assert audio.publish(armed=True, **invalid) == AudibleAlert.none
  assert audio.publish(armed=True) == AudibleAlert.none
  assert audio.publish() == AudibleAlert.disengage


def test_startup_new_session_and_old_sequence_do_not_chime(audio):
  assert audio.publish(armed=True) == AudibleAlert.none
  assert audio.publish(armed=False, session='new-card') == AudibleAlert.none
  assert audio.publish(armed=True, session='new-card', sequence=1) == AudibleAlert.none
  assert audio.publish(armed=True, session='new-card') == AudibleAlert.engage


def test_runtime_native_pending_permission_and_loss(audio):
  audio.publish()
  cs = car.CarState.new_message(canValid=True, gearShifter=car.CarState.GearShifter.drive, vEgo=20.0)
  for requested, allowed, expected in ((False, False, AudibleAlert.none), (True, True, AudibleAlert.engage),
                                      (True, False, AudibleAlert.disengage)):
    native = SimpleNamespace(requestedLateral=False, requestedLongitudinal=requested,
                             lateralAllowed=False, longitudinalAllowed=allowed)
    result = decide_axes(standard_lateral=False, standard_longitudinal=True,
                         intent=SimpleNamespace(allowedLatch=False, pauseLateral=False, pauseLongitudinal=False),
                         native=native, car_state=cs, initialized=True, model_ready=True,
                         no_entry=False, immediate_disable=False, dm_lockout=False, pause_brake_mps=0.0)
    assert result.native_acknowledged
    assert audio.publish(longitudinal=result.longitudinal_active, acknowledged=result.native_acknowledged) == expected


def test_actuator_ack_does_not_own_engagement_sound(audio):
  audio.publish()
  assert audio.publish(longitudinal=True, enabled=False, acknowledged=False) == AudibleAlert.none


def test_mismatched_payload_timestamp_is_silent(audio):
  audio.publish()
  stamp = audio.now + 50_000_000
  payload = encode_intent(IntentState('card', 2, stamp - 1, stamp, stamp + 200_000_000,
                                       False, False, False, True, lateralArmed=True))
  assert audio.publish(armed=True, payload=payload) == AudibleAlert.none


def test_native_only_subscriber_retains_alert(audio):
  sm = messaging.SubMaster(['selfdriveState'])
  state = messaging.new_message('selfdriveState', valid=True)
  state.selfdriveState.alertSound = AudibleAlert.engage
  sm.update_msgs(audio.now / 1e9, [state.as_reader()])
  audio.sound.get_audible_alert(sm)
  audio.sound.update_alert.assert_called_once_with(AudibleAlert.engage)


def test_output_drop_and_recovery_do_not_sound_when_engagement_is_unchanged(audio):
  audio.publish(enabled=False)
  assert audio.publish(enabled=True, longitudinal=True) == AudibleAlert.engage
  for active, acknowledged in ((False, True), (True, True), (False, False), (True, True)):
    assert audio.publish(enabled=True, longitudinal=active, acknowledged=acknowledged) == AudibleAlert.none
  assert audio.publish(enabled=False) == AudibleAlert.disengage


def test_explicit_longitudinal_pause_and_resume_sound_once(audio):
  audio.publish(enabled=True, longitudinal=True)
  assert audio.publish(enabled=True, pause_longitudinal=True) == AudibleAlert.disengage
  assert audio.publish(enabled=True, pause_longitudinal=True) == AudibleAlert.none
  assert audio.publish(enabled=True, longitudinal=True) == AudibleAlert.engage


@pytest.mark.parametrize('invalid', [{'state_age_ns': 101_000_000}, {'state_age_ns': -1}, {'state_valid': False}])
def test_standard_lateral_stale_state_and_recovery_do_not_replay(audio, invalid):
  audio.publish(active=True, enabled=True)
  assert audio.publish(active=True, enabled=True, **invalid) == AudibleAlert.none
  assert audio.publish(active=True, enabled=True) == AudibleAlert.none
  assert audio.publish(active=True, enabled=True, pause_lateral=True) == AudibleAlert.disengage


def test_explicit_lateral_pause_remains_known_without_standard_state(audio):
  audio.publish(active=True, enabled=True)
  assert audio.publish(active=True, enabled=True, pause_lateral=True, state_valid=False) == AudibleAlert.disengage
  assert audio.publish(active=True, enabled=True, pause_lateral=True) == AudibleAlert.none
