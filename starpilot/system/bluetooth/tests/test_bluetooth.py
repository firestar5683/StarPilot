import io
import threading
import time

import numpy as np
import pytest

from openpilot.starpilot.system.bluetooth.audio import BluetoothAudioSink
import openpilot.starpilot.system.bluetooth.daemon as bluetooth_daemon
from openpilot.starpilot.system.bluetooth.bluez import PairingAgent
from openpilot.starpilot.system.bluetooth.daemon import BluetoothController
from openpilot.starpilot.system.bluetooth.elm327 import DTCParseError
from openpilot.starpilot.system.bluetooth.protocol import (A2DP_SINK_UUID, HID_UUID, BluetoothClient, BluetoothDevice, BluetoothStatus,
                                                           SPP_UUID, device_capabilities, show_pairing_device)
from openpilot.system import hardware
from openpilot.system.ui.lib.bluetooth_manager import BluetoothManager


class FakeParams:
  def __init__(self, **values):
    self.values = values

  def get_bool(self, key):
    return bool(self.values.get(key, False))

  def get(self, key, encoding=None, **_kwargs):
    value = self.values.get(key)
    return value.decode(encoding) if encoding and isinstance(value, bytes) else value

  def put_bool(self, key, value):
    self.values[key] = value

  def put(self, key, value):
    self.values[key] = value

  def remove(self, key):
    self.values.pop(key, None)


class FakeAgent:
  def __init__(self):
    self.responses = []

  def set_auto_accept_incoming(self, _enabled):
    pass

  def respond(self, prompt_id, accepted, value):
    self.responses.append((prompt_id, accepted, value))
    return prompt_id == "prompt"


class FakeBlueZ:
  def __init__(self):
    self.agent = FakeAgent()
    self.powered = False
    self.discoverable = False
    self.discovering = False
    self.closed = False
    self.actions = []
    self.device = {
      "path": "/fake/device",
      "address": "00:11:22:33:44:55",
      "name": "Speaker",
      "paired": True,
      "trusted": True,
      "connected": False,
      "audio": True,
      "controller": False,
      "serial": False,
    }

  def close(self):
    self.closed = True

  def set_powered(self, powered):
    self.powered = powered

  def set_discoverable(self, discoverable):
    self.discoverable = discoverable

  def status(self):
    return {"powered": self.powered, "discovering": self.discovering, "devices": [dict(self.device)], "prompt": None}

  def start_discovery(self):
    self.discovering = True

  def stop_discovery(self):
    self.discovering = False
    self.actions.append(("stop_scan", ""))

  def device_for_address(self, _address):
    return dict(self.device)

  def pair(self, address, _device_path=None):
    self.actions.append(("pair", address))

  def connect(self, address):
    self.actions.append(("connect", address))

  def disconnect(self, address):
    self.actions.append(("disconnect", address))

  def remove(self, address):
    self.actions.append(("remove", address))


class FakeRadio:
  available = True
  ready = True

  def __init__(self):
    self.starts = 0
    self.stops = 0

  def start(self):
    self.starts += 1

  def stop(self):
    self.stops += 1


class BlockingStopRadio(FakeRadio):
  def __init__(self):
    super().__init__()
    self.stop_started = threading.Event()
    self.allow_stop = threading.Event()

  def stop(self):
    self.stops += 1
    self.stop_started.set()
    self.allow_stop.wait()


class BlockingPowerClient:
  def __init__(self):
    self.power_entered = threading.Event()
    self.allow_power = threading.Event()
    self.power_finished = threading.Event()
    self.status_calls = 0

  def set_power(self, _enabled):
    self.power_entered.set()
    self.allow_power.wait()
    self.power_finished.set()

  def status(self):
    self.status_calls += 1
    return BluetoothStatus()


class FakeProcess:
  def __init__(self):
    self.stdin = io.BytesIO()
    self.stopped = False

  def poll(self):
    return 0 if self.stopped else None

  def terminate(self):
    self.stopped = True

  def wait(self, timeout=None):
    return 0

  def kill(self):
    self.stopped = True


