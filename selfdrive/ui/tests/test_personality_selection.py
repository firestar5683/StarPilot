"""Host regressions for actual native methods; graphics/Params are synthetic.

Run without root native conftest: pytest -c /dev/null --confcutdir=selfdrive/ui/tests
These tests do not simulate vehicle dynamics or prove on-device touch delivery.
"""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
OPTIONS = ["aggressive", "standard", "relaxed"]


def methods(path, class_name, names, env):
  tree = ast.parse((ROOT / path).read_text())
  cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
  cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
  cls.bases = [ast.Name(id="Base", ctx=ast.Load())]
  module = ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[]))
  namespace = {"Base": Base, **env}
  exec(compile(module, str(ROOT / path), "exec"), namespace)
  return namespace[class_name]


class Base:
  def _update_state(self):
    pass

  def _handle_mouse_release(self, _):
    pass


class Params:
  def __init__(self, **values):
    self.values, self.writes = values, []

  def get_bool(self, key):
    return bool(self.values.get(key, False))

  def get_int(self, key, **kwargs):
    return self.values.get(key, kwargs.get("default", 0))

  get = get_int

  def remove(self, key):
    self.values.pop(key, None)

  def put_int(self, key, value):
    self.values[key] = value
    self.writes.append((key, value))

  put = put_bool = put_nonblocking = put_int


class Choice:
  def __init__(self):
    self.value, self.selected_button = "standard", 1
    self._options = OPTIONS
    self.action_item = self

  def set_value(self, value):
    self.value = value

  def set_selected_button(self, value):
    self.selected_button = value

  def set_enabled(self, value):
    self.enabled = value

  def set_visible(self, value):
    self.visible = value

  def set_state(self, value):
    self.state = value

  set_checked = set_state

  def set_description(self, _):
    pass


@pytest.mark.parametrize("mici", [False, True], ids=["comma3", "comma4"])
@pytest.mark.parametrize("selected", [0, 2])
def test_onroad_readback_repairs_stale_widget_even_when_shared_cache_matches(mici, selected):
  sm = {"selfdriveState": SimpleNamespace(personality=OPTIONS[selected])}
  class SubMaster(dict):
    updated = {"selfdriveState": True}
  state = SimpleNamespace(sm=SubMaster(sm), personality=selected, started=True)
  path = "selfdrive/ui/" + ("mici/" if mici else "") + "layouts/settings/toggles.py"
  cls = methods(path, "TogglesLayoutMici" if mici else "TogglesLayout", {"_update_state"},
                {"ui_state": state, "PERSONALITY_TO_INT": dict(zip(OPTIONS, range(3), strict=True))})
  layout = cls()
  layout._personality_seen = None
  choice = Choice()
  layout._personality_toggle = layout._long_personality_setting = choice
  layout._longitudinal_mode = SimpleNamespace(update=lambda: None, label="Chill")
  layout._experimental_btn = Choice()
  layout._sync_mode_selection = lambda: None
  layout._update_state()
  assert (choice.value if mici else choice.selected_button) == (OPTIONS[selected] if mici else selected)
  # UI feedback for a queued write must survive repeated pre-write messages.
  next_selected = (selected + 1) % 3
  choice.set_value(OPTIONS[next_selected])
  choice.set_selected_button(next_selected)
  layout._update_state()
  assert (choice.value if mici else choice.selected_button) == (OPTIONS[next_selected] if mici else next_selected)
  # A new selfdrived result still wins, including a safety-enforced reversion.
  state.sm["selfdriveState"].personality = OPTIONS[(selected + 2) % 3]
  layout._update_state()
  assert (choice.value if mici else choice.selected_button) == (OPTIONS[(selected + 2) % 3] if mici else (selected + 2) % 3)


@pytest.mark.parametrize("selected", range(3))
def test_comma4_settings_cycles_existing_selection_without_profile_writes(selected):
  # Execute the real BigMultiToggle and BigMultiParamToggle release chain.
  multi = methods("selfdrive/ui/mici/widgets/button.py", "BigMultiToggle", {"_handle_mouse_release"}, {"MousePos": object})
  param = methods("selfdrive/ui/mici/widgets/button.py", "BigMultiParamToggle", {"_handle_mouse_release"},
                  {"Base": multi, "MousePos": object})
  button = param()
  button.value, button._options, button._select_callback = OPTIONS[selected], OPTIONS, None
  button.set_value = lambda value: setattr(button, "value", value)
  button._param, button._params = "LongitudinalPersonality", Params(IsOnroad=True, IsOffroad=False)
  button._handle_mouse_release(None)
  assert button._params.writes == [("LongitudinalPersonality", (selected + 1) % 3)]


