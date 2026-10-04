import ast
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
import sys
import time
import types

import pytest

from openpilot.starpilot.drive_state.owner import Mode, Rejected
from openpilot.starpilot.drive_state.tests.test_transport import fixture


@pytest.mark.parametrize('profile', ['compact', 'large'])
def test_force_offroad_uses_profile_dialog_and_submits_once(fixture, profile):
  source = Path(__file__).resolve().parents[2] / 'ui/runtime_app.py'
  tree = ast.parse(source.read_text())
  session = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'StarShellSession')
  method = next(node for node in session.body if isinstance(node, ast.FunctionDef) and node.name == '_drive_change')
  ui = NS(started=True, started_frame=10)
  gui = NS(push_widget=Mock(), texture=Mock(return_value='native-icon'))
  result = NS(CONFIRM=1, CANCEL=0)
  modules = {}
  for name in ('openpilot.system.ui.widgets', 'openpilot.system.ui.widgets.confirm_dialog', 'openpilot.selfdrive.ui.mici.widgets.dialog'):
    modules[name] = types.ModuleType(name)
  modules['openpilot.system.ui.widgets'].DialogResult = result
  compact = Mock(side_effect=lambda title, icon, callback, red: NS(confirm=lambda: callback()))
  large = Mock(side_effect=lambda title, button, callback: NS(confirm=lambda: callback(result.CONFIRM), cancel=lambda: callback(result.CANCEL)))
  modules['openpilot.selfdrive.ui.mici.widgets.dialog'].BigConfirmationDialog = compact
  modules['openpilot.system.ui.widgets.confirm_dialog'].ConfirmDialog = large
  namespace = dict(ui_state=ui, gui_app=gui, Profile=NS(COMPACT='compact'),
                   ShellMode=NS(SETTINGS='settings'), DriveStateRejected=Rejected, time=time)
  exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
  native = NS(drive_state=fixture.control, profile=profile, selected='system', _mode='settings')
  native._drive_change = types.MethodType(namespace['_drive_change'], native)
  revision = fixture.owner.snapshot().revision
  fixture.physical.allowed.return_value = False
  with patch.dict(sys.modules, modules):
    native._drive_change('offroad', revision)
    assert fixture.owner.snapshot().mode == Mode.AUTO
    assert compact.call_count == (profile == 'compact')
    assert large.call_count == (profile == 'large')
    dialog = gui.push_widget.call_args.args[0]
    if profile == 'large':
      dialog.cancel()
      assert fixture.owner.snapshot().mode == Mode.AUTO
    ui.started_frame += 1
    dialog.confirm()
    assert fixture.owner.snapshot().mode == Mode.AUTO
    native._drive_change('offroad', revision)
    dialog = gui.push_widget.call_args.args[0]
    writes = len(fixture.owner.params.writes)
    dialog.confirm()
    assert fixture.owner.snapshot().mode == Mode.OFFROAD
    assert len(fixture.owner.params.writes) == writes + 1
    dialog.confirm()
    assert len(fixture.owner.params.writes) == writes + 1
