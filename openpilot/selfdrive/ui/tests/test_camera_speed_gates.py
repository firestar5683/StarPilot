from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from openpilot.selfdrive.ui.onroad import augmented_road_view as large
from openpilot.selfdrive.ui.mici.onroad import augmented_road_view as compact
from openpilot.selfdrive.ui.onroad import cameraview as large_camera
from openpilot.selfdrive.ui.mici.onroad import cameraview as compact_camera


@pytest.mark.parametrize("module", [large, compact])
@pytest.mark.parametrize("initial", [large.NARROW_ROAD_CAM, large.WIDE_CAM])
def test_experimental_camera_hysteresis_boundaries_match_on_both_displays(module, initial):
  view = object.__new__(module.AugmentedRoadView)
  view.close = Mock()
  view.available_streams = [module.NARROW_ROAD_CAM, module.WIDE_CAM]
  view._stream_type = initial
  view._switching = False
  view.switch_stream = Mock(side_effect=lambda target: setattr(view, "_stream_type", target))
  sm = {"selfdriveState": SimpleNamespace(experimentalMode=True), "carState": SimpleNamespace(vEgo=0)}
  for speed, target in [(5, initial), (10, initial), (4.9, module.WIDE_CAM),
                        (5, module.WIDE_CAM), (7.5, module.WIDE_CAM), (10, module.WIDE_CAM),
                        (10.1, module.NARROW_ROAD_CAM), (10, module.NARROW_ROAD_CAM), (5, module.NARROW_ROAD_CAM)]:
    sm["carState"].vEgo = speed
    before = view._stream_type
    calls = view.switch_stream.call_count
    view._switch_stream_if_needed(sm)
    assert view._stream_type == target
    assert view.switch_stream.call_count == calls + (before != target)


@pytest.mark.parametrize("module", [large, compact])
@pytest.mark.parametrize("experimental,wide_available", [(False, True), (True, False)])
def test_nonexperimental_or_missing_wide_stream_uses_narrow(module, experimental, wide_available):
  view = object.__new__(module.AugmentedRoadView)
  view.close = Mock()
  view.available_streams = [module.NARROW_ROAD_CAM] + ([module.WIDE_CAM] if wide_available else [])
  view._stream_type = module.WIDE_CAM
  view._switching = False
  view.switch_stream = Mock()
  sm = {"selfdriveState": SimpleNamespace(experimentalMode=experimental), "carState": SimpleNamespace(vEgo=0)}
  view._switch_stream_if_needed(sm)
  view.switch_stream.assert_called_once_with(module.NARROW_ROAD_CAM)


@pytest.mark.parametrize("choice,target", [(compact.CAMERA_VIEW_STANDARD, compact.NARROW_ROAD_CAM),
                                           (compact.CAMERA_VIEW_WIDE, compact.WIDE_CAM),
                                           (compact.CAMERA_VIEW_DRIVER, compact.DRIVER_CAM)])
def test_compact_explicit_camera_choice_still_overrides_speed(choice, target):
  view = object.__new__(compact.AugmentedRoadView)
  view.close = Mock()
  view.available_streams = [compact.NARROW_ROAD_CAM, compact.WIDE_CAM, compact.DRIVER_CAM]
  view._stream_type = compact.NARROW_ROAD_CAM
  view._switching = False
  view.switch_stream = Mock()
  sm = {"selfdriveState": SimpleNamespace(experimentalMode=True), "carState": SimpleNamespace(vEgo=30)}
  assert view._switch_stream_if_needed(sm, choice) == target
  assert view.switch_stream.call_count == (target != compact.NARROW_ROAD_CAM)


@pytest.mark.parametrize('module', [large_camera, compact_camera])
@pytest.mark.parametrize('after_failure', [100., 1.])
def test_connection_retries_advance_when_recorded_clock_is_frozen_or_rewound(module, after_failure, monkeypatch):
  view = object.__new__(module.CameraView)
  view.close = Mock()
  view._initialize_textures = Mock()
  view._name, view._stream_type = 'camerad', 0
  view.available_streams = ['stale']
  view.last_connection_attempt = 0.0
  view.client = Mock(num_buffers=3)
  connected = [False]
  view.client.is_connected.side_effect = lambda: connected[0]

  def connect(_):
    connected[0] = view.client.connect.call_count > 1
    return connected[0]

  view.client.connect.side_effect = connect
  view.client.available_streams.return_value = [0]
  host, recorded = [10.], [100.]
  monkeypatch.setattr(module.time, 'monotonic', lambda: host[0])
  monkeypatch.setattr(module.rl, 'get_time', lambda: recorded[0])
  assert not view._ensure_connection()
  view.client.connect.assert_called_once_with(False)
  recorded[0] = after_failure
  host[0] = 10.1
  assert not view._ensure_connection()  # Still respect the host retry interval.
  assert view.client.connect.call_count == 1
  for index in range(100):
    host[0] = 10.1 + index * .01
    view._ensure_connection()
  assert connected[0] and view.client.connect.call_count == 2
  assert view.last_connection_attempt >= 10.2
  view._initialize_textures.assert_called_once()
  assert view.available_streams == [0] and recorded[0] == after_failure
