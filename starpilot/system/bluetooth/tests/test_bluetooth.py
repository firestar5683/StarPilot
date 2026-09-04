import io
import json
import queue
import struct
import threading
import time

from types import SimpleNamespace

import numpy as np
import pytest

from jeepney import DBusAddress, new_method_call

from openpilot.starpilot.system.bluetooth.audio import BluetoothAudioSink
from openpilot.starpilot.system.bluetooth.bluez import BlueZClient, BlueZError, PairingAgent
from openpilot.starpilot.system.bluetooth.companion import (
  ADVERTISEMENT_IFACE, COMPANION_ADVERTISEMENT_PATH, COMPANION_APP_PATH, COMPANION_COMMAND_PATH, COMPANION_PROTOCOL_VERSION,
  COMPANION_LIVE_PATH, COMPANION_LIVE_UUID, COMPANION_RESPONSE_PATH, COMPANION_SERVICE_PATH, COMPANION_SERVICE_UUID,
  COMPANION_STATUS_PATH, GATT_CHARACTERISTIC_IFACE, OBJECT_MANAGER_IFACE, PROPERTIES_IFACE, CompanionGattApplication,
  CompanionProtocol, load_editable_params,
)
from openpilot.starpilot.system.bluetooth.daemon import COMPANION_BOND_SETTLE_INTERVAL, BluetoothController
from openpilot.starpilot.system.bluetooth.live import (
  LIVE_FRAME_MAGIC, LIVE_FRAME_RATE_HZ, LIVE_FRAME_SIZE, LIVE_FRAME_TYPE_HEALTH,
  LIVE_FRAME_TYPE_STATE, LIVE_HEALTH_FRAME_RATE_HZ, LIVE_HEALTH_TICK_DIVISOR, LIVE_NOTIFICATION_FRAGMENT_COUNT,
  LIVE_NOTIFICATION_SIZE, LIVE_PATH_FRAME_RATE_HZ, LIVE_PROTOCOL_VERSION,
  LIVE_TOTAL_FRAME_RATE_HZ, LIVE_TOTAL_NOTIFICATION_RATE_HZ,
  BorderState, ConditionalChillReason, HealthFlags, LiveFlags,
  LiveSnapshot, LiveTelemetryPublisher, ModelSource, build_health_snapshot, build_live_details, build_live_snapshot,
  live_notification_fragments,
)
from openpilot.starpilot.system.bluetooth.protocol import (A2DP_SINK_UUID, HID_UUID, BluetoothClient, BluetoothDevice, BluetoothStatus,
                                                           device_capabilities, show_pairing_device)
from openpilot.starpilot.system.bluetooth.radio import BluetoothRadio
from openpilot.selfdrive.ui.lib.starpilot_version import STARPILOT_DISPLAY_VERSION
from openpilot.system import hardware
from openpilot.system.ui.lib.bluetooth_manager import BluetoothManager, companion_setup_visible


class FakeParams:
  def __init__(self, **values):
    self.values = values

  def get_bool(self, key):
    return bool(self.values.get(key, False))

  def get_int(self, key, default=0):
    value = self.values.get(key)
    return default if value is None else int(value)

  def get(self, key, encoding=None, **_kwargs):
    value = self.values.get(key)
    return value.decode(encoding) if encoding and isinstance(value, bytes) else value

  def put_bool(self, key, value):
    self.values[key] = value

  def put(self, key, value):
    self.values[key] = value

  def remove(self, key):
    self.values.pop(key, None)


