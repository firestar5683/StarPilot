from types import SimpleNamespace
import pytest
from test_navigation_params import _params_client, the_galaxy


def client_for(monkeypatch, supported=True, onroad=False):
  client, params = _params_client(monkeypatch, {"IsOnroad": onroad, "TeslaWakeOnCAN": False}, "pc")
  monkeypatch.setattr(the_galaxy, "_get_param_type_info", lambda: ({"TeslaWakeOnCAN"}, {"TeslaWakeOnCAN": bool}))
  monkeypatch.setattr(the_galaxy, "supports_tesla_can_wake", lambda _: supported, raising=False)
  monkeypatch.setattr(the_galaxy, "update_starpilot_toggles", lambda: None)
  monkeypatch.setattr(the_galaxy, "validate_tesla_can_wake_firmware", lambda *_: None, raising=False)
  launches = []
  monkeypatch.setattr(the_galaxy.threading, "Thread", lambda **kw: SimpleNamespace(start=lambda: launches.append(kw["target"])))
  return client, params, launches


@pytest.mark.parametrize("supported,onroad,confirmed,status", [
  (False, False, True, 403), (True, True, True, 403), (True, False, False, 409),
])
def test_tesla_firmware_rejects_unsupported_onroad_or_unconfirmed_write(monkeypatch, supported, onroad, confirmed, status):
  client, params, launches = client_for(monkeypatch, supported, onroad)
  response = client.put("/api/params", json={"key": "TeslaWakeOnCAN", "value": True, "confirmedPandaFirmwareFlash": confirmed})
  assert response.status_code == status
  assert params.values["TeslaWakeOnCAN"] is False
  assert not launches


@pytest.mark.parametrize("enabled", [False, True])
def test_tesla_firmware_confirmed_offroad_write_launches_flash(monkeypatch, enabled):
  client, params, launches = client_for(monkeypatch)
  response = client.put("/api/params", json={"key": "TeslaWakeOnCAN", "value": enabled, "confirmedPandaFirmwareFlash": True})
  assert response.status_code == 200
  assert params.get_bool("TeslaWakeOnCAN") is enabled
  assert launches == [the_galaxy._flash_panda_then_reboot]


def test_missing_tesla_firmware_does_not_save_or_flash(monkeypatch):
  client, params, launches = client_for(monkeypatch)
  def unavailable(*_):
    raise RuntimeError("Tesla firmware is missing")
  monkeypatch.setattr(the_galaxy, "validate_tesla_can_wake_firmware", unavailable)
  response = client.put("/api/params", json={"key": "TeslaWakeOnCAN", "value": True, "confirmedPandaFirmwareFlash": True})
  assert response.status_code == 409
  assert "missing" in response.get_json()["error"]
  assert params.values["TeslaWakeOnCAN"] is False
  assert not launches


@pytest.mark.parametrize("supported", [False, True])
def test_params_payload_reports_tesla_capability_and_off_default(monkeypatch, supported):
  client, params, _ = client_for(monkeypatch, supported=supported)
  params.values.pop("TeslaWakeOnCAN")
  monkeypatch.setattr(the_galaxy, "_get_default_param_values", lambda: {"TeslaWakeOnCAN": "0"})
  response = client.get("/api/params/all")
  assert response.status_code == 200
  assert response.get_json()["TeslaCANWakeAvailable"] is supported
  assert response.get_json()["TeslaWakeOnCAN"] is False
