import ast
from pathlib import Path
from types import SimpleNamespace

import pytest


def load_handle_agnos_update(cur_version: str):
  source_path = Path(__file__).parents[1] / "updated.py"
  module = ast.parse(source_path.read_text())
  function = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "handle_agnos_update")

  def fail(*_args, **_kwargs):
    raise AssertionError("accepted AGNOS version attempted to update")

  scope = {
    "HARDWARE": SimpleNamespace(get_os_version=lambda: cur_version),
    "OVERLAY_MERGED": "/unused",
    "cloudlog": SimpleNamespace(info=lambda *_args, **_kwargs: None),
    "run": lambda *_args, **_kwargs: "19.8.1\n19.8.1 19.8.2\n",
    "set_consistent_flag": fail,
  }
  ast.fix_missing_locations(function)
  exec(compile(ast.Module(body=[function], type_ignores=[]), str(source_path), "exec"), scope)
  return scope["handle_agnos_update"]


@pytest.mark.parametrize("cur_version", ["19.8.1", "19.8.2"])
def test_accepted_agnos_version_is_not_reflashed(cur_version):
  load_handle_agnos_update(cur_version)()
