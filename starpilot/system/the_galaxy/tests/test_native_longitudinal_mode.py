"""Host-only native client + MICI integration; fake Params, no graphics/device."""
import ast
import re
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

from openpilot.selfdrive.ui.mici.layouts.settings.longitudinal_mode import LongitudinalModeClient, MODE_LABELS, validate_snapshot
from test_longitudinal_mode import Params, mode
from test_longitudinal_mode_api import client_for

SOURCE = Path(__file__).resolve().parents[4] / "selfdrive/ui/mici/layouts/settings/toggles.py"


class Executor:
  def __init__(self):
    self.jobs = []

  def submit(self, fn, *args):
    future = Future()
    self.jobs.append((future, fn, args))
    return future

  def finish(self):
    future, fn, args = self.jobs.pop(0)
    try:
      future.set_result(fn(*args))
    except Exception as exc:
      future.set_exception(exc)


def setup_client(values=None):
  params = Params({"ConditionalExperimental": False, "ExperimentalModeConfirmed": False, **(values or {})})
  api, signals = client_for(params)
  requests = []
  def transport(body=None):
    requests.append(body)
    response = api.get('/api/longitudinal_mode') if body is None else api.put('/api/longitudinal_mode', json=body)
    if response.status_code != 200:
      raise ValueError(response.json['error'])
    return response.json
  executor = Executor()
  now = [0]
  client = LongitudinalModeClient(transport, executor, lambda: now[0])
  def finish():
    executor.finish()
    client.update()
  client.update()
  finish()
  return client, params, requests, signals, now, finish


@pytest.mark.parametrize('onroad', [False, True])
def test_full_cycle_uses_guarded_api_and_never_confirms_persistently(onroad):
  client, params, requests, signals, _, finish = setup_client({'IsOnroad': onroad, 'IsOffroad': not onroad})
  assert client.label == 'Chill' and client.enabled
  assert not params.writes
  for label in ['Experimental', 'Conditional Experimental', 'Conditional Chill', 'Chill']:
    client.cycle()
    assert client.pending and not client.enabled
    client.cycle()  # double tap cannot enqueue another write
    finish()
    assert client.label == label and client.enabled
  puts = [body for body in requests if body is not None]
  assert [body['mode'] for body in puts] == list(mode.MODES)[1:] + ['chill']
  assert len(signals) == 4
  assert puts[0]['acknowledged'] is True
  assert params.values['ExperimentalModeConfirmed'] is False
  assert all(key != 'ExperimentalModeConfirmed' for key, _ in params.writes)


def test_native_polling_does_not_flash_button_or_allow_overlapping_writes():
  client, params, requests, _, now, finish = setup_client()
  layout, state = native_layout()
  layout._longitudinal_mode = client
  button = layout._experimental_btn
  assert button.enabled()
  for _ in range(3):
    now[0] += 2
    layout._update_state()
    assert not client.enabled  # Existing in-flight click guard stays intact.
    layout._cycle_longitudinal_mode()
    assert not params.writes
    assert button.enabled(), 'Read-only polling must not dim the speed control title'
    state.params.values['SafeMode'] = True
    assert not button.enabled()
    state.params.values['SafeMode'] = False
    finish()
    assert button.enabled()
  assert all(request is None for request in requests)
  layout._cycle_longitudinal_mode()
  assert client.pending and not button.enabled()
  layout._cycle_longitudinal_mode()
  finish()
  assert button.enabled() and client.label == 'Experimental'
  assert len([request for request in requests if request is not None]) == 1
  client._transport = lambda *args: {}
  now[0] += 2
  layout._update_state()
  finish()
  assert not button.enabled() and client.label == 'Unavailable'


def test_external_refresh_is_read_only_and_stale_click_rejected():
  client, params, requests, _, now, finish = setup_client()
  params.values['ConditionalChill'] = True
  client.cycle()  # stale displayed Chill cannot overwrite an external edit
  finish()
  assert client.label == 'Conditional Chill' and client.error
  assert not params.writes
  params.values['ConditionalExperimental'] = True
  now[0] += 2
  client.update()
  finish()
  assert client.label == 'Conditional Experimental'
  assert not params.writes
  assert len([r for r in requests if r is not None]) == 1


