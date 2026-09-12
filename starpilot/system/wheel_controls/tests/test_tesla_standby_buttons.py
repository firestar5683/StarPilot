"""Decode real Tesla DBC frames; no CAN sockets or transmitters are opened."""
import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from cereal import car, log
from opendbc.can import CANPacker
from opendbc.car.tesla.values import CAR
from openpilot.starpilot.system.wheel_controls import wheel_controlsd
from test_wheel_controlsd import FakeParams


def observer_module():
  path = Path(__file__).resolve().parents[1] / "tesla_standby_buttons.py"
  assert path.exists(), "The passive Tesla standby button observer is not implemented"
  return importlib.import_module("openpilot.starpilot.system.wheel_controls.tesla_standby_buttons")


@pytest.fixture
def observer():
  return observer_module().TeslaStandbyButtonObserver("tesla_model3_party")


def packet(timestamp, *pressed_values, bus=0, valid=True, address=None):
  packer = CANPacker("tesla_model3_party")
  event = log.Event.new_message(logMonoTime=timestamp, valid=valid)
  event.init("can", len(pressed_values))
  for frame, pressed in zip(event.can, pressed_values, strict=True):
    addr, data, src = packer.make_can_msg("UI_warning", bus, {"scrollWheelPressed": pressed})
    frame.address, frame.dat, frame.src = addr if address is None else address, data, src
  return event


@pytest.mark.parametrize("model", [CAR.TESLA_MODEL_3, CAR.TESLA_MODEL_Y])
def test_only_supported_tesla_fingerprints_select_existing_party_dbc(model):
  cp = car.CarParams.new_message(brand="tesla", carFingerprint=model.value)
  assert observer_module().tesla_button_dbc(cp) == "tesla_model3_party"
  cp.brand = "toyota"
  assert observer_module().tesla_button_dbc(cp) is None
  cp.brand, cp.carFingerprint = "tesla", CAR.TESLA_MODEL_S_PREAP.value
  assert observer_module().tesla_button_dbc(cp) is None


def test_first_held_sample_seeds_then_only_new_presses_emit_original_timestamp(observer):
  assert observer.update([packet(100, 1)], 100) == 0
  assert observer.update([packet(200, 1)], 200) == 0
  assert observer.update([packet(300, 0)], 300) == 0
  assert observer.update([packet(400, 1)], 500) == 400
  assert observer.update([packet(600, 1), packet(700, 0)], 800) == 0


def test_press_and_release_in_one_received_packet_are_not_lost(observer):
  assert observer.update([packet(100, 0)], 100) == 0
  assert observer.update([packet(200, 1, 0)], 250) == 200
  assert observer.update([packet(300, 1)], 350) == 300


def test_wrong_bus_invalid_unrelated_truncated_and_future_messages_do_not_wake(observer):
  assert observer.update([packet(100, 0)], 100) == 0
  assert observer.update([packet(200, 1, bus=2)], 300) == 0
  assert observer.update([packet(300, 1, valid=False)], 400) == 0
  assert observer.update([packet(400, 1, address=0x312)], 500) == 0
  assert observer.update([packet(600, 1)], 500) == 0
  truncated = packet(600, 1)
  truncated.can[0].dat = truncated.can[0].dat[:2]
  assert observer.update([truncated], 700) == 0
  assert observer.update([packet(800, 1)], 900) == 800


def test_stale_gap_reseeds_held_state_instead_of_waking(observer):
  assert observer.update([packet(100, 0)], 100) == 0
  assert observer.update([], 2_000_000_100) == 0
  assert observer.update([packet(2_000_000_200, 1)], 2_000_000_300) == 0
  assert observer.update([packet(2_000_000_400, 0), packet(2_000_000_500, 1)], 2_000_000_600) == 2_000_000_500


def test_old_packets_never_replay_a_button_press(observer):
  assert observer.update([packet(100, 0), packet(200, 1)], 300) == 200
  assert observer.update([packet(100, 0), packet(200, 1)], 400) == 0
  assert observer.update([packet(500, 0)], 500) == 0
  assert observer.update([packet(600, 1)], 2_000_000_600) == 0
  assert observer.update([packet(2_000_000_700, 1)], 2_000_000_800) == 0


