from collections import deque
from types import SimpleNamespace as NS

import pytest

from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.starpilot.controllers.cruise_action import CruiseActionPublisher
from openpilot.starpilot.controllers.mode_actions import ModeActionPublisher, ModeIntent, publish_switchback
from openpilot.starpilot.controllers.tests.test_wheel_actions import Publisher, candidate, services, DRIVE, NOW
from openpilot.starpilot.controllers.wheel_actions import WheelPublisher, WheelConsumer
from openpilot.starpilot.favorites.actions import BOOKMARK, SET_SPEED, TRAFFIC, FORCE_COAST
from openpilot.starpilot.favorites.owner import FavoritesOwner, default_slots
from openpilot.starpilot.ui.onroad_state import OnroadState, SpeedLimitObservation
from openpilot.starpilot.ui.shell import ShellMode


@pytest.fixture
def native_session(tmp_path, monkeypatch):
  from openpilot.starpilot.ui import runtime_app
  from openpilot.selfdrive.ui import ui_state as module
  params = Params(str(tmp_path))
  _, cp = candidate(False)
  sm = services(cp)
  sm['selfdriveState'] = NS(enabled=True)
  status = publish_switchback(None, ModeIntent(DRIVE, False, False), session='b' * 32,
                             sequence=1, now_ns=NOW, source_car_control_ns=NOW)
  sm['slcState'] = status.slcState
  for key in ('selfdriveState', 'slcState'):
    sm.logMonoTime[key], sm.recv_time[key] = NOW, NOW / 1e9
    sm.seen[key] = sm.alive[key] = sm.valid[key] = True
  ui = NS(CP=cp, sm=sm, params=params, has_longitudinal_control=True, personality=0, started_frame=1)
  monkeypatch.setattr(runtime_app, 'ui_state', ui)
  monkeypatch.setattr(runtime_app.time, 'monotonic_ns', lambda: NOW)
  monkeypatch.setattr(module, 'device', NS(awake=True, toggle_screen_off=lambda: True))
  sender = Publisher()
  monkeypatch.setattr(runtime_app, '_slc_action_publisher', lambda: sender)
  session = runtime_app.StarShellSession.__new__(runtime_app.StarShellSession)
  session._mode = ShellMode.ONROAD
  state = OnroadState(True, True, 15, 80, SpeedLimitObservation())
  vars(session)['snapshot'] = lambda *_: NS(onroad=state)
  vars(session)['_favorite_authority'] = lambda: True
  vars(session)['_conditional_favorite_active'] = lambda: False
  session.mode_actions, session.cruise_actions = ModeActionPublisher(), CruiseActionPublisher()
  session._wheel_personality = None
  session._wheel_consumer, session._wheel_pending = WheelConsumer(), deque(maxlen=32)
  session._wheel_sock = object()
  session.slc_actions = None
  calls = []
  session._native_favorite_actions = lambda: session.native_favorite_actions(lambda: calls.append('bookmark') or True,
                                                                           lambda value: calls.append(value), lambda: True)
  session.favorites_owner = FavoritesOwner(params, session._native_favorite_actions, lambda: True)
  return runtime_app, session, ui, sender, calls


def test_actual_favorite_value_callback_reads_units_and_publishes_absolute_receipt(native_session):
  _, session, ui, sender, _ = native_session
  ui.params.put('IsMetric', True, block=True)
  slots = default_slots()
  slots[0].update(enabled=True, key=SET_SPEED, label='Set speed', value=55)
  owner = session.favorites_owner
  owner.save(slots, owner.snapshot().revision)
  request = owner.snapshot().slots[0].request
  assert owner.invoke(request).success
  event = messaging.log_from_bytes(sender.events[-1][1])
  assert str(event.slcAction.kind) == 'cruiseSet'
  assert event.slcAction.controllerCruise.targetSpeedMps == pytest.approx(55 / 3.6)
  vars(session)['_favorite_authority'] = lambda: False
  assert not owner.invoke(owner.snapshot().slots[0].request).success
  assert len(sender.events) == 1


