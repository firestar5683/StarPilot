from pathlib import Path
from unittest.mock import Mock, patch
from types import SimpleNamespace as NS

import pytest

from openpilot.common.params import Params
from openpilot.selfdrive.ui import ui_state as native
from openpilot.starpilot.ui.display_owner import DisplayOwner
from openpilot.starpilot.ui.display_preferences import GPU_LOADING, DisplayPreferences, read_preferences
from openpilot.starpilot.ui.feature_settings_state import row_change
from openpilot.starpilot.ui.presentation import Profile


@pytest.mark.parametrize('profile', [Profile.LARGE, Profile.COMPACT])
def test_actual_display_owner_gpu_default_save_stale_and_corrupt(tmp_path, profile):
  params = Params(str(tmp_path))
  owner = DisplayOwner(params, lambda: True, gpu_capable=True)
  row = next(r for r in owner.snapshot(profile).rows if r.key == GPU_LOADING)
  assert row.value == 'Off' and row.available and row.default_value == 'Off'
  request = row_change(row, 1)
  assert request is not None
  assert owner.apply(request)
  assert read_preferences(params, large=profile == Profile.LARGE).keep_screen_on_gpu_loading
  assert not owner.apply(request)
  Path(params.get_param_path(GPU_LOADING)).write_bytes(b'bad')
  assert not read_preferences(params, large=profile == Profile.LARGE).keep_screen_on_gpu_loading


@pytest.mark.parametrize(
  'started,loading,manual_off,expected', [(True, True, False, True), (True, True, True, False), (True, False, False, False), (False, True, False, False)]
)
def test_actual_native_wake_gpu_is_onroad_only_and_manual_off_wins(started, loading, manual_off, expected):
  device = native.Device.__new__(native.Device)
  device._ignition = False
  device._awake = True
  device._screen_off = manual_off
  device._screen_off_started = started
  device._override_interactive_timeout = None
  device._interaction_time = 0
  device._prev_timed_out = False
  device._interactive_timeout_callbacks = []
  device._wake_touch_active = False
  device._display_preferences = DisplayPreferences(keep_screen_on_gpu_loading=True, turn_off_screen=True)
  device._set_awake = Mock()
  ui = NS(started=started, ignition=False, chestnut_loading=loading, sm=NS(valid={}, alive={}))
  with (
    patch.object(native, 'ui_state', ui),
    patch.object(native, 'PC', False),
    patch.object(native.gui_app, '_mouse_events', []),
    patch.object(native.time, 'monotonic', return_value=10),
  ):
    device._update_wakefulness()
  device._set_awake.assert_called_once_with(expected)


def test_gpu_row_absent_on_unsupported_device(tmp_path):
  owner = DisplayOwner(Params(str(tmp_path)), lambda: True, gpu_capable=False)
  assert all(row.key != GPU_LOADING for row in owner.snapshot(Profile.LARGE).rows)
