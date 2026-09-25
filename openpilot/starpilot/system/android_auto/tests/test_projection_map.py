"""The map overlay is created only when the AA layout enables it, prepared outside the frame, drawn at its placement."""
import copy
import unittest

from openpilot.starpilot.system.android_auto import projection_onroad as projection
from openpilot.starpilot.system.android_auto.projection_layout import default_layout_for_viewport
from openpilot.starpilot.system.android_auto.tests import test_projection_onroad_boundary as boundary


class FakeMap:
  def __init__(self, *, fonts):
    self.fonts = fonts
    self.prepared, self.drawn, self.closed = [], [], False

  def prepare(self, data, width, height):
    self.prepared.append((data, width, height))

  def draw(self, rect, opacity):
    self.drawn.append((rect, opacity))

  def close(self):
    self.closed = True


class FakeFeed:
  def __init__(self):
    self.reads = []

  def read(self, sm, *, navigation_requested=None):
    self.reads.append(sm)
    return "map input"


class TestProjectionMap(unittest.TestCase):
  def native(self):
    native, events = boundary.TestProjectionOnroad().dependencies()
    native.map_overlay, native.map_feed = FakeMap, FakeFeed
    return native, events

  def layout(self, **map_placement):
    document = default_layout_for_viewport((2880, 1080))
    document["widgets"]["nav_map"].update(map_placement)
    return document

  def test_disabled_map_builds_nothing(self):
    native, _ = self.native()
    view = projection.ProjectionOnroad(dependencies=native, viewport=(2880, 1080), customization=self.layout())
    self.assertIsNone(view.map)
    view.prepare()
    view.close()

  def test_enabled_map_prepares_onroad_and_draws_at_placement(self):
    native, _ = self.native()
    layout = self.layout(enabled=True, x=100, y=200, width=640, height=480, opacity=45)
    view = projection.ProjectionOnroad(dependencies=native, viewport=(2880, 1080), customization=layout)
    self.assertIsInstance(view.map, FakeMap)
    self.assertIs(view.map.fonts, view.fonts)
    self.assertEqual(view.onroad.map_layer, view._map_layer)
    view.prepare()
    self.assertEqual(view.map.prepared, [], "nothing to prepare while offroad")
    native.ui_state.started = True
    view.prepare()
    self.assertEqual(view.map.prepared, [("map input", 640, 480)])
    self.assertEqual(view.map_feed.reads, [native.ui_state.sm])
    view._map_layer(None, None)
    self.assertEqual(view.map.drawn, [((100, 200, 640, 480), 0.45)])
    overlay = view.map
    view.close()
    self.assertTrue(overlay.closed)

  def test_older_dependencies_without_a_map_still_work(self):
    native, _ = self.native()
    del native.map_overlay
    view = projection.ProjectionOnroad(dependencies=native, viewport=(2880, 1080),
                                       customization=self.layout(enabled=True))
    self.assertIsNone(view.map)
    native.ui_state.started = True
    view.prepare()
    view.close()

  def test_layout_document_is_not_mutated(self):
    native, _ = self.native()
    layout = self.layout(enabled=True)
    before = copy.deepcopy(layout)
    view = projection.ProjectionOnroad(dependencies=native, viewport=(2880, 1080), customization=layout)
    native.ui_state.started = True
    view.prepare()
    view.close()
    self.assertEqual(layout, before)
