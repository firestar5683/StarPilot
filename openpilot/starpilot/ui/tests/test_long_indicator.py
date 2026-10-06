from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import pyray as rl
import pytest

from openpilot.cereal import log
from openpilot.selfdrive.ui.mici.onroad import long_indicator as indicator


@pytest.fixture
def display(monkeypatch):
  class Messages(dict):
    recv_frame = {'selfdriveState': 12}
    alive = {'longitudinalPlan': True}
  sm = Messages(selfdriveState=NS(enabled=True, personality=NS(raw=1), alertSize=log.SelfdriveState.AlertSize.none),
                longitudinalPlan=NS(hasLead=True, longitudinalPlanSource=log.LongitudinalPlan.LongitudinalPlanSource.e2e),
                onroadEvents=[])
  state = NS(sm=sm, started_frame=10, has_longitudinal_control=True)
  monkeypatch.setattr(indicator, 'ui_state', state)
  monkeypatch.setattr(indicator.rl, 'get_time', lambda: 1.)
  with patch.object(indicator.gui_app, 'texture', side_effect=lambda path, *args, **kwargs: path):
    widget = indicator.LongIndicator()
  widget._draw_centered = Mock()
  widget.set_should_draw(True)
  return widget, state


@pytest.mark.parametrize('missing', ['longitudinal', 'engagement', 'drive'])
def test_no_longitudinal_indicator_from_unavailable_or_previous_drive(display, missing):
  widget, state = display
  if missing == 'longitudinal':
    state.has_longitudinal_control = False
  elif missing == 'engagement':
    state.sm['selfdriveState'].enabled = False
  else:
    state.started_frame = 13
  widget._render(rl.Rectangle(0, 0, 476, 240))
  widget._draw_centered.assert_not_called()


def test_indicator_tracks_lead_policy_and_yields_to_alerts(display):
  widget, state = display
  rect = rl.Rectangle(0, 0, 476, 240)
  for _ in range(60):
    widget._render(rect)
  lead_draws = widget._draw_centered.call_args_list[-8:-6]
  assert lead_draws[1].args[0].endswith('car_green.png')
  assert lead_draws[1].args[3] > .95
  state.sm['selfdriveState'].alertSize = log.SelfdriveState.AlertSize.full
  for _ in range(60):
    widget._render(rect)
  assert all(call.args[3] < .001 for call in widget._draw_centered.call_args_list[-8:])
