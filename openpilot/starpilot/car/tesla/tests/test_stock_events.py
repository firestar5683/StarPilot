from types import SimpleNamespace

import pytest

from opendbc.car import structs
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.tests.test_preap_stock import params
from opendbc.car.tesla.tests.preap_stream import PreAPStream
from openpilot.cereal import log
from openpilot.selfdrive.selfdrived.events import Events, ET
from openpilot.starpilot.car.tesla.stock_events import StockCruiseConsumer, publish_stock_status


class Capture:
  def send(self, service, message):
    assert service == 'slcCruiseEvent'
    self.raw = message.to_bytes()


class Sources(dict):
  valid = {'carState': True}
  alive = {'carState': True}


def receive(cp, internal, state, *, previous=False, sequence=1, session='card', stamp=20_000_000_000):
  publisher = Capture()
  publish_stock_status(publisher, cp, internal, session=session, sequence=sequence, car_state_stamp=stamp, valid=True)
  consumer = StockCruiseConsumer(cp)
  consumer.session, consumer.previous = session, previous
  sm = Sources(carState=state)
  sm.logMonoTime = {'carState': stamp}
  events = Events()
  with log.Event.from_bytes(publisher.raw) as envelope:
    consumer.update(events, sm, envelope=envelope, now_ns=stamp, session=session)
  return events


@pytest.mark.parametrize('previous,current,name,text,sound', (
  (False, True, 'teslaCCEngaged', 'Tesla Cruise Engaged', 'engage'),
  (True, False, 'teslaCCDisengaged', 'Tesla Cruise Disengaged', 'disengage'),
))
def test_serialized_stock_edges_reach_actual_alert_consumer(previous, current, name, text, sound):
  cp = params()
  state = structs.CarState(canValid=True)
  internal = SimpleNamespace(di_cruise_state='ENABLED' if current else 'OVERRIDE', cruiseEnabled=False, enableLongControl=False)
  events = receive(cp, internal, state, previous=previous)
  assert getattr(log.OnroadEvent.EventName, name) in events.names
  alerts = events.create_alerts([ET.WARNING])
  alert = next(a for a in alerts if a.alert_text_1 == text)
  assert alert.audible_alert == getattr(log.SelfdriveState.AudibleAlert, sound)


@pytest.mark.parametrize('requested,cruise,expected', ((True, 0, True), (True, 1, False), (True, 2, False), (False, 0, False)))
def test_actual_parser_not_armed_condition_and_serialized_alert(requested, cruise, expected):
  cp = params()
  ci, stream = CarInterface(cp), PreAPStream()
  ci.update([])
  for tick in range(1, 75):
    lever = 2 if requested and tick in (61, 71) else 0
    state = ci.update([(1_000_000_000 + tick * 10_000_000, stream.frames(tick, lever=lever, cruise=cruise))])
  events = receive(cp, ci.CS.preap, state)
  assert (log.OnroadEvent.EventName.teslaCCNotArmed in events.names) == expected
  assert any(a.alert_text_1 == 'Arm Stock Cruise to Enable Speed Control' for a in events.create_alerts([ET.PERMANENT])) == expected


def test_enabled_to_override_reports_disengage_without_fake_pcm_disable():
  cp = params()
  ci, stream = CarInterface(cp), PreAPStream()
  ci.update([])
  for tick in range(1, 65):
    ci.update([(1_000_000_000 + tick * 10_000_000, stream.frames(tick, cruise=2))])
  current = ci.update([(1_650_000_000, stream.frames(65, cruise=4))])
  assert current.cruiseState.enabled
  events = receive(cp, ci.CS.preap, current, previous=True)
  assert log.OnroadEvent.EventName.teslaCCDisengaged in events.names
  assert log.OnroadEvent.EventName.pcmDisable not in events.names


@pytest.mark.parametrize('mutation', ('invalid', 'wrong_cp', 'wrong_session', 'wrong_frame', 'expired', 'replay', 'can_error'))
def test_transport_rejects_unbound_or_stale_stock_receipt(mutation):
  cp = params()
  state = structs.CarState(canValid=True)
  publisher = Capture()
  stamp = 20_000_000_000
  publish_stock_status(publisher, cp, SimpleNamespace(di_cruise_state='ENABLED', cruiseEnabled=False, enableLongControl=False),
                       session='card', sequence=1, car_state_stamp=stamp, valid=True)
  consumer = StockCruiseConsumer(cp)
  sm = Sources(carState=state)
  sm.logMonoTime = {'carState': stamp}
  with log.Event.from_bytes(publisher.raw) as decoded:
    envelope = decoded.as_builder()
  session, now = 'card', stamp
  if mutation == 'invalid':
    envelope.valid = False
  elif mutation == 'wrong_cp':
    envelope.slcCruiseEvent.teslaStockCruise.cpFingerprint = 'wrong'
  elif mutation == 'wrong_session':
    session = 'other'
  elif mutation == 'wrong_frame':
    sm.logMonoTime['carState'] += 1
  elif mutation == 'expired':
    now += 100_000_001
  elif mutation == 'replay':
    consumer.session, consumer.sequence = 'card', 1
  elif mutation == 'can_error':
    state.canValid = False
  events = Events()
  consumer.update(events, sm, envelope=envelope.as_reader(), now_ns=now, session=session)
  assert not events.names


def test_actual_card_publisher_socket_reaches_stock_alert_consumer(monkeypatch):
  import time
  from openpilot.cereal import messaging
  from opendbc.car.tesla.tests.test_preap_startup import exercise_startup
  from opendbc.car.tesla.values import CAR

  def probe(card, ci, controls, saved):
    consumer = StockCruiseConsumer(card.CP)
    subscriber = messaging.sub_sock('carState', timeout=100, conflate=True)
    stream = PreAPStream()
    ci.update([])
    for tick in range(1, 65):
      state = ci.update([(1_000_000_000 + tick * 10_000_000, stream.frames(tick, cruise=1))])
    assert state.canValid and not state.cruiseState.enabled
    tick = 64
    for cruise, expected in ((2, log.OnroadEvent.EventName.teslaCCEngaged),
                             (4, log.OnroadEvent.EventName.teslaCCDisengaged)):
      observed = False
      for _ in range(30):
        tick += 1
        state = ci.update([(1_000_000_000 + tick * 10_000_000, stream.frames(tick, cruise=cruise))])
        card.state_publish(state, None)
        received = messaging.recv_one(subscriber)
        if received is None:
          time.sleep(0.01)
          continue
        sm = Sources(carState=received.carState)
        sm.logMonoTime = {'carState': received.logMonoTime}
        events = Events()
        consumer.poll(events, sm, now_ns=received.logMonoTime, session=card.slc_producer_session)
        if expected in events.names:
          observed = True
          break
        time.sleep(0.01)
      assert observed, (cruise, expected)
      if cruise == 4:
        assert state.cruiseState.enabled
        assert log.OnroadEvent.EventName.pcmDisable not in events.names

  exercise_startup(CAR.TESLA_MODEL_S_PREAP, False, False, False, monkeypatch, probe=probe)
