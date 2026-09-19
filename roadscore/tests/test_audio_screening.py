import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
from scipy.io import wavfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from review_hook_audio import screen


class AudioScreeningTests(unittest.TestCase):
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