@pytest.fixture
def daemon_subscription(monkeypatch):
  params = FakeParams({"ScreenManagement": True, "StandbyMode": True, "StandbyWakeButton": True,
                       "IsOnroad": True, "CarParams": car.CarParams.new_message(
                         brand="tesla", carFingerprint=CAR.TESLA_MODEL_3.value).to_bytes()})
  memory = FakeParams()
  daemon = wheel_controlsd.WheelControlsDaemon(params, memory)
  subscriptions, queued, drains = [], [], []

  def subscribe(endpoint, **kwargs):
    if endpoint == "carState":
      assert kwargs == {"conflate": False}
      return "carState-subscription"
    assert endpoint == "can"
    sock = object()
    subscriptions.append(sock)
    return sock

  def drain(sock, wait_for_one=False):
    assert wait_for_one is False
    if sock == "carState-subscription":
      return []
    drains.append(sock)
    messages, queued[:] = list(queued), []
    return messages

  messaging = SimpleNamespace(sub_sock=subscribe, drain_sock=drain)
  import cereal
  monkeypatch.setitem(sys.modules, "cereal.messaging", messaging)
  monkeypatch.setattr(cereal, "messaging", messaging, raising=False)
  monkeypatch.setattr(wheel_controlsd.time, "monotonic_ns", lambda: 1_000_000_000)
  monkeypatch.setattr(wheel_controlsd.time, "clock_gettime_ns", lambda _clock: 1_000_000_000)
  yield daemon, params, memory, subscriptions, queued, drains
  daemon.close()


def test_daemon_opens_can_only_for_enabled_onroad_supported_tesla_and_reseeds_changes(daemon_subscription):
  daemon, params, memory, subscriptions, queued, drains = daemon_subscription
  configure = getattr(daemon, "_configure_tesla_buttons", None)
  assert callable(configure), "The passive Tesla subscription is not connected to the daemon"
  params.put_bool("StandbyWakeButton", False)
  configure()
  assert subscriptions == []
  params.put_bool("StandbyWakeButton", True)
  params.put_bool("IsOnroad", False)
  configure()
  assert subscriptions == []
  params.put_bool("IsOnroad", True)
  configure()
  configure()
  assert len(subscriptions) == 1
  queued[:] = [packet(100, 0), packet(200, 1)]
  daemon._poll_tesla_buttons()
  assert memory.get_int("StandbyButtonPressTime") == 200

  params.put_bool("StandbyMode", False)
  configure()
  daemon._poll_tesla_buttons()
  assert len(drains) == 1
  params.put_bool("StandbyMode", True)
  configure()
  queued[:] = [packet(300, 1)]
  daemon._poll_tesla_buttons()
  assert len(subscriptions) == 2
  assert memory.get_int("StandbyButtonPressTime") == 200

  params.put("CarParams", car.CarParams.new_message(brand="tesla", carFingerprint=CAR.TESLA_MODEL_Y.value).to_bytes())
  configure()
  queued[:] = [packet(400, 1)]
  daemon._poll_tesla_buttons()
  assert len(subscriptions) == 3
  assert memory.get_int("StandbyButtonPressTime") == 200
  params.put("CarParams", car.CarParams.new_message(brand="toyota", carFingerprint="unsupported").to_bytes())
  configure()
  daemon._poll_tesla_buttons()
  assert len(subscriptions) == 3
  assert len(drains) == 3


def test_daemon_run_loop_publishes_passive_tesla_press_without_external_inputs(daemon_subscription, monkeypatch):
  daemon, _params, memory, subscriptions, queued, _drains = daemon_subscription
  queued[:] = [packet(100, 0), packet(200, 1)]
  # Only hardware enumeration and the blocking selector are replaced; run/configure/poll stay real.
  monkeypatch.setattr(daemon, "_scan_devices", lambda: None)
  selections = iter([[]])
  monkeypatch.setattr(daemon.selector, "select", lambda timeout: next(selections))
  with pytest.raises(StopIteration):
    daemon.run()
  assert memory.get_int("StandbyButtonPressTime") == 200
  assert len(subscriptions) == 1


def test_can_boot_clock_is_converted_to_ui_monotonic_clock_after_suspend(daemon_subscription, monkeypatch):
  daemon, _params, memory, _subscriptions, queued, _drains = daemon_subscription
  daemon._configure_tesla_buttons()
  monkeypatch.setattr(wheel_controlsd.time, "clock_gettime_ns", lambda _clock: 6_000_000_000)
  queued[:] = [packet(5_000_000_100, 0), packet(5_000_000_200, 1)]
  daemon._poll_tesla_buttons()
  assert memory.get_int("StandbyButtonPressTime") == 200
