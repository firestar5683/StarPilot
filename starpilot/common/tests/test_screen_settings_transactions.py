"""Exercise screen writes across the real Galaxy/cache wrappers and processes."""
import ast
import multiprocessing
from pathlib import Path

import pytest

from openpilot.selfdrive.ui.lib.ui_param_cache import UIParamCache
from openpilot.starpilot.common.screen_settings import brightness_preferences, set_brightness_mode, write_screen_setting

from test_screen_settings import Params


def galaxy_params(params):
  source = Path(__file__).resolve().parents[3] / 'starpilot/system/the_galaxy/the_galaxy.py'
  node = next(node for node in ast.parse(source.read_text()).body
              if isinstance(node, ast.ClassDef) and node.name == 'ParamsCompat')
  namespace = {}
  exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
  return namespace['ParamsCompat'](params)


class SilentOnceParams(Params):
  def __init__(self, values):
    super().__init__(values)
    self.fail_once = True

  def put_bool(self, key, value):
    if self.fail_once:
      self.fail_once = False
      return  # Native Params does not propagate C++ putBool's error return.
    super().put_bool(key, value)


def test_galaxy_failed_wake_write_preserves_enabled_selection():
  params = SilentOnceParams({'StandbyWakeCriticalAlert': True})
  with pytest.raises(OSError):
    write_screen_setting(galaxy_params(params), 'StandbyWakeCriticalAlert', False)
  assert params.values == {'StandbyWakeCriticalAlert': True}


def test_cached_native_mode_change_preserves_a_newer_galaxy_manual_value():
  params = Params({'ScreenBrightness': 25, 'ScreenBrightnessManual': 25})
  cache = UIParamCache(params, ttl=60)
  assert brightness_preferences(cache, 'ScreenBrightness')['manual'] == 25
  write_screen_setting(galaxy_params(params), 'ScreenBrightness', 70)
  set_brightness_mode(cache, 'ScreenBrightness', 'auto')
  assert params.values == {'ScreenBrightness': 101, 'ScreenBrightnessManual': 70}
  set_brightness_mode(cache, 'ScreenBrightness', 'manual')
  assert brightness_preferences(cache, 'ScreenBrightness')['manual'] == 70


class SharedParams:
  """Manager-backed typed values and a shared path; no device Params are opened."""
  def __init__(self, values, directory, operation=None, paused=None, release=None):
    self.values, self.directory = values, directory
    self.operation, self.paused, self.release = operation, paused, release
    self.did_pause = False
    self.did_fail = False

  def get_param_path(self):
    return self.directory

  def pause(self):
    self.did_pause = True
    self.paused.set()
    assert self.release.wait(5), 'Parent did not release the test transaction'

  def get(self, key, **kwargs):
    value = self.values.get(key)
    if self.operation == 'snapshot' and key == 'ScreenBrightness' and not self.did_pause:
      self.pause()
    return value

  def put_int(self, key, value):
    if self.operation == 'rollback' and key == 'ScreenBrightness':
      if not self.did_fail:
        self.did_fail = True
        return
      if not self.did_pause:
        self.pause()
    self.values[key] = value

  def remove(self, key):
    self.values.pop(key, None)


def write_in_other_process(values, directory, operation, paused, release, outcomes):
  params = galaxy_params(SharedParams(values, directory, operation, paused, release))
  try:
    if operation == 'snapshot':
      set_brightness_mode(params, 'ScreenBrightness', 'auto')
    else:
      write_screen_setting(params, 'ScreenBrightness', 60)
  except OSError:
    outcomes.put('failed')
  else:
    outcomes.put('saved')


@pytest.mark.parametrize('operation', ['snapshot', 'rollback'])
def test_other_process_cannot_write_during_snapshot_or_rollback(tmp_path, operation):
  context = multiprocessing.get_context('spawn')
  with context.Manager() as manager:
    values = manager.dict(ScreenBrightness=25, ScreenBrightnessManual=25)
    directory = str(tmp_path / 'd')
    paused, release, outcomes = context.Event(), context.Event(), context.Queue()
    writer = context.Process(target=write_in_other_process, args=(values, directory, operation, paused, release, outcomes))
    writer.start()
    try:
      assert paused.wait(5), 'Other process did not reach the intended transaction step'
      native = UIParamCache(SharedParams(values, directory))
      # The competing UI must report busy before changing either parameter.
      with pytest.raises(BlockingIOError):
        write_screen_setting(native, 'ScreenBrightness', 70)
    finally:
      release.set()
      writer.join(5)
      if writer.is_alive():
        writer.terminate()
        writer.join(5)
    assert writer.exitcode == 0
    assert outcomes.get(timeout=5) == ('saved' if operation == 'snapshot' else 'failed')
    assert dict(values) == {'ScreenBrightness': 101 if operation == 'snapshot' else 25, 'ScreenBrightnessManual': 25}
    # A later retry succeeds and its remembered value survives mode switches.
    write_screen_setting(native, 'ScreenBrightness', 70)
    set_brightness_mode(native, 'ScreenBrightness', 'auto')
    set_brightness_mode(native, 'ScreenBrightness', 'manual')
    assert dict(values) == {'ScreenBrightness': 70, 'ScreenBrightnessManual': 70}
    outcomes.close()
    outcomes.join_thread()


def test_lock_creation_failure_leaves_values_unchanged(tmp_path):
  values = {'ScreenBrightness': 25, 'ScreenBrightnessManual': 25}
  params = SharedParams(values, str(tmp_path / 'unavailable' / 'd'))
  with pytest.raises(OSError):
    write_screen_setting(params, 'ScreenBrightness', 101)
  assert values == {'ScreenBrightness': 25, 'ScreenBrightnessManual': 25}
