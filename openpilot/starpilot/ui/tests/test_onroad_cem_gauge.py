"""Read-only Dom CEM visuals with real presentation state and source boundaries."""
from contextlib import ExitStack
from dataclasses import replace
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
import copy

import pyray as rl
import pytest

from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.curve_speed.status import CurveObservation
from openpilot.starpilot.ui.appearance_preferences import CameraViewChoice
from openpilot.starpilot.ui.conditional_status import ConditionalDisplay
from openpilot.starpilot.ui.onroad_cem_gauge import AetherGauge, IndicatorType, gauge_data
from openpilot.starpilot.ui.onroad_conditional import reason, status, stop_active
from openpilot.starpilot.ui.onroad_customization import CEM_GAUGE_WIDGET, DEFAULT_WIDGET_ORDER, default_document, validate_document
from openpilot.starpilot.ui.onroad_state import (AlertSize, ConditionalLead, OnroadAlert, OnroadState,
                                               SpeedLimitObservation, conditional_lead_from_message)


def state(reason='cem_stop', *, effective=False, **changes):
  value = ConditionalDisplay(ModeChoice.CEM, effective, reason, 8 if reason == 'cem_stop' else 4, 'planner', 1)
  return replace(OnroadState(effective, True, 20., 90., SpeedLimitObservation(), lateral_active=True,
                             longitudinal_active=effective, slc_system_long_available=effective,
                             conditional_configured=ModeChoice.CEM,
                             conditional_effective=value if effective else None,
                             conditional_perception=None if effective else value), **changes)


@pytest.mark.parametrize('missing', ['scene_unavailable', 'unavailable'])
@pytest.mark.parametrize('effective', [False, True])
def test_missing_scene_is_hidden_without_erasing_policy_receipt(missing, effective):
  sample = state(missing, effective=effective)
  raw = sample.conditional_effective or sample.conditional_perception
  assert raw is not None and raw.reason == missing
  assert reason(sample) is None and status(sample) is None
  assert gauge_data(sample) is None and not stop_active(sample)
  assert (sample.conditional_effective or sample.conditional_perception) is raw


@pytest.mark.parametrize('effective', [False, True])
def test_stop_graphic_preserves_informational_and_control_distinction(effective):
  sample = state(effective=effective)
  data = gauge_data(sample)
  assert data is not None and data.indicator_type is IndicatorType.STOP_LIGHT
  assert data.text == 'STOP' and not data.is_numeric and data.unit == ''
  assert stop_active(sample) is effective
  assert sample.longitudinal_active is effective


@pytest.mark.parametrize('kind', ['no_trigger', 'manual_chill', 'manual_experimental', 'ccm_veto', 'unknown_wire_reason'])
def test_gauge_never_infers_trigger_from_raw_lead_or_speed(kind):
  sample = state(kind, conditional_lead=ConditionalLead(12., 0.))
  assert gauge_data(sample) is None


def test_current_lead_stopped_slow_hysteresis_and_absence_are_distinct():
  sample = state('cem_lead', conditional_lead=ConditionalLead(12., .7))
  assert gauge_data(sample).text == 'STOPPED'
  threshold = replace(sample, conditional_lead=ConditionalLead(12., 1.))
  assert gauge_data(threshold).text == 'SLOW'
  assert gauge_data(threshold, lead_stopped=True).text == 'STOPPED'
  assert gauge_data(replace(sample, conditional_lead=None)).text == 'LEAD'


@pytest.mark.parametrize('bad', [None, NS(leadOne=NS(status=False, dRel=12., vLead=0.)),
                              NS(leadOne=NS(status=True, dRel=0., vLead=0.)),
                              NS(leadOne=NS(status=True, dRel=float('nan'), vLead=0.)),
                              NS(leadOne=NS(status=True, dRel=12., vLead=float('inf')))])
def test_missing_or_invalid_radar_metrics_are_not_defaulted_to_stopped(bad):
  assert conditional_lead_from_message(bad) is None


def test_current_radar_metrics_use_native_units():
  assert conditional_lead_from_message(NS(leadOne=NS(status=True, dRel=12., vLead=2.))) == ConditionalLead(12., 2.)