class FakeELM:
  instances = []

  def __init__(self, address):
    self.address = address
    self.adapter_name = "Fake ELM327"
    self.closed = False
    self.commands = []
    self.opened = False
    FakeELM.instances.append(self)

  def open(self):
    self.opened = True
    return self.adapter_name

  def close(self):
    self.closed = True

  def command(self, value):
    self.commands.append(value)
    if value == "fail":
      raise RuntimeError("transport failed")
    if value == "bad_input":
      raise ValueError("invalid command")
    return f"response for {value}"

  def read_dtcs(self):
    return {"codes": ["P0133"], "raw": "43 01 33"}


def test_protocol_round_trip_and_capabilities():
  audio, controller, serial = device_capabilities([A2DP_SINK_UUID, HID_UUID])
  assert audio and controller
  assert not serial
  status = BluetoothStatus.from_dict({
    "available": True,
    "enabled": True,
    "devices": [{"address": "00:11:22:33:44:55", "name": "Combo", "uuids": [A2DP_SINK_UUID, HID_UUID], "audio": True, "controller": True}],
  })
  assert status.devices == (BluetoothDevice("00:11:22:33:44:55", "Combo", uuids=(A2DP_SINK_UUID, HID_UUID), audio=True, controller=True),)


def test_serial_capability_round_trips_and_is_discoverable():
  audio, controller, serial = device_capabilities([SPP_UUID.upper()])
  assert not audio and not controller and serial

  status = BluetoothStatus.from_dict({
    "devices": [{"address": "00:11:22:33:44:55", "name": "OBDII", "serial": True}],
  })
  assert status.devices[0].serial
  assert show_pairing_device("00:11:22:33:44:55", "OBDII", False, False, False, False,
                             audio=False, controller=False, serial=True)


def test_serial_device_is_not_auto_reconnected_but_audio_device_is(monkeypatch):
  class StopMaintenance(Exception):
    pass

  params = FakeParams(IsOffroad=True, BluetoothEnabled=True)
  client = FakeBlueZ()
  client.powered = True
  client.device.update(paired=True, trusted=True, connected=False, audio=False, controller=False, serial=True)
  sleeps = 0

  def sleep(_delay):
    nonlocal sleeps
    sleeps += 1
    if sleeps > 1:
      raise StopMaintenance

  monkeypatch.setattr(bluetooth_daemon.time, "sleep", sleep)
  controller = BluetoothController(params, lambda: client, FakeRadio(), sleep=sleep, elm_factory=FakeELM)
  controller._bluez = client
  controller._last_reconnect = -100.0
  with pytest.raises(StopMaintenance):
    controller.maintain_connections()
  assert client.actions == []

  client.device.update(audio=True, serial=False)
  sleeps = 0
  controller._last_reconnect = -100.0
  with pytest.raises(StopMaintenance):
    controller.maintain_connections()
  assert client.actions == [("connect", client.device["address"])]


def make_elm_controller(elm_factory=FakeELM):
  params = FakeParams(IsOffroad=True, BluetoothEnabled=True)
  client = FakeBlueZ()
  client.device.update(paired=True, trusted=True, serial=True)
  controller = BluetoothController(params, lambda: client, FakeRadio(), elm_factory=elm_factory)
  return controller, client, params


def test_elm_is_lazy_and_requires_a_paired_serial_device():
  FakeELM.instances = []
  controller, client, params = make_elm_controller()
  assert FakeELM.instances == []
  controller.status()
  assert FakeELM.instances == []

  result = controller.handle({"command": "elm_open", "address": client.device["address"]})
  assert result == {"adapter": "Fake ELM327"}
  assert len(FakeELM.instances) == 1

  params.values["IsOffroad"] = False
  with pytest.raises(RuntimeError, match="offroad"):
    controller.handle({"command": "elm_command", "address": client.device["address"], "value": "ATI"})

  params.values["IsOffroad"] = True
  client.device["paired"] = False
  controller.handle({"command": "elm_close", "address": client.device["address"]})
  with pytest.raises(RuntimeError, match="Pair"):
    controller.handle({"command": "elm_open", "address": client.device["address"]})

  client.device.update(paired=True, serial=False)
  with pytest.raises(RuntimeError, match="Serial Port Profile"):
    controller.handle({"command": "elm_open", "address": client.device["address"]})


