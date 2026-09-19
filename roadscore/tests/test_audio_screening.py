import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
from scipy.io import wavfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from review_hook_audio import screen, assembly_check, compare_initial


class AudioScreeningTests(unittest.TestCase):
  def test_comparison_uses_matching_prefix_and_preserves_gain(self):
    rate = 48000
    wave = np.column_stack([np.sin(np.arange(rate)*2*np.pi*220/rate)]*2).astype('float32')
    with tempfile.TemporaryDirectory() as folder:
      current, reference = Path(folder)/'current.wav', Path(folder)/'reference.wav'
      wavfile.write(current, rate, wave*.2)
      wavfile.write(reference, rate, np.concatenate([wave*.1, wave]))
      result = compare_initial(current, reference)
      self.assertEqual(result['matched_start_seconds'], 1)
      self.assertAlmostEqual(result['rms_change_db'], 6.0206, places=3)

  def test_expected_crossfade_is_excluded_but_other_changes_are_reported(self):
    parts = [np.zeros((40, 2)), np.ones((40, 2))]
    core = np.concatenate(parts)
    core[20:40] = .3
    self.assertEqual(assembly_check(core, parts, 10)['status'], 'matches outside crossfades')
    core[2] = .1
    self.assertEqual(assembly_check(core, parts, 10)['status'], 'unexpected difference outside crossfades')

  def test_detects_clipping_silence_and_repeated_blocks(self):
    rate = 48000
    block = np.random.default_rng(17).normal(0, .05, (rate, 2)).astype('float32')
    audio = np.concatenate([block, block, np.zeros((rate, 2), 'float32')])
    audio[0, 0] = 1.01
    with tempfile.TemporaryDirectory() as folder:
      path = Path(folder) / 'test.wav'
      wavfile.write(path, rate, audio)
      result = screen(path)
      self.assertEqual(result['samples_at_or_above_full_scale'], 1)
      self.assertAlmostEqual(result['longest_quiet_seconds'], 1)
      self.assertEqual(result['exact_repeated_nonsilent_1s_blocks'], [])
      audio[0] = block[0]
      wavfile.write(path, rate, audio)
      result = screen(path)
      self.assertEqual(result['exact_repeated_nonsilent_1s_blocks'], [[0, 1]])


if __name__ == '__main__':
  unittest.main()
