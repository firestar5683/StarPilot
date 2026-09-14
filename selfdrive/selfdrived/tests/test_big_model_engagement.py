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
