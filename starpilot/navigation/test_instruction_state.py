import json

import pytest

from openpilot.starpilot.navigation.instruction_state import NAV_INSTRUCTION_MAX_AGE, parse_instruction_state


@pytest.mark.parametrize("encode", [lambda state: state, json.dumps, lambda state: json.dumps(state).encode()])
def test_instruction_expires_without_a_new_write(monkeypatch, encode):
  now = [100.0]
  monkeypatch.setattr("time.monotonic", lambda: now[0])
  state = {"valid": True, "updatedAtMonotonic": now[0], "maneuverModifier": "right"}
  raw = encode(state)
  assert parse_instruction_state(raw) == state
  now[0] += NAV_INSTRUCTION_MAX_AGE
  assert parse_instruction_state(raw) == state
  now[0] += 0.001
  assert parse_instruction_state(raw) == {}


@pytest.mark.parametrize("timestamp", [None, True, "100", "bad", float("nan"), float("inf"), -float("inf"), 101.0, 97.0, 10**400])
def test_rejects_missing_invalid_future_or_stale_timestamp(monkeypatch, timestamp):
  monkeypatch.setattr("time.monotonic", lambda: 100.0)
  assert parse_instruction_state({"valid": True, "updatedAtMonotonic": timestamp}) == {}


@pytest.mark.parametrize("raw", [None, {}, [], "[]", "null", "{", b"\xff", {"valid": True},
                                 {"valid": False, "updatedAtMonotonic": 100.0}])
def test_rejects_invalid_instruction(monkeypatch, raw):
  monkeypatch.setattr("time.monotonic", lambda: 100.0)
  assert parse_instruction_state(raw) == {}
