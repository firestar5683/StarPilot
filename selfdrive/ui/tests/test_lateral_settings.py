import pytest

from openpilot.common.params import Params
from openpilot.selfdrive.ui.layouts.settings.starpilot import lateral, panel
from openpilot.system.ui.widgets import DialogResult


@pytest.mark.parametrize(("is_metric", "unit", "maximum"), [(False, "mph", 99), (True, "km/h", 150)])
def test_lane_change_speed_uses_current_units(monkeypatch, tmp_path, is_metric, unit, maximum):
  params = Params(str(tmp_path), return_defaults=True)
  params.put_int("MinimumLaneChangeSpeed", 30)
  params.put_bool("IsMetric", not is_metric)
  monkeypatch.setattr(panel, "FrameCachedParams", lambda: params)
  monkeypatch.setattr(lateral.gui_app, "font", lambda *_args: None)
  dialogs = []
  monkeypatch.setattr(lateral.gui_app, "push_widget", dialogs.append)

  layout = lateral.StarPilotLateralLayout()
  row = next(row for row in layout._lane_change_rows if row.id == "MinimumLaneChangeSpeed")

  # Read the current preference, even when units change after the page is built.
  params.put_bool("IsMetric", is_metric)
  assert row.get_value() == f"30 {unit}"
  row.on_click()
  dialog = dialogs.pop()
  assert (dialog.min_val, dialog.max_val, dialog.step) == (0, maximum, 1)
  assert dialog.formatted_value() == f"30 {unit}"
  assert params.get_int("MinimumLaneChangeSpeed") == 30

  dialog._user_callback(DialogResult.CONFIRM, maximum)
  assert params.get_int("MinimumLaneChangeSpeed") == maximum