@pytest.mark.parametrize('values', [{'SafeMode': True}, {'IsOnroad': True}, {'IsOffroad': None}])
def test_locked_snapshot_disables_cycle(values):
  client, params, requests, _, _, _ = setup_client(values)
  client.cycle()
  assert not client.enabled and not params.writes
  assert requests == [None]


def test_partial_failure_readback_without_retry_or_rollback():
  client, params, requests, signals, _, finish = setup_client({'ConditionalChill': True})
  params.fail_at = 2
  client.cycle()
  finish()
  assert client.error and not client.pending
  assert client.state['values'] == {key: params.values[key] for key in mode.MODE_KEYS}
  assert len(params.writes) == 2 and len(signals) == 1
  assert len([r for r in requests if r is not None]) == 1


def test_read_failure_disables_and_recovers_without_writes():
  client, params, _, _, now, finish = setup_client()
  original = client._transport
  client._transport = lambda *args: {}
  now[0] += 2
  client.update()
  finish()
  assert client.label == 'Unavailable' and not client.enabled
  client.cycle()
  client._transport = original
  now[0] += 2
  client.update()
  finish()
  assert client.enabled and not params.writes


def test_network_wait_never_blocks_ui_thread():
  entered, release = Event(), Event()
  def transport(body=None):
    entered.set()
    assert release.wait(2)
    return mode.snapshot(Params(), True)
  with ThreadPoolExecutor(max_workers=1) as executor:
    client = LongitudinalModeClient(transport, executor)
    try:
      client.update()
      assert entered.wait(1)
      for _ in range(100):
        client.update()
        client.cycle()
      assert not client.enabled
    finally:
      release.set()


@pytest.mark.parametrize('edit', [{'locked': 'false'}, {'mode': 'unknown'}, {'experimental_confirmed': None},
                                  {'values': {}}, {'mode': 'chill'}])
def test_malformed_or_inconsistent_state_rejected(edit):
  with pytest.raises(ValueError):
    validate_snapshot({**mode.snapshot(Params(), True), **edit})


class Button:
  def __init__(self, *args, **kwargs):
    self.value = None
    self._sub_label = SimpleNamespace(set_font_size=lambda size: None)
  def set_enabled(self, value):
    self.enabled = value
  def set_visible(self, value):
    self.visible = value
  def set_value(self, value):
    self.value = value
  def set_checked(self, value):
    self.checked = value
  def set_click_callback(self, callback):
    self.click = callback


class NativeParams(Params):
  def get(self, key, **kwargs):
    return super().get(key)
  put_int = Params.put_bool
  def remove(self, key):
    self.writes.append((key, None))
    self.values.pop(key, None)


def native_layout(values=None):
  class Scroller:
    def __init__(self):
      self._scroller = SimpleNamespace(add_widgets=lambda widgets: None)
    def _update_state(self):
      pass
    def show_event(self):
      pass
  params = NativeParams({'IsRHDOverride': True, 'DisableOpenpilotLongitudinal': False, **(values or {})})
  state = SimpleNamespace(params=params, CP=SimpleNamespace(openpilotLongitudinalControl=True, alphaLongitudinalAvailable=False),
                          experimental_mode_available=True, has_longitudinal_control=True, engaged=False,
                          sm=SimpleNamespace(updated={'selfdriveState': False}), update_params=lambda: None,
                          add_engaged_transition_callback=lambda cb: None)
  client = SimpleNamespace(label='Conditional Chill', enabled=True, display_enabled=True, update=lambda: None, cycle=lambda: None)
  env = dict(NavScroller=Scroller, LongitudinalModeButton=Button, BigParamControl=Button, BigMultiParamToggle=Button,
             LongitudinalModeClient=lambda: client, ui_state=state, lock_reason=mode.lock_reason,
             restart_needed_callback=lambda: None, log=SimpleNamespace(LongitudinalPersonality=SimpleNamespace(relaxed=2)))
  tree = ast.parse(SOURCE.read_text())
  cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
  exec(compile(ast.Module(body=[cls], type_ignores=[]), str(SOURCE), 'exec'), env)
  return env['TogglesLayoutMici'](), state