def test_curve_selected_source_retains_speed_units_and_csc_reduction():
  curve = CurveObservation(True, 15., 15., True, True, False, 100., 2., 30., 'curve', 'selected', 'saved', True, False, .005)
  sample = state('cem_curve', effective=True, curve=curve, metric=True)
  data = gauge_data(sample)
  assert data.indicator_type is IndicatorType.ROAD_CURVE and data.indicator_value == .005
  assert (data.text, data.unit, data.reduction_text) == ('54', 'km/h', '-36')
  assert (gauge_data(replace(sample, metric=False)).text, gauge_data(replace(sample, metric=False)).unit) == ('34', 'mph')
  perception = state('cem_curve', curve=curve)
  assert gauge_data(perception).text == '45'  # Actual ego speed; no CSC control authority.
  assert gauge_data(perception).reduction_text == ''


@pytest.mark.parametrize('changes', [{'alert': OnroadAlert(size=AlertSize.FULL, critical=True)},
                                    {'longitudinal_overridden': True}, {'reverse_driver_camera': True}])
def test_safety_and_driver_camera_states_suppress_gauge(changes):
  assert gauge_data(state(**changes)) is None


@pytest.mark.parametrize('camera', [CameraViewChoice.DRIVER, CameraViewChoice.NONE])
def test_gauge_is_hidden_for_non_road_camera(camera):
  sample = state()
  assert gauge_data(replace(sample, appearance=replace(sample.appearance, camera_view=camera))) is None


def test_custom_placement_disable_layer_migration_preserve_existing_widgets():
  older = default_document()
  older['layouts']['large'].pop(CEM_GAUGE_WIDGET)
  older['layouts']['large']['current_speed'].update(x=740, y=90, enabled=False)
  older['widgetOrder'] = {'large': [key for key in DEFAULT_WIDGET_ORDER['large'] if key != CEM_GAUGE_WIDGET]}
  frozen = copy.deepcopy(older)
  migrated = validate_document(older)
  assert older == frozen
  assert {key: value for key, value in migrated['layouts']['large'].items() if key != CEM_GAUGE_WIDGET} == older['layouts']['large']
  assert [key for key in migrated['widgetOrder']['large'] if key != CEM_GAUGE_WIDGET] == older['widgetOrder']['large']
  migrated['layouts']['large'][CEM_GAUGE_WIDGET].update(x=960, y=600, enabled=True)
  assert validate_document(migrated) == migrated
  gauge = AetherGauge(Mock())
  sample = state(customization=migrated)
  with patch.object(gauge, '_render_unified_road') as draw:
    gauge.render(sample)
    assert draw.call_args.args[1:3] == (1132., 685.)
    migrated['layouts']['large'][CEM_GAUGE_WIDGET]['enabled'] = False
    draw.reset_mock()
    gauge.render(sample)
    draw.assert_not_called()


def test_missing_receipt_clears_lead_memory_without_cooldown():
  gauge = AetherGauge(Mock())
  with patch.object(gauge, '_render_unified_road') as draw:
    gauge.render(state('cem_lead', conditional_lead=ConditionalLead(12., .7)))
    assert gauge._lead_stopped
    gauge.render(state('scene_unavailable'))
    assert not gauge._lead_stopped
    assert draw.call_count == 1


def test_dom_stop_road_has_fill_chevrons_line_and_pulsing_light():
  gauge = AetherGauge(Mock())
  with ExitStack() as stack:
    draws = {name: stack.enter_context(patch.object(rl, name)) for name in dir(rl) if name.startswith('draw_')}
    stack.enter_context(patch.object(rl, 'get_frame_time', return_value=1 / 60))
    stack.enter_context(patch.object(rl, 'get_time', return_value=1.))
    stack.enter_context(patch.object(gauge, '_draw_mini_cradle'))
    gauge.render(state())
  assert draws['draw_triangle'].call_count == 48
  assert draws['draw_line_ex'].call_count > 48  # Road edges, stop-line glow, and flowing chevrons.
  assert draws['draw_circle_v'].call_count == 5  # Three bulbs plus red-light bloom.


