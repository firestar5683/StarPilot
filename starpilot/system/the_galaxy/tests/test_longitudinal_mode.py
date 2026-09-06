"""Host-only tests: no device Params, controller, or service imports."""
import importlib.util
from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

MODULE = Path(__file__).resolve().parents[1] / "longitudinal_mode.py"
spec = importlib.util.spec_from_file_location("longitudinal_mode", MODULE)
mode = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mode)


class Params:
  def __init__(self, values=None, fail_at=None):
    self.directory = TemporaryDirectory(prefix="starpilot-mode-test-")
    self.values = {"IsOffroad": True, "IsOnroad": False, "SafeMode": False,
                   "ExperimentalModeConfirmed": True, "ExperimentalMode": False, "ConditionalExperimental": True, "ConditionalChill": False, **(values or {})}
    self.writes = []
    self.fail_at = fail_at

  def get_param_path(self):
    return str(Path(self.directory.name) / "d")

  def get(self, key):
    return self.values.get(key)

  def get_bool(self, key):
    return self.values.get(key, False)

  def put_bool(self, key, value):
    self.writes.append((key, value))
    if len(self.writes) == self.fail_at:
      raise OSError("injected write failure")
    self.values[key] = value


@pytest.mark.parametrize("cem,ccm,experimental", list(product([False, True], repeat=3)))
def test_read_precedence_without_writes(cem, ccm, experimental):
  params = Params(dict(zip(mode.MODE_KEYS, [experimental, ccm, cem])))
  result = mode.snapshot(params, True)
  assert result["mode"] == ("conditional_experimental" if cem else "conditional_chill" if ccm else "experimental" if experimental else "chill")
  assert not params.writes


@pytest.mark.parametrize("target", ["chill", "experimental", "conditional_experimental", "conditional_chill"])
@pytest.mark.parametrize("cem,ccm,experimental", list(product([False, True], repeat=3)))
def test_all_transitions(target, cem, ccm, experimental):
  params = Params(dict(zip(mode.MODE_KEYS, [experimental, ccm, cem])))
  before = params.values.copy()
  result = mode.set_mode(params, target, before, lambda: True)
  assert result["mode"] == target
  if target == mode.selected_mode(before):
    assert not params.writes  # A no-op never normalizes dormant flags.
  else:
    intermediate = before.copy()
    for key, value in params.writes:
      intermediate[key] = value
      assert mode.selected_mode(intermediate) in {mode.selected_mode(before), target}
    assert sum(params.values[key] for key in mode.MODE_KEYS) == (target != "chill")


@pytest.mark.parametrize("values,capable", [({"IsOffroad": False}, True), ({"IsOffroad": None}, True),
  ({"IsOnroad": True}, True), ({"IsOnroad": None}, True), ({"SafeMode": True}, True),
  ({"SafeMode": None}, True), ({}, False)])
def test_guards_fail_closed(values, capable):
  params = Params(values)
  with pytest.raises(mode.ModeError):
    mode.set_mode(params, "experimental", params.values.copy(), lambda: capable)
  assert not params.writes


@pytest.mark.parametrize("target", [None, True, 1, [], {}, "Experimental", ""])
def test_invalid_modes_never_write(target):
  params = Params()
  with pytest.raises(mode.ModeError):
    mode.set_mode(params, target, params.values.copy(), lambda: True)
  assert not params.writes


def test_stale_or_missing_expected_state_never_writes():
  params = Params()
  for expected in [None, {}, {key: False for key in mode.MODE_KEYS}]:
    with pytest.raises(mode.ModeError):
      mode.set_mode(params, "experimental", expected, lambda: True)
  assert not params.writes


@pytest.mark.parametrize("fail_at", [1, 2, 3])
def test_failed_write_keeps_old_or_requested_mode(fail_at):
  params = Params(fail_at=fail_at)
  with pytest.raises(mode.ModeError):
    mode.set_mode(params, "experimental", params.values.copy(), lambda: True)
  assert mode.selected_mode(params.values) in {"conditional_experimental", "experimental"}
  assert len(params.writes) == fail_at  # No unsafe rollback or later enabling.


def test_readback_failure_stops_without_further_writes():
  params = Params()
  params.put_bool = lambda key, value: params.writes.append((key, value))
  with pytest.raises(mode.ModeError):
    mode.set_mode(params, "experimental", params.values.copy(), lambda: True)
  assert params.writes == [("ExperimentalMode", True)]
  assert mode.selected_mode(params.values) == "conditional_experimental"


def test_guard_rechecked_before_every_write():
  params = Params()
  def capable():
    return len(params.writes) < 2
  with pytest.raises(mode.ModeError):
    mode.set_mode(params, "experimental", params.values.copy(), capable)
  assert params.writes == [("ExperimentalMode", True), ("ConditionalChill", False)]