def test_elm_commands_use_one_session_and_close_on_transport_failure(monkeypatch):
  FakeELM.instances = []
  controller, client, _ = make_elm_controller()
  address = client.device["address"]
  controller.handle({"command": "elm_open", "address": address})
  assert controller.handle({"command": "elm_open", "address": address}) == {"adapter": "Fake ELM327"}
  assert controller.handle({"command": "elm_command", "address": address, "value": "ATI"}) == {"response": "response for ATI"}
  assert controller.handle({"command": "elm_read_dtcs", "address": address}) == {"codes": ["P0133"], "raw": "43 01 33"}
  with pytest.raises(ValueError, match="invalid command"):
    controller.handle({"command": "elm_command", "address": address, "value": "bad_input"})

  def fail_dtcs():
    raise DTCParseError("No valid Mode 03 response", "garbage")

  monkeypatch.setattr(FakeELM.instances[0], "read_dtcs", fail_dtcs)
  with pytest.raises(DTCParseError):
    controller.handle({"command": "elm_read_dtcs", "address": address})
  assert controller._elm is not None and not FakeELM.instances[0].closed
  with pytest.raises(RuntimeError, match="transport"):
    controller.handle({"command": "elm_command", "address": address, "value": "fail"})
  assert controller._elm is None
  assert FakeELM.instances[0].closed


def test_elm_open_replaces_a_different_session_and_close_is_allowed_onroad():
  FakeELM.instances = []
  controller, client, params = make_elm_controller()
  first = client.device["address"]
  second = "AA:BB:CC:DD:EE:FF"
  controller.handle({"command": "elm_open", "address": first})
  controller.handle({"command": "elm_open", "address": second})
  assert len(FakeELM.instances) == 2
  assert FakeELM.instances[0].closed
  assert not FakeELM.instances[1].closed

  params.values["IsOffroad"] = False
  controller.handle({"command": "elm_close", "address": second})
  assert FakeELM.instances[1].closed and controller._elm is None


def test_elm_cleanup_happens_before_poweroff_forget_shutdown_and_onroad(monkeypatch):
  class StopMaintenance(Exception):
    pass

  for cleanup in ("power", "forget", "shutdown", "onroad"):
    FakeELM.instances = []
    controller, client, params = make_elm_controller()
    address = client.device["address"]
    controller.handle({"command": "elm_open", "address": address})
    session = FakeELM.instances[0]

    if cleanup == "power":
      controller.handle({"command": "set_power", "enabled": False})
    elif cleanup == "forget":
      controller.handle({"command": "forget", "address": address})
    elif cleanup == "shutdown":
      controller.close()
    else:
      params.values["IsOffroad"] = False
      sleeps = 0

      def sleep(_delay):
        nonlocal sleeps
        sleeps += 1
        if sleeps > 1:
          raise StopMaintenance

      monkeypatch.setattr(bluetooth_daemon.time, "sleep", sleep)
      controller._sleep = sleep
      with pytest.raises(StopMaintenance):
        controller.maintain_connections()

    assert session.closed and controller._elm is None


def test_pairing_list_filters_anonymous_and_irrelevant_advertisements():
  assert not show_pairing_device("00:11:22:33:44:55", "00:11:22:33:44:55", False, False, False, False, False, False)
  assert not show_pairing_device("00:11:22:33:44:55", "Nearby sensor", False, False, False, False, False, False)
  assert show_pairing_device("00:11:22:33:44:55", "Media Remote", False, False, False, False, False, True)
  assert show_pairing_device("00:11:22:33:44:55", "Media Remote", False, False, False, False, False, True, discovering=True)
  assert show_pairing_device("00:11:22:33:44:55", "OBDII", False, False, False, False, False, False, False, discovering=True)
  assert not show_pairing_device("00:11:22:33:44:55", "00:11:22:33:44:55", False, False, False, False, False, False, False, discovering=True)
  assert not show_pairing_device("00:11:22:33:44:55", "OBDII", False, False, False, True, False, False, False, discovering=True)
  assert show_pairing_device("00:11:22:33:44:55", "Known device", True, True, False, False, False, False)