def test_projection_saved_gauge_migration_keeps_native_layout_and_exit_layer():
  from openpilot.starpilot.system.android_auto.projection_layout import (CAR_EXIT, default_layout, projection_customization,
                                                                      validate_layout)
  from openpilot.starpilot.system.android_auto.tests.test_projection_layout import SCREEN
  document = default_layout(SCREEN)
  document['widgets'].pop(CEM_GAUGE_WIDGET)
  document['widgetOrder'] = [key for key in document.get('widgetOrder', []) if key != CEM_GAUGE_WIDGET]
  if not document['widgetOrder']:
    document.pop('widgetOrder')
  frozen = copy.deepcopy(document)
  migrated = validate_layout(document, SCREEN)
  assert document == frozen
  assert {key: value for key, value in migrated['widgets'].items() if key != CEM_GAUGE_WIDGET} == document['widgets']
  assert migrated['widgets'][CEM_GAUGE_WIDGET]['enabled']
  base = default_document()
  unchanged = copy.deepcopy(base)
  projected = projection_customization(migrated, base)
  assert base == unchanged and projected['layouts']['compact'] == base['layouts']['compact']
  assert projected['layouts']['large'][CEM_GAUGE_WIDGET]['enabled']
  if 'widgetOrder' in migrated:
    assert migrated['widgetOrder'][-1] == CAR_EXIT


def test_numeric_cradle_measurement_and_draw_share_explicit_bitmap_font_roles():
  from openpilot.starpilot.ui.onroad_cem_gauge import AetherGaugeData
  from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole
  fonts = Mock(spec=BitmapFonts)
  metrics = {'54': NS(width=110., height=90.), '-36': NS(width=55., height=40.), 'km/h': NS(width=66., height=38.)}
  fonts.measure.side_effect = lambda text, _role, _size: metrics[text]
  gauge = AetherGauge(fonts)
  data = AetherGaugeData('54', unit='km/h', reduction_text='-36', is_numeric=True)
  with patch.object(rl, 'draw_line_ex'):
    gauge._draw_mini_cradle(500., 145., data)
  assert [call.args for call in fonts.measure.call_args_list] == [
    ('54', FontRole.BOLD, 75), ('-36', FontRole.MEDIUM, 33), ('km/h', FontRole.MEDIUM, 30)]
  expected = {'54': (FontRole.BOLD, 75, 445., 154.), '-36': (FontRole.MEDIUM, 33, 564., 179.),
              'km/h': (FontRole.MEDIUM, 30, 467., 251.)}
  for text, layout in expected.items():
    calls = [call.args for call in fonts.draw.call_args_list if call.args[0] == text]
    assert len(calls) == 5  # Four Dom shadow samples plus the measured foreground glyph.
    assert calls[-1][1:5] == layout
    assert [call[3:5] for call in calls[:4]] == [(layout[2] + dx, layout[3] + dy)
                                                   for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1))]


def test_text_cradle_uses_profile_measurement_and_keeps_shadow_geometry():
  from openpilot.starpilot.ui.onroad_cem_gauge import AetherGaugeData
  from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole
  fonts = Mock(spec=BitmapFonts)
  fonts.measure.return_value = NS(width=200., height=58.)
  gauge = AetherGauge(fonts)
  gauge._draw_mini_cradle(500., 145., AetherGaugeData('STOPPED'))
  fonts.measure.assert_called_once_with('STOPPED', FontRole.BOLD, 48)
  calls = [call.args for call in fonts.draw.call_args_list]
  assert len(calls) == 5
  assert calls[-1][:5] == ('STOPPED', FontRole.BOLD, 48, 400., 160.)
  assert [call[3:5] for call in calls[:4]] == [(399., 159.), (401., 159.), (399., 161.), (401., 161.)]


