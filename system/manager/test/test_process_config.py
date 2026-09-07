from types import SimpleNamespace

import pytest

from cereal import car
from opendbc.car.ford.values import CAR as FORD_CAR
from opendbc.car.gm.values import CAR as GM_CAR
import openpilot.system.manager.process_config as process_config
from openpilot.system.manager.process_config import (
  allow_uploads,
  bluetooth_enabled,
  camera_run,
  managed_processes,
  sentry_mode,
  soundd_run,
  ublox,
  wheel_controls_enabled,
)


class FakeParams:
  def __init__(self, always_allow_uploads: bool = False):
    self.always_allow_uploads = always_allow_uploads

  def get_bool(self, key: str) -> bool:
    assert key == "AlwaysAllowUploads"
    return self.always_allow_uploads


@pytest.mark.parametrize(
  "started,no_uploads,no_onroad_uploads,always_allow_uploads,expected",
  [
    (True, False, False, False, True),
    (False, False, False, False, True),
    (True, True, False, False, False),
    (False, True, False, False, False),
    (True, True, True, False, False),
    (False, True, True, False, True),
    (True, True, False, True, True),
  ],
)
def test_allow_uploads(started, no_uploads, no_onroad_uploads, always_allow_uploads, expected):
  params = FakeParams(always_allow_uploads)
  toggles = SimpleNamespace(no_uploads=no_uploads, no_onroad_uploads=no_onroad_uploads)

  assert allow_uploads(started, params, car.CarParams.new_message(), toggles) is expected


def test_uploader_runs_at_background_priority():
  assert managed_processes["uploader"].nice == 19


def test_mapd_runs_onroad_or_during_offroad_map_transfer(monkeypatch):
  class MemoryParams:
    values = {}

    def __init__(self, *, memory=False):
      assert memory

    def get_bool(self, key):
      return self.values.get(key, False)

  monkeypatch.setattr(process_config, "Params", MemoryParams)
  params = object()
  CP = car.CarParams.new_message()
  toggles = SimpleNamespace()

  assert process_config.run_mapd(True, params, CP, toggles)
  assert not process_config.run_mapd(False, params, CP, toggles)

  MemoryParams.values["DownloadMaps"] = True
  assert process_config.run_mapd(False, params, CP, toggles)

  MemoryParams.values = {"DownloadMaps": False, "CancelDownloadMaps": True}
  assert process_config.run_mapd(False, params, CP, toggles)


@pytest.mark.parametrize("enabled", [False, True])
def test_bluetooth_process_is_param_gated(enabled):
  params = SimpleNamespace(get_bool=lambda key: enabled if key == "BluetoothEnabled" else False)
  assert bluetooth_enabled(False, params, car.CarParams.new_message(), SimpleNamespace()) is enabled


@pytest.mark.parametrize(
  "started,driver_view,audio_test,expected",
  [(True, False, False, True), (False, True, False, True), (False, False, True, True), (False, False, False, False)],
)
def test_soundd_runs_for_driving_and_bluetooth_audio_test(started, driver_view, audio_test, expected):
  values = {"IsDriverViewEnabled": driver_view, "BluetoothAudioTestActive": audio_test}
  params = SimpleNamespace(get_bool=lambda key: values.get(key, False))
  assert soundd_run(started, params, car.CarParams.new_message(), SimpleNamespace()) is expected


def test_wheel_controls_process_runs_on_supported_devices_at_background_priority():
  process = managed_processes["wheel_controlsd"]
  assert process.nice == 19


@pytest.mark.parametrize("enabled", [False, True])
def test_wheel_controls_process_is_mapping_gated(enabled):
  params = SimpleNamespace(get_bool=lambda key: enabled if key == "WheelControlsEnabled" else False)
  assert wheel_controls_enabled(False, params, car.CarParams.new_message(), SimpleNamespace()) is enabled


class CameraParams:
  def __init__(self, capture: bool):
    self.capture = capture

  def get_bool(self, key: str) -> bool:
    assert key in {"IsDriverViewEnabled", "SentryModeCapture"}
    return self.capture if key == "SentryModeCapture" else False


@pytest.mark.parametrize(
  "started,capture,expected",
  [
    (False, True, True),
    (False, False, False),
    (True, False, True),
  ],
)
def test_camera_run_preserves_onroad_camera_and_offroad_sentry_capture(started, capture, expected):
  assert camera_run(started, CameraParams(capture), car.CarParams.new_message(), SimpleNamespace()) is expected


class SentryParams:
  def __init__(self, enabled: bool):
    self.enabled = enabled

  def get_bool(self, key: str) -> bool:
    assert key == "SentryModeEnabled"
    return self.enabled


@pytest.mark.parametrize("started,enabled,expected", [(True, True, False), (False, True, True), (False, False, False)])
def test_sentry_process_is_offroad_only(started, enabled, expected):
  assert sentry_mode(started, SentryParams(enabled), car.CarParams.new_message(), SimpleNamespace()) is expected


class GpsParams:
  def __init__(self, CP=None):
    self.values = {}
    if CP is not None:
      self.values["CarParams"] = CP.to_bytes()

  def get(self, key: str):
    return self.values.get(key)

  def get_bool(self, key: str) -> bool:
    return bool(self.values.get(key, False))

  def put_bool(self, key: str, value: bool):
    self.values[key] = value


@pytest.mark.parametrize("brand,fingerprint,persisted,live_brand,expected,car_gps", [
  ("gm", "", False, "gm", False, False),
  ("mock", "", False, "mock", False, False),
  ("ford", "", False, "ford", False, False),
  ("gm", GM_CAR.CHEVROLET_BOLT_CC_2018_2021, False, "gm", False, False),
  ("gm", GM_CAR.CHEVROLET_BOLT_CC_2018_2021, True, "gm", True, True),
  ("gm", GM_CAR.CHEVROLET_BOLT_CC_2018_2021, True, "", True, True),
  ("gm", "unknown GM", True, "gm", True, False),
  ("mock", "mock", True, "", True, False),
  ("ford", FORD_CAR.FORD_MUSTANG_MACH_E_MK1, True, "", False, True),
  ("gm", "", "corrupt", "", False, False),
], ids=["missing-gm", "missing-mock", "missing-ford", "stale-live-cp", "persisted-gm",
        "empty-live-cp", "unknown-gm", "non-car-gps", "vehicle-gps", "corrupt-cp"])
def test_ublox_startup(monkeypatch, brand, fingerprint, persisted, live_brand, expected, car_gps):
  monkeypatch.setattr(process_config, "ublox_available", lambda: True)
  current = car.CarParams.new_message(brand=brand, carFingerprint=fingerprint)
  params = GpsParams(current if persisted is True else None)
  if persisted == "corrupt":
    params.values["CarParams"] = b"invalid_corrupt_data"
  live_cp = car.CarParams.new_message(brand=live_brand, carFingerprint=fingerprint if live_brand else "")

  assert ublox(True, params, live_cp, SimpleNamespace()) is expected
  assert params.get_bool("UbloxAvailable")
  assert params.get_bool("CarGpsAvailable") is car_gps
  assert not ublox(False, params, live_cp, SimpleNamespace())
  if persisted is False and fingerprint:
    params.values["CarParams"] = current.to_bytes()
    assert ublox(True, params, live_cp, SimpleNamespace())  # Same stale live CP, now with current persisted CP.
  monkeypatch.setattr(process_config, "ublox_available", lambda: False)
  assert not ublox(True, params, live_cp, SimpleNamespace())
