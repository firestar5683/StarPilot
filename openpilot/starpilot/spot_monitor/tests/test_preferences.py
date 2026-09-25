"""Strict saved V-ASM owner; malformed bytes never activate or get rewritten."""

import json
from pathlib import Path

import pytest

from openpilot.common.params import Params
from openpilot.starpilot.spot_monitor.policy import decode_annotation
from openpilot.starpilot.spot_monitor.preferences import Preferences, decode, encode, enabled, read_preferences


ANNOTATION = {"version": 1, "width": 352, "height": 352,
              "poly_left": [[0, 0], [352, 0], [352, 352], [0, 352]], "poly_right": []}


class FakeParams:
  def __init__(self, path):
    self.path = path

  def get_param_path(self, key):
    return str(self.path)


def test_absent_disabled_and_valid_exact_document(tmp_path):
  path = tmp_path / "VASMPreferences"
  params = FakeParams(path)
  assert read_preferences(params).valid
  assert not enabled(params, development=True)
  annotation = decode_annotation(json.dumps(ANNOTATION))
  raw = encode(Preferences(True, annotation, 0.9, 0.3))
  path.write_bytes(raw)
  saved = read_preferences(params)
  assert saved.readable and saved.valid and saved.preferences.enabled
  assert len(saved.fingerprint) == 64
  assert decode(raw) == saved.preferences
  assert enabled(params, development=True)
  assert not enabled(params, development=False)


def test_explicit_disabled_unconfigured_reset_roundtrip_and_enable_refusal():
  raw = encode(Preferences())
  assert json.loads(raw) == {"annotation": None, "confidence": 0.94, "enabled": False,
                             "smoothSeconds": 0.2, "version": 1}
  assert decode(raw) == Preferences()
  assert decode(raw.replace(b'"enabled":false', b'"enabled":true')) is None
  with pytest.raises(ValueError):
    encode(Preferences(enabled=True))


def test_corrupt_unreadable_and_wrong_types_preserved_disabled(tmp_path):
  base = json.loads(encode(Preferences(True, decode_annotation(json.dumps(ANNOTATION)))))
  for changed in ({"version": True}, {"enabled": 1}, {"confidence": 0.79}, {"smoothSeconds": 0.51},
                  {"annotation": {**ANNOTATION, "version": 2}}, {"unexpected": 1}):
    raw = json.dumps({**base, **changed}).encode()
    path = tmp_path / "VASMPreferences"
    path.write_bytes(raw)
    params = FakeParams(path)
    assert not read_preferences(params).valid
    assert not enabled(params, development=True)
    assert path.read_bytes() == raw
  path.unlink()
  path.symlink_to(tmp_path / "missing")
  assert not read_preferences(FakeParams(path)).readable
  assert not enabled(FakeParams(path), development=True)
  assert decode(b'{"version":1,"version":1}') is None
  assert decode(b"{" + b" " * 8192) is None


def test_manager_predicate_requires_saved_doc_development_gate_and_absolute_asset(tmp_path, monkeypatch):
  from openpilot.system.manager.process_config import vasm_monitor

  params = Params(str(tmp_path / "params"))
  path = Path(params.get_param_path("VASMPreferences"))
  path.write_bytes(encode(Preferences(True, decode_annotation(json.dumps(ANNOTATION)))))
  monkeypatch.setenv("STARPILOT_VASM_DEVELOPMENT", "1")
  monkeypatch.delenv("STARPILOT_VASM_MODEL_PATH", raising=False)
  assert not vasm_monitor(True, params, None)
  monkeypatch.setenv("STARPILOT_VASM_MODEL_PATH", "relative/model.onnx")
  assert not vasm_monitor(True, params, None)
  monkeypatch.setenv("STARPILOT_VASM_MODEL_PATH", "/external/model.onnx")
  assert vasm_monitor(True, params, None)
  assert not vasm_monitor(False, params, None)
  monkeypatch.delenv("STARPILOT_VASM_DEVELOPMENT")
  assert not vasm_monitor(True, params, None)
  path.write_bytes(b"bad")
  monkeypatch.setenv("STARPILOT_VASM_DEVELOPMENT", "1")
  assert not vasm_monitor(True, params, None)
