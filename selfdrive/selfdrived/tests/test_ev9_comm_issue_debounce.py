import ast
from pathlib import Path


DEBOUNCE_FRAMES = 50


def load_helpers():
  # selfdrived imports target-built messaging libraries. Load this pure helper
  # from source so the focused regression runs on development hosts as well.
  source_path = Path(__file__).parents[1] / "selfdrived.py"
  tree = ast.parse(source_path.read_text())
  helper_names = {
    "ev9_transient_comm_issue_debounce_enabled",
    "update_ev9_invalid_only_comm_issue_debounce",
  }
  helpers = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in helper_names]
  namespace = {"EV9_INVALID_ONLY_COMM_ISSUE_DEBOUNCE_FRAMES": DEBOUNCE_FRAMES}
  exec(compile(ast.Module(body=helpers, type_ignores=[]), source_path, "exec"), namespace)
  return tuple(namespace[name] for name in sorted(helper_names))


feature_enabled, update_debounce = load_helpers()


def test_feature_defaults_on_when_param_is_missing():
  assert feature_enabled(None)
  assert feature_enabled(b"1")
  assert not feature_enabled(b"0")


def test_ev9_invalid_only_requires_half_second():
  frames = 0
  for _ in range(DEBOUNCE_FRAMES - 1):
    frames, add_event = update_debounce(True, True, True, True, False, frames)
    assert not add_event

  assert frames == 49
  frames, add_event = update_debounce(True, True, True, True, False, frames)
  assert frames == 50
  assert add_event


def test_healthy_cycle_resets_invalid_only_burst():
  frames = 37
  frames, add_event = update_debounce(True, True, True, True, True, frames)

  assert frames == 0
  assert not add_event


def test_non_ev9_and_disabled_feature_remain_immediate():
  assert update_debounce(True, False, True, True, False, 0) == (0, True)
  assert update_debounce(False, True, True, True, False, 0) == (0, True)


def test_dead_or_bad_frequency_remains_immediate_and_resets():
  assert update_debounce(True, True, False, True, False, 32) == (0, True)
  assert update_debounce(True, True, True, False, False, 32) == (0, True)