def test_desktop_fake_bluetooth_is_stateful_and_interactive(monkeypatch, tmp_path):
  monkeypatch.setenv("SP_ALLOW_DESKTOP_FAKE_BLUETOOTH", "1")
  monkeypatch.setenv("SIMULATION", "1")
  monkeypatch.setenv("NOBOARD", "1")
  client = BluetoothClient(socket_path=str(tmp_path / "bluetooth.sock"))

  initial = client.status()
  speaker, controller = initial.devices[:2]
  assert initial.available and initial.enabled and speaker.connected

  client.start_scan()
  assert client.status().discovering

  client.pair(controller.address)
  client.connect(controller.address)
  paired_controller = next(device for device in client.status().devices if device.address == controller.address)
  assert paired_controller.paired and paired_controller.trusted and paired_controller.connected

  client.select_audio(speaker.address)
  assert client.status().selected_audio == speaker.address
  assert client.test_audio(speaker.address) == 3.0

  client.forget(controller.address)
  forgotten_controller = next(device for device in client.status().devices if device.address == controller.address)
  assert not forgotten_controller.paired and not forgotten_controller.connected

  client.set_power(False)
  disabled = client.status()
  assert not disabled.enabled and not disabled.powered and not disabled.discovering
  assert disabled.selected_audio == speaker.address
  with pytest.raises(RuntimeError, match="Enable Bluetooth"):
    client.start_scan()
  client.set_power(True)
  enabled = client.status()
  assert enabled.enabled and enabled.selected_audio == speaker.address


def test_desktop_fake_bluetooth_cannot_activate_on_device(monkeypatch, tmp_path):
  monkeypatch.setenv("SP_ALLOW_DESKTOP_FAKE_BLUETOOTH", "1")
  monkeypatch.setenv("SIMULATION", "1")
  monkeypatch.setenv("NOBOARD", "1")
  monkeypatch.setattr(hardware, "PC", False)
  client = BluetoothClient(socket_path=str(tmp_path / "bluetooth.sock"))

  assert client._get_desktop_fake() is None
  assert client._desktop_fake is None


def test_pairing_agent_accept_reject_and_timeout():
  agent = PairingAgent()
  agent.set_auto_accept_incoming(True)
  assert agent.request("confirmation", "/incoming", "123456") == (True, "")
  agent.set_auto_accept_incoming(False)
  result = []
  worker = threading.Thread(target=lambda: result.append(agent.request("confirmation", "/device", "123456", timeout=1.0)))
  worker.start()
  deadline = time.monotonic() + 1.0
  while agent.prompt is None and time.monotonic() < deadline:
    time.sleep(0.01)
  assert agent.prompt is not None
  assert agent.respond(agent.prompt["id"], True)
  worker.join(timeout=1.0)
  assert result == [(True, "")]
  assert agent.request("pin", "/device", timeout=0.01) == (False, "")


def test_disabled_status_does_not_start_radio_or_bluez():
  params = FakeParams(IsOffroad=True, BluetoothEnabled=False)
  radio = FakeRadio()
  created = []
  controller = BluetoothController(params, lambda: created.append(FakeBlueZ()) or created[-1], radio)
  status = controller.status()
  assert status["available"] and not status["enabled"] and not status["powered"]
  assert radio.starts == 0 and created == []


def test_enabled_initialization_registers_bluetooth_agent_without_ui_poll():
  params = FakeParams(IsOffroad=True, BluetoothEnabled=True)
  radio = FakeRadio()
  created = []
  controller = BluetoothController(params, lambda: created.append(FakeBlueZ()) or created[-1], radio)

  controller.initialize()

  assert radio.starts == 1 and len(created) == 1
  assert created[0].powered


