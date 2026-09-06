"""Host-only widget integration: real class bodies, fake graphics and Params."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_native_longitudinal_mode import Button, native_layout, setup_client, MODE_LABELS, mode

ROOT = Path(__file__).resolve().parents[4]


def load_class(path, name, env):
  tree = ast.parse(path.read_text())
  cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
  exec(compile(ast.Module(body=[cls], type_ignores=[]), str(path), 'exec'), env)
  return env[name]


def big_layout(values=None):
  _, state = native_layout(values)
  state.ui_params = state.params
  client, params, requests, signals, now, finish = setup_client(values)
  # One Params store serves the local guard and extracted API handler.
  params.values.update({'IsRHDOverride': True, 'DisableOpenpilotLongitudinal': False})
  original_get = params.get
  params.get = lambda key, **kwargs: original_get(key)
  state.params = state.ui_params = params

  class Item:
    def __init__(self, title='', description='', *args, **kwargs):
      self.title, self.description = title, description
      self.action_item = Button()
      self.action_item.selected_button = kwargs.get('selected_index', -1)
      self.action_item.callback = kwargs.get('callback')
      self.buttons = kwargs.get('buttons', [])
    def set_description(self, value):
      self.description = value
    def set_visible(self, value):
      self.visible = value

  class Widget:
    pass

  env = dict(Widget=Widget, ui_state=state, tr=lambda x: x, DESCRIPTIONS={},
             multiple_button_item=Item, toggle_item=Item, UnknownKeyName=KeyError,
             Scroller=lambda widgets, **kw: SimpleNamespace(widgets=widgets),
             LongitudinalModeClient=lambda: client, MODE_LABELS=MODE_LABELS, lock_reason=mode.lock_reason)
  tree = ast.parse((ROOT / 'selfdrive/ui/layouts/settings/toggles.py').read_text())
  descriptions = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'DESCRIPTIONS' for t in n.targets))
  env['tr_noop'] = lambda x: x
  exec(compile(ast.Module(body=[descriptions], type_ignores=[]), '<descriptions>', 'exec'), env)
  cls = load_class(ROOT / 'selfdrive/ui/layouts/settings/toggles.py', 'TogglesLayout', env)
  return cls(), state, client, params, requests, now, finish


@pytest.mark.parametrize('onroad', [False, True])
def test_comma3_all_modes_guarded_and_no_optimistic_selection(onroad):
  layout, state, client, params, requests, _, finish = big_layout({'IsOnroad': onroad, 'IsOffroad': not onroad})
  state.engaged = onroad
  assert layout._toggles['ExperimentalMode'] in layout._scroller.widgets
  assert not layout._toggles['ExperimentalMode'].visible
  assert layout._mode_setting.visible
  assert layout._mode_setting in layout._scroller.widgets
  assert [f() for f in layout._mode_setting.buttons] == ['Chill', 'Experimental', 'Cond. Exp.', 'Cond. Chill']
  for target in [1, 2, 3, 0]:
    previous = list(MODE_LABELS).index(client.state['mode'])
    layout._mode_setting.action_item.selected_button = target  # shared widget's eager update
    layout._select_longitudinal_mode(target)
    assert layout._mode_setting.action_item.selected_button == previous
    assert not layout._mode_enabled()
    finish()
    layout._update_state()
    assert layout._mode_setting.action_item.selected_button == target
  assert len([r for r in requests if r]) == 4
  assert not any(k == 'LongitudinalControlMode' for k, _ in params.writes)


@pytest.mark.parametrize('values', [{'SafeMode': True}, {'IsOffroad': False}, {'IsOnroad': True}, {'SafeMode': None}])
def test_comma3_locked_clicks_are_read_only(values):
  layout, state, client, params, requests, _, _ = big_layout(values)
  layout._update_state()
  layout._select_longitudinal_mode(1)
  assert not layout._mode_enabled()
  assert not params.writes and requests == [None]


def test_comma3_pending_capability_engagement_and_missing_state():
  layout, state, client, params, requests, _, _ = big_layout()
  for key, value in [('DisableOpenpilotLongitudinal', True), ('DisableOpenpilotLongitudinal', None)]:
    params.values[key] = value
    assert not layout._mode_enabled()
  params.values['DisableOpenpilotLongitudinal'] = False
  state.CP.alphaLongitudinalAvailable = True
  assert not layout._mode_enabled()
  params.values['AlphaLongitudinalEnabled'] = True
  assert layout._mode_enabled()
  state.engaged = True
  assert layout._mode_enabled()  # Engagement alone is not a mode lock.
  state.engaged = False
  state.CP = None
  assert not layout._mode_enabled()
  client.state = None
  layout._update_state()
  assert layout._mode_setting.action_item.selected_button == -1
  assert not params.writes and requests == [None]


def test_comma3_button_labels_fit_shipped_font():
  import re
  lines = (ROOT / 'selfdrive/assets/fonts/Inter-Medium.fnt').read_text().splitlines()
  base = int(re.search(r'lineHeight=(\d+)', lines[1])[1])
  glyphs = {int(d['id']): int(d['xadvance']) for line in lines if line.startswith('char ')
            for d in [dict(re.findall(r'(\w+)=(-?\d+)', line))]}
  layout, *_ = big_layout()
  for label in layout._mode_setting.buttons:
    assert sum(glyphs[ord(c)] for c in label()) * 40 / base < 260 - 20
  # Comma 3: 2160px display, expanded 500px settings sidebar, 40px
  # scroller padding per side. Title/icon must not overlap the four buttons.
  lines = (ROOT / 'selfdrive/assets/fonts/Inter-Regular.fnt').read_text().splitlines()
  base = int(re.search(r'lineHeight=(\d+)', lines[1])[1])
  glyphs = {int(d['id']): int(d['xadvance']) for line in lines if line.startswith('char ')
            for d in [dict(re.findall(r'(\w+)=(-?\d+)', line))]}
  title_width = sum(glyphs[ord(c)] for c in layout._mode_setting.title()) * 50 / base
  assert 20 + 80 + 20 + title_width + 20 + 4 * 260 + 3 * 20 + 20 <= 2160 - 500 - 2 * 40


def test_comma4_actual_multi_indicator_draw_and_dispatch_without_advancing():
  class Base(Button):
    LABEL_HORIZONTAL_PADDING = 40
    def __init__(self, text, value='', *args, **kwargs):
      super().__init__()
      self.value = value
      self._rect = SimpleNamespace(x=0, width=402)
      self._txt_enabled_toggle = SimpleNamespace(width=84)
      self.pills = []
      self.releases = 0
    def _handle_mouse_release(self, pos):
      self.releases += 1
    def _draw_content(self, y):
      pass
    def _draw_pill(self, x, y, checked):
      self.pills.append((x, y, checked))

  env = dict(BigButton=Base, BigToggle=Base, Callable=object, MousePos=object)
  # Real shared multi-toggle drawing, not a fake indicator implementation.
  load_class(ROOT / 'selfdrive/ui/mici/widgets/button.py', 'BigMultiToggle', env)
  env['MODE_LABELS'] = MODE_LABELS
  cls = load_class(ROOT / 'selfdrive/ui/mici/widgets/longitudinal_mode.py', 'LongitudinalModeButton', env)
  button = cls()
  for index, value in enumerate([*MODE_LABELS.values(), 'Unavailable']):
    button.set_value(value)
    button.pills.clear()
    button._draw_content(0)
    assert [checked for _, _, checked in button.pills] == [i == index for i in range(4)]
    button._handle_mouse_release(None)
    assert button.value == value
  assert button.releases == 5
