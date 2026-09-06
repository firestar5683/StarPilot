"""Exercise the actual Flask handlers in isolation, without native/device imports."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask, jsonify, request

from test_longitudinal_mode import Params, mode

SOURCE = Path(__file__).resolve().parents[1] / "the_galaxy.py"


def client_for(params, capable=True):
  tree = ast.parse(SOURCE.read_text())
  setup = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "setup")
  routes = [node for node in setup.body if isinstance(node, ast.FunctionDef) and node.name in {"longitudinal_mode", "get_param"}]
  signals = []
  app = Flask(__name__)
  env = dict(app=app, request=request, jsonify=jsonify, params=params,
             LONGITUDINAL_MODE_LOCK=mode.WRITE_LOCK, LONGITUDINAL_MODE_KEYS=mode.MODE_KEYS,
             ModeError=mode.ModeError, set_longitudinal_mode=mode.set_mode,
             longitudinal_mode_snapshot=mode.snapshot, _get_longitudinal_mode_capable=lambda: capable,
             update_starpilot_toggles=lambda: signals.append(True))
  exec(compile(ast.Module(body=routes, type_ignores=[]), str(SOURCE), "exec"), env)
  return app.test_client(), signals


def test_live_snapshot_precedence_no_load_writes():
  params = Params({"ConditionalExperimental": True, "ConditionalChill": False, "ExperimentalMode": True})
  client, signals = client_for(params)
  response = client.get("/api/longitudinal_mode")
  assert response.status_code == 200
  assert response.json["mode"] == "conditional_experimental"
  assert response.json["values"]["ExperimentalMode"] is True
  assert not params.writes and not signals


def test_put_readback_and_failed_partial_write_signal():
  params = Params(fail_at=3)
  client, signals = client_for(params)
  response = client.put("/api/longitudinal_mode", json={"mode": "experimental", "expected": params.values.copy()})
  assert response.status_code == 500
  assert signals == [True]
  assert len(params.writes) == 3
  assert client.get("/api/longitudinal_mode").json["values"] == {key: params.values[key] for key in mode.MODE_KEYS}


@pytest.mark.parametrize("body", [None, [], {}, {"mode": "bad"}, {"mode": "experimental", "expected": {}}])
def test_bad_request_rejected(body):
  params = Params()
  client, _ = client_for(params)
  assert client.put("/api/longitudinal_mode", json=body).status_code == 400
  assert not params.writes


@pytest.mark.parametrize("guard,capable", [({"IsOnroad": True}, True), ({"SafeMode": True}, True), ({}, False)])
def test_api_guards_and_legacy_favorites(guard, capable):
  params = Params(guard)
  client, _ = client_for(params, capable)
  assert client.put("/api/longitudinal_mode", json={"mode": "conditional_chill", "expected": params.values.copy()}).status_code == 403
  assert client.put("/api/params", json={"key": "ConditionalChill", "value": True}).status_code == 403
  assert not params.writes


def test_legacy_favorite_uses_guarded_adapter():
  params = Params()
  client, signals = client_for(params)
  response = client.put("/api/params", json={"key": "ConditionalChill", "value": True})
  assert response.status_code == 200
  assert response.json["updated"] == {"ConditionalChill": True, "ConditionalExperimental": False, "ExperimentalMode": False}
  assert signals == [True]
  assert client.put("/api/params", json={"key": "ExperimentalMode", "value": "true"}).status_code == 400


def test_experimental_requires_acknowledgement_does_not_mark_confirmed():
  params = Params({"ExperimentalModeConfirmed": False})
  client, _ = client_for(params)
  body = {"mode": "experimental", "expected": params.values.copy()}
  assert client.put("/api/longitudinal_mode", json=body).status_code == 409
  assert not params.writes
  assert client.put("/api/longitudinal_mode", json={**body, "acknowledged": "true"}).status_code == 409
  assert client.put("/api/longitudinal_mode", json={**body, "acknowledged": True}).status_code == 200
  assert params.values["ExperimentalModeConfirmed"] is False
  assert all(key != "ExperimentalModeConfirmed" for key, _ in params.writes)


@pytest.mark.parametrize("cp,values,expected", [
  (None, {}, False),
  (SimpleNamespace(alphaLongitudinalAvailable=False, openpilotLongitudinalControl=False), {}, False),
  (SimpleNamespace(alphaLongitudinalAvailable=False, openpilotLongitudinalControl=True), {}, True),
  (SimpleNamespace(alphaLongitudinalAvailable=True, openpilotLongitudinalControl=True), {"AlphaLongitudinalEnabled": False}, False),
  (SimpleNamespace(alphaLongitudinalAvailable=True, openpilotLongitudinalControl=True), {"AlphaLongitudinalEnabled": True}, True),
  (SimpleNamespace(alphaLongitudinalAvailable=False, openpilotLongitudinalControl=True), {"DisableOpenpilotLongitudinal": True}, False),
])
def test_capability_pending_vehicle_guards(cp, values, expected):
  from contextlib import nullcontext
  node = next(node for node in ast.parse(SOURCE.read_text()).body if isinstance(node, ast.FunctionDef) and node.name == "_get_longitudinal_mode_capable")
  env = {"_safe_params_get_bool": lambda key, default=False: values.get(key, False),
         "_safe_params_get_live_raw": lambda key: b"cp" if cp else None,
         "car": SimpleNamespace(CarParams=SimpleNamespace(from_bytes=lambda raw: nullcontext(cp)))}
  exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), "exec"), env)
  assert env[node.name]() is expected


def test_real_params_compat_missing_and_failed_reads_fail_closed():
  tree = ast.parse(SOURCE.read_text())
  compat = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ParamsCompat")
  env = {}
  exec(compile(ast.Module(body=[compat], type_ignores=[]), str(SOURCE), "exec"), env)
  params = Params()
  wrapped = env["ParamsCompat"](params)
  # Fake get lacks the optional block keyword, exercising the real fallback.
  assert mode.snapshot(wrapped, True)["locked"] is False
  params.values.pop("IsOffroad")
  assert mode.snapshot(wrapped, True)["locked"] is True
  def failed_read(*args, **kwargs):
    raise OSError("unreadable Params")
  params.get = failed_read
  assert mode.snapshot(wrapped, True)["locked"] is True


def test_manual_and_persisted_overrides_and_child_values_untouched():
  overrides = {"PersistExperimentalState": True, "PersistedCEStatus": 2,
               "PersistChillState": True, "PersistedCCStatus": 3, "CESpeed": 27, "CCMSpeed": 43}
  params = Params(overrides)
  client, _ = client_for(params)
  response = client.put("/api/longitudinal_mode", json={"mode": "conditional_chill", "expected": params.values.copy()})
  assert response.status_code == 200
  assert {key: params.values[key] for key in overrides} == overrides
  assert all(key in mode.MODE_KEYS for key, _ in params.writes)
