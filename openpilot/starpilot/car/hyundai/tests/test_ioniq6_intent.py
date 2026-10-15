"""Ioniq 6 AOL: full engagement arms AOL, and brake's LONG withdrawal keeps LAT intent."""
from types import SimpleNamespace
from typing import Any

import pytest

from opendbc.car import Bus, structs
from openpilot.cereal import messaging
from openpilot.selfdrive.car.card import Car
from openpilot.selfdrive.car.tests.test_hyundai_aol import candidate
from openpilot.starpilot.aol.intent import AOL_TOGGLE, AolSettings
from openpilot.starpilot.aol.transport_pause import TransportPauseFeedback, _healthy_transport_native, independent_lateral_health
from openpilot.starpilot.aol.wire import PandaSlot, SafetyState, encode_safety
from openpilot.starpilot.car.hyundai.aol import create_intent
from openpilot.starpilot.car.hyundai.ioniq6_intent import Ioniq6CardIntent

ButtonType = structs.CarState.ButtonEvent.Type
NOW = 10_000_000_000


def ioniq6(alt=False):
  _, cp = candidate(alt)
  cp.safetyConfigs[0].safetyParam = 0x8895 if alt else 0x8815
  return cp


def settings(lkas_action=AOL_TOGGLE, enabled=True):
  return AolSettings(enabled, 0.0, lkas_action, 0, (0, 0, 0), (0, 0, 0))


class Drive:
  def __init__(self, intent):
    self.intent = intent
    self.cs = structs.CarState(canValid=True, gearShifter=structs.CarState.GearShifter.drive, vEgo=20.0)
    self.now = NOW
    self.step()

  def step(self, *, engaged=None, cruise=None, buttons=(), standard=None):
    if cruise is not None:
      self.cs.cruiseState.enabled = cruise
    self.cs.buttonEvents = [structs.CarState.ButtonEvent(type=b, pressed=p) for b, p in buttons]
    self.now += 10_000_000
    enabled = engaged if standard is None else standard
    self.intent.update(self.cs, now_ns=self.now, standard_enabled=bool(enabled))
    return self.intent.output(self.cs)[:2]

  def engage(self):
    return self.step(engaged=True, cruise=True)

  def brake(self):
    return self.step(engaged=False, cruise=False)

  def lkas(self, engaged):
    self.step(engaged=engaged, buttons=((ButtonType.lkas, True),))
    return self.step(engaged=engaged, buttons=((ButtonType.lkas, False),))


@pytest.mark.parametrize('alt', [False, True])
def test_qualified_ioniq6_uses_engagement_intent(alt):
  assert isinstance(create_intent(ioniq6(alt), settings()), Ioniq6CardIntent)


def test_full_engagement_arms_aol_so_brake_only_drops_long():
  drive = Drive(create_intent(ioniq6(), settings()))
  assert drive.step(engaged=False) == (False, False)
  assert drive.engage() == (True, False)
  assert drive.brake() == (True, False)
  # LKAS then drops the remaining AOL lateral.
  assert drive.lkas(engaged=False) == (False, True)
  # A fresh SET engagement is LAT and LONG again.
  assert drive.engage() == (True, False)


def test_lkas_in_full_op_pauses_lateral_and_stale_control_does_not_rearm():
  drive = Drive(create_intent(ioniq6(), settings()))
  drive.engage()
  assert drive.lkas(engaged=True) == (False, True)
  # carControl briefly stale while cruise stays engaged is not a new engagement.
  assert drive.step(standard=False) == (False, True)
  assert drive.step(standard=True) == (False, True)
  # Brake keeps the driver's lateral pause; LKAS restores AOL.
  assert drive.brake() == (False, True)
  assert drive.lkas(engaged=False) == (True, False)


@pytest.mark.parametrize('config', ['lkas_not_aol', 'aol_disabled', 'acc_fault', 'can_invalid'])
def test_engagement_does_not_arm_without_lkas_aol(config):
  intent = create_intent(ioniq6(), settings(lkas_action=0 if config == 'lkas_not_aol' else AOL_TOGGLE,
                                             enabled=config != 'aol_disabled'))
  drive = Drive(intent)
  drive.cs.accFaulted = config == 'acc_fault'
  drive.cs.canValid = config != 'can_invalid'
  drive.engage()
  assert not intent.allowed_latch


class Peers:
  def __init__(self, messages):
    self.messages = {m.which(): m for m in messages}
    self.logMonoTime = {n: int(m.logMonoTime) for n, m in self.messages.items()}
    self.seen = self.valid = self.alive = self.updated = dict.fromkeys(self.messages, True)

  def __getitem__(self, name):
    return getattr(self.messages[name], name)


