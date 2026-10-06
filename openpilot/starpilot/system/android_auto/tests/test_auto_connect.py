import json
import socket
import threading
import time

import pytest

from openpilot.starpilot.system.android_auto import auto_connect
from openpilot.starpilot.system.android_auto.auto_connect import AutoConnectPolicy
from openpilot.starpilot.system.android_auto.bluez_phone import address_from_path
from openpilot.starpilot.system.android_auto.tests.fake_head_unit import FakeHeadUnit, make_identity, rfcomm_head_unit
from openpilot.starpilot.system.android_auto.tests.test_android_auto import make_supervisor

CAR = "AA:BB:CC:DD:EE:01"


@pytest.fixture(scope="module")
def identity(tmp_path_factory):
  return make_identity(tmp_path_factory.mktemp("identity"))


def decide(policy, now, onroad=False, car_link=False, ready=True, running=False, enabled=True):
  return policy.decide(now, enabled=enabled, onroad=onroad, car_link=car_link, ready=ready, running=running)


# -------------------------------------------------------------------- policy

def test_policy_starts_when_car_present_and_ready():
  policy = AutoConnectPolicy()
  assert decide(policy, 0, onroad=False) is None
  assert decide(policy, 1, onroad=True, ready=False) is None      # Bluetooth still starting
  assert decide(policy, 2, onroad=True) == "start"
  assert decide(AutoConnectPolicy(), 0, car_link=True) == "start"  # the car reached the comma while offroad
  assert decide(AutoConnectPolicy(), 0, onroad=True, enabled=False) is None


def test_policy_stops_after_car_gone():
  policy = AutoConnectPolicy()
  assert decide(policy, 0, onroad=True, running=True) is None
  assert decide(policy, 10, running=True) is None                # ignition off: grace period starts
  assert decide(policy, 10 + auto_connect.STOP_AFTER - 1, running=True) is None
  assert decide(policy, 20, car_link=True, running=True) is None  # car link seen again: timer resets
  assert decide(policy, 21, running=True) is None
  assert decide(policy, 21 + auto_connect.STOP_AFTER, running=True) == "stop"
  assert decide(policy, 100) is None                             # stopped, car still gone: no restart


def test_policy_leaves_sessions_that_never_saw_the_car():
  policy = AutoConnectPolicy()
  for now in range(0, 300, 10):
    assert decide(policy, now, running=True) is None


def test_policy_manual_stop_holds_until_next_drive():
  policy = AutoConnectPolicy()
  assert decide(policy, 0, onroad=True) == "start"
  policy.manual_stop(running=True)
  assert decide(policy, 1, onroad=True) is None
  assert decide(policy, 2, onroad=True, car_link=True) is None
  assert decide(policy, 3) is None                               # ignition off
  assert decide(policy, 4, onroad=True) == "start"               # next drive


def test_policy_manual_start_clears_hold_and_idle_stop_does_not_hold():
  policy = AutoConnectPolicy()
  policy.manual_stop(running=False)
  assert decide(policy, 0, onroad=True) == "start"
  policy.manual_stop(running=True)
  policy.manual_start()
  assert decide(policy, 1, onroad=True) == "start"


def test_policy_waits_after_refused_start():
  policy = AutoConnectPolicy()
  policy.start_refused(0)
  assert decide(policy, 1, onroad=True) is None
  assert decide(policy, auto_connect.START_REFUSED_WAIT, onroad=True) == "start"


# ----------------------------------------------------------------- supervisor

def test_address_from_path():
  assert address_from_path("/org/bluez/hci0/dev_aa_bb_cc_dd_ee_01") == CAR


def auto_supervisor(identity, tmp_path, monkeypatch, onroad):
  sup, _ = make_supervisor(identity, tmp_path, monkeypatch, lambda *a, **k: socket.socketpair()[0])
  sup._onroad = lambda: onroad["value"]
  starts = []
  alive = {"value": False}
  monkeypatch.setattr(sup, "start", lambda trigger="manual": (starts.append(trigger), alive.update(value=True)))
  monkeypatch.setattr(sup, "stop", lambda *a, **k: alive.update(value=False))
  monkeypatch.setattr(sup, "_session_alive", lambda: alive["value"])
  return sup, starts, alive


def test_supervisor_auto_starts_on_ignition_and_stops_when_car_gone(identity, tmp_path, monkeypatch):
  onroad = {"value": False}
  sup, starts, alive = auto_supervisor(identity, tmp_path, monkeypatch, onroad)
  bluez = sup._phone()
  assert bluez.trusted == [CAR]
  bluez.connected = False
  sup.maintain(0)
  assert starts == [] and bluez.hfp_registrations == 1           # standby gateway, nothing started
  bluez.adapter_ready = False
  onroad["value"] = True
  sup.maintain(2)
  assert starts == []                                            # radio not up yet: no wasted attempt
  bluez.adapter_ready = True
  sup.maintain(4)
  assert starts == ["onroad"] and alive["value"]
  onroad["value"] = False
  sup.maintain(6)
  sup.maintain(6 + auto_connect.STOP_AFTER)
  assert not alive["value"]


