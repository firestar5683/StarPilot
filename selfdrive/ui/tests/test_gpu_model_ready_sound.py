import ast
from pathlib import Path
from types import SimpleNamespace
import wave

import pytest

from openpilot.starpilot.common.gpu_model_ready_sound import GpuModelReadyChime


def update(chime, now=0, **kwargs):
  return chime.update(**dict(active=False, loading=False, onroad=True, enabled=True, now=now) | kwargs)


def test_ready_once_after_success_not_during_loading_or_failure():
  chime = GpuModelReadyChime()
  assert not update(chime, loading=True)
  assert not update(chime, 1, active=True, loading=True)
  assert update(chime, 2, active=True)
  chime.consume()
  assert not update(chime, 3, active=True)
  assert not update(chime, 4, loading=True)
  assert not update(chime, 5)


def test_restart_with_already_ready_model_does_not_chime():
  assert not update(GpuModelReadyChime(), active=True)


@pytest.mark.parametrize("cancel", [dict(enabled=False), dict(onroad=False), dict(active=False), dict(loading=True)])
def test_cancel_pending_on_disabled_offroad_fallback_or_reload(cancel):
  chime = GpuModelReadyChime()
  update(chime)
  assert update(chime, 1, active=True)
  assert not update(chime, 2, **(dict(active=True) | cancel))


def test_pending_notification_expires_without_late_chime():
  chime = GpuModelReadyChime()
  update(chime)
  assert update(chime, 1, active=True)
  assert not update(chime, 6, active=True)
  assert not update(chime, 7, active=True)


def test_enabling_option_after_load_does_not_replay():
  chime = GpuModelReadyChime()
  update(chime, enabled=False)
  assert not update(chime, 1, active=True, enabled=False)
  assert not update(chime, 2, active=True, enabled=True)


@pytest.mark.parametrize("alert,timeout,valid,alive,expected", [(1,False,True,True,False),(0,True,True,True,False),(0,False,False,True,False),(0,False,True,False,False),(0,False,True,True,True)])
def test_soundd_never_replaces_existing_or_timeout_alerts(alert,timeout,valid,alive,expected):
  source=(Path(__file__).parents[1]/'soundd.py').read_text()
  cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='Soundd')
  method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='update_model_ready_sound')
  scope={'time':SimpleNamespace(monotonic=lambda:1.1),'AudibleAlert':SimpleNamespace(none=0),'GPU_MODEL_READY_ALERT':2000}
  exec(compile(ast.Module(body=[method],type_ignores=[]),'<soundd method>','exec'),scope)
  calls=[]
  sound=SimpleNamespace(model_ready_last_check=1.0,model_ready_pending=True,model_ready_chime=GpuModelReadyChime(),current_alert=alert,selfdrive_timeout_alert=timeout,update_alert=calls.append)
  sm=SimpleNamespace(valid={'selfdriveState':valid},alive={'selfdriveState':alive})
  scope['update_model_ready_sound'](sound,sm)
  assert calls == ([2000] if expected else [])


def test_notification_asset_matches_soundd_audio_format():
  with wave.open(str(Path(__file__).parents[2]/'assets/sounds/model_ready.wav')) as audio:
    assert (audio.getnchannels(),audio.getsampwidth(),audio.getframerate()) == (1,2,48000)
    assert 0 < audio.getnframes() < 48000
