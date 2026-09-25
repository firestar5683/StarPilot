"""Evaluate the actual SCons graph with fake nodes; never execute compilers."""

import ctypes.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


SOURCE = Path(__file__).resolve().parents[3] / "selfdrive/modeld/SConscript"
EXPECTED_TARGETS = {
  "dmonitoring_model_tinygrad.pkl",
  "driving_warp_1344x760_tinygrad.pkl", "driving_warp_1928x1208_tinygrad.pkl",
  "dm_warp_1344x760_tinygrad.pkl", "dm_warp_1928x1208_tinygrad.pkl",
  "jetlink_warp_1344x760_512x256.pkl", "jetlink_warp_1344x760_1024x512.pkl",
  "jetlink_warp_1928x1208_512x256.pkl", "jetlink_warp_1928x1208_1024x512.pkl",
}


class Returned(Exception):
  pass


@pytest.fixture
def graph(monkeypatch, tmp_path):
  script = ModuleType("SCons.Script")
  script.Action = lambda command, description: command
  script.Value = lambda value: value
  monkeypatch.setitem(sys.modules, script.__name__, script)
  helpers = ModuleType("openpilot.selfdrive.modeld.helpers")
  helpers.chestnut_present = Mock(return_value=False)
  monkeypatch.setitem(sys.modules, helpers.__name__, helpers)
  env = Mock()
  env.Clone.return_value = env

  def node(path):
    relative = path.removeprefix("#")
    return SimpleNamespace(abspath=str(tmp_path / relative), relpath=relative)

  env.Dir.side_effect = node

  def stop():
    raise Returned()

  def evaluate(arch):
    scope = {"env": env, "arch": arch, "Import": Mock(), "Return": stop, "Dir": node, "File": node}
    try:
      exec(compile(SOURCE.read_text(), str(SOURCE), "exec"), scope)
    except Returned:
      pass
    return scope

  return evaluate, env, helpers.chestnut_present


def test_missing_llvm_pc_skips_graph_before_probe_or_compilation(graph, monkeypatch, capsys):
  evaluate, env, present = graph
  llvm = Mock(return_value=None)
  monkeypatch.setattr(ctypes.util, "find_library", llvm)
  evaluate("aarch64")
  llvm.assert_called_once_with("LLVM")
  env.Clone.assert_not_called()
  env.Command.assert_not_called()
  present.assert_not_called()
  assert "Install LLVM to compile models" in capsys.readouterr().out


@pytest.mark.parametrize("arch,llvm,backend", [
  ("aarch64", "libLLVM.so", "DEV=CPU:LLVM"),
  ("Darwin", None, "DEV=METAL JIT=2"),
  ("comma_arm64", None, "DEV=QCOM"),
])
def test_supported_backend_retains_models_and_camera_warp_graph(graph, monkeypatch, arch, llvm, backend):
  evaluate, env, present = graph
  library = Mock(return_value=llvm)
  monkeypatch.setattr(ctypes.util, "find_library", library)
  evaluate(arch)
  assert library.call_count == (1 if arch == "aarch64" else 0)
  present.assert_not_called()
  calls = env.Command.call_args_list
  assert len(calls) == 9
  targets = [Path(call.args[0]).name for call in calls]
  assert set(targets) == EXPECTED_TARGETS
  assert targets[0] == "dmonitoring_model_tinygrad.pkl"
  assert "driving_tinygrad.pkl" not in targets
  assert sum(name.startswith("driving_warp_") for name in targets) == 2
  assert sum(name.startswith("dm_warp_") for name in targets) == 2
  assert all(backend in call.args[2] for call in calls)
  env.Execute.assert_not_called()


def test_llvm_probe_error_does_not_schedule_compilation(graph, monkeypatch):
  evaluate, env, present = graph
  monkeypatch.setattr(ctypes.util, "find_library", Mock(side_effect=OSError("probe failed")))
  with pytest.raises(OSError, match="probe failed"):
    evaluate("aarch64")
  env.Command.assert_not_called()
  present.assert_not_called()


def test_build_does_not_probe_chestnut_or_regenerate_shipped_big_artifacts(graph, monkeypatch):
  evaluate, env, present = graph
  present.return_value = True
  library = Mock()
  monkeypatch.setattr(ctypes.util, "find_library", library)
  evaluate("Darwin")
  library.assert_not_called()
  present.assert_not_called()
  assert env.Command.call_count == 9
  assert {Path(call.args[0]).name for call in env.Command.call_args_list} == EXPECTED_TARGETS
  assert not any(Path(call.args[0]).name.startswith("big_driving_") for call in env.Command.call_args_list)
  env.SideEffect.assert_not_called()
  env.Execute.assert_not_called()
