"""CPU-only ownership and cleanup checks for the projection-only road view."""

import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).parents[1]
UI_STATE = ROOT.parents[2] / 'selfdrive/ui/ui_state.py'
PRESENTATION = ROOT.parents[1] / 'ui/presentation.py'

spec = importlib.util.spec_from_file_location('private_projection_onroad', ROOT / 'projection_onroad.py')
assert spec is not None and spec.loader is not None
projection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projection)


class FakeGraphics:
  BLACK = object()

  @staticmethod
  def Color(*values): return values

  @staticmethod
  def Rectangle(*values): return values

  @staticmethod
  def draw_rectangle(*_): pass

  @staticmethod
  def draw_rectangle_rounded(*_): pass

  @staticmethod
  def draw_rectangle_rounded_lines_ex(*_): pass

  @staticmethod
  def unload_texture(*_): pass


class TestProjectionOnroad(unittest.TestCase):
  def dependencies(self, *, fail_view=False, fail_camera=False):
    events = []
    ui = SimpleNamespace(projection_read_only=True, started=False, _offroad_transition_callbacks=[],
                         sm=object(), started_frame=0, is_onroad=lambda: False)

    class Fonts:
      def __init__(self, profile, directory, *, headless_context):
        self.profile = profile
        events.append(('fonts', profile, headless_context))

      def draw(self, *_): events.append('draw')
      def close(self): events.append('fonts_closed')

    class Camera:
      def __init__(self):
        if fail_camera:
          raise RuntimeError('camera shader failed')
        events.append('camera')
        ui._offroad_transition_callbacks.append(self._offroad_transition)

      def _offroad_transition(self): pass
      def close(self): events.append('camera_closed')
      def render_camera_model_layer(self, *_args, **_kwargs): events.append('camera_render')

    class View:
      def __init__(self, *_args, **kwargs):
        if fail_view:
          raise RuntimeError('view texture failed')
        events.append('view')
        self.viewport = kwargs['projection_viewport']
        self.steering_wheel = SimpleNamespace(_texture=None)
        self.driver_monitor_layer = None

      def render(self, *_): events.append('road_render')
      def close(self): events.append('view_closed')

    class Adapter:
      def __init__(self, *_): events.append('adapter')
      def build(self, *_args, **_kwargs): return SimpleNamespace(onroad=SimpleNamespace())

    native = SimpleNamespace(rl=FakeGraphics, ui_state=ui, camera=Camera, onroad=View,
                             monitor=lambda *_: SimpleNamespace(render=lambda *_a, **_k: None),
                             fonts=Fonts, font_role=SimpleNamespace(BRAND='brand', MEDIUM='medium'),
                             profile=SimpleNamespace(LARGE='large'), font_directory=lambda: Path('/unused'),
                             adapter=Adapter, current_message=lambda *_a, **_k: None,
                             shell_mode=SimpleNamespace(ONROAD='onroad'))
    return native, events

  def test_standby_and_live_view_only_construct_display_owners(self):
    native, events = self.dependencies()
    view = projection.ProjectionOnroad(dependencies=native)
    self.assertEqual((view.width, view.height), (1860, 1240))
    self.assertEqual(view.onroad.viewport, (1860, 1240))
    self.assertEqual(events[:4], [('fonts', 'large', True), 'camera', 'view', 'adapter'])
    view.render()
    self.assertIn('draw', events)
    self.assertNotIn('road_render', events)
    native.ui_state.started = True
    view.render()
    self.assertIn('road_render', events)
    view.close()
    self.assertEqual(events[-3:], ['view_closed', 'camera_closed', 'fonts_closed'])
    self.assertEqual(native.ui_state._offroad_transition_callbacks, [])

  def test_negotiated_viewport_overrides_landscape_fallback(self):
    native, _ = self.dependencies()
    view = projection.ProjectionOnroad(dependencies=native, viewport=(2880, 1080))
    self.assertEqual(view.onroad.viewport, (2880, 1080))
    view.close()

  def test_failed_renderer_construction_closes_prior_resources(self):
    native, events = self.dependencies(fail_view=True)
    with self.assertRaisesRegex(RuntimeError, 'view texture failed'):
      projection.ProjectionOnroad(dependencies=native)
    self.assertEqual(events[-2:], ['camera_closed', 'fonts_closed'])
    self.assertEqual(native.ui_state._offroad_transition_callbacks, [])

  def test_failed_camera_construction_closes_fonts(self):
    native, events = self.dependencies(fail_camera=True)
    with self.assertRaisesRegex(RuntimeError, 'camera shader failed'):
      projection.ProjectionOnroad(dependencies=native)
    self.assertEqual(events[-1], 'fonts_closed')

  def test_source_avoids_action_owners_and_native_ui_state_has_explicit_read_only_path(self):
    source = (ROOT / 'current_car_ui.py').read_text()
    composition = (ROOT / 'projection_onroad.py').read_text()
    self.assertIn("os.environ['STARPILOT_PROJECTION_READ_ONLY'] = '1'", source)
    self.assertNotIn('StarMainLayout', source)
    self.assertNotIn('PubMaster', source + composition)
    self.assertNotIn('WifiManager', source + composition)
    self.assertNotIn('GalaxyAccessOwner', source + composition)
    self.assertIn('CameraView.__init__(self', composition)
    self.assertNotIn('AugmentedRoadView.__init__(self', composition)
    self.assertIn('headless_context=True', composition)
    self.assertIn('if self.projection_read_only:', UI_STATE.read_text())
    self.assertIn('if ui_state.projection_read_only:', UI_STATE.read_text())
    self.assertIn('headless_context: bool = False', PRESENTATION.read_text())

  def test_projection_update_skips_prime_thread_and_device_power(self):
    tree = ast.parse(UI_STATE.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'UIState')
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'update')
    namespace: dict = {'time': SimpleNamespace(monotonic=lambda: 42.0),
                 'device': SimpleNamespace(update=lambda: self.fail('device power invoked'))}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(UI_STATE), 'exec'), namespace)
    events = []
    fake = SimpleNamespace(projection_read_only=True,
                           sm=SimpleNamespace(update=lambda *_: events.append('sm')),
                           _update_state=lambda: events.append('state'),
                           _update_status=lambda: events.append('status'),
                           update_params=lambda: events.append('params'),
                           _projection_params_at=None,
                           prime_state=SimpleNamespace(start=lambda: self.fail('prime API invoked')))
    namespace['update'](fake)
    namespace['update'](fake)
    self.assertEqual(events, ['sm', 'state', 'status', 'params', 'sm', 'state', 'status'])

  def test_projection_params_exposes_reads_without_write_methods(self):
    tree = ast.parse(UI_STATE.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'ProjectionParams')
    namespace: dict = {'Params': object}
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(UI_STATE), 'exec'), namespace)
    source = SimpleNamespace(get=lambda key: b'value', get_bool=lambda key: True,
                             get_int=lambda key: 2, get_float=lambda key: 0.5,
                             get_param_path=lambda key: Path('/unused'))
    params = namespace['ProjectionParams'](source)
    self.assertEqual(params.get('x'), b'value')
    self.assertTrue(params.get_bool('x'))
    for method in ('put', 'remove', 'clear_all', 'delete'):
      self.assertFalse(hasattr(params, method))


if __name__ == '__main__':
  unittest.main()