def transport_fixture(*, long_requested=True):
  cp = ioniq6(alt=True)
  config = cp.safetyConfigs[0]
  slots = (PandaSlot(0, 'unit-ioniq', config.safetyModel.raw, config.safetyParam, cp.alternativeExperience, False),)
  # Brake revoked LONG at the Panda; the host has not yet withdrawn its LONG request.
  native = SafetyState(1, True, NOW - 20_000_000, NOW + 180_000_000, config.safetyModel.raw, config.safetyParam,
                       True, False, True, long_requested, 'unit-ioniq', 'unit-session',
                       sourcePandaStatesMonoTime=NOW - 21_000_000, pandaInventory=slots)
  safety = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=native.observedMonoTime)
  safety.aolSafetyWire = encode_safety(native)
  pandas = messaging.new_message('pandaStates', 1, valid=True, logMonoTime=NOW)
  p = pandas.pandaStates[0]
  p.safetyModel, p.safetyParam, p.alternativeExperience = config.safetyModel, config.safetyParam, cp.alternativeExperience
  axis = messaging.new_message('aolAxisState', valid=True, logMonoTime=NOW - 1_000_000)
  a = axis.aolAxisState
  a.sessionId = a.faultSessionId = 'unit-session'
  a.qualified, a.sequence, a.faultReason = True, 2, 'none'
  a.observedMonoTime, a.validUntilMonoTime = axis.logMonoTime, axis.logMonoTime + 30_000_000
  a.sourceCarStateMonoTime = axis.logMonoTime - 1000
  a.desiredLateral = a.lateralActive = a.nativeAcknowledged = True
  events = messaging.new_message('onroadEvents', 1, valid=True, logMonoTime=NOW - 1_000_000)
  events.onroadEvents[0].name = 'pedalPressed'
  events.onroadEvents[0].userDisable = True
  sm = Peers([safety.as_reader(), pandas.as_reader(), axis.as_reader(), events.as_reader()])
  cs = structs.CarState(canValid=True, brakePressed=True, vEgo=13.5, gearShifter=structs.CarState.GearShifter.drive)
  feedback = TransportPauseFeedback(cp)
  # An already observed healthy, acknowledged LAT+LONG baseline one frame earlier.
  feedback.session = native.axisSessionId
  feedback.healthy_feedback_ns = NOW - 10_000_000
  feedback.healthy_native_ns = native.observedMonoTime
  feedback.healthy_inventory = (native.pandaSerial, tuple(s.hardwareSerial for s in slots))
  return cp, cs, sm, native, feedback


def test_brake_long_revoke_window_retains_lateral_intent():
  cp, cs, sm, native, feedback = transport_fixture()
  # Recorded 2026-10-14 drive, 586.87 s: this window used to hard-reset the AOL latch.
  assert _healthy_transport_native(sm, cp, cs, 'unit-session', NOW) is None
  assert independent_lateral_health(sm, cp, cs, 'unit-session', NOW) == native
  assert not feedback.observe(sm, cp, cs, NOW, latched=True, brake_source_ns=NOW - 1000)
  assert feedback.honda_brake_ns == NOW - 1000


@pytest.mark.parametrize('mutation', ['no_source', 'no_brake', 'stale_source', 'no_baseline'])
def test_brake_window_without_its_conditions_still_fails_closed(mutation):
  cp, cs, sm, _, feedback = transport_fixture()
  source = {'no_source': 0, 'stale_source': NOW - 30_000_001}.get(mutation, NOW - 1000)
  cs.brakePressed = mutation != 'no_brake'
  if mutation == 'no_baseline':
    feedback.healthy_feedback_ns = 0
  assert feedback.observe(sm, cp, cs, NOW, latched=True, brake_source_ns=source)
  assert feedback.honda_brake_ns == 0


def test_card_ioniq6_brake_source_reads_tcs():
  cp = ioniq6()
  cs = structs.CarState(canValid=True, brakePressed=True)
  card: Any = Car.__new__(Car)
  card.CP = cp
  parser = SimpleNamespace(vl={'TCS': {'DriverBraking': 1}}, ts_nanos={'TCS': {'DriverBraking': NOW + 9_000_000_000}})
  card.CI = SimpleNamespace(can_parsers={Bus.pt: parser})
  card._aol_can_observation = (cs, NOW - 1000, NOW + 9_000_000_000, NOW + 9_000_001_000)
  assert card.aol_honda_brake_source(cs, NOW) == NOW - 1000
  parser.ts_nanos['TCS']['DriverBraking'] -= 30_000_001
  assert card.aol_honda_brake_source(cs, NOW) == 0
  parser.ts_nanos['TCS']['DriverBraking'] += 30_000_001
  parser.vl['TCS']['DriverBraking'] = 0
  assert card.aol_honda_brake_source(cs, NOW) == 0