@pytest.mark.parametrize("selected", range(3))
def test_comma3_settings_selects_existing_personality_onroad(selected):
  cls = methods("selfdrive/ui/layouts/settings/toggles.py", "TogglesLayout", {"_set_longitudinal_personality"}, {})
  layout = cls()
  layout._personality_seen = None
  layout._params = Params(IsOnroad=True, IsOffroad=False)
  layout._set_longitudinal_personality(selected)
  assert layout._params.writes == [("LongitudinalPersonality", selected)]


@pytest.mark.parametrize("started,capable,safe,visible,allowed", [
  (True, True, False, True, True),
  (False, True, False, True, False),
  (True, False, False, True, False),
  (True, True, True, True, False),
  (True, True, False, False, False),
])
def test_comma4_sidebar_requires_longitudinal_control(started, capable, safe, visible, allowed):
  params = Params(SafeMode=safe, LongitudinalPersonality=1)
  state = SimpleNamespace(started=started, has_longitudinal_control=capable, ui_params=params, personality=1)
  enum = SimpleNamespace(aggressive=0, standard=1, relaxed=2)
  cls = methods("selfdrive/ui/mici/onroad/augmented_road_view.py", "AugmentedRoadView",
                {"_sidebar_personality_touch_enabled", "_cycle_personality_profile", "_handle_mouse_release"},
                {"ui_state": state, "log": SimpleNamespace(LongitudinalPersonality=enum), "MousePos": object})
  view = cls()
  view._sidebar_widgets_visible = lambda: visible
  view._touch_in_sidebar = lambda _: True
  view._sidebar_personality_pressed = True
  assert view._sidebar_personality_touch_enabled() is allowed
  view._handle_mouse_release(None)
  assert params.writes == ([("LongitudinalPersonality", 2)] if allowed else [])


@pytest.mark.parametrize("mici", [False, True], ids=["comma3", "comma4"])
@pytest.mark.parametrize("safe,capable", [(False, True), (True, True), (False, False), (True, False)])
def test_settings_enable_selection_onroad_but_preserve_safety_gates(mici, safe, capable):
  params = Params(SafeMode=safe, LongitudinalPersonality=1, IsOnroad=True, IsOffroad=False)
  state = SimpleNamespace(params=params, update_params=lambda: None, engaged=True,
                          CP=SimpleNamespace(alphaLongitudinalAvailable=False),
                          has_longitudinal_control=capable, experimental_mode_available=capable)
  path = "selfdrive/ui/" + ("mici/" if mici else "") + "layouts/settings/toggles.py"
  cls = methods(path, "TogglesLayoutMici" if mici else "TogglesLayout", {"_update_toggles"},
                {"ui_state": state, "tr": lambda s: s,
                 "log": SimpleNamespace(LongitudinalPersonality=SimpleNamespace(relaxed=2))})
  layout = cls()
  layout._personality_seen = None
  layout._params = params
  choice = Choice()
  layout._personality_toggle = layout._long_personality_setting = choice
  layout._experimental_btn = Choice()
  layout._toggles = {"ExperimentalMode": Choice()}
  layout._toggle_defs = {}
  layout._refresh_toggles = []
  layout._sync_rhd_toggle = layout._update_experimental_mode_icon = lambda: None
  layout._update_toggles()
  assert choice.enabled is (capable and not safe)
  assert all(key in {"ExperimentalMode", "LongitudinalPersonality"} for key, _ in params.writes)


def test_comma4_stale_standard_tile_does_not_reselect_active_relaxed():
  # Sidebar has selected Relaxed and updated the shared cache. The settings
  # widget still says Standard. Before the fix its next tap wrote Relaxed again.
  class SubMaster(dict):
    updated = {"selfdriveState": True}
  state = SimpleNamespace(sm=SubMaster(selfdriveState=SimpleNamespace(personality="relaxed")),
                          personality=2, started=True)
  cls = methods("selfdrive/ui/mici/layouts/settings/toggles.py", "TogglesLayoutMici", {"_update_state"},
                {"ui_state": state, "PERSONALITY_TO_INT": dict(zip(OPTIONS, range(3), strict=True))})
  multi = methods("selfdrive/ui/mici/widgets/button.py", "BigMultiToggle", {"_handle_mouse_release"}, {"MousePos": object})
  param = methods("selfdrive/ui/mici/widgets/button.py", "BigMultiParamToggle", {"_handle_mouse_release"},
                  {"Base": multi, "MousePos": object})
  button = param()
  button.value, button._options, button._select_callback = "standard", OPTIONS, None
  button.set_value = lambda value: setattr(button, "value", value)
  button._param, button._params = "LongitudinalPersonality", Params(LongitudinalPersonality=2, IsOnroad=True, IsOffroad=False)
  layout = cls()
  layout._personality_seen = None
  layout._personality_toggle = button
  layout._longitudinal_mode = SimpleNamespace(update=lambda: None, label="Chill")
  layout._experimental_btn = Choice()
  layout._update_state()
  assert not button._params.writes
  button._handle_mouse_release(None)
  assert button._params.writes == [("LongitudinalPersonality", 0)]
