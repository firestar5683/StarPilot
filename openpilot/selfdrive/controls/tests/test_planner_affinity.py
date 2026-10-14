from unittest import mock

import pytest

from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.common.realtime import Priority
from openpilot.selfdrive.controls import plannerd
from openpilot.starpilot.longitudinal.upstream import plannerd as upstream


class StartupBoundary(Exception):
  pass


@pytest.mark.parametrize('selected', [True, False])
def test_actual_saved_planner_entry_sets_original_core_and_priority_before_cp(selected):
  calls = []
  with OpenpilotPrefix():
    Params().put_bool('UseStarPilotLongitudinalPlanner', selected, block=True)
    original_get = Params.get

    def get(params, key, *args, **kwargs):
      if key == 'CarParams':
        assert calls == [('realtime', 5, Priority.CTRL_LOW)]
        raise StartupBoundary
      return original_get(params, key, *args, **kwargs)

    with mock.patch.object(Params, 'get', get), \
         mock.patch.object(plannerd, 'config_realtime_process', side_effect=lambda core, priority: calls.append(('realtime', core, priority))), \
         mock.patch.object(upstream, 'config_realtime_process', side_effect=lambda core, priority: calls.append(('realtime', core, priority))):
      with pytest.raises(StartupBoundary):
        plannerd.main()
    assert calls == [('realtime', 5, Priority.CTRL_LOW)]


def test_planner_has_no_late_affinity_override():
  import ast
  from pathlib import Path
  tree = ast.parse(Path(plannerd.__file__).read_text())
  overrides = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and
               isinstance(node.func, ast.Name) and node.func.id == 'set_core_affinity']
  assert not overrides
