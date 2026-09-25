from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

import numpy as np

from openpilot.common.basedir import BASEDIR
from openpilot.common.params import Params
from openpilot.selfdrive.ui.soundd import AudibleAlert, Soundd, sound_list
from openpilot.starpilot.audio.sound_pack import MAX_WAV_BYTES, SoundPackLoader, installed_packs, read_wav
from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest
from openpilot.starpilot.ui.sounds_owner import SoundsOwner


def write_wav(path, samples=(100, -200, 300), channels=1, rate=48000):
  path.parent.mkdir(parents=True, exist_ok=True)
  with wave.open(str(path), "wb") as target:
    target.setnchannels(channels)
    target.setsampwidth(2)
    target.setframerate(rate)
    target.writeframes(np.array(samples, dtype=np.int16).tobytes())


class SoundPackTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.base = Path(temporary.name)
    self.params = Params(str(self.base / "params"))
    self.params.put("SoundPack", "stock", block=True)
    self.root = self.base / "packs"
    self.stock = Path(BASEDIR) / "openpilot/selfdrive/assets/sounds"
    self.pack = self.root / "custom" / "sounds"
    self.pack.mkdir(parents=True)
    self.loader = SoundPackLoader(self.params, self.stock, self.root)

  def test_stock_samples_are_exact_and_cached(self):
    filenames = tuple({spec[0] for spec in sound_list.values()})
    loaded = self.loader.refresh(filenames, 0)
    for filename in filenames:
      with wave.open(str(self.stock / filename), "rb") as source:
        expected = np.frombuffer(source.readframes(source.getnframes()), dtype=np.int16).astype(np.float32) / (2**16/2)
      np.testing.assert_array_equal(loaded[filename], expected)
      self.assertFalse(loaded[filename].flags.writeable)
    with patch("openpilot.starpilot.audio.sound_pack.read_wav", side_effect=AssertionError("reload")):
      self.assertIsNone(self.loader.refresh(filenames, 0.2))
      self.assertIsNone(self.loader.refresh(filenames, 1))

  def test_logical_alias_and_individual_fallback(self):
    write_wav(self.pack / "prompt.wav")
    self.params.put("SoundPack", "custom", block=True)
    loaded = self.loader.refresh(("warning.wav", "critical.wav"), 0)
    np.testing.assert_array_equal(loaded["warning.wav"], np.array((100, -200, 300), dtype=np.float32) / 32768)
    np.testing.assert_array_equal(loaded["critical.wav"], read_wav(self.stock / "critical.wav"))
    write_wav(self.pack / "prompt.wav", (500,))
    self.assertIsNone(self.loader.refresh(("warning.wav", "critical.wav"), 0.5))
    self.assertEqual(len(self.loader.refresh(("warning.wav", "critical.wav"), 1)["warning.wav"]), 1)

  def test_invalid_custom_files_fall_back(self):
    path = self.pack / "engage.wav"
    self.params.put("SoundPack", "custom", block=True)
    for kind in ("empty", "stereo", "rate", "truncated", "garbage", "oversize", "symlink"):
      with self.subTest(kind=kind):
        path.unlink(missing_ok=True)
        if kind == "garbage":
          path.write_bytes(b"invalid")
        elif kind == "oversize":
          with path.open("wb") as target:
            target.truncate(MAX_WAV_BYTES + 1)
        elif kind == "symlink":
          path.symlink_to(self.stock / "engage.wav")
        else:
          write_wav(path, () if kind == "empty" else (100, 200), channels=2 if kind == "stereo" else 1,
                    rate=24000 if kind == "rate" else 48000)
          if kind == "truncated":
            path.write_bytes(path.read_bytes()[:-2])
        loader = SoundPackLoader(self.params, self.stock, self.root)
        np.testing.assert_array_equal(loader.refresh(("engage.wav",), 0)["engage.wav"], read_wav(self.stock / "engage.wav"))

  def test_missing_traversal_and_symlink_pack_fall_back(self):
    (self.root / "linked").symlink_to(self.root / "custom", target_is_directory=True)
    self.assertEqual(installed_packs(self.root), ("starpilot", "stock", "custom"))
    for name in ("missing", "../custom", "linked"):
      self.params.put("SoundPack", name, block=True)
      loader = SoundPackLoader(self.params, self.stock, self.root)
      fallback = self.stock.parent / "sounds_starpilot" if name == "../custom" else self.stock
      np.testing.assert_array_equal(loader.refresh(("engage.wav",), 0)["engage.wav"], read_wav(fallback / "engage.wav"))

  def test_owner_parked_saved_source_and_unavailable_repair(self):
    parked = [True]
    owner = SoundsOwner(self.params, lambda: parked[0], self.root)
    row = owner.snapshot().rows[-1]
    self.assertEqual(row.choices, ("StarPilot (Built-in)", "Stock (openpilot)", "custom"))
    request = FeatureSettingsRequest("SoundPack", row.source, "custom")
    self.assertTrue(owner.apply(request))
    self.assertFalse(owner.apply(request))
    parked[0] = False
    self.assertFalse(owner.apply(FeatureSettingsRequest("SoundPack", b"custom", "stock")))
    parked[0] = True
    self.params.put("SoundPack", "missing", block=True)
    self.assertEqual(owner.snapshot().rows[-1].repair_value, "starpilot")
    self.assertTrue(owner.apply(FeatureSettingsRequest("SoundPack", b"missing", "stock")))

  def test_callback_does_not_read_files_or_params_and_keeps_chimes(self):
    sound = Soundd(self.params, pack_root=self.root)
    sound.current_alert = AudibleAlert.engage
    output = np.zeros((32, 1), dtype=np.float32)
    with patch("pathlib.Path.open", side_effect=AssertionError("callback IO")), \
         patch.object(sound.pack_loader, "refresh", side_effect=AssertionError("callback refresh")):
      sound.callback(output, 32, None, None)
    self.assertTrue(np.any(output))
    self.assertIsNotNone(sound.axis_alerts)

  def test_service_swap_preserves_gain_and_callback_snapshot(self):
    write_wav(self.pack / "engage.wav", (1000, -1000))
    self.params.put("SoundPack", "custom", block=True)
    sound = Soundd(self.params, pack_root=self.root)
    sound.pack_loader = self.loader
    sound.load_sounds()
    sound.current_alert = AudibleAlert.engage
    sound.current_volume = 0.25
    sound.saved_volumes["EngageVolume"] = 50
    np.testing.assert_array_equal(sound.get_sound_data(2), np.array((1000, -1000), dtype=np.float32) / 65536)
    previous = sound.loaded_sounds
    self.params.put("SoundPack", "stock", block=True)
    self.loader.checked_at -= 2
    sound.load_sounds()
    self.assertIsNot(previous, sound.loaded_sounds)
    np.testing.assert_array_equal(previous[AudibleAlert.engage], np.array((1000, -1000), dtype=np.float32) / 32768)

  def test_corrupt_selection_can_be_repaired_without_read_mutation(self):
    path = Path(self.params.get_param_path("SoundPack"))
    path.write_bytes(b"\xff")
    owner = SoundsOwner(self.params, lambda: True, self.root)
    row = owner.snapshot().rows[-1]
    self.assertEqual(row.source, b"\xff")
    self.assertEqual(row.repair_value, "starpilot")
    self.assertEqual(path.read_bytes(), b"\xff")
    self.assertTrue(owner.apply(FeatureSettingsRequest("SoundPack", b"\xff", "stock")))

  def test_current_names_and_legacy_precedence(self):
    self.params.put("SoundPack", "custom", block=True)
    for current, legacy in (("warning.wav", "prompt.wav"), ("dm_warning.wav", "prompt_distracted.wav"),
                            ("critical.wav", "warning_soft.wav"), ("dm_critical.wav", "warning_immediate.wav")):
      with self.subTest(current=current):
        write_wav(self.pack / current, (700,))
        loader = SoundPackLoader(self.params, self.stock, self.root)
        self.assertEqual(loader.refresh((current,), 0)[current][0], 700 / 32768)
        write_wav(self.pack / legacy, (900,))
        self.assertEqual(loader.refresh((current,), 1)[current][0], 900 / 32768)

  def test_service_cache_gate_performs_no_filesystem_reads(self):
    self.loader.refresh(("engage.wav",), 0)
    with patch("pathlib.Path.open", side_effect=AssertionError("cached Params read")), \
         patch("pathlib.Path.lstat", side_effect=AssertionError("cached stat")), \
         patch("pathlib.Path.is_dir", side_effect=AssertionError("cached directory")):
      for frame in range(1, 20):
        self.assertIsNone(self.loader.refresh(("engage.wav",), frame / 20))
