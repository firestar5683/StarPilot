import copy
import unittest
from dataclasses import replace
from unittest.mock import patch

import numpy as np
import pyray as rl

from openpilot.starpilot.ui.onroad_customization import PROFILES, default_document, validate_document
from openpilot.starpilot.ui.onroad_state import OnroadState, SpeedLimitObservation
from openpilot.starpilot.ui.onroad_torque import TorqueBarWidget


def scene(document=None):
  return replace(OnroadState(True, True, 20, 80, SpeedLimitObservation(), lateral_active=True),
                 customization=document or default_document())


def geometry(profile, state, torque=.3, alpha=1.):
  data = PROFILES[profile]
  bounds = data['bounds']
  rect = rl.Rectangle(*(bounds[key] for key in ('x', 'y', 'width', 'height')))
  widget = TorqueBarWidget()
  widget._torque_filter.update = lambda value: torque
  widget._alpha_filter.update = lambda value: alpha
  calls, dots = [], []
  with patch('openpilot.starpilot.ui.onroad_torque.draw_polygon', side_effect=lambda rect, points, **kwargs: calls.append((rect, points.copy(), kwargs))), \
       patch('openpilot.starpilot.ui.onroad_torque.rl.draw_circle', side_effect=lambda x, y, radius, color: dots.append((x, y, radius))):
    widget.render(rect, state, data['width'])
  return calls, dots


