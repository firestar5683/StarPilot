import pytest

from opendbc.car import structs
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.tests.test_preap_stock import params
from opendbc.car.tesla.tests.preap_stream import PreAPStream
from openpilot.cereal import log
from openpilot.selfdrive.car.car_events import CarEvents
from openpilot.selfdrive.selfdrived.events import Events, ET


def decoded(state):
  return structs.CarState.from_bytes(state.to_bytes())


@pytest.mark.parametrize("previous,current,name,text,sound", (
  (False, True, "teslaCCEngaged", "Tesla Cruise Engaged", "engage"),
  (True, False, "teslaCCDisengaged", "Tesla Cruise Disengaged", "disengage"),
))
def test_serialized_stock_edges_reach_actual_alert_consumer(previous, current, name, text, sound):
  cp = params()
  old, state = structs.CarState(), structs.CarState()
  state.canValid = old.canValid = True
  state.cruiseState.enabled, old.cruiseState.enabled = current, previous
  state.teslaStockCruiseEngaged, old.teslaStockCruiseEngaged = current, previous
  with decoded(state) as cs, decoded(old) as prev:
    events = CarEvents(cp).update(cs, prev, structs.CarControl())
    assert getattr(log.OnroadEvent.EventName, name) in events.names
    received = Events()
    received.add_from_msg(events.to_msg())
    alert = next(a for a in received.create_alerts([ET.WARNING]) if a.alert_text_1 == text)
    assert alert.audible_alert == getattr(log.SelfdriveState.AudibleAlert, sound)
    assert cs.cruiseState.enabled == current


@pytest.mark.parametrize("requested,cruise,expected", ((True, 0, True), (True, 1, False), (True, 2, False), (False, 0, False)))
def test_actual_parser_not_armed_condition_and_serialized_alert(requested, cruise, expected):
  cp = params()
  ci, stream = CarInterface(cp), PreAPStream()
  ci.update([])
  prev = structs.CarState()
  for tick in range(1, 75):
    lever = 2 if requested and tick in (61, 71) else 0
    state = ci.update([(1_000_000_000 + tick * 10_000_000, stream.frames(tick, lever=lever, cruise=cruise))])
  with decoded(state) as cs:
    assert cs.teslaStockCruiseNotArmed == expected
    events = CarEvents(cp).update(cs, prev, structs.CarControl())
    assert (log.OnroadEvent.EventName.teslaCCNotArmed in events.names) == expected
    alerts = events.create_alerts([ET.PERMANENT])
    assert any(a.alert_text_1 == "Arm Stock Cruise to Enable Speed Control" for a in alerts) == expected


def test_wrong_safety_profile_cannot_emit_preap_alerts():
  cp = params()
  cp.safetyConfigs[0].safetyModel = 35
  state = structs.CarState()
  state.canValid = state.cruiseState.enabled = state.teslaStockCruiseNotArmed = True
  events = CarEvents(cp).update(state, structs.CarState(), structs.CarControl())
  names = log.OnroadEvent.EventName
  assert not {names.teslaCCEngaged, names.teslaCCDisengaged, names.teslaCCNotArmed}.intersection(events.names)


def test_enabled_to_override_reports_stock_disengage_without_fake_pcm_disable():
  cp = params()
  ci, stream = CarInterface(cp), PreAPStream()
  ci.update([])
  for tick in range(1, 65):
    state = ci.update([(1_000_000_000 + tick * 10_000_000, stream.frames(tick, cruise=2))])
  with decoded(state) as previous:
    state = ci.update([(1_650_000_000, stream.frames(65, cruise=4))])
    with decoded(state) as current:
      assert current.cruiseState.enabled and previous.cruiseState.enabled
      assert previous.teslaStockCruiseEngaged and not current.teslaStockCruiseEngaged
      events = CarEvents(cp).update(current, previous, structs.CarControl())
      assert log.OnroadEvent.EventName.teslaCCDisengaged in events.names
      assert log.OnroadEvent.EventName.pcmDisable not in events.names