class TypedJsonFakeParams(FakeParams):
  def get(self, key, encoding=None, **kwargs):
    value = super().get(key, encoding=encoding, **kwargs)
    if key == "BluetoothCompanionDevices" and isinstance(value, str):
      return json.loads(value)
    return value

  def put(self, key, value):
    if key == "BluetoothCompanionDevices" and not isinstance(value, list):
      raise TypeError("Type mismatch while writing param BluetoothCompanionDevices")
    super().put(key, value)


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
    self.pairing_mode_error = None
    self.router = object()
    self.device = {
      "path": "/fake/device",
      "address": "00:11:22:33:44:55",
      "name": "Speaker",
      "paired": True,
      "trusted": True,
      "connected": False,
      "audio": True,
      "controller": False,
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
    self.device["connected"] = True

  def disconnect(self, address):
    self.actions.append(("disconnect", address))
    self.device["connected"] = False

  def remove(self, address):
    self.actions.append(("remove", address))

  def _call(self, *args):
    self.actions.append(("call", *args))

  def adapter(self):
    return "/org/bluez/hci0", {}

  def set_pairing_mode(self, enabled):
    self.actions.append(("pairing_mode", enabled))
    if self.pairing_mode_error is not None:
      raise self.pairing_mode_error

  def paired_device_for_path(self, path):
    if path != "/org/bluez/hci0/dev_phone" or not self.device["paired"]:
      return None
    return {**self.device, "path": path}

  def set_device_property(self, address, name, signature, value):
    self.actions.append(("property", address, name, signature, value))
    if name == "Trusted":
      self.device["trusted"] = bool(value)


class FakeCompanion:
  def __init__(self, _router, _call, authorize, protocol):
    self.authorize = authorize
    self.protocol = protocol
    self.started = ""
    self.closed = False
    self.rearmed = 0
    self.refreshed = 0

  def start(self, adapter_path):
    self.started = adapter_path

  def rearm_advertisement(self):
    self.rearmed += 1

  def refresh_services(self):
    self.refreshed += 1

  def close(self):
    self.closed = True


class FakeRadio:
  available = True
  ready = True

  def __init__(self):
    self.starts = 0
    self.stops = 0
    self.connectable = []

  def start(self):
    self.starts += 1

  def stop(self):
    self.stops += 1

  def set_connectable(self, enabled):
    self.connectable.append(enabled)


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


@pytest.mark.parametrize("registered", [True, None])
def test_radio_le_security_check_leaves_ready_or_unknown_platform_alone(monkeypatch, registered):
  calls = []
  monkeypatch.setattr(BluetoothRadio, "_le_security_manager_registered", staticmethod(lambda: registered))
  monkeypatch.setattr("openpilot.starpilot.system.bluetooth.radio.subprocess.run", lambda *args, **kwargs: calls.append((args, kwargs)))

  BluetoothRadio().ensure_le_security_manager()

  assert calls == []


def test_radio_repairs_missing_le_security_manager_through_bluez(monkeypatch):
  checks = iter((False, False, True))
  calls = []
  monkeypatch.setattr(BluetoothRadio, "_le_security_manager_registered", staticmethod(lambda: next(checks)))
  monkeypatch.setattr("openpilot.starpilot.system.bluetooth.radio.subprocess.run",
                      lambda args, **_kwargs: calls.append(args) or SimpleNamespace(returncode=0))
  monkeypatch.setattr("openpilot.starpilot.system.bluetooth.radio.time.sleep", lambda _seconds: None)

  BluetoothRadio().ensure_le_security_manager()

  assert calls == [["bluetoothctl", "power", "off"], ["bluetoothctl", "power", "on"]]


def test_protocol_round_trip_and_capabilities():
  audio, controller = device_capabilities([A2DP_SINK_UUID, HID_UUID])
  assert audio and controller
  status = BluetoothStatus.from_dict({
    "available": True,
    "enabled": True,
    "devices": [{"address": "00:11:22:33:44:55", "name": "Combo", "uuids": [A2DP_SINK_UUID, HID_UUID], "audio": True, "controller": True}],
  })
  assert status.devices == (BluetoothDevice("00:11:22:33:44:55", "Combo", uuids=(A2DP_SINK_UUID, HID_UUID), audio=True, controller=True),)


def test_companion_protocol_is_read_only_and_versioned():
  params = FakeParams(IsOffroad=True, GitBranch="Dom")
  protocol = CompanionProtocol(params, clock=lambda: 1234.9)

  status = json.loads(protocol.status_bytes())
  assert LIVE_PATH_FRAME_RATE_HZ == 0
  assert LIVE_TOTAL_FRAME_RATE_HZ == 12
  assert LIVE_TOTAL_NOTIFICATION_RATE_HZ == 48
  assert status == {
    "branch": "Dom",
    "device": "StarPilot",
    "live": {
      "frame_size": LIVE_FRAME_SIZE,
      "protocol_version": LIVE_PROTOCOL_VERSION,
      "rate_hz": LIVE_FRAME_RATE_HZ,
      "notification_fragments": LIVE_NOTIFICATION_FRAGMENT_COUNT,
      "notification_size": LIVE_NOTIFICATION_SIZE,
      "uuid": COMPANION_LIVE_UUID,
      "frame_types": [LIVE_FRAME_TYPE_STATE, LIVE_FRAME_TYPE_HEALTH],
      "health_rate_hz": LIVE_HEALTH_FRAME_RATE_HZ,
      "path_rate_hz": LIVE_PATH_FRAME_RATE_HZ,
      "total_rate_hz": LIVE_TOTAL_FRAME_RATE_HZ,
      "notification_rate_hz": LIVE_TOTAL_NOTIFICATION_RATE_HZ,
    },
    "onroad": False,
    "protocol_version": COMPANION_PROTOCOL_VERSION,
    "version": STARPILOT_DISPLAY_VERSION,
  }
  assert json.loads(protocol.handle(b'{"id":"one","op":"ping"}')) == {
    "data": {"time": 1234}, "id": "one", "ok": True, "op": "ping",
  }
  metadata_response = protocol.handle(b'{"id":"meta","op":"get_live_metadata"}')
  metadata = json.loads(metadata_response)["data"]
  assert metadata["model"]["key"] == ""
  assert metadata["alert"]["id"] == 0
  assert len(metadata_response) <= 512
  rejected = json.loads(protocol.handle(b'{"id":"two","op":"set_speed"}'))
  assert not rejected["ok"] and "Unsupported" in rejected["error"]


def _call(protocol, payload):
  return json.loads(protocol.handle(json.dumps(payload).encode()))


def test_companion_reads_and_writes_editable_params():
  editable = load_editable_params()
  assert editable, "settings catalog should provide editable params"
  bool_key = next(k for k, m in editable.items() if m["data_type"] == "bool" and not m["requires_offroad"])

  params = FakeParams(IsOffroad=True)
  protocol = CompanionProtocol(params, clock=lambda: 0)

  written = _call(protocol, {"id": "w", "op": "set_params", "key": bool_key, "value": True})
  assert written["ok"] and written["data"] == {"key": bool_key, "applied": True}
  assert params.values[bool_key] is True

  read = _call(protocol, {"id": "r", "op": "get_params", "keys": [bool_key]})
  assert read["ok"] and read["data"][bool_key] is True


def test_companion_rejects_non_editable_and_bad_reads():
  protocol = CompanionProtocol(FakeParams(IsOffroad=True), clock=lambda: 0)

  rejected = _call(protocol, {"id": "1", "op": "set_params", "key": "NotARealParam", "value": 1})
  assert not rejected["ok"] and "not editable" in rejected["error"]

  missing_keys = _call(protocol, {"id": "2", "op": "get_params"})
  assert not missing_keys["ok"] and "keys" in missing_keys["error"]

  too_many = _call(protocol, {"id": "3", "op": "get_params", "keys": [str(i) for i in range(32)]})
  assert not too_many["ok"] and "at most" in too_many["error"]


def test_companion_offroad_gated_write_rejected_onroad():
  editable = load_editable_params()
  offroad_only = next((k for k, m in editable.items() if m["requires_offroad"]), None)
  if offroad_only is None:
    pytest.skip("no offroad-gated params in catalog")

  params = FakeParams(IsOffroad=False)  # car is on
  protocol = CompanionProtocol(params, clock=lambda: 0)
  response = _call(protocol, {"id": "x", "op": "set_params", "key": offroad_only, "value": 1})
  assert not response["ok"] and "car is off" in response["error"]
  assert offroad_only not in params.values


def test_companion_sets_navigation_destination():
  params = FakeParams(IsOffroad=True)
  protocol = CompanionProtocol(params, clock=lambda: 0)
  response = _call(protocol, {"id": "n", "op": "set_navigation",
                              "name": "Work", "latitude": 37.42, "longitude": -122.08})
  assert response["ok"] and response["data"]["name"] == "Work"
  stored = json.loads(params.values["NavDestination"])
  assert stored["latitude"] == 37.42 and stored["longitude"] == -122.08


class FakeSubMaster(dict):
  def __init__(self, **services):
    super().__init__(services)
    self.valid = dict.fromkeys(services, True)


def test_live_snapshot_packs_complete_versioned_driving_state():
  params = FakeParams(
    ConditionalChill=True,
    SpeedLimitController=True,
    CurveSpeedController=True,
    UsbGpuActive=True,
    UsbGpuLoading=False,
    IsMetric=False,
    AccelerationProfile=3,
    LongitudinalPersonality=2,
    DrivingModel="galaxy-model",
    DrivingModelName="Galaxy Model",
    DrivingModelVersion="v15",
  )
  params_memory = FakeParams(CCStatus=4, CEStatus=0, SwitchbackModeEnabled=False)
  lateral_state = SimpleNamespace(
    which=lambda: "angleState",
    angleState=SimpleNamespace(steeringAngleDesiredDeg=13.7),
  )
  sm = FakeSubMaster(
    deviceState=SimpleNamespace(started=True),
    carState=SimpleNamespace(
      vEgo=20.0, vEgoCluster=20.25, vCruiseCluster=84.6, aEgo=-0.45,
      gasPressed=False, brakePressed=True, standstill=False, steeringAngleDeg=12.3, steeringTorque=-2.5,
      cruiseState=SimpleNamespace(available=True, enabled=True, standstill=False, nonAdaptive=False),
    ),
    selfdriveState=SimpleNamespace(
      enabled=True, active=True, experimentalMode=False, personality=2, state=2,
      alertType="controlsUnresponsive", alertText1="TAKE CONTROL", alertText2="Controls Unresponsive", alertStatus=2,
    ),
    carControl=SimpleNamespace(latActive=True, longActive=True, actuators=SimpleNamespace(steeringAngleDeg=0.0)),
    controlsState=SimpleNamespace(longControlState=2, lateralControlState=lateral_state, vCruiseDEPRECATED=0.0),
    radarState=SimpleNamespace(leadOne=SimpleNamespace(status=True, dRel=26.4, vRel=-1.75, modelProb=0.992)),
    longitudinalPlan=SimpleNamespace(aTarget=-0.61, shouldStop=False),
    drivingModelData=SimpleNamespace(meta=SimpleNamespace(laneChangeState=2, laneChangeDirection=2)),
    starpilotCarState=SimpleNamespace(
      alwaysOnLateralEnabled=True, pauseLateral=True, trafficModeEnabled=False, pulseAndGlide=False,
    ),
    starpilotPlan=SimpleNamespace(
      slcSpeedLimit=20.1, slcSpeedLimitOffset=1.12, cscControllingSpeed=True, cscSpeed=17.2, redLight=True,
      forcingStop=False, trackingLead=True, pulseGlideCoasting=False,
    ),
    onroadEvents=[],
  )

  snapshot = build_live_snapshot(sm, params, params_memory)
  frame = snapshot.pack(513, 0x12345678)

  assert len(frame) == LIVE_FRAME_SIZE
  assert struct.unpack_from("<2sBBHHII", frame) == (
    LIVE_FRAME_MAGIC, LIVE_PROTOCOL_VERSION, 1, LIVE_FRAME_SIZE, 513, 0x12345678, snapshot.flags,
  )
  telemetry = struct.unpack_from("<hHhhhhhHhHHhH", frame, 16)
  assert telemetry == (2025, 2350, -45, -61, 123, 137, -25, 264, -175, 992, 2010, 112, 1720)
  state = struct.unpack_from("<10B4BII", frame, 42)
  assert state[:10] == (2, int(BorderState.LONGITUDINAL_ONLY), 2, int(ConditionalChillReason.LEAD), 3, 2, 2, 2, 2, int(ModelSource.BIG))
  assert state[10:14] == (255, 105, 180, 255)
  assert state[14] != 0 and state[15] != 0
  assert snapshot.flags & LiveFlags.CONDITIONAL_CHILL
  assert snapshot.flags & LiveFlags.BIG_MODEL
  assert snapshot.flags & LiveFlags.BRAKE_PRESSED
  assert snapshot.flags & LiveFlags.STOPPING
  assert snapshot.flags & LiveFlags.RED_LIGHT
  fragments = live_notification_fragments(frame)
  assert len(fragments) == LIVE_NOTIFICATION_FRAGMENT_COUNT
  assert all(len(fragment) == LIVE_NOTIFICATION_SIZE for fragment in fragments)
  assert b"".join(fragment[4:] for fragment in fragments) == frame
  assert [fragment[3] & 0x0F for fragment in fragments] == list(range(LIVE_NOTIFICATION_FRAGMENT_COUNT))
  details = build_live_details(sm)
  assert details["alert"]["id"] == snapshot.alert_id
  assert details["alert"]["text1"] == "TAKE CONTROL"


def test_live_publisher_sequences_frames():
  params = FakeParams(DrivingModel="model")
  frames = []
  publisher = LiveTelemetryPublisher(frames.append, params, FakeParams(), monotonic=lambda: 12.345)
  sm = FakeSubMaster()

  publisher.publish_once(sm)
  publisher.publish_once(sm)

  assert [struct.unpack_from("<H", frame, 6)[0] for frame in frames] == [0, 1]
  assert all(struct.unpack_from("<I", frame, 8)[0] == 12345 for frame in frames)


def test_live_publisher_caches_persistent_params_for_one_second():
  class CountingParams(FakeParams):
    def __init__(self, **values):
      super().__init__(**values)
      self.reads = 0

    def get_bool(self, key):
      self.reads += 1
      return super().get_bool(key)

    def get_int(self, key, default=0):
      self.reads += 1
      return super().get_int(key, default)

    def get(self, key, encoding=None, **kwargs):
      self.reads += 1
      return super().get(key, encoding=encoding, **kwargs)

  now = [0.0]
  params = CountingParams(IsMetric=False)
  publisher = LiveTelemetryPublisher(lambda _frame: None, params, FakeParams(), monotonic=lambda: now[0])

  first = publisher.publish_once(FakeSubMaster())
  first_reads = params.reads
  params.values["IsMetric"] = True
  now[0] = 0.5
  cached = publisher.publish_once(FakeSubMaster())
  now[0] = 1.0
  refreshed = publisher.publish_once(FakeSubMaster())

  assert first_reads == 13
  assert params.reads == 2 * first_reads
  assert not struct.unpack_from("<I", first, 12)[0] & LiveFlags.METRIC
  assert not struct.unpack_from("<I", cached, 12)[0] & LiveFlags.METRIC
  assert struct.unpack_from("<I", refreshed, 12)[0] & LiveFlags.METRIC


def test_live_publisher_uses_driving_model_data_only():
  assert "drivingModelData" in LiveTelemetryPublisher.SERVICES
  assert "modelV2" not in LiveTelemetryPublisher.SERVICES


def test_health_snapshot_packs_device_state_and_flags():
  params = FakeParams(IsOffroad=False)
  monotonic_ns = 100_000_000_000
  sm = FakeSubMaster(
    deviceState=SimpleNamespace(
      started=True,
      cpuUsagePercent=[10, 55, 30, 40], gpuUsagePercent=42, memoryUsagePercent=61, freeSpacePercent=73.4,
      cpuTempC=[48.5, 51.2], gpuTempC=[44.0], memoryTempC=47.5, maxTempC=52.0, intakeTempC=33.0,
      thermalStatus=0, fanSpeedPercentDesired=30, powerDrawW=12.5, somPowerDrawW=8.25,
      carBatteryCapacityUwh=20_000_000, screenBrightnessPercent=80,
      networkType=1, networkStrength=4, networkMetered=False,
      lastAthenaPingTime=monotonic_ns - 10_000_000_000,
    ),
  )

  snapshot = build_health_snapshot(sm, params, monotonic_ns)
  frame = snapshot.pack(321, 0x0BADCAFE)

  assert len(frame) == LIVE_FRAME_SIZE
  assert struct.unpack_from("<2sBBHHII", frame) == (
    LIVE_FRAME_MAGIC, LIVE_PROTOCOL_VERSION, LIVE_FRAME_TYPE_HEALTH, LIVE_FRAME_SIZE, 321, 0x0BADCAFE, snapshot.flags,
  )
  payload = struct.unpack_from("<4B5h2B3H4BI18x", frame, 16)
  assert payload == (55, 42, 61, 73, 512, 440, 475, 520, 330, 0, 30, 1250, 825, 200, 80, 1, 4, 0, 100)

  flags = HealthFlags(snapshot.flags)
  for expected in (HealthFlags.ONROAD, HealthFlags.WIFI_CONNECTED, HealthFlags.LOCAL_NON_METERED_LINK,
                   HealthFlags.THERMAL_OK, HealthFlags.FAN_ACTIVE, HealthFlags.CLOUD_PINGED):
    assert flags & expected
  for absent in (HealthFlags.OFFROAD, HealthFlags.NETWORK_METERED, HealthFlags.CELLULAR_CONNECTED,
                 HealthFlags.THERMAL_OVERHEATED, HealthFlags.THERMAL_CRITICAL, HealthFlags.LOW_STORAGE):
    assert not flags & absent
  assert not snapshot.flags & (1 << 12)  # reserved and intentionally unused

  fragments = live_notification_fragments(frame)
  assert len(fragments) == LIVE_NOTIFICATION_FRAGMENT_COUNT
  assert b"".join(fragment[4:] for fragment in fragments) == frame


def test_health_snapshot_reports_offroad_metered_and_low_storage():
  params = FakeParams(IsOffroad=True)
  sm = FakeSubMaster(
    deviceState=SimpleNamespace(
      started=False, freeSpacePercent=4.0, thermalStatus=2, fanSpeedPercentDesired=0,
      networkType=4, networkStrength=2, networkMetered=True, carBatteryCapacityUwh=0,
    ),
  )

  snapshot = build_health_snapshot(sm, params)
  flags = HealthFlags(snapshot.flags)

  assert flags & HealthFlags.OFFROAD
  assert flags & HealthFlags.NETWORK_METERED
  assert flags & HealthFlags.CELLULAR_CONNECTED
  assert flags & HealthFlags.THERMAL_OVERHEATED
  assert flags & HealthFlags.LOW_STORAGE
  assert not flags & HealthFlags.ONROAD
  assert not flags & HealthFlags.LOCAL_NON_METERED_LINK  # cellular + metered → no local non-metered link
  assert not flags & HealthFlags.FAN_ACTIVE


def test_live_publisher_interleaves_frame_types_on_one_sequence():
  publisher = LiveTelemetryPublisher(lambda _frame: None, FakeParams(), FakeParams(), monotonic=lambda: 1.0)
  sm = FakeSubMaster()

  state = publisher.publish_once(sm)
  health = publisher.publish_health_once(sm)

  assert [frame[3] for frame in (state, health)] == [LIVE_FRAME_TYPE_STATE, LIVE_FRAME_TYPE_HEALTH]
  assert [struct.unpack_from("<H", frame, 6)[0] for frame in (state, health)] == [0, 1]
  assert all(len(frame) == LIVE_FRAME_SIZE for frame in (state, health))


def test_live_health_frame_rate_matches_total():
  health_slots = {tick for tick in range(LIVE_FRAME_RATE_HZ) if tick % LIVE_HEALTH_TICK_DIVISOR == 0}

  assert len(health_slots) == LIVE_HEALTH_FRAME_RATE_HZ
  assert LIVE_TOTAL_FRAME_RATE_HZ == LIVE_FRAME_RATE_HZ + LIVE_HEALTH_FRAME_RATE_HZ


def test_companion_gatt_contract_requires_authenticated_characteristics():
  app = object.__new__(CompanionGattApplication)
  objects = app.managed_objects()

  assert objects[COMPANION_SERVICE_PATH]["org.bluez.GattService1"]["UUID"] == ("s", COMPANION_SERVICE_UUID)
  assert objects[COMPANION_STATUS_PATH]["org.bluez.GattCharacteristic1"]["Flags"] == ("as", ["encrypt-authenticated-read"])
  assert objects[COMPANION_COMMAND_PATH]["org.bluez.GattCharacteristic1"]["Flags"] == ("as", ["encrypt-authenticated-write"])
  assert objects[COMPANION_RESPONSE_PATH]["org.bluez.GattCharacteristic1"]["Flags"] == ("as", ["encrypt-authenticated-read"])
  assert objects[COMPANION_LIVE_PATH]["org.bluez.GattCharacteristic1"]["UUID"] == ("s", COMPANION_LIVE_UUID)
  assert objects[COMPANION_LIVE_PATH]["org.bluez.GattCharacteristic1"]["Flags"] == (
    "as", ["encrypt-authenticated-read", "encrypt-authenticated-notify", "notify"])


def test_companion_live_characteristic_reads_and_notifies():
  class FakeFilter:
    def __init__(self):
      self.messages = queue.Queue()

    def __enter__(self):
      return self.messages

    def __exit__(self, *_args):
      pass

  class FakeRouter:
    def __init__(self):
      self.message_filter = FakeFilter()
      self.sent = []

    def filter(self, *_args, **_kwargs):
      return self.message_filter

    def send(self, message):
      self.sent.append(message)

  def message(member, signature=None, body=()):
    request = new_method_call(
      DBusAddress(COMPANION_LIVE_PATH, bus_name="org.bluez", interface=GATT_CHARACTERISTIC_IFACE),
      member, signature, body,
    )
    request.header.serial = 1
    return request

  class FakePublisher:
    def __init__(self):
      self.started = False
      self.closed = False

    def start(self):
      self.started = True

    def close(self):
      self.closed = True

  publishers = []
  router = FakeRouter()
  protocol = CompanionProtocol(
    FakeParams(IsOffroad=False, DrivingModel="model"),
    publisher_factory=lambda *_args: publishers.append(FakePublisher()) or publishers[-1],
  )
  app = CompanionGattApplication(router, lambda *_args: (), lambda path: path == "/phone/one", protocol)
  app._registered = True

  read = message("ReadValue", "a{sv}", ({"device": ("o", "/phone/one"), "link": ("s", "LE")},))
  assert len(app._dispatch(read).body[0]) == LIVE_FRAME_SIZE
  assert publishers == []

  app._dispatch(message("StartNotify"))
  assert publishers[0].started
  frame = LiveSnapshot().pack(7, 100)
  protocol._publish_live(frame)
  notification_values = [signal.body[1]["Value"][1] for signal in router.sent[-LIVE_NOTIFICATION_FRAGMENT_COUNT:]]
  assert b"".join(value[4:] for value in notification_values) == frame
  assert len(router.sent[-1].serialise(2)) > 0

  app._dispatch(message("StopNotify"))
  assert publishers[0].closed
  notifications = len(router.sent)
  cached_frame = LiveSnapshot().pack(8, 200)
  protocol._publish_live(cached_frame)
  assert len(router.sent) == notifications
  assert app._dispatch(read).body[0] == cached_frame
  app._dispatch(message("StartNotify"))
  assert len(publishers) == 2 and publishers[1].started
  app._dispatch(message("StopNotify"))
  assert publishers[1].closed
  app.close()


def test_companion_start_notify_cannot_outlive_application_close():
  class FakeFilter:
    def __init__(self):
      self.messages = queue.Queue()

    def __enter__(self):
      return self.messages

    def __exit__(self, *_args):
      pass

  class FakeRouter:
    def __init__(self):
      self.message_filter = FakeFilter()

    def filter(self, *_args, **_kwargs):
      return self.message_filter

    def send(self, _message):
      pass

  start_entered = threading.Event()
  allow_start = threading.Event()

  class BlockingPublisher:
    def __init__(self):
      self.active = False
      self.closed = False

    def start(self):
      start_entered.set()
      assert allow_start.wait(1.0)
      self.active = True

    def close(self):
      self.active = False
      self.closed = True

  publisher = BlockingPublisher()
  protocol = CompanionProtocol(FakeParams(), publisher_factory=lambda *_args: publisher)
  app = CompanionGattApplication(FakeRouter(), lambda *_args: (), lambda _path: False, protocol)
  start_errors = []

  def start_notifying():
    try:
      app._set_notifying(True)
    except Exception as error:
      start_errors.append(error)

  start_thread = threading.Thread(target=start_notifying)
  start_thread.start()
  assert start_entered.wait(1.0)

  close_entered = threading.Event()
  close_finished = threading.Event()

  def close_app():
    close_entered.set()
    app.close()
    close_finished.set()

  close_thread = threading.Thread(target=close_app)
  close_thread.start()
  assert close_entered.wait(1.0)
  assert not close_finished.wait(0.05)

  allow_start.set()
  start_thread.join(timeout=1.0)
  close_thread.join(timeout=1.0)

  assert not start_thread.is_alive() and not close_thread.is_alive()
  assert start_errors == []
  assert publisher.closed and not publisher.active
  assert protocol._publisher is None


def test_companion_start_notify_failure_rolls_back_and_can_retry():
  class FakeFilter:
    def __init__(self):
      self.messages = queue.Queue()

    def __enter__(self):
      return self.messages

    def __exit__(self, *_args):
      pass

  class FakeRouter:
    def __init__(self):
      self.message_filter = FakeFilter()
      self.sent = []

    def filter(self, *_args, **_kwargs):
      return self.message_filter

    def send(self, message):
      self.sent.append(message)

  class FakePublisher:
    def __init__(self, fail):
      self.fail = fail
      self.active = False
      self.closed = False

    def start(self):
      if self.fail:
        raise RuntimeError("publisher failed to start")
      self.active = True

    def close(self):
      self.active = False
      self.closed = True

  publishers = []

  def publisher_factory(*_args):
    publisher = FakePublisher(fail=not publishers)
    publishers.append(publisher)
    return publisher

  protocol = CompanionProtocol(FakeParams(), publisher_factory=publisher_factory)
  app = CompanionGattApplication(FakeRouter(), lambda *_args: (), lambda _path: False, protocol)

  with pytest.raises(RuntimeError, match="publisher failed"):
    app._set_notifying(True)
  assert not app._notifying
  assert publishers[0].closed
  assert protocol._publisher is None

  app._set_notifying(True)
  assert app._notifying and publishers[1].active
  app._set_notifying(False)
  assert not app._notifying and publishers[1].closed
  app.close()


def test_companion_rearm_advertisement_reregisters_broadcast():
  class FakeFilter:
    def __init__(self):
      self.messages = queue.Queue()

    def __enter__(self):
      return self.messages

    def __exit__(self, *_args):
      pass

  class FakeRouter:
    def __init__(self):
      self.message_filter = FakeFilter()

    def filter(self, *_args, **_kwargs):
      return self.message_filter

    def send(self, _message):
      pass

  calls = []
  app = CompanionGattApplication(FakeRouter(), lambda *args: calls.append(args), lambda _path: False)

  app.rearm_advertisement()
  assert calls == []

  app._registered = True
  app._adapter_path = "/org/bluez/hci0"
  app.rearm_advertisement()
  members = [call[2] for call in calls]
  assert members == ["UnregisterAdvertisement", "RegisterAdvertisement"]
  assert all(call[0] == "/org/bluez/hci0" for call in calls)

  app.close()
  calls.clear()
  app.rearm_advertisement()
  assert calls == []


def test_companion_gatt_exports_serializable_bluez_objects():
  app = object.__new__(CompanionGattApplication)

  object_manager = new_method_call(
    DBusAddress(COMPANION_APP_PATH, bus_name="org.bluez", interface=OBJECT_MANAGER_IFACE), "GetManagedObjects",
  )
  object_manager.header.serial = 1
  assert len(app._dispatch(object_manager).serialise(2)) > 0

  advertisement = new_method_call(
    DBusAddress(COMPANION_ADVERTISEMENT_PATH, bus_name="org.bluez", interface=PROPERTIES_IFACE),
    "GetAll", "s", (ADVERTISEMENT_IFACE,),
  )
  advertisement.header.serial = 1
  response = app._dispatch(advertisement)
  assert response.body[0]["ServiceUUIDs"] == ("as", [COMPANION_SERVICE_UUID])
  assert len(response.serialise(2)) > 0


def test_companion_gatt_close_is_idempotent():
  class FakeFilter:
    def __init__(self):
      self.messages = queue.Queue()
      self.exit_count = 0

    def __enter__(self):
      return self.messages

    def __exit__(self, *_args):
      self.exit_count += 1

  class FakeRouter:
    def __init__(self):
      self.message_filter = FakeFilter()

    def filter(self, *_args, **_kwargs):
      return self.message_filter

    def send(self, _message):
      pass

  router = FakeRouter()
  app = CompanionGattApplication(router, lambda *_args: (), lambda _path: False)

  app.close()
  app.close()

  assert router.message_filter.exit_count == 1
  assert not app._thread.is_alive()


def test_companion_gatt_rejects_unbonded_access_and_scopes_responses_by_phone():
  protocol = CompanionProtocol(FakeParams(IsOffroad=True))
  app = object.__new__(CompanionGattApplication)
  app.protocol = protocol
  app._authorize = lambda path: path == "/phone/one"
  app._responses = {}

  def message(path, member, signature, body):
    request = new_method_call(DBusAddress(path, bus_name="org.bluez", interface=GATT_CHARACTERISTIC_IFACE), member, signature, body)
    request.header.serial = 1
    return request

  unbonded = message(COMPANION_STATUS_PATH, "ReadValue", "a{sv}", (
    {"device": ("o", "/phone/two"), "link": ("s", "LE")},
  ))
  with pytest.raises(PermissionError, match="LE bonded"):
    app._dispatch(unbonded)

  classic = message(COMPANION_STATUS_PATH, "ReadValue", "a{sv}", (
    {"device": ("o", "/phone/one"), "link": ("s", "BR/EDR")},
  ))
  with pytest.raises(PermissionError, match="LE bonded"):
    app._dispatch(classic)

  write = message(COMPANION_COMMAND_PATH, "WriteValue", "aya{sv}", (
    b'{"id":"one","op":"ping"}', {"device": ("o", "/phone/one"), "link": ("s", "LE")},
  ))
  app._dispatch(write)
  read = message(COMPANION_RESPONSE_PATH, "ReadValue", "a{sv}", (
    {"device": ("o", "/phone/one"), "link": ("s", "LE")},
  ))
  response = json.loads(app._dispatch(read).body[0])
  assert response["id"] == "one" and response["ok"]
  assert "/phone/two" not in app._responses


def test_pairing_list_filters_anonymous_and_irrelevant_advertisements():
  assert not show_pairing_device("00:11:22:33:44:55", "00:11:22:33:44:55", False, False, False, False, False, False)
  assert not show_pairing_device("00:11:22:33:44:55", "Nearby sensor", False, False, False, False, False, False)
  assert show_pairing_device("00:11:22:33:44:55", "Media Remote", False, False, False, False, False, True)
  assert show_pairing_device("00:11:22:33:44:55", "Media Remote", False, False, False, False, False, True, True)
  assert not show_pairing_device("00:11:22:33:44:55", "Nearby sensor", False, False, False, False, False, False, True)
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

  client.start_companion_pairing()
  companion = client.status()
  assert companion.companion_enabled and companion.companion_pairing
  assert 115 <= companion.companion_pairing_remaining <= 120
  client.stop_companion_pairing()
  assert not client.status().companion_pairing

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


def test_pairing_agent_auto_accept_handler():
  agent = PairingAgent()
  assert not agent.should_auto_accept("/device")  # no handler installed
  agent.auto_accept_handler = lambda path: path == "/phone"
  assert agent.should_auto_accept("/phone")
  assert not agent.should_auto_accept("/speaker")
  agent.auto_accept_handler = lambda path: (_ for _ in ()).throw(RuntimeError("boom"))
  assert not agent.should_auto_accept("/phone")


def test_bluez_disconnect_waits_for_confirmed_state(monkeypatch):
  client = object.__new__(BlueZClient)
  states = iter((True, True, False))
  calls = []
  client.device_for_address = lambda _address: {"path": "/phone", "connected": next(states)}
  client._call = lambda *args, **kwargs: calls.append((args, kwargs))
  monkeypatch.setattr("openpilot.starpilot.system.bluetooth.bluez.time.sleep", lambda _delay: None)

  client.disconnect("00:11:22:33:44:55")

  assert calls[0][0][:3] == ("/phone", "org.bluez.Device1", "Disconnect")


def test_bluez_disconnect_accepts_removed_device_as_disconnected():
  client = object.__new__(BlueZClient)
  calls = 0

  def device_for_address(_address):
    nonlocal calls
    calls += 1
    if calls == 1:
      return {"path": "/phone", "connected": True}
    raise RuntimeError("Bluetooth device was not found")

  client.device_for_address = device_for_address
  client._call = lambda *_args, **_kwargs: None

  client.disconnect("00:11:22:33:44:55")


def test_bluez_companion_lookup_requires_persisted_bond():
  client = object.__new__(BlueZClient)
  path = "/org/bluez/hci0/dev_phone"
  props = {
    "Address": "00:11:22:33:44:55",
    "Name": "iPhone",
    "Paired": True,
    "Bonded": False,
    "Trusted": False,
    "Connected": True,
  }
  client.managed_objects = lambda: {path: {"org.bluez.Device1": props}}

  assert client.paired_device_for_path(path) is None
  props["Bonded"] = True
  assert client.paired_device_for_path(path) == {
    "path": path,
    "address": "00:11:22:33:44:55",
    "name": "iPhone",
    "paired": True,
    "bonded": True,
    "trusted": False,
    "connected": True,
  }


def test_bluez_start_discovery_is_idempotent_when_already_discovering():
  client = object.__new__(BlueZClient)
  client.adapter = lambda: ("/org/bluez/hci0", {"Discovering": True})
  client._call = lambda *_args, **_kwargs: pytest.fail("StartDiscovery should not be repeated")

  client.start_discovery()


def test_bluez_start_discovery_accepts_in_progress_race():
  client = object.__new__(BlueZClient)
  client.adapter = lambda: ("/org/bluez/hci0", {"Discovering": False})
  client._call = lambda *_args, **_kwargs: (_ for _ in ()).throw(
    BlueZError("org.bluez.Error.InProgress", "Operation already in progress"),
  )

  client.start_discovery()


def test_bluez_start_discovery_preserves_other_errors():
  client = object.__new__(BlueZClient)
  client.adapter = lambda: ("/org/bluez/hci0", {"Discovering": False})
  client._call = lambda *_args, **_kwargs: (_ for _ in ()).throw(
    BlueZError("org.bluez.Error.Failed", "Discovery failed"),
  )

  with pytest.raises(RuntimeError, match="Discovery failed"):
    client.start_discovery()


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


def test_companion_pairing_window_and_bond_authorization():
  params = TypedJsonFakeParams(IsOffroad=True, BluetoothEnabled=True, BluetoothCompanionEnabled=False)
  client = FakeBlueZ()
  client.device.update({"name": "Phone", "audio": False, "trusted": False})
  companions = []

  def companion_factory(*args):
    companions.append(FakeCompanion(*args))
    return companions[-1]

  radio = FakeRadio()
  controller = BluetoothController(params, lambda: client, radio, companion_factory=companion_factory)
  controller.handle({"command": "start_companion_pairing"})
  assert params.get_bool("BluetoothCompanionEnabled")
  assert companions[0].started == "/org/bluez/hci0"
  status = controller.status()
  assert status["companion_pairing"] and 115 <= status["companion_pairing_remaining"] <= 120
  assert ("pairing_mode", True) in client.actions
  assert companions[0].rearmed == 0

  assert companions[0].authorize("/org/bluez/hci0/dev_phone")
  assert params.get("BluetoothCompanionDevices") == ["00:11:22:33:44:55"]
  assert ("property", "00:11:22:33:44:55", "Trusted", "b", True) in client.actions
  status = controller.status()
  assert status["companion_enabled"]
  assert status["companion_devices"] == ["00:11:22:33:44:55"]
  assert not status["companion_pairing"]
  assert client.actions[-1] == ("pairing_mode", False)
  assert radio.connectable[-1] is True

  controller.handle({"command": "set_companion", "enabled": False})
  assert companions[0].closed and not params.get_bool("BluetoothCompanionEnabled")

  controller.handle({"command": "forget", "address": client.device["address"]})
  assert params.get("BluetoothCompanionDevices") == []


def test_companion_bond_auto_accepts_but_waits_for_le_gatt_authorization():
  params = TypedJsonFakeParams(
    IsOffroad=True,
    BluetoothEnabled=True,
    BluetoothCompanionEnabled=False,
    BluetoothCompanionDevices=[],
  )
  client = FakeBlueZ()
  client.device.update({"name": "Phone", "audio": False, "trusted": False})
  companions = []
  controller = BluetoothController(
    params, lambda: client, FakeRadio(),
    companion_factory=lambda *args: companions.append(FakeCompanion(*args)) or companions[-1],
  )
  controller.handle({"command": "start_companion_pairing"})

  assert client.agent.auto_accept_handler("/org/bluez/hci0/dev_phone")

  controller._pairing_address = "AA:BB:CC:DD:EE:FF"
  assert not client.agent.auto_accept_handler("/org/bluez/hci0/dev_other")
  controller._pairing_address = ""

  controller._maintain_pending_companions()
  assert params.get("BluetoothCompanionDevices") == []
  assert controller.status()["companion_pairing"]

  assert companions[0].authorize("/org/bluez/hci0/dev_phone")
  assert params.get("BluetoothCompanionDevices") == ["00:11:22:33:44:55"]
  assert ("property", "00:11:22:33:44:55", "Trusted", "b", True) in client.actions
  status = controller.status()
  assert status["companion_devices"] == ["00:11:22:33:44:55"]
  assert not status["companion_pairing"]
  assert client.actions[-1] == ("pairing_mode", False)


def test_companion_authorization_waits_for_auto_accepted_bond_to_settle():
  class SettlingBondBlueZ(FakeBlueZ):
    def __init__(self):
      super().__init__()
      self.lookup_count = 0

    def paired_device_for_path(self, path):
      self.lookup_count += 1
      if self.lookup_count <= 2:
        return None
      return super().paired_device_for_path(path)

  params = TypedJsonFakeParams(IsOffroad=True, BluetoothEnabled=True, BluetoothCompanionEnabled=False)
  client = SettlingBondBlueZ()
  client.device.update({"name": "iPhone", "audio": False, "trusted": False})
  sleeps = []
  companions = []
  controller = BluetoothController(
    params, lambda: client, FakeRadio(), sleep=lambda delay: sleeps.append(delay),
    companion_factory=lambda *args: companions.append(FakeCompanion(*args)) or companions[-1],
  )
  controller.handle({"command": "start_companion_pairing"})

  assert client.agent.auto_accept_handler("/org/bluez/hci0/dev_phone")
  assert companions[0].authorize("/org/bluez/hci0/dev_phone")
  assert sleeps == [COMPANION_BOND_SETTLE_INTERVAL]
  assert params.get("BluetoothCompanionDevices") == [client.device["address"]]
  assert "/org/bluez/hci0/dev_phone" not in controller._pending_companion_paths


def test_companion_authorization_waits_for_just_works_bond_without_agent_callback():
  class SettlingJustWorksBlueZ(FakeBlueZ):
    def __init__(self):
      super().__init__()
      self.lookup_count = 0

    def paired_device_for_path(self, path):
      self.lookup_count += 1
      if self.lookup_count <= 2:
        return None
      return super().paired_device_for_path(path)

  params = TypedJsonFakeParams(IsOffroad=True, BluetoothEnabled=True, BluetoothCompanionEnabled=False)
  client = SettlingJustWorksBlueZ()
  client.device.update({"name": "iPhone", "audio": False, "trusted": False})
  sleeps = []
  companions = []
  controller = BluetoothController(
    params, lambda: client, FakeRadio(), sleep=lambda delay: sleeps.append(delay),
    companion_factory=lambda *args: companions.append(FakeCompanion(*args)) or companions[-1],
  )
  controller.handle({"command": "start_companion_pairing"})

  assert companions[0].authorize("/org/bluez/hci0/dev_phone")
  assert sleeps == [COMPANION_BOND_SETTLE_INTERVAL, COMPANION_BOND_SETTLE_INTERVAL]
  assert params.get("BluetoothCompanionDevices") == [client.device["address"]]


def test_phone_pair_forget_repair_and_reconnect_workflow():
  class WorkflowBlueZ(FakeBlueZ):
    def __init__(self):
      super().__init__()
      self.present = False
      self.device.update({"name": "iPhone", "paired": False, "trusted": False, "connected": False,
                          "audio": False, "controller": False})

    def status(self):
      devices = [dict(self.device)] if self.present else []
      return {"powered": self.powered, "discovering": self.discovering, "devices": devices, "prompt": None}

    def device_for_address(self, address):
      if not self.present or address.upper() != self.device["address"].upper():
        raise RuntimeError(f"Bluetooth device {address} was not found")
      return dict(self.device)

    def paired_device_for_path(self, path):
      if not self.present:
        return None
      return super().paired_device_for_path(path)

    def remove(self, address):
      self.device_for_address(address)
      self.actions.append(("remove", address))
      self.present = False
      self.device.update({"paired": False, "trusted": False, "connected": False})

    def bond_phone(self, connected=True):
      self.present = True
      self.device.update({"paired": True, "trusted": False, "connected": connected})

  params = TypedJsonFakeParams(
    IsOffroad=True,
    BluetoothEnabled=True,
    BluetoothCompanionEnabled=False,
    BluetoothCompanionDevices=[],
  )
  client = WorkflowBlueZ()
  companions = []
  controller = BluetoothController(
    params, lambda: client, FakeRadio(),
    companion_factory=lambda *args: companions.append(FakeCompanion(*args)) or companions[-1],
  )

  initial = BluetoothStatus.from_dict(controller.status())
  assert companion_setup_visible(initial)
  assert initial.companion_devices == () and initial.devices == ()

  controller.handle({"command": "start_companion_pairing"})
  pairing = BluetoothStatus.from_dict(controller.status())
  assert pairing.companion_pairing and companion_setup_visible(pairing)

  client.bond_phone()
  assert client.agent.auto_accept_handler("/org/bluez/hci0/dev_phone")
  assert companions[0].authorize("/org/bluez/hci0/dev_phone")
  paired = BluetoothStatus.from_dict(controller.status())
  assert paired.companion_devices == (client.device["address"],)
  assert paired.companion_connected and not paired.companion_pairing
  assert companion_setup_visible(paired)

  client.device["connected"] = False
  disconnected = BluetoothStatus.from_dict(controller.status())
  assert not disconnected.companion_connected
  assert companion_setup_visible(disconnected)
  assert controller._companion is companions[0] and not companions[0].closed
  assert client.agent.auto_accept_handler("/org/bluez/hci0/dev_phone")

  client.device["connected"] = True
  assert BluetoothStatus.from_dict(controller.status()).companion_connected

  controller.handle({"command": "forget", "address": client.device["address"]})
  forgotten = BluetoothStatus.from_dict(controller.status())
  assert params.get("BluetoothCompanionDevices") == []
  assert not params.get_bool("BluetoothCompanionEnabled")
  assert forgotten.companion_devices == () and forgotten.devices == ()
  assert not forgotten.companion_connected and companion_setup_visible(forgotten)
  assert companions[0].closed and controller._companion is None
  assert not companions[0].authorize("/org/bluez/hci0/dev_phone")

  controller.handle({"command": "start_companion_pairing"})
  assert len(companions) == 2 and not companions[1].closed
  client.bond_phone()
  assert client.agent.auto_accept_handler("/org/bluez/hci0/dev_phone")
  assert companions[1].authorize("/org/bluez/hci0/dev_phone")
  repaired = BluetoothStatus.from_dict(controller.status())
  assert repaired.companion_devices == (client.device["address"],)
  assert repaired.companion_connected and companion_setup_visible(repaired)


def test_phone_is_not_saved_until_bluez_trust_succeeds():
  class RetryTrustBlueZ(FakeBlueZ):
    fail_trust = True

    def set_device_property(self, address, name, signature, value):
      if name == "Trusted" and self.fail_trust:
        raise RuntimeError("unable to trust")
      super().set_device_property(address, name, signature, value)

  params = TypedJsonFakeParams(
    IsOffroad=True,
    BluetoothEnabled=True,
    BluetoothCompanionEnabled=False,
    BluetoothCompanionDevices=[],
  )
  client = RetryTrustBlueZ()
  client.device.update({"name": "iPhone", "audio": False, "trusted": False})
  controller = BluetoothController(params, lambda: client, FakeRadio(), companion_factory=lambda *args: FakeCompanion(*args))
  controller.handle({"command": "start_companion_pairing"})
  assert client.agent.auto_accept_handler("/org/bluez/hci0/dev_phone")

  with pytest.raises(RuntimeError, match="unable to trust"):
    controller._companion.authorize("/org/bluez/hci0/dev_phone")
  controller._maintain_pending_companions()
  assert params.get("BluetoothCompanionDevices") == []
  assert controller.status()["companion_pairing"]
  assert "/org/bluez/hci0/dev_phone" in controller._pending_companion_paths

  client.fail_trust = False
  controller._maintain_pending_companions()
  assert params.get("BluetoothCompanionDevices") == [client.device["address"]]
  assert not controller.status()["companion_pairing"]


def test_failed_bluez_forget_keeps_phone_authorization_and_service_state():
  class FailingRemoveBlueZ(FakeBlueZ):
    def remove(self, _address):
      raise RuntimeError("remove failed")

  address = "00:11:22:33:44:55"
  params = TypedJsonFakeParams(
    IsOffroad=True,
    BluetoothEnabled=True,
    BluetoothCompanionEnabled=True,
    BluetoothCompanionDevices=[address],
  )
  client = FailingRemoveBlueZ()
  companions = []
  controller = BluetoothController(
    params, lambda: client, FakeRadio(),
    companion_factory=lambda *args: companions.append(FakeCompanion(*args)) or companions[-1],
  )
  controller.status()

  with pytest.raises(RuntimeError, match="remove failed"):
    controller.handle({"command": "forget", "address": address})

  assert params.get("BluetoothCompanionDevices") == [address]
  assert params.get_bool("BluetoothCompanionEnabled")
  assert controller._companion is companions[0] and not companions[0].closed


def test_saved_phone_service_returns_after_bluetooth_power_cycle():
  address = "00:11:22:33:44:55"
  params = TypedJsonFakeParams(
    IsOffroad=True,
    BluetoothEnabled=True,
    BluetoothCompanionEnabled=True,
    BluetoothCompanionDevices=[address],
  )
  clients = []
  companions = []

  def client_factory():
    client = FakeBlueZ()
    client.device.update({"name": "iPhone", "audio": False, "controller": False, "connected": False})
    clients.append(client)
    return client

  controller = BluetoothController(
    params, client_factory, FakeRadio(),
    companion_factory=lambda *args: companions.append(FakeCompanion(*args)) or companions[-1],
  )
  before = BluetoothStatus.from_dict(controller.status())
  assert companion_setup_visible(before)
  assert companions[0].started == "/org/bluez/hci0"

  controller.handle({"command": "set_power", "enabled": False})
  assert companions[0].closed
  assert params.get("BluetoothCompanionDevices") == [address]
  assert params.get_bool("BluetoothCompanionEnabled")

  controller.handle({"command": "set_power", "enabled": True})
  after = BluetoothStatus.from_dict(controller.status())
  assert len(clients) == 2 and len(companions) == 2
  assert companions[1].started == "/org/bluez/hci0" and not companions[1].closed
  assert after.companion_devices == (address,)
  assert companion_setup_visible(after)


def test_reconnect_maintenance_connects_audio_and_controllers_but_not_phone_centrals():
  params = FakeParams(IsOffroad=True, BluetoothEnabled=True)
  client = FakeBlueZ()
  controller = BluetoothController(params, lambda: client, FakeRadio())
  status = controller.status()

  controller._maintain_reconnects(status, controller._last_reconnect + 15.0)
  assert client.actions[-1] == ("connect", client.device["address"])

  client.actions.clear()
  client.device.update({"connected": False, "audio": False, "controller": False})
  phone_status = controller.status()
  controller._maintain_reconnects(phone_status, controller._last_reconnect + 15.0)
  assert not any(action[0] == "connect" for action in client.actions)


def test_companion_advertisement_rearms_when_saved_phone_disconnects():
  address = "00:11:22:33:44:55"
  params = TypedJsonFakeParams(
    IsOffroad=True,
    BluetoothEnabled=True,
    BluetoothCompanionEnabled=True,
    BluetoothCompanionDevices=[address],
  )
  client = FakeBlueZ()
  client.device.update({"name": "iPhone", "audio": False, "controller": False, "connected": True})
  companions = []
  controller = BluetoothController(
    params, lambda: client, FakeRadio(),
    companion_factory=lambda *args: companions.append(FakeCompanion(*args)) or companions[-1],
  )

  controller._maintain_companion_advertisement(controller.status())
  assert companions[-1].rearmed == 0

  client.device["connected"] = False
  controller._maintain_companion_advertisement(controller.status())
  assert companions[-1].rearmed == 1

  controller._maintain_companion_advertisement(controller.status())
  assert companions[-1].rearmed == 1


def test_companion_reconnect_does_not_reregister_gatt_services():
  address = "00:11:22:33:44:55"
  params = TypedJsonFakeParams(
    IsOffroad=True,
    BluetoothEnabled=True,
    BluetoothCompanionEnabled=True,
    BluetoothCompanionDevices=[address],
  )
  client = FakeBlueZ()
  client.device.update({"name": "iPhone", "audio": False, "controller": False, "connected": True})
  companions = []
  controller = BluetoothController(
    params, lambda: client, FakeRadio(),
    companion_factory=lambda *args: companions.append(FakeCompanion(*args)) or companions[-1],
  )

  controller._maintain_companion_advertisement(controller.status())
  assert companions[-1].refreshed == 0

  controller._maintain_companion_advertisement(controller.status())
  assert companions[-1].refreshed == 0
  assert companions[-1].rearmed == 0

  client.device["connected"] = False
  controller._maintain_companion_advertisement(controller.status())
  assert companions[-1].rearmed == 1
  client.device["connected"] = True
  controller._maintain_companion_advertisement(controller.status())
  assert companions[-1].refreshed == 0
  assert companions[-1].rearmed == 1


def test_companion_advertisement_ignores_disconnect_of_unsaved_device():
  params = TypedJsonFakeParams(
    IsOffroad=True,
    BluetoothEnabled=True,
    BluetoothCompanionEnabled=True,
    BluetoothCompanionDevices=["AA:BB:CC:DD:EE:FF"],
  )
  client = FakeBlueZ()
  client.device.update({"address": "00:11:22:33:44:55", "name": "Speaker", "connected": True})
  companions = []
  controller = BluetoothController(
    params, lambda: client, FakeRadio(),
    companion_factory=lambda *args: companions.append(FakeCompanion(*args)) or companions[-1],
  )

  controller._maintain_companion_advertisement(controller.status())
  client.device["connected"] = False
  controller._maintain_companion_advertisement(controller.status())
  assert companions[-1].rearmed == 0


def test_connect_to_phone_reports_actionable_hint_and_rearms_companion():
  address = "00:11:22:33:44:55"
  params = TypedJsonFakeParams(
    IsOffroad=True,
    BluetoothEnabled=True,
    BluetoothCompanionEnabled=True,
    BluetoothCompanionDevices=[address],
  )

  class ProfileUnavailableBlueZ(FakeBlueZ):
    def __init__(self):
      super().__init__()
      self.device.update({"name": "iPhone", "audio": False, "controller": False, "trusted": False})

    def connect(self, address):
      self.actions.append(("connect", address))
      raise RuntimeError("br-connection-profile-unavailable")

  client = ProfileUnavailableBlueZ()
  companions = []
  controller = BluetoothController(params, lambda: client, FakeRadio(),
                                   companion_factory=lambda *args: companions.append(FakeCompanion(*args)) or companions[-1])

  with pytest.raises(RuntimeError, match="connect from the phone"):
    controller.handle({"command": "connect", "address": address})

  assert ("property", address, "Trusted", "b", True) in client.actions
  assert companions and companions[-1].started == "/org/bluez/hci0" and not companions[-1].closed
  assert companions[-1].rearmed == 1


def test_connect_failure_on_audio_device_keeps_the_bluez_error():
  params = FakeParams(IsOffroad=True, BluetoothEnabled=True)

  class ProfileUnavailableBlueZ(FakeBlueZ):
    def connect(self, address):
      self.actions.append(("connect", address))
      raise RuntimeError("br-connection-profile-unavailable")

  client = ProfileUnavailableBlueZ()
  controller = BluetoothController(params, lambda: client, FakeRadio())

  with pytest.raises(RuntimeError, match="br-connection-profile-unavailable"):
    controller.handle({"command": "connect", "address": client.device["address"]})


def test_connect_failure_on_unregistered_ble_device_keeps_the_bluez_error():
  params = TypedJsonFakeParams(
    IsOffroad=True,
    BluetoothEnabled=True,
    BluetoothCompanionDevices=[],
  )

  class ProfileUnavailableBlueZ(FakeBlueZ):
    def __init__(self):
      super().__init__()
      self.device.update({"name": "BLE Sensor", "audio": False, "controller": False})

    def connect(self, address):
      self.actions.append(("connect", address))
      raise RuntimeError("br-connection-profile-unavailable")

  client = ProfileUnavailableBlueZ()
  controller = BluetoothController(params, lambda: client, FakeRadio())

  with pytest.raises(RuntimeError, match="br-connection-profile-unavailable"):
    controller.handle({"command": "connect", "address": client.device["address"]})


def test_saved_companion_reenables_service_when_daemon_starts():
  params = FakeParams(
    BluetoothCompanionEnabled=False,
    BluetoothCompanionDevices='["00:11:22:33:44:55"]',
  )

  BluetoothController(params, lambda: FakeBlueZ(), FakeRadio())

  assert params.get_bool("BluetoothCompanionEnabled")


def test_known_companion_does_not_close_pairing_window_for_another_phone():
  address = "00:11:22:33:44:55"
  params = FakeParams(
    IsOffroad=True,
    BluetoothEnabled=True,
    BluetoothCompanionEnabled=True,
    BluetoothCompanionDevices=json.dumps([address]),
  )
  client = FakeBlueZ()
  companions = []
  controller = BluetoothController(
    params, lambda: client, FakeRadio(),
    companion_factory=lambda *args: companions.append(FakeCompanion(*args)) or companions[-1],
  )

  controller.handle({"command": "start_companion_pairing"})
  assert companions[0].authorize("/org/bluez/hci0/dev_phone")
  assert controller.status()["companion_pairing"]
  assert client.actions[-1] == ("pairing_mode", True)


@pytest.mark.parametrize("command_request,companion_enabled", [
  ({"command": "set_companion", "enabled": True}, False),
  ({"command": "start_companion_pairing"}, True),
  ({"command": "stop_companion_pairing"}, True),
])
def test_companion_commands_cannot_power_disabled_bluetooth(command_request, companion_enabled):
  params = FakeParams(IsOffroad=True, BluetoothEnabled=False, BluetoothCompanionEnabled=companion_enabled)
  client = FakeBlueZ()
  radio = FakeRadio()
  factory_calls = []

  def client_factory():
    factory_calls.append(True)
    return client

  controller = BluetoothController(params, client_factory, radio)

  with pytest.raises(RuntimeError, match="Enable Bluetooth"):
    controller.handle(command_request)

  assert factory_calls == []
  assert radio.starts == 0
  assert controller._bluez is None
  assert not client.powered


def test_companion_pairing_is_offroad_only_and_rejects_unbonded_phone():
  params = FakeParams(
    IsOffroad=False,
    BluetoothEnabled=True,
    BluetoothCompanionEnabled=True,
    BluetoothCompanionDevices=json.dumps(["00:11:22:33:44:55"]),
  )
  client = FakeBlueZ()
  client.device["paired"] = False
  companions = []
  controller = BluetoothController(
    params, lambda: client, FakeRadio(),
    companion_factory=lambda *args: companions.append(FakeCompanion(*args)) or companions[-1],
  )

  with pytest.raises(RuntimeError, match="offroad"):
    controller.handle({"command": "start_companion_pairing"})
  controller.status()
  assert not companions[0].authorize("/org/bluez/hci0/dev_phone")


def test_companion_disable_does_not_fail_open_when_pairing_close_fails():
  params = FakeParams(IsOffroad=True, BluetoothEnabled=True, BluetoothCompanionEnabled=False)
  client = FakeBlueZ()
  companions = []
  controller = BluetoothController(
    params, lambda: client, FakeRadio(),
    companion_factory=lambda *args: companions.append(FakeCompanion(*args)) or companions[-1],
  )
  controller.handle({"command": "set_companion", "enabled": True})
  controller.handle({"command": "start_companion_pairing"})

  client.pairing_mode_error = RuntimeError("adapter busy")
  with pytest.raises(RuntimeError, match="adapter busy"):
    controller.handle({"command": "set_companion", "enabled": False})
  assert params.get_bool("BluetoothCompanionEnabled")
  assert controller._companion is companions[0] and not companions[0].closed
  assert controller.status()["companion_pairing"]

  client.pairing_mode_error = None
  controller.handle({"command": "set_companion", "enabled": False})
  assert not params.get_bool("BluetoothCompanionEnabled")
  assert companions[0].closed


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