def test_supervisor_auto_start_on_car_connection_and_user_stop_hold(identity, tmp_path, monkeypatch):
  onroad = {"value": False}
  sup, starts, alive = auto_supervisor(identity, tmp_path, monkeypatch, onroad)
  bluez = sup._phone()
  bluez.connected = False
  sup._hfp_connected(CAR.lower())                                # the car reached the hands-free gateway
  sup.maintain(time.monotonic())
  assert starts == ["car_connected"]
  sup.user_stop()
  sup.maintain(time.monotonic())
  assert starts == ["car_connected"] and sup.status()["auto_paused"]


def test_supervisor_auto_connect_off(identity, tmp_path, monkeypatch):
  onroad = {"value": True}
  sup, starts, _ = auto_supervisor(identity, tmp_path, monkeypatch, onroad)
  sup.set_auto_connect(False)
  bluez = sup._phone()
  sup.maintain(0)
  assert starts == [] and bluez.released == 1 and bluez.hfp_registrations == 0
  assert json.loads((tmp_path / "aa" / "config.json").read_text())["auto_connect"] is False


def test_supervisor_auto_start_refused_reports_and_waits(identity, tmp_path, monkeypatch):
  onroad = {"value": True}
  sup, _ = make_supervisor(identity, tmp_path, monkeypatch, lambda *a, **k: socket.socketpair()[0])
  sup._onroad = lambda: onroad["value"]
  calls = []

  def refuse(trigger="manual"):
    calls.append(trigger)
    raise RuntimeError("Android Auto identity missing")
  monkeypatch.setattr(sup, "start", refuse)
  sup.maintain(0)
  sup.maintain(2)
  assert calls == ["onroad"] and "identity missing" in sup.status()["error"]


def test_hfp_answers_only_the_chosen_car(identity, tmp_path, monkeypatch):
  sup, _ = make_supervisor(identity, tmp_path, monkeypatch, lambda *a, **k: socket.socketpair()[0])
  assert sup._hfp_accepts(CAR) and sup._hfp_accepts(CAR.lower())
  assert not sup._hfp_accepts("11:22:33:44:55:66")
  sup._pairing_until = time.monotonic() + 60
  assert not sup._hfp_accepts("11:22:33:44:55:66")  # a window without approval grants no new car access


def test_unapproved_car_paired_in_window_is_not_selected(identity, tmp_path, monkeypatch):
  sup, _ = make_supervisor(identity, tmp_path, monkeypatch, lambda *a, **k: socket.socketpair()[0])
  sup._onroad = lambda: False
  bluez = sup._phone()
  bluez.connected = False
  sup.prepare_pairing(60)
  bluez.paired_devices.append(("11:22:33:44:55:66", "Speaker", False))
  sup.maintain()
  assert sup.config["receiver_address"] == CAR                   # not an Android Auto car
  bluez.paired_devices.append(("22:33:44:55:66:77", "Accord", True))
  sup.maintain()
  assert sup.config["receiver_address"] == CAR
  assert "22:33:44:55:66:77" not in bluez.trusted


# ------------------------------------------------ channel cache + phone class

def rejecting_car(identity, cars, channels):
  def rfcomm(address, channel, timeout=15.0):
    channels.append(channel)
    hu = FakeHeadUnit(identity, reject_auth=True)
    cars.append(hu)
    phone, car = socket.socketpair()

    def car_side():
      with car:
        rfcomm_head_unit(car, ("127.0.0.1", hu.port), pings=False)
        time.sleep(1.0)
    threading.Thread(target=car_side, daemon=True).start()
    return phone
  return rfcomm


def test_channel_cached_and_phone_class_restored_after_handshake(identity, tmp_path, monkeypatch):
  from openpilot.starpilot.system.android_auto import bt_sockets
  cars, channels = [], []
  sup, _ = make_supervisor(identity, tmp_path, monkeypatch, rejecting_car(identity, cars, channels))
  sdp_calls = []
  original_l2cap = bt_sockets.connect_l2cap
  monkeypatch.setattr(bt_sockets, "connect_l2cap", lambda *a, **k: (sdp_calls.append(1), original_l2cap(*a, **k))[1])
  sup.start()
  deadline = time.monotonic() + 15
  while len(cars) < 2:
    assert time.monotonic() < deadline, sup.status()
    time.sleep(0.05)
  bluez = sup._phone()
  sup.stop()
  for hu in cars:
    hu.close()
  assert channels[:2] == [8, 8] and len(sdp_calls) == 1          # second attempt skipped SDP
  assert sup.config["rfcomm_cache"] == {CAR: 8}
  assert json.loads((tmp_path / "aa" / "config.json").read_text())["rfcomm_cache"] == {CAR: 8}
  assert bluez.class_restored >= 2                               # after each handshake, before projection
  assert bluez.released == 0                                     # auto-connect keeps the car's gateway