def test_native_render_refresh_is_read_only_even_in_safe_mode():
  layout, state = native_layout({'SafeMode': True, 'ExperimentalMode': True})
  for _ in range(10):
    layout._update_state()
  assert not state.params.writes
  assert layout._experimental_btn.value == 'Conditional Chill'
  assert not layout._experimental_btn.enabled()
  # Original show/transition enforcement remains, not moved into rendering.
  layout._update_toggles()
  assert state.params.writes == [('ExperimentalMode', False), ('LongitudinalPersonality', 2)]
  assert layout._personality_toggle.value == 'relaxed'
  assert state.params.values['ConditionalExperimental'] is True


@pytest.mark.parametrize('key,value', [('IsOffroad', False), ('IsOnroad', True), ('SafeMode', True),
                                      ('SafeMode', None), ('DisableOpenpilotLongitudinal', True),
                                      ('DisableOpenpilotLongitudinal', None)])
def test_native_local_guards(key, value):
  layout, state = native_layout({key: value})
  assert not layout._mode_enabled()
  assert not state.params.writes


def test_native_capability_pending_alpha_engagement_and_server_lock():
  layout, state = native_layout()
  assert layout._mode_enabled()
  state.CP.alphaLongitudinalAvailable = True
  assert not layout._mode_enabled()
  state.params.values['AlphaLongitudinalEnabled'] = True
  assert layout._mode_enabled()
  state.engaged = True
  assert layout._mode_enabled()  # Dom allows mode selection while engaged.
  state.engaged = False
  state.CP = None
  assert not layout._mode_enabled()
  state.CP = SimpleNamespace(openpilotLongitudinalControl=False, alphaLongitudinalAvailable=False)
  assert not layout._mode_enabled()
  layout._longitudinal_mode.enabled = False
  assert not layout._mode_enabled()
  assert not state.params.writes


def test_comma4_onroad_engaged_tap_reaches_guarded_client():
  layout, state = native_layout({'IsOnroad': True, 'IsOffroad': False})
  state.engaged = True
  calls = []
  layout._longitudinal_mode.cycle = lambda: calls.append('cycle')
  assert layout._mode_enabled()
  layout._cycle_longitudinal_mode()
  assert calls == ['cycle']
  state.params.values['SafeMode'] = True
  layout._cycle_longitudinal_mode()
  assert calls == ['cycle']
  assert not state.params.writes


def test_native_existing_unavailable_vehicle_cleanup_preserved():
  layout, state = native_layout({'ExperimentalMode': True})
  state.experimental_mode_available = False
  layout._update_toggles()
  assert state.params.writes == [('ExperimentalMode', None)]
  assert layout._experimental_btn.visible is False


def test_native_tile_font_metrics_fit_without_wrapping_or_clipping():
  # Raylib BMFont measurement: sum glyph advances / lineHeight, MICI scale
  # 1.16, zero letter spacing. Use the shipped font metrics, not estimates.
  def width(text, size, weight):
    path = SOURCE.parents[4] / 'assets/fonts' / f'Inter-{weight}.fnt'
    lines = path.read_text().splitlines()
    base = int(re.search(r'lineHeight=(\d+)', lines[1])[1])
    glyphs = {int(d['id']): int(d['xadvance']) for line in lines if line.startswith('char ')
              for d in [dict(re.findall(r'(\w+)=(-?\d+)', line))]}
    return sum(glyphs[ord(c)] for c in text) * size * 1.16 / base
  button_source = SOURCE.parents[2] / 'widgets/longitudinal_mode.py'
  assert 'LongitudinalModeButton()' in SOURCE.read_text()
  assert '_sub_label.set_font_size(20)' in button_source.read_text()
  assert width('speed control', 36, 'Bold') < 402 - 2 * 40 - 84
  for label in [*MODE_LABELS.values(), 'Unavailable']:
    assert width(label, 20, 'Regular') < 402 - 2 * 40 - 84
  assert (36 + 20) * 1.16 < 180 - 2 * 23
  assert 3 * 35 + 66 <= 180  # four native personality-style pills