@pytest.mark.parametrize('projection', [False, True])
def test_numeric_caption_declared_footprint_fits_actual_bottom_content_edge(projection):
  from openpilot.starpilot.system.android_auto.projection_layout import (default_layout_for_viewport, layout_metadata_for_viewport,
                                                                      projection_customization, validate_layout_for_viewport)
  from openpilot.starpilot.ui.onroad_customization import customization_metadata
  from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile
  viewport = (2160, 1080)
  if projection:
    document = default_layout_for_viewport(viewport)
    metadata = layout_metadata_for_viewport(viewport)
    placed = document['widgets'][CEM_GAUGE_WIDGET]
    placed.update(x=980, y=750, enabled=True)
    validated = validate_layout_for_viewport(document, viewport)
    customization = projection_customization(validated, default_document())
  else:
    document = default_document()
    metadata = customization_metadata()['profiles']['large']
    placed = document['layouts']['large'][CEM_GAUGE_WIDGET]
    placed.update(x=980, y=750, enabled=True)
    customization = validate_document(document)
  assert metadata['widgets'][CEM_GAUGE_WIDGET]['height'] == 300
  # Both screens clip the onroad content 30 pixels above the physical bottom.
  assert metadata['bounds']['y'] + metadata['bounds']['height'] == 1050
  assert placed['y'] + 300 == 1050
  fonts = Mock(spec=BitmapFonts)
  fonts.measure.side_effect = lambda _text, _role, size: NS(width=80., height=size * Profile.LARGE.font_scale)
  gauge = AetherGauge(fonts)
  with patch.object(rl, 'draw_line_ex'):
    sample = state('cem_curve', customization=customization)
    gauge._draw_mini_cradle(1152., placed['y'] + 145, gauge_data(sample))
  unit_calls = [call.args for call in fonts.draw.call_args_list if call.args[0] == 'mph']
  assert len(unit_calls) == 5
  unit_size = unit_calls[-1][2]
  assert unit_calls[-1][1] is FontRole.MEDIUM
  assert max(call[4] for call in unit_calls) + unit_size * Profile.LARGE.font_scale <= 1050
  for invalid_y in (751, 780):
    placed['y'] = invalid_y
    with pytest.raises(ValueError):
      if projection:
        validate_layout_for_viewport(document, viewport)
      else:
        validate_document(document)


@pytest.mark.parametrize('projection', [False, True])
@pytest.mark.parametrize('kind', [None, 'scene_unavailable', 'unavailable', 'no_trigger', 'manual_chill',
                                'manual_experimental', 'unknown_wire_reason', 'cem_signal', 'cem_speed',
                                'cem_stop', 'cem_lead', 'cem_curve', 'curve_control'])
def test_source_drawer_reserves_gauge_only_when_actual_renderer_draws(projection, kind):
  from openpilot.starpilot.system.android_auto.projection_layout import default_layout_for_viewport, projection_customization
  from openpilot.starpilot.ui.large_speed_geometry import source_panel_bounds
  from openpilot.starpilot.ui.tests.test_speed_stack import road

  viewport = (2160, 1080)
  document = default_document()
  document['layouts']['large']['speed_limit_actions']['y'] = 750
  if projection:
    projected = default_layout_for_viewport(viewport)
    projected['widgets']['speed_limit_actions']['y'] = 750
    document = projection_customization(projected, document)
  sample = replace(state(kind if kind and kind != 'curve_control' else 'no_trigger'), customization=document,
                   longitudinal_active=True, slc_system_long_available=True, speed_limit=road().speed_limit)
  if kind is None:
    sample = replace(sample, conditional_perception=None)
  elif kind == 'curve_control':
    curve = CurveObservation(True, 15., 15., True, True, False, 100., 2., 30., 'curve', 'selected', 'saved', True, False, .005)
    sample = replace(sample, curve=curve)
  content = NS(x=30, y=30, width=1800, height=1020)
  bounds = source_panel_bounds(sample, 200, content)
  disabled = copy.deepcopy(document)
  disabled['layouts']['large'][CEM_GAUGE_WIDGET]['enabled'] = False
  disabled_bounds = source_panel_bounds(replace(sample, customization=disabled), 200, content)
  gauge = AetherGauge(Mock())
  with patch.object(gauge, '_render_unified_road') as draw:
    gauge.render(sample)
  visible = kind in ('cem_stop', 'cem_lead', 'cem_curve', 'curve_control')
  assert (gauge_data(sample) is not None) is visible
  assert draw.called is visible
  assert bounds is not None and disabled_bounds is not None
  if not visible:
    assert bounds == disabled_bounds  # A blank gauge consumes exactly the disabled footprint.
  else:
    placed = document['layouts']['large'][CEM_GAUGE_WIDGET]
    x, y, width, height = bounds
    assert (x + width <= placed['x'] or x >= placed['x'] + 344 or
            y + height <= placed['y'] or y >= placed['y'] + 300)
