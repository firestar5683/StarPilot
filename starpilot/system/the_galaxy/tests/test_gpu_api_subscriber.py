import ast
from pathlib import Path
from types import SimpleNamespace
from flask import Flask, jsonify
from openpilot.starpilot.system.the_galaxy import external_gpu_vitals as telemetry


def test_home_route_uses_canonical_shared_subscriber(monkeypatch):
  # Execute the actual route body without importing vehicle/hardware services.
  source = Path(__file__).resolve().parents[1] / "the_galaxy.py"
  setup = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "setup")
  route = next(n for n in setup.body if isinstance(n, ast.FunctionDef) and n.name == "get_external_gpu_vitals")
  route.decorator_list = []
  app = Flask("shared_gpu_subscriber")
  namespace = {"jsonify": jsonify}
  exec(compile(ast.Module(body=[route], type_ignores=[]), str(source), "exec"), namespace)
  calls = []
  sentinel = SimpleNamespace()
  monkeypatch.setattr(telemetry, "_sm", sentinel)
  monkeypatch.setattr(telemetry, "external_gpu_vitals", lambda **kwargs: calls.append(telemetry._sm) or {"tempC": 50})
  with app.test_request_context():
    for _ in range(2):
      result = namespace["get_external_gpu_vitals"]()
      assert result.get_json() == {"tempC": 50}
      assert result.headers["Cache-Control"] == "no-store"
  assert calls == [sentinel, sentinel]
