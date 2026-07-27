from concurrent.futures import ThreadPoolExecutor

import json
import threading
import time

from openpilot.starpilot.system import external_app_pairing as pairing
from openpilot.system.vehicle_telemetry import core


def _use_test_config(monkeypatch, tmp_path):
  config_path = tmp_path / core.VEHICLE_TELEMETRY_CONFIG_FILENAME
  monkeypatch.setattr(
    pairing,
    "update_vehicle_telemetry_config",
    lambda mutator: core.update_vehicle_telemetry_config(mutator, config_path),
  )
  return config_path


def test_pairing_code_has_exactly_one_concurrent_redemption(monkeypatch, tmp_path):
  config_path = _use_test_config(monkeypatch, tmp_path)
  created = pairing.create_pairing(tmp_path, "http://192.168.0.75:8082", now=100.0)
  workers = 8
  barrier = threading.Barrier(workers)

  def redeem(index):
    barrier.wait()
    return pairing.complete_pairing(tmp_path, created["pairingCode"], f"Client {index}", now=101.0)

  with ThreadPoolExecutor(max_workers=workers) as executor:
    results = list(executor.map(redeem, range(workers)))

  successes = [connection for connection, error in results if connection is not None and error is None]
  errors = [error for connection, error in results if connection is None]
  assert len(successes) == 1
  assert errors == ["No external-app pairing is waiting"] * (workers - 1)
  assert not pairing.pairing_path(tmp_path).exists()
  assert not (tmp_path / pairing.PAIRING_CLAIM_FILENAME).exists()

  config = core.load_vehicle_telemetry_config(config_path)
  assert config["mode"] == "galaxy"
  assert config["fetch"]["enabled"]
  assert len(config["fetch"]["clients"]) == 1
  issued_token = successes[0]["capabilities"]["vehicleTelemetry"]["bearerToken"]
  assert config["fetch"]["clients"][0]["token"] == issued_token


def test_concurrent_invalid_attempts_cannot_bypass_attempt_limit(monkeypatch, tmp_path):
  _use_test_config(monkeypatch, tmp_path)
  created = pairing.create_pairing(tmp_path, "http://192.168.0.75:8082", now=100.0)
  invalid_code = "000000" if created["pairingCode"] != "000000" else "999999"
  workers = pairing.MAX_PAIRING_ATTEMPTS
  barrier = threading.Barrier(workers)

  def reject(_index):
    barrier.wait()
    return pairing.complete_pairing(tmp_path, invalid_code, "Bad client", now=101.0)

  with ThreadPoolExecutor(max_workers=workers) as executor:
    results = list(executor.map(reject, range(workers)))

  assert results == [(None, "The external-app pairing code is invalid")] * workers
  assert not pairing.pairing_path(tmp_path).exists()
  assert not (tmp_path / pairing.PAIRING_CLAIM_FILENAME).exists()
  assert pairing.complete_pairing(tmp_path, created["pairingCode"], "Late client", now=101.0) == (
    None,
    "No external-app pairing is waiting",
  )


def test_invalid_attempt_is_atomically_persisted_for_the_next_request(monkeypatch, tmp_path):
  _use_test_config(monkeypatch, tmp_path)
  created = pairing.create_pairing(tmp_path, "http://192.168.0.75:8082", now=100.0)
  invalid_code = "000000" if created["pairingCode"] != "000000" else "999999"

  assert pairing.complete_pairing(tmp_path, invalid_code, "Bad client", now=101.0)[1] == "The external-app pairing code is invalid"
  record = json.loads(pairing.pairing_path(tmp_path).read_text(encoding="utf-8"))
  assert record["attempts"] == 1
  assert not (tmp_path / pairing.PAIRING_CLAIM_FILENAME).exists()


def test_shared_config_update_lock_preserves_concurrent_mutations(tmp_path):
  config_path = tmp_path / core.VEHICLE_TELEMETRY_CONFIG_FILENAME
  core.save_vehicle_telemetry_config({}, config_path)
  first_entered = threading.Event()
  release_first = threading.Event()
  entries = []

  def update_push(config):
    entries.append("push")
    first_entered.set()
    assert release_first.wait(timeout=2.0)
    config["push"]["vehicleName"] = "EV9"
    return config

  def update_fetch(config):
    entries.append("fetch")
    config["fetch"]["port"] = 17766
    return config

  with ThreadPoolExecutor(max_workers=2) as executor:
    first = executor.submit(core.update_vehicle_telemetry_config, update_push, config_path)
    assert first_entered.wait(timeout=2.0)
    second = executor.submit(core.update_vehicle_telemetry_config, update_fetch, config_path)
    time.sleep(0.05)
    assert entries == ["push"]
    release_first.set()
    first.result(timeout=2.0)
    second.result(timeout=2.0)

  config = core.load_vehicle_telemetry_config(config_path)
  assert entries == ["push", "fetch"]
  assert config["push"]["vehicleName"] == "EV9"
  assert config["fetch"]["port"] == 17766
