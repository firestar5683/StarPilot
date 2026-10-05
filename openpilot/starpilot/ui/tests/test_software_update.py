from types import SimpleNamespace
from unittest.mock import patch

from openpilot.starpilot.ui.software_update import NativeSoftwareUpdate


class ImmediateThread:
  def __init__(self, target, daemon):
    self.target = target

  def start(self):
    self.target()


def test_native_selected_branch_and_rollback_use_existing_owner():
  calls = []
  status = {"installed": {"branch": "Dom"}, "updater": {"fast": {"detail": "Receiving objects: 50%"}}}
  owner = SimpleNamespace(
    status=SimpleNamespace(snapshot=lambda: dict(status)),
    snapshot=lambda: {"selectedTarget": "Other", "canFastUpdate": True, "canRollback": True},
    action=lambda action, payload, authorized: calls.append((action, payload, authorized())),
  )
  with (
    patch('openpilot.starpilot.ui.software_update.SoftwareOperations', return_value=owner),
    patch('openpilot.starpilot.ui.software_update.threading.Thread', ImmediateThread),
  ):
    update = NativeSoftwareUpdate(lambda: True)
    update.refresh()
    assert update.detail() == "Receiving objects: 50%"
    assert update.available('fast')
    assert update.submit('fast')
    assert update.submit('rollback')
  assert calls == [('fast', {'action': 'fast', 'branch': 'Other'}, True), ('rollback', {'action': 'rollback', 'branch': 'Dom'}, True)]


def test_native_fresh_permission_loss_prevents_submission():
  allowed = [True]
  with patch('openpilot.starpilot.ui.software_update.SoftwareOperations') as owner:
    update = NativeSoftwareUpdate(lambda: allowed[0])
    allowed[0] = False
    assert not update.submit('fast')
    owner.return_value.action.assert_not_called()


def test_native_refresh_keeps_actions_stable_and_submission_blocks_them():
  queued, calls = [], []

  class DeferredThread(ImmediateThread):
    def start(self):
      queued.append(self.target)

  status = {"installed": {"branch": "Dom"}, "updater": {"fast": {"detail": "Already up to date."}}}
  owner = SimpleNamespace(
    status=SimpleNamespace(snapshot=lambda: dict(status)),
    snapshot=lambda: {"selectedTarget": "Dom", "canFastUpdate": True, "canRollback": True},
    action=lambda action, payload, authorized: calls.append(action),
  )
  with (
    patch('openpilot.starpilot.ui.software_update.SoftwareOperations', return_value=owner),
    patch('openpilot.starpilot.ui.software_update.threading.Thread', DeferredThread),
  ):
    update = NativeSoftwareUpdate(lambda: True)
    update.refresh()
    assert not update.available('fast')
    queued.pop(0)()
    update.error = "Transient read failure"
    update.next_refresh = 0
    update.refresh()
    assert update.available('fast') and update.available('rollback')
    update.refresh()
    assert len(queued) == 1
    queued.pop(0)()
    assert update.detail() == "Already up to date."
    update.next_refresh = 0
    update.refresh()
    assert update.submit('fast')
    assert not update.available('fast') and not update.available('rollback')
    assert not update.submit('rollback')
    queued.pop(0)()
    assert not update.available('fast')
    assert calls == []
    queued.pop(0)()
    assert calls == ['fast']
    assert update.available('fast') and update.available('rollback')