def test_card_receipt_invokes_real_native_bookmark_and_quick_select_callback(native_session, monkeypatch):
  runtime, session, ui, _, calls = native_session
  source, publisher = WheelPublisher(ui.params), Publisher()
  queue = []
  monkeypatch.setattr(runtime.messaging, 'recv_one_or_none', lambda _: queue.pop(0) if queue else None)
  for sequence, code in enumerate((8, 11), start=1):
    ui.params.put('DistanceButtonControl', code, block=True)
    if code == 11:
      owner = session.favorites_owner
      assert owner.configure_index(0, BOOKMARK, owner.snapshot().revision)
    source.publish((('DistanceButtonControl', code),), ui.CP, publisher, now_ns=NOW, drive_id=DRIVE,
                   source_car_ns=NOW, source_control_ns=NOW)
    queue.append(messaging.log_from_bytes(publisher.events[-1][1]))
    session._poll_wheel(NOW)
    assert len(calls) == sequence
  assert calls == ['bookmark', 'bookmark']


def test_actual_native_traffic_and_coast_callbacks_emit_owner_requests(native_session):
  _, session, _, sender, _ = native_session
  actions = session._native_favorite_actions()
  assert actions[TRAFFIC].invoke()
  session.mode_actions.last_ns = 0
  assert actions[FORCE_COAST].invoke()
  assert [str(messaging.log_from_bytes(raw).slcAction.kind) for _, raw in sender.events] == [
    'trafficModeToggle', 'forceCoastToggle']

@pytest.mark.parametrize('vehicle,filtered', [('TOYOTA_PRIUS', True), ('TOYOTA_SIENNA_4TH_GEN', False)])
def test_toyota_default_gap_callback_saves_personality_once(native_session, monkeypatch, vehicle, filtered):
  from opendbc.car import structs
  from opendbc.car.toyota.interface import CarInterface
  from opendbc.car.toyota.values import CAR
  runtime, session, ui, _, _ = native_session
  rack = structs.CarParams.CarFw.new_message(ecu=structs.CarParams.Ecu.eps,
                                            fwVersion=b'8965B47070\x00\x00\x00\x00\x00\x00')
  ui.CP = CarInterface.get_params(getattr(CAR, vehicle), {0: {0x2FF: 4} if filtered else {}, 1: {}, 2: {}},
                                  [rack] if filtered else [], False, False, False)
  ui.has_longitudinal_control = ui.CP.openpilotLongitudinalControl
  ui.personality = 1
  def save_personality(value):
    ui.params.put('LongitudinalPersonality', value, block=True)
    ui.personality = value
    return True
  session._native_favorite_actions = lambda: session.native_favorite_actions(lambda: True, save_personality, lambda: True)
  queue = []
  monkeypatch.setattr(runtime.messaging, 'recv_one_or_none', lambda _: queue.pop(0) if queue else None)
  owner, publisher = WheelPublisher(), Publisher()
  from openpilot.starpilot.controllers.tests.test_wheel_actions import state
  owner.observe(ui.params, ui.CP, state(), now_ns=NOW - 20_000_000, drive_id=DRIVE)
  owner.observe(ui.params, ui.CP, state(True), now_ns=NOW - 10_000_000, drive_id=DRIVE)
  commands = owner.observe(ui.params, ui.CP, state(False), now_ns=NOW, drive_id=DRIVE)
  assert commands == (('DistanceButtonControl', 1),)
  assert owner.suppress_distance_release
  owner.publish(commands, ui.CP, publisher, now_ns=NOW, drive_id=DRIVE, source_car_ns=NOW, source_control_ns=NOW)
  queue.append(messaging.log_from_bytes(publisher.events[-1][1]))
  session._poll_wheel(NOW)
  assert ui.params.get('LongitudinalPersonality') == 0
  session._poll_wheel(NOW)
  assert ui.params.get('LongitudinalPersonality') == 0
