"""Layer documents must survive persistence and remain independent per output."""
import copy
import json

import pytest

from openpilot.starpilot.ui.onroad_customization import (
  DEFAULT_WIDGET_ORDER, MODE_WIDGET, PROFILES, customization_metadata, decode_document, default_document, validate_document,
)
from openpilot.starpilot.system.android_auto.projection_layout import (
  default_layout_for_viewport, decode_layout_for_viewport, layout_metadata_for_viewport, projection_customization, validate_layout_for_viewport,
)


@pytest.mark.parametrize('profile', ['large', 'compact'])
def test_native_order_roundtrip(profile):
  document = default_document()
  before = copy.deepcopy(document)
  order = list(reversed(DEFAULT_WIDGET_ORDER[profile]))
  document['widgetOrder'] = {profile: order}
  assert decode_document(json.dumps(document).encode()) == document
  assert document['layouts'] == before['layouts']
  assert customization_metadata()['profiles'][profile]['widgetOrder'] == list(DEFAULT_WIDGET_ORDER[profile])
  assert set(order) == set(PROFILES[profile]['widgets'])


@pytest.mark.parametrize('order', [None, {}, [], ['bogus'], ['current_speed'] * 8, [False] * 8])
def test_bad_orders_rejected_by_both_outputs(order):
  native = default_document()
  native['widgetOrder'] = {'large': order}
  with pytest.raises(ValueError):
    validate_document(native)
  projection = default_layout_for_viewport((2880, 1080))
  projection['widgetOrder'] = order
  with pytest.raises(ValueError):
    validate_layout_for_viewport(projection, (2880, 1080))


def test_projection_order_is_independent_from_native_and_survives_decode():
  native = default_document()
  native['widgetOrder'] = {profile: list(DEFAULT_WIDGET_ORDER[profile]) for profile in PROFILES}
  before = copy.deepcopy(native)
  projection = default_layout_for_viewport((2880, 1080))
  # Legacy AA layouts must not inherit native large ordering.
  assert 'large' not in projection_customization(projection, native)['widgetOrder']
  projection['widgetOrder'] = list(reversed(layout_metadata_for_viewport((2880, 1080))['widgetOrder']))
  decoded = decode_layout_for_viewport(json.dumps(projection).encode(), (2880, 1080))
  assert decoded == projection
  converted = projection_customization(decoded, native)
  assert converted['widgetOrder']['large'] == projection['widgetOrder']
  assert converted['widgetOrder']['compact'] == native['widgetOrder']['compact']
  assert native == before


def test_legacy_projection_order_adds_upstream_mode_widget():
  projection = default_layout_for_viewport((2880, 1080))
  projection['widgets'].pop(MODE_WIDGET)
  projection['widgetOrder'] = [key for key in DEFAULT_WIDGET_ORDER['large'] if key != MODE_WIDGET]
  migrated = validate_layout_for_viewport(projection, (2880, 1080))
  assert migrated['widgets'][MODE_WIDGET]['enabled'] is False
  assert migrated['widgetOrder'] == [*projection['widgetOrder'], MODE_WIDGET, 'nav_card', 'nav_map', 'nav_home', 'nav_work']


def test_old_documents_keep_their_original_shape():
  assert validate_document(default_document()) == default_document()
  assert validate_layout_for_viewport(default_layout_for_viewport((1860, 1080)), (1860, 1080)) == default_layout_for_viewport((1860, 1080))


@pytest.mark.parametrize('profile,viewport', [('large', None), ('compact', None), ('large', (2880, 1080))])
def test_renderer_dispatches_each_widget_in_saved_order(profile, viewport):
  # Load the real composition method without native IPC/Params imports, which
  # are unavailable on CPU-only hosts. Widget drawing is replaced with a trace.
  import ast
  from pathlib import Path
  from types import SimpleNamespace as NS
  from unittest.mock import Mock
  from openpilot.starpilot.ui.onroad_customization import MODE_WIDGET, placement, widget_order, RAIL_WIDGETS

  source = Path(__file__).parents[1] / 'onroad.py'
  tree = ast.parse(source.read_text())
  method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == '_ordered_widgets')
  namespace = {'MODE_WIDGET': MODE_WIDGET, 'placement': placement, 'widget_order': widget_order, 'RAIL_WIDGETS': RAIL_WIDGETS,
               'AlertSize': NS(NONE='none', FULL='full'), 'CameraViewChoice': NS(NONE='none'),
               'rl': NS(Rectangle=lambda x, y, width, height: NS(x=x, y=y, width=width, height=height))}
  exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
  seen = []
  view = NS(fonts=NS(profile=profile), projection_viewport=viewport)
  view.pip_layer = Mock(side_effect=lambda rect, state, submit: [submit(key, lambda key=key: seen.append(key))
                                                               for key in ('pip_left', 'pip_right')])
  view.driver_monitor_layer = lambda *args: seen.append('driver_monitor')
  view._driving_mode = lambda *args: seen.append(MODE_WIDGET)
  view._slc_actions = lambda *args: seen.append('speed_limit_actions')
  for attr, key in [('unified_speed', 'cruise_limits'), ('current_speed', 'current_speed'),
                    ('steering_wheel', 'steering_wheel'), ('torque_bar', 'torque_bar')]:
    setattr(view, attr, NS(render=lambda *args, key=key: seen.append(key)))
  view.compact_hud = NS(_speed_limit_sign=lambda state: seen.append('speed_limit'),
                        render_max_speed=lambda state: seen.append('max_speed'),
                        render_steering_wheel=lambda state: seen.append('steering_wheel'))
  view.compact_sidebar = NS(render=lambda *args, widget: seen.append(widget))
  document = default_document()
  order = list(reversed(DEFAULT_WIDGET_ORDER[profile]))
  if viewport:
    projection = default_layout_for_viewport(viewport)
    order = list(reversed(layout_metadata_for_viewport(viewport)['widgetOrder']))
    projection['widgetOrder'] = order
    document = projection_customization(projection, document)
    view.map_layer = lambda *args: seen.append('nav_map')
    view.navigation = NS(render=lambda *args: seen.append('nav_card'))
    view.navigation_favorites = NS(render=lambda key, state: seen.append(key))
  document['widgetOrder'] = {profile: order}
  state = NS(customization=document, camera_available=True, viewport_width=1860, alert=NS(size='none'),
             appearance=NS(camera_view='road', hide_speed=False, hide_steering_wheel=False, show_torque_bar=True))
  namespace['_ordered_widgets'](view, NS(x=30, y=30, width=1800, height=1020), state)
  assert seen == order
  view.pip_layer.assert_called_once()  # Acquire the camera frame once, then draw each side at its layer.
  seen.clear()
  state.alert.size = 'full'
  namespace['_ordered_widgets'](view, NS(x=30, y=30, width=1800, height=1020), state)
  assert 'steering_wheel' not in seen
  assert 'speed_limit_actions' not in seen
  assert 'torque_bar' not in seen