def test_power_pair_audio_and_offroad_enforcement():
  params = FakeParams(IsOffroad=True, BluetoothEnabled=False)
  radio = FakeRadio()
  clients = []
  controller = BluetoothController(params, lambda: clients.append(FakeBlueZ()) or clients[-1], radio)
  controller.handle({"command": "set_power", "enabled": True})
  assert params.get_bool("BluetoothEnabled") and radio.starts == 1 and clients[0].powered
  controller.handle({"command": "select_audio", "address": "00:11:22:33:44:55"})
  assert params.get("BluetoothAudioAddress") == "00:11:22:33:44:55"
  controller.handle({"command": "select_audio", "address": ""})
  assert params.get("BluetoothAudioAddress") is None
  assert clients[0].actions == []
  params.values["IsOffroad"] = False
  with pytest.raises(RuntimeError, match="offroad"):
    controller.handle({"command": "start_scan"})
  controller.handle({"command": "connect", "address": "00:11:22:33:44:55"})
  assert clients[0].actions[-1] == ("connect", "00:11:22:33:44:55")
  params.values["IsOffroad"] = True
  controller.handle({"command": "set_power", "enabled": False})
  assert not params.get_bool("BluetoothEnabled") and radio.stops == 1 and clients[0].closed


def test_disconnect_is_idempotent_and_suppresses_auto_reconnect():
  params = FakeParams(IsOffroad=False, BluetoothEnabled=True)
  client = FakeBlueZ()
  controller = BluetoothController(params, lambda: client, FakeRadio())

  controller.handle({"command": "disconnect", "address": client.device["address"]})

  address = client.device["address"].upper()
  assert client.actions == [("disconnect", client.device["address"])]
  assert address in controller._manual_disconnect_until
  assert controller._manual_disconnect_until[address] > time.monotonic()


def test_power_off_preserves_saved_audio_selection():
  params = FakeParams(IsOffroad=True, BluetoothEnabled=False, BluetoothAudioAddress="00:11:22:33:44:55")
  controller = BluetoothController(params, FakeBlueZ, FakeRadio())

  controller.handle({"command": "set_power", "enabled": True})
  controller.handle({"command": "set_power", "enabled": False})

  assert params.get("BluetoothAudioAddress") == "00:11:22:33:44:55"


def test_status_does_not_restart_radio_during_disable():
  params = FakeParams(IsOffroad=True, BluetoothEnabled=True)
  radio = BlockingStopRadio()
  client = FakeBlueZ()
  controller = BluetoothController(params, lambda: client, radio)
  controller._bluez = client

  errors = []
  def disable():
    try:
      controller.handle({"command": "set_power", "enabled": False})
    except Exception as error:
      errors.append(error)

  status_started = threading.Event()
  status_done = threading.Event()
  status_result = []

  def read_status():
    status_started.set()
    status_result.append(controller.status())
    status_done.set()

  worker = threading.Thread(target=disable, daemon=True)
  worker.start()
  assert radio.stop_started.wait(timeout=1.0)

  status_worker = threading.Thread(target=read_status, daemon=True)
  status_worker.start()
  try:
    assert status_started.wait(timeout=1.0)
    assert not status_done.wait(timeout=0.1)
  finally:
    radio.allow_stop.set()

  worker.join(timeout=1.0)
  status_worker.join(timeout=1.0)

  assert not worker.is_alive()
  assert not status_worker.is_alive()
  assert errors == []
  assert radio.starts == 0
  assert radio.stops == 1
  status = status_result[0]
  assert not status["enabled"]
  assert not params.get_bool("BluetoothEnabled")


def test_status_poll_does_not_overlap_power_transition():
  client = BlockingPowerClient()
  manager = object.__new__(BluetoothManager)
  manager._client = client
  manager._lock = threading.Lock()
  manager._client_lock = threading.Lock()
  manager._status = BluetoothStatus()
  manager._active = True
  manager._exit = False
  manager._operation_error = ""
  manager._operations = {}
  manager._power_pending = False
  manager._audio_test_deadline = 0.0

  manager.set_power(True)
  assert client.power_entered.wait(timeout=1.0)
  poller = threading.Thread(target=manager._poll_status)
  poller.start()
  poller.join(timeout=1.0)

  client.allow_power.set()
  assert client.power_finished.wait(timeout=1.0)

  assert not poller.is_alive()
  assert client.status_calls == 0


