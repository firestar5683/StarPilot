import pytest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import BOLT_CC_WORDS, CAR, is_bolt_cc_profile
from openpilot.cereal import log
from openpilot.selfdrive.car.car_events import CarEvents
from openpilot.selfdrive.selfdrived.events import EVENTS, ET, Events
from openpilot.selfdrive.selfdrived.state import StateMachine
from openpilot.starpilot.aol.intent import disarming_fault
from openpilot.starpilot.car.events import event_rules

Gear = structs.CarState.GearShifter
Name = log.OnroadEvent.EventName
PROFILES = [(identity, removed, word) for identity, words in BOLT_CC_WORDS.items()
            for removed, word in enumerate(words)]


def params(identity, removed=False):
  fingerprint = gen_empty_fingerprint()
  if not removed:
    fingerprint[2][0x180] = 4
  return CarInterface.get_params(identity, fingerprint, [], False, False, False)


def state(gear, *, enable=False):
  cs = structs.CarState(gearShifter=gear, vEgo=20.0, canValid=True, buttonEnable=enable)
  cs.cruiseState.available = True
  return cs


def events_for(cp, cs, previous):
  produced = CarEvents(cp).update(cs, previous, structs.CarControl())
  received = Events(event_rules(cp))
  received.add_from_msg(produced.to_msg())
  return produced, received


@pytest.mark.parametrize('identity,removed,word', PROFILES)
@pytest.mark.parametrize('gear', (Gear.manumatic, Gear.unknown, Gear.park, Gear.neutral, Gear.reverse, Gear.sport, Gear.brake, Gear.eco))
def test_checked_bolt_unsupported_gear_blocks_entry_and_disables_immediately(identity, removed, word, gear):
  cp = params(identity, removed)
  assert is_bolt_cc_profile(cp)
  assert cp.safetyConfigs[0].safetyParam == word
  previous = state(Gear.low)
  current = state(gear, enable=True)
  produced, received = events_for(cp, current, previous)
  for events in (produced, received):
    assert Name.wrongGear in events.names
    assert events.contains(ET.NO_ENTRY)
    assert events.contains(ET.USER_DISABLE)
    assert events.contains(ET.SOFT_DISABLE)
    message = next(event for event in events.to_msg() if event.name == Name.wrongGear)
    assert message.noEntry and message.userDisable and message.softDisable and not message.immediateDisable
    alerts = events.create_alerts([ET.NO_ENTRY, ET.USER_DISABLE])
    assert any('Gear not D' in (alert.alert_text_1, alert.alert_text_2) for alert in alerts)
    assert disarming_fault(events.to_msg(), current) == (gear == Gear.unknown)
  machine = StateMachine()
  assert not machine.update(received)[0]
  _, allowed = events_for(cp, previous, state(Gear.drive))
  allowed.add(Name.buttonEnable)
  assert machine.update(allowed)[0]
  assert not machine.update(received)[0]
  assert machine.state == log.SelfdriveState.OpenpilotState.disabled
  assert ET.USER_DISABLE in machine.current_alert_types
  assert ET.SOFT_DISABLE not in machine.current_alert_types
  _, recovered = events_for(cp, previous, current)
  assert not machine.update(recovered)[0]
  recovered.add(Name.buttonEnable)
  assert machine.update(recovered)[0]


@pytest.mark.parametrize('identity,removed,word', PROFILES)
@pytest.mark.parametrize('gear', (Gear.drive, Gear.low))
def test_checked_bolt_supported_gears_are_unchanged(identity, removed, word, gear):
  cp = params(identity, removed)
  produced, received = events_for(cp, state(gear), state(Gear.drive))
  assert Name.wrongGear not in produced.names
  assert Name.wrongGear not in received.names


@pytest.mark.parametrize('identity', (CAR.CHEVROLET_VOLT_CC, CAR.CHEVROLET_VOLT, CAR.CHEVROLET_BOLT_EUV))
def test_other_actual_gm_factories_keep_manumatic_admission(identity):
  cp = params(identity)
  assert not is_bolt_cc_profile(cp)
  assert event_rules(cp) == {}
  produced, received = events_for(cp, state(Gear.manumatic), state(Gear.drive))
  assert Name.wrongGear not in produced.names
  assert Name.wrongGear not in received.names


def test_rules_are_instance_local_and_wrong_profile_cannot_change_global_classification():
  cp = params(CAR.CHEVROLET_BOLT_CC_2018_2021)
  rules = event_rules(cp)
  scoped, ordinary = Events(rules), Events()
  scoped.add(Name.wrongGear)
  ordinary.add(Name.wrongGear)
  assert scoped.contains(ET.USER_DISABLE)
  assert ordinary.contains(ET.SOFT_DISABLE) and not ordinary.contains(ET.USER_DISABLE)
  assert ET.USER_DISABLE not in EVENTS[Name.wrongGear]
  altered = structs.CarParams.new_message(**cp.to_dict())
  altered.safetyConfigs[0].safetyParam = 4
  assert event_rules(altered) == {}
  scoped.clear()
  assert not scoped.contains(ET.USER_DISABLE)


def test_pedal_factory_has_no_scoped_gear_rules():
  fingerprint = gen_empty_fingerprint()
  fingerprint[0][0x201] = 6
  fingerprint[2][0x180] = 4
  cp = CarInterface.get_params(CAR.CHEVROLET_BOLT_CC_2018_2021, fingerprint, [], False, False, False)
  assert not is_bolt_cc_profile(cp)
  assert event_rules(cp) == {}


def test_unaffected_volt_reverse_pauses_legacy_aol_output_without_clearing_intent():
  from openpilot.starpilot.aol.intent import AolCardIntent, AolSettings
  cp = params(CAR.CHEVROLET_VOLT_CC)
  owner = AolCardIntent(AolSettings(True, 0.0, 0, 0, (0, 0, 0), (0, 0, 0)))
  drive = state(Gear.drive)
  owner.update(drive)
  assert owner.allowed_latch
  reverse = state(Gear.reverse)
  _, events = events_for(cp, reverse, drive)
  assert Name.reverseGear in events.names
  assert not disarming_fault(events.to_msg(), reverse)
  owner.update(reverse, fault_active=disarming_fault(events.to_msg(), reverse))
  assert owner.allowed_latch
  assert not owner.output(reverse)[0]
  owner.update(drive)
  assert owner.allowed_latch
  assert owner.output(drive)[0]
