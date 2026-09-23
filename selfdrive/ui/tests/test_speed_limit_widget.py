from types import SimpleNamespace

import pyray as rl
import pytest

from openpilot.selfdrive.ui.onroad.starpilot.widgets import speed_limit as speed_limit_widget


@pytest.mark.parametrize(
  ("state", "memory_write", "sources_enabled"),
  [
    ({"speed_limit_changed": True, "unconfirmed_valid": True, "override_mode": "manual"},
     ("SpeedLimitAccepted", True), True),
    ({
      "speed_limit_changed": False,
      "unconfirmed_valid": False,
      "override_mode": "manual",
      "slc_overridden_speed": 1.0,
    },
     ("SLCAdoptSpeedLimit", True), True),
    ({
      "speed_limit_changed": False,
      "unconfirmed_valid": False,
      "override_mode": "pedal",
      "slc_overridden_speed": 1.0,
    },
     ("SLCAdoptSpeedLimit", True), True),
    ({"speed_limit_changed": False, "unconfirmed_valid": False, "override_mode": ""},
     None, False),
  ],
)
def test_sign_tap_accepts_pending_adopts_override_or_toggles_sources(state, memory_write, sources_enabled, monkeypatch):
  class SourceParams:
    def __init__(self):
      self.enabled = True

    def get_bool(self, _key):
      return self.enabled

    def put_bool(self, _key, value):
      self.enabled = value

  sources = SourceParams()
  memory_writes = []
  monkeypatch.setattr(speed_limit_widget, "ui_state", SimpleNamespace(ui_params=sources))
  monkeypatch.setattr(
    speed_limit_widget,
    "Params",
    lambda memory=False: SimpleNamespace(put_bool=lambda key, value: memory_writes.append((key, value))),
  )
  monkeypatch.setattr(speed_limit_widget.rl, "check_collision_point_rec", lambda *_args: True)

  widget = object.__new__(speed_limit_widget.SpeedLimitWidget)
  widget._slc_state = state
  widget._sign_rect = rl.Rectangle(0, 0, 10, 10)
  widget._handle_mouse_press((0, 0))

  assert memory_writes == ([] if memory_write is None else [memory_write])
  assert sources.enabled is sources_enabled