def test_audio_uses_soundd_engage_alert_and_cleans_up():
  params = FakeParams(IsOffroad=True, BluetoothEnabled=True)
  params_memory = FakeParams()
  client = FakeBlueZ()
  client.device["connected"] = True
  controller = BluetoothController(params, lambda: client, FakeRadio(), params_memory, sleep=lambda _delay: None)

  result = controller.handle({"command": "test_audio", "address": client.device["address"]})
  deadline = time.monotonic() + 1.0
  while params.get_bool("BluetoothAudioTestActive") and time.monotonic() < deadline:
    time.sleep(0.01)

  assert params.get("BluetoothAudioAddress") == client.device["address"]
  assert 2500 <= result["audio_test_delay_ms"] <= 3000
  assert params_memory.get("TestAlert") == "engage"
  assert not params.get_bool("BluetoothAudioTestActive")


def test_audio_requires_connected_device_and_offroad():
  params = FakeParams(IsOffroad=True, BluetoothEnabled=True)
  client = FakeBlueZ()
  controller = BluetoothController(params, lambda: client, FakeRadio(), FakeParams())

  with pytest.raises(RuntimeError, match="Connect"):
    controller.handle({"command": "test_audio", "address": client.device["address"]})
  params.values["IsOffroad"] = False
  with pytest.raises(RuntimeError, match="offroad"):
    controller.handle({"command": "test_audio", "address": client.device["address"]})


def test_scan_stops_after_timeout():
  params = FakeParams(IsOffroad=True, BluetoothEnabled=True)
  client = FakeBlueZ()
  controller = BluetoothController(params, lambda: client, FakeRadio())
  controller.handle({"command": "start_scan"})
  assert client.discovering and controller._scan_deadline > time.monotonic()

  controller._maintain_scan(controller.status(), controller._scan_deadline)
  assert not client.discovering and controller._scan_deadline == 0.0


def test_pair_keeps_discovery_until_pair_starts():
  params = FakeParams(IsOffroad=True, BluetoothEnabled=True)
  client = FakeBlueZ()
  controller = BluetoothController(params, lambda: client, FakeRadio())
  controller.handle({"command": "start_scan"})
  controller.handle({"command": "pair", "address": client.device["address"]})

  deadline = time.monotonic() + 1.0
  while not any(action[0] == "pair" for action in client.actions) and time.monotonic() < deadline:
    time.sleep(0.01)

  pair_index = client.actions.index(("pair", client.device["address"]))
  assert client.actions[-1] == ("stop_scan", "")
  assert pair_index < len(client.actions) - 1


def test_audio_queue_is_nonblocking_and_falls_back():
  params = FakeParams(BluetoothEnabled=True, BluetoothAudioAddress="00:11:22:33:44:55")
  process = FakeProcess()
  sink = BluetoothAudioSink(params, popen_factory=lambda *_args, **_kwargs: process, start_thread=False)
  sink._aplay = "/usr/bin/aplay"
  sink._thread = threading.Thread(target=sink._run, daemon=True)
  sink._thread.start()
  samples = np.array([-1.0, 0.0, 1.0], dtype=np.float32)
  deadline = time.monotonic() + 1.0
  while not sink._address and time.monotonic() < deadline:
    time.sleep(0.01)
  assert not sink.submit(samples)
  deadline = time.monotonic() + 1.0
  while not sink.healthy and time.monotonic() < deadline:
    time.sleep(0.01)
  assert sink.healthy
  assert len(process.stdin.getvalue()) == 12
  assert sink.submit(samples)
  process.stopped = True
  assert not sink.healthy
  sink.close()


def test_full_audio_queue_immediately_restores_local_output():
  params = FakeParams(BluetoothEnabled=True, BluetoothAudioAddress="00:11:22:33:44:55")
  process = FakeProcess()
  sink = BluetoothAudioSink(params, start_thread=False)
  sink._aplay = "/usr/bin/aplay"
  sink._address = "00:11:22:33:44:55"
  sink._process = process
  sink._healthy = True
  sink._last_write = time.monotonic()
  samples = np.zeros(3, dtype=np.float32)

  assert sink.submit(samples)
  assert sink.submit(samples)
  assert sink.submit(samples)
  assert not sink.submit(samples)
  assert not sink.healthy


def test_audio_address_decodes_device_params_bytes():
  params = FakeParams(BluetoothEnabled=True, BluetoothAudioAddress=b"00:11:22:33:44:55")
  sink = BluetoothAudioSink(params, start_thread=False)
  assert sink.desired_address() == "00:11:22:33:44:55"
