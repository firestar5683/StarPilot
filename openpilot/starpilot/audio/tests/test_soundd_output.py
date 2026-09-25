"""Actual soundd load, alert service, stream configuration and audio callback."""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

import numpy as np
import pytest

from openpilot.common.params import Params
from openpilot.selfdrive.ui import soundd
from openpilot.starpilot.audio.sound_pack import DEFAULT_PACK, SoundPackLoader, read_wav


@pytest.mark.parametrize("raw", [None, b"", b"default", b"Frog", b"frogpilot", b"missing", b"\xff"])
def test_default_repair_persists_and_flows_through_actual_stream(tmp_path, raw):
  params = Params(str(tmp_path / "params"))
  if raw is not None:
    Path(params.get_param_path("SoundPack")).write_bytes(raw)
  daemon = soundd.Soundd(params, pack_root=tmp_path / "packs")
  assert params.get("SoundPack") == DEFAULT_PACK
  root = Path(soundd.__file__).resolve().parents[1] / "assets/sounds_starpilot"
  class Stream:
    def __init__(self, **kw):
      self.kw = kw
  device = NS(_terminate=lambda: None, _initialize=lambda: None, OutputStream=Stream)
  stream = daemon.get_stream(device)
  assert stream.kw["samplerate"] == 48000 and stream.kw["channels"] == 1
  assert stream.kw["blocksize"] == 4096
  for alert in (soundd.AudibleAlert.engage, soundd.AudibleAlert.disengage,
                soundd.AudibleAlert.prompt, soundd.AudibleAlert.warningSoft, soundd.AudibleAlert.warningImmediate):
    daemon.current_alert = soundd.AudibleAlert.none
    class State:
      updated = {"selfdriveState": True}
      logMonoTime = {}
      valid = {"selfdriveState": True}
      alive = {"selfdriveState": True}
      def __init__(self, sound):
        self.sound = sound
      def __getitem__(self, service):
        return NS(alertSound=NS(raw=self.sound))
    daemon.get_audible_alert(State(alert))
    daemon.current_volume = .5
    output = np.zeros((4096, 1), np.float32)
    with patch("pathlib.Path.open", side_effect=AssertionError("callback file IO")):
      stream.kw["callback"](output, 4096, None, None)
    assert np.isfinite(output).all() and np.max(np.abs(output)) <= .5 and np.any(output != 0)
    logical = soundd.sound_list[alert][0]
    from openpilot.starpilot.audio.sound_pack import BUILTIN_FILES
    expected = read_wav(root / BUILTIN_FILES[logical])
    np.testing.assert_array_equal(output[:, 0], expected[:4096] * .5)


def test_warning_urgency_levels_and_loop_finish(tmp_path):
  daemon = soundd.Soundd(Params(str(tmp_path / "params")), pack_root=tmp_path / "packs")
  alerts = (soundd.AudibleAlert.promptRepeat, soundd.AudibleAlert.warningSoft, soundd.AudibleAlert.warningImmediate)
  rms, peak = [], []
  for alert in alerts:
    samples = daemon.loaded_sounds[alert]
    rms.append(float(np.sqrt(np.mean(samples ** 2))))
    peak.append(float(np.max(np.abs(samples))))
    assert np.isfinite(samples).all() and 0 < peak[-1] < 1
    assert samples[0] == 0 and samples[-1] == 0
    daemon.current_alert, daemon.current_sound_frame, daemon.current_volume = alert, 0, 1.
    output = np.zeros((len(samples) * 2 + 4096, 1), np.float32)
    daemon.callback(output, len(output), None, None)
    np.testing.assert_array_equal(output[:len(samples), 0], samples)
    np.testing.assert_array_equal(output[len(samples):2*len(samples), 0], samples)
    daemon.update_alert(soundd.AudibleAlert.none)
    tail = np.zeros((len(samples), 1), np.float32)
    daemon.callback(tail, len(tail), None, None)
    assert daemon.current_alert == soundd.AudibleAlert.none
    output.fill(1)
    daemon.callback(output, len(output), None, None)
    assert not np.any(output)
  assert rms[0] < rms[1] < rms[2] and peak[0] < peak[1] < peak[2]


def test_builtin_loading_does_not_require_stock_and_damaged_clip_uses_stock(tmp_path):
  from openpilot.starpilot.audio.sound_pack import BUILTIN_FILES
  params = Params(str(tmp_path / "params"))
  params.put("SoundPack", DEFAULT_PACK, block=True)
  actual = Path(soundd.__file__).resolve().parents[1] / "assets"
  stock = tmp_path / "assets/sounds"
  builtin = stock.parent / "sounds_starpilot"
  builtin.mkdir(parents=True)
  for name in set(BUILTIN_FILES.values()):
    (builtin / name).write_bytes((actual / "sounds_starpilot" / name).read_bytes())
  loader = SoundPackLoader(params, stock, tmp_path / "packs")
  loaded = loader.refresh(("engage.wav", "warning.wav"), 0)
  assert np.any(loaded["engage.wav"])
  stock.mkdir()
  (stock / "engage.wav").write_bytes((actual / "sounds/engage.wav").read_bytes())
  (builtin / "engage.wav").write_text("version https://git-lfs.github.com/spec/v1\n")
  restored = loader.refresh(("engage.wav", "warning.wav"), 1)
  np.testing.assert_array_equal(restored["engage.wav"], read_wav(stock / "engage.wav"))
  np.testing.assert_array_equal(restored["warning.wav"], loaded["warning.wav"])


@pytest.mark.parametrize("name", ["stock", "custom"])
def test_valid_explicit_pack_survives_restart(tmp_path, name):
  params = Params(str(tmp_path / "params"))
  packs = tmp_path / "packs"
  custom = packs / "custom/sounds"
  custom.mkdir(parents=True)
  params.put("SoundPack", name, block=True)
  soundd.Soundd(params, pack_root=packs)
  soundd.Soundd(params, pack_root=packs)
  assert params.get("SoundPack") == name