class TestTorqueLayout(unittest.TestCase):
  def test_moved_polygon_dot_and_gradient_origin_translate_without_resizing(self):
    for profile in PROFILES:
      with self.subTest(profile=profile):
        document = default_document()
        base = document['layouts'][profile]['torque_bar']
        base['x'] += 10
        base['y'] -= 40
        document = validate_document(document)
        original, original_dots = geometry(profile, scene())
        moved, moved_dots = geometry(profile, scene(document))
        for (old_rect, old_points, old_style), (new_rect, new_points, new_style) in zip(original, moved, strict=True):
          np.testing.assert_array_equal(new_points, old_points + np.array([10, -40], dtype=np.float32))
          self.assertEqual((new_rect.x, new_rect.y, new_rect.width, new_rect.height),
                           (old_rect.x + 10, old_rect.y - 40, old_rect.width, old_rect.height))
          if 'gradient' in old_style:
            for field in ('start', 'end', 'stops'):
              self.assertEqual(getattr(new_style['gradient'], field), getattr(old_style['gradient'], field))
            self.assertEqual([tuple(getattr(color, channel) for channel in 'rgba') for color in new_style['gradient'].colors],
                             [tuple(getattr(color, channel) for channel in 'rgba') for color in old_style['gradient'].colors])
        self.assertEqual(moved_dots, [(x + 10, y - 40, radius) for x, y, radius in original_dots])

  def test_metadata_bounds_enclose_all_legal_polygon_and_dot_states(self):
    for profile, data in PROFILES.items():
      widget = data['widgets']['torque_bar']
      x, y = widget['default']['x'], widget['default']['y']
      right, bottom = x + widget['width'], y + widget['height']
      for torque in np.linspace(-1, 1, 41):
        for alpha in (0, .01, .2, .5, 1):
          polygons, dots = geometry(profile, scene(), float(torque), alpha)
          for _, points, _ in polygons:
            self.assertGreaterEqual(float(points[:, 0].min()), x)
            self.assertGreaterEqual(float(points[:, 1].min()), y)
            self.assertLessEqual(float(points[:, 0].max()), right)
            self.assertLessEqual(float(points[:, 1].max()), bottom)
          for cx, cy, radius in dots:
            self.assertGreaterEqual(cx - radius, x)
            self.assertGreaterEqual(cy - radius, y)
            self.assertLessEqual(cx + radius, right)
            self.assertLessEqual(cy + radius, bottom)

  def test_only_torque_underlay_can_overlap_reserved_actions(self):
    document = default_document()
    self.assertEqual(validate_document(document), document)
    document['layouts']['compact']['torque_bar'].update(x=174, y=179)
    validate_document(document)
    for key in ('max_speed', 'driver_monitor', 'steering_wheel'):
      with self.subTest(key=key):
        invalid = default_document()
        invalid['layouts']['compact'][key].update(x=174, y=19 if key == 'max_speed' else 179)
        with self.assertRaises(ValueError):
          validate_document(invalid)

  def test_complete_old_three_and_four_widget_shapes_migrate(self):
    for count in (3, 4):
      document = default_document()
      for key in ('model_confidence', 'conditional_mode', 'following_distance'):
        del document['layouts']['compact'][key]
      for layout in document['layouts'].values():
        del layout['torque_bar']
        del layout['speed_limit_actions']
        if count == 3:
          del layout['driver_monitor']
      document['palette']['text'] = '#12345678'
      document['layouts']['large']['current_speed'].update(x=700, y=200, enabled=False)
      old = copy.deepcopy(document)
      result = validate_document(document)
      self.assertEqual(document, old)
      self.assertEqual(result['palette'], old['palette'])
      for profile, layout in old['layouts'].items():
        for key, placement in layout.items():
          self.assertEqual(result['layouts'][profile][key], placement)
        self.assertEqual(result['layouts'][profile]['torque_bar'], default_document()['layouts'][profile]['torque_bar'])
        self.assertEqual(result['layouts'][profile]['speed_limit_actions'], default_document()['layouts'][profile]['speed_limit_actions'])

  def test_mixed_legacy_shape_is_rejected(self):
    document = default_document()
    for layout in document['layouts'].values():
      del layout['torque_bar']
      del layout['speed_limit_actions']
    del document['layouts']['large']['driver_monitor']
    with self.assertRaises(ValueError):
      validate_document(document)

  def test_disabled_widget_keeps_filter_updates_without_drawing(self):
    widget = TorqueBarWidget()
    data = PROFILES['compact']['bounds']
    rect = rl.Rectangle(*(data[key] for key in ('x', 'y', 'width', 'height')))
    document = default_document()
    document['layouts']['compact']['torque_bar']['enabled'] = False
    with patch('openpilot.starpilot.ui.onroad_torque.draw_polygon') as draw:
      widget.render(rect, replace(scene(document), torque_utilization=.8), 536)
      draw.assert_not_called()
    self.assertGreater(widget._torque_filter.x, 0)
    self.assertGreater(widget._alpha_filter.x, 0)

  def test_unknown_source_or_inactive_lateral_resets_without_drawing(self):
    from types import SimpleNamespace as NS
    widget = TorqueBarWidget()
    for lateral, source in ((True, False), (False, True)):
      widget._torque_filter.x = widget._alpha_filter.x = .8
      state = NS(lateral_active=lateral, torque_source_available=source, customization=default_document())
      with patch('openpilot.starpilot.ui.onroad_torque.draw_polygon') as draw:
        widget.render(rl.Rectangle(0, 0, 476, 240), state, 536)
        draw.assert_not_called()
      self.assertEqual((widget._torque_filter.x, widget._alpha_filter.x), (0, 0))

  def test_new_drive_resets_existing_filters_before_first_fresh_render(self):
    from types import SimpleNamespace as NS
    widget = TorqueBarWidget()
    state = NS(lateral_active=True, torque_source_available=True, torque_drive_frame=10,
               torque_utilization=.8, customization=default_document())
    rect = rl.Rectangle(0, 0, 476, 240)
    with patch('openpilot.starpilot.ui.onroad_torque.draw_polygon'), patch('openpilot.starpilot.ui.onroad_torque.rl.draw_circle'):
      for _ in range(30):
        widget.render(rect, state, 536)
      self.assertGreater(widget._torque_filter.x, .7)
      self.assertGreater(widget._alpha_filter.x, .9)
      state.torque_drive_frame = 100
      widget.render(rect, state, 536)
      self.assertLess(widget._torque_filter.x, .2)
      self.assertLess(widget._alpha_filter.x, .2)
