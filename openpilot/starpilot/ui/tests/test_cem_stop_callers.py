"""A committed planner stop reaches both actual camera and onroad display callers."""
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from openpilot.starpilot.conditional_mode.effective_status import publish_ack
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.status import observation
from openpilot.starpilot.conditional_mode.tests.test_projection import MONO
from openpilot.starpilot.longitudinal.tests import test_cem_green_release as fixture
from openpilot.starpilot.ui.conditional_status import ConditionalDisplayProjector
from openpilot.starpilot.ui.onroad import axis_status_color, driving_mode_description
from openpilot.starpilot.ui.onroad_conditional import status, stop_active
from openpilot.starpilot.ui.preview_shell import reference_onroad
from openpilot.selfdrive.ui.onroad import augmented_road_view as large
from openpilot.selfdrive.ui.mici.onroad import augmented_road_view as compact


@pytest.mark.parametrize('camera', [large, compact])
def test_cross_traffic_stop_publication_keeps_mode_border_and_camera_then_releases(camera):
  case = fixture.CemGreenCallerTests(methodName='runTest')
  case.setUp()
  try:
    case.prime()
    projector = ConditionalDisplayProjector()
    view = object.__new__(camera.AugmentedRoadView)
    view.close = Mock()
    view.available_streams = [camera.NARROW_ROAD_CAM, camera.WIDE_CAM]
    view._stream_type, view._switching = camera.WIDE_CAM, False
    view.switch_stream = Mock(side_effect=lambda target: setattr(view, '_stream_type', target))
    base = replace(reference_onroad('onroad_engaged_no_camera'), visual_preview=None,
                   lateral_active=True, longitudinal_active=True, conditional_configured=ModeChoice.CEM)

    def cycle(**kwargs):
      proposal, result, held, plan = case.cycle(stopped=True, **kwargs)
      now = MONO + (case.tick - 1) * 50_000_000
      return proposal, result, held, plan, now

    # Capture the actual consumer input without replacing its behavior.
    original_consume = case.consumer.sample
    captured = []
    def consume(wire, **kwargs):
      captured.append(wire)
      return original_consume(wire, **kwargs)
    with patch.object(case.consumer, 'sample', side_effect=consume):
      for tick in range(48):
        _, result, held, plan, now = cycle(
          position=fixture.RED_97_X, velocity=fixture.RED_97_V, lead=tick % 3 != 0)
        assert result.accepted and result.experimental and held and plan.shouldStop and plan.aTarget <= 0.
        wire = observation(captured[-1], now)
        assert wire is not None
        ack = publish_ack(session='a' * 32, sequence=tick + 1, observed_ns=now,
          selfdrive_state_ns=now - 2_000_000, drive_id=case.drive,
          effective_experimental=result.experimental, result=result, accepted_proposal=wire)
        display = projector.project(ack.starpilotSelfdriveState, now_ns=now, event_ns=now,
          selfdrive_ns=now - 2_000_000, drive_id=case.drive, selfdrive_experimental=result.experimental,
          selfdrive_enabled=True, long_active=True, car_valid=True, system_long=True)
        assert display is not None and display.reason == 'cem_stop'
        state = replace(base, conditional_effective=display, experimental_enabled=result.experimental)
        visual_status = status(state)
        assert stop_active(state) and visual_status is not None and visual_status[:2] == ('CEM', 'STOP')
        assert driving_mode_description(state) == 'ACC - Experimental'
        color = axis_status_color(state)
        assert (color.r, color.g, color.b) == (218, 111, 37)
        view._switch_stream_if_needed({'selfdriveState': SimpleNamespace(experimentalMode=result.experimental),
                                       'carState': SimpleNamespace(vEgo=0.)})
        assert view._stream_type == camera.WIDE_CAM
      view.switch_stream.assert_not_called()
      for _ in range(18):
        _, result, held, plan, _ = cycle(position=fixture.CLEAR_64_X, velocity=fixture.CLEAR_64_V, should_stop=False)
      assert result.accepted and not result.experimental and not held and not plan.shouldStop and plan.aTarget > 0.
      assert not case.owner.mode.projector.stop_detector.committed
  finally:
    case.doCleanups()


@pytest.mark.parametrize('source', ['modelV2', 'carState', 'selfdriveState', 'carControl'])
def test_missing_authority_retains_stop_memory_without_claiming_a_current_mode(source):
  case = fixture.CemGreenCallerTests(methodName='runTest')
  case.setUp()
  try:
    case.prime()
    captured = []
    original_consume = case.consumer.sample
    def consume(wire, **kwargs):
      captured.append(wire)
      return original_consume(wire, **kwargs)
    with patch.object(case.consumer, 'sample', side_effect=consume):
      proposal, result, held, _ = case.cycle(stopped=True, position=fixture.RED_97_X,
                                            velocity=fixture.RED_97_V, unavailable=source)
    now = MONO + (case.tick - 1) * 50_000_000
    assert case.owner.mode.projector.stop_detector.committed
    assert not result.accepted and not held
    if source == 'modelV2':
      assert proposal.override_experimental is False and proposal.decision.reason.value == 'scene_unavailable'
    else:
      assert proposal.override_experimental is None
    ack = publish_ack(session='a' * 32, sequence=1, observed_ns=now,
      selfdrive_state_ns=now - 2_000_000, drive_id=case.drive,
      effective_experimental=result.experimental, result=result, accepted_proposal=observation(captured[-1], now))
    display = ConditionalDisplayProjector().project(ack.starpilotSelfdriveState, now_ns=now, event_ns=now,
      selfdrive_ns=now - 2_000_000, drive_id=case.drive, selfdrive_experimental=result.experimental,
      selfdrive_enabled=True, long_active=True, car_valid=True, system_long=True)
    assert display is None
    state = replace(reference_onroad('onroad_engaged_no_camera'), visual_preview=None,
                    conditional_effective=display, conditional_perception=None)
    assert status(state) is None and not stop_active(state)
    # Fresh evidence resumes the same genuine stop without acquiring a new one.
    _, result, held, plan = case.cycle(stopped=True, position=fixture.RED_97_X, velocity=fixture.RED_97_V)
    assert result.accepted and result.experimental and held and plan.shouldStop
  finally:
    case.doCleanups()