def test_stale_cached_channel_is_dropped(identity, tmp_path, monkeypatch):
  def rfcomm(address, channel, timeout=15.0):
    raise ConnectionRefusedError(111, "Connection refused")
  sup, _ = make_supervisor(identity, tmp_path, monkeypatch, rfcomm)
  sup.config["rfcomm_cache"] = {CAR: 5}
  sup.start()
  deadline = time.monotonic() + 5
  while sup.config["rfcomm_cache"]:
    assert time.monotonic() < deadline, sup.status()
    time.sleep(0.02)
  sup.stop()


def test_config_sanitizes_channel_cache(tmp_path):
  from openpilot.starpilot.system.android_auto import identity as identity_store
  path = tmp_path / "config.json"
  path.write_text(json.dumps({"config_version": 2, "rfcomm_cache": {"aa:bb:cc:dd:ee:01": 8, "X": 99, "Y": "3", "Z": True}}))
  config = identity_store.load_config(path)
  assert config["rfcomm_cache"] == {CAR: 8} and config["auto_connect"] is True
  assert identity_store.load_config(tmp_path / "missing.json")["rfcomm_cache"] is not identity_store.DEFAULT_CONFIG["rfcomm_cache"]


def test_config_v2_rgba_pipeline_upgrades_to_gpu_nv12(tmp_path):
  from openpilot.starpilot.system.android_auto import identity as identity_store
  path = tmp_path / "config.json"
  # Every v2 save wrote these off; the car view could not do anything else then.
  path.write_text(json.dumps({"config_version": 2, "gpu_nv12": False, "async_readback": False, "fps": 20}))
  config = identity_store.load_config(path)
  assert config["gpu_nv12"] is True and config["async_readback"] is True and config["fps"] == 20
  identity_store.save_config(config, path)
  # From v3 on they are a real choice and stay as saved.
  path.write_text(json.dumps({**json.loads(path.read_text()), "gpu_nv12": False}))
  assert identity_store.load_config(path)["gpu_nv12"] is False


def _wireless_backoff_harness(sup, monkeypatch, failure):
  from openpilot.starpilot.system.android_auto import supervisor
  now = [100.0]
  monkeypatch.setattr(supervisor.time, "monotonic", lambda: now[0])
  monkeypatch.setattr(sup, "_lease", lambda: supervisor.NoLease())
  sup.config["connection"] = "wireless"
  starts, waits = [], []

  def attempt(_):
    starts.append(now[0])
    if len(starts) == 2:
      sup._stop.set()
    raise failure

  def wait(seconds):
    waits.append(seconds)
    now[0] += seconds
    if len(starts) == 1 and now[0] - starts[0] >= 5 and not sup._hfp_link.is_set():
      sup._hfp_connected(CAR.lower())  # the car reaches out mid-backoff, e.g. the driver taps Android Auto
    if sup._stop.is_set():
      raise supervisor.Cancelled()

  monkeypatch.setattr(sup, "_attempt", attempt)
  monkeypatch.setattr(sup, "_wait", wait)
  return starts, waits


def test_car_opening_hands_free_ends_the_backoff_early(identity, tmp_path, monkeypatch):
  from openpilot.starpilot.system.android_auto import supervisor
  sup, _ = make_supervisor(identity, tmp_path, monkeypatch, lambda *a, **k: socket.socketpair()[0])
  sup.select_receiver(CAR, "Civic")
  monkeypatch.setattr(supervisor, "BACKOFF_SECONDS", (30.0,))
  starts, _ = _wireless_backoff_harness(sup, monkeypatch, RuntimeError("car not answering"))
  sup._run(1)
  assert len(starts) == 2
  assert starts[1] - starts[0] < 6  # retried when the car connected, not after the 30 s backoff


def test_one_hands_free_connection_ends_only_one_backoff(identity, tmp_path, monkeypatch):
  sup, _ = make_supervisor(identity, tmp_path, monkeypatch, lambda *a, **k: socket.socketpair()[0])
  sup.select_receiver(CAR, "Civic")
  sup._hfp_connected(CAR)
  started = time.monotonic()
  sup._wait_backoff(0.3, car_can_wake=True)
  assert time.monotonic() - started < 0.1   # the car reached out: retry now
  started = time.monotonic()
  sup._wait_backoff(0.3, car_can_wake=True)  # the link is still fresh, but that connection was used
  assert time.monotonic() - started >= 0.25
  sup._hfp_connected(CAR)                    # a new connection from the car ends the next one early again
  started = time.monotonic()
  sup._wait_backoff(0.3, car_can_wake=True)
  assert time.monotonic() - started < 0.1


def test_car_ending_projection_still_gets_its_full_pause(identity, tmp_path, monkeypatch):
  from openpilot.starpilot.system.android_auto import supervisor
  from openpilot.starpilot.system.android_auto.session import PeerRequestedStop
  sup, _ = make_supervisor(identity, tmp_path, monkeypatch, lambda *a, **k: socket.socketpair()[0])
  sup.select_receiver(CAR, "Civic")
  starts, waits = _wireless_backoff_harness(sup, monkeypatch, PeerRequestedStop("Head unit ended projection"))
  sup._run(1)
  assert waits[0] == supervisor.PEER_STOP_RETRY_SECONDS
