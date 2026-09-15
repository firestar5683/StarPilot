import ast
from pathlib import Path

import pytest

from cereal import log
from openpilot.selfdrive.selfdrived.events import EVENTS, ET

EventName = log.OnroadEvent.EventName


def test_big_model_loading_does_not_block_engagement():
  # The big model loads in the background while the small model drives, so waiting for it
  # must never keep the driver from engaging.
  assert ET.NO_ENTRY not in EVENTS[EventName.bigModelLoading]
  assert ET.PERMANENT in EVENTS[EventName.bigModelLoading]


def test_big_model_pending_is_advisory_only():
  pending = EVENTS[EventName.bigModelPending]
  assert set(pending) == {ET.PERMANENT}


def test_big_model_failure_still_disengages():
  assert ET.SOFT_DISABLE in EVENTS[EventName.bigModelFailed]


def test_pending_is_raised_before_loading_is_cleared():
  """selfdrived polls UsbGpuLoading and UsbGpuPending separately at 100 Hz.

  Clearing loading first leaves a window where neither is set, which reads as a failed load:
  captured as exactly one frame of bigModelFailed at the moment the load completed, on two
  drives (50.77 s and 62.98 s).
  """
  import ast
  from pathlib import Path

  from openpilot.selfdrive.modeld import modeld

  source = (Path(modeld.__file__).with_name("modeld.py")).read_text(encoding="utf-8")
  main_fn = next(n for n in ast.parse(source).body
                 if isinstance(n, ast.FunctionDef) and n.name == "main")
  collect = next(
    node for node in ast.walk(main_fn)
    if isinstance(node, ast.If) and "UsbGpuPending" in ast.dump(node)
    and "take" in ast.dump(node)
  )
  # The success branch is the `if loaded_big_model is not None:` inside the collect block.
  success = next(n for n in ast.walk(collect)
                 if isinstance(n, ast.If) and "loaded_big_model" in ast.dump(n.test))
  writes = [
    node.args[0].value
    for node in ast.walk(ast.Module(body=list(success.body), type_ignores=[]))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    and node.func.attr == "put_bool" and node.args
    and isinstance(node.args[0], ast.Constant)
  ]
  pending_writes = [i for i, k in enumerate(writes) if k == "UsbGpuPending"]
  loading_writes = [i for i, k in enumerate(writes) if k == "UsbGpuLoading"]
  assert pending_writes and loading_writes
  assert min(pending_writes) < min(loading_writes), \
    "UsbGpuPending must be raised before UsbGpuLoading is cleared"


def test_loading_banner_is_brief_and_hands_over_to_the_icon():
  # The load can run for minutes; the banner announces the handover to the small model and
  # then gets out of the way, leaving the blinking eGPU icon as the "still loading" cue.
  from openpilot.selfdrive.selfdrived import selfdrived

  assert selfdrived.BIG_MODEL_LOADING_ALERT_SECONDS == 3.0

  source = (Path(selfdrived.__file__)).read_text(encoding="utf-8")
  tree = ast.parse(source)
  guard = next(
    node for node in ast.walk(tree)
    if isinstance(node, ast.If) and "bigModelLoading" in ast.dump(node)
    and "BIG_MODEL_LOADING_ALERT_SECONDS" in ast.dump(node.test)
  )
  # The alert must be gated on elapsed time, not added unconditionally every frame.
  assert "big_model_loading_t" in ast.dump(guard.test)


def _big_failed(*, attempted, loading, pending, big_active, model_unavailable=False):
  """Mirror of selfdrived's big_failed expression, extracted from the source."""
  source = (Path(__file__).parents[1] / "selfdrived.py").read_text(encoding="utf-8")
  tree = ast.parse(source)
  assign = next(
    node for node in ast.walk(tree)
    if isinstance(node, ast.Assign)
    and any(isinstance(t, ast.Name) and t.id == "big_failed" for t in node.targets)
  )
  scope = {
    "self": type("S", (), {"big_model_attempted": attempted})(),
    "loading": loading,
    "pending": pending,
    "big_active": big_active,
    "model_unavailable": model_unavailable,
  }
  return eval(compile(ast.Expression(assign.value), "<big_failed>", "eval"), {}, scope)  # noqa: S307


@pytest.mark.parametrize("state,expected", [
  # A loaded model waiting for the driver to disengage is a success, not a failure.
  (dict(attempted=True, loading=False, pending=True, big_active=False), False),
  (dict(attempted=True, loading=True, pending=False, big_active=False), False),
  (dict(attempted=True, loading=False, pending=False, big_active=True), False),
  # Genuine failures must still be reported.
  (dict(attempted=True, loading=False, pending=False, big_active=False), True),
  (dict(attempted=True, loading=False, pending=False, big_active=True,
        model_unavailable=True), True),
  # Never report a failure for a big model that was never attempted.
  (dict(attempted=False, loading=False, pending=False, big_active=False), False),
])
def test_pending_big_model_is_not_reported_as_failed(state, expected):
  assert _big_failed(**state) is expected
