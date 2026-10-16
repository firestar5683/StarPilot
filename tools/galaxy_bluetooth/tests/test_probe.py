import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('galaxy_probe', Path(__file__).resolve().parents[1] / 'bridge/probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
  def test_exact_live_encoder_format(self):
    with patch.object(probe.shutil, 'which', return_value='/test/ffmpeg'), patch.object(probe.subprocess, 'run') as run:
      run.return_value = subprocess.CompletedProcess([], 0, b'\xff\xd8jpeg\xff\xd9', b'')
      self.assertTrue(probe.live_encoder_check()['available'])
      args = run.call_args.args[0]
      self.assertEqual(args[-3:], ['-f', 'rawvideo', 'pipe:1'])
      self.assertEqual(args[args.index('-c:v') + 1], 'mjpeg')
      self.assertEqual(len(run.call_args.kwargs['input']), 960 * 480 * 4)

  def test_missing_encoder_is_reported(self):
    with patch.object(probe.shutil, 'which', return_value=None):
      self.assertFalse(probe.live_encoder_check()['available'])

  def test_broken_or_incomplete_output_is_reported(self):
    with patch.object(probe.shutil, 'which', return_value='/test/ffmpeg'), patch.object(probe.subprocess, 'run') as run:
      run.return_value = subprocess.CompletedProcess([], 1, b'', b'muxer unavailable')
      self.assertEqual(probe.live_encoder_check()['error'], 'muxer unavailable')
      run.return_value = subprocess.CompletedProcess([], 0, b'\xff\xd8incomplete', b'')
      self.assertFalse(probe.live_encoder_check()['available'])
      run.side_effect = subprocess.TimeoutExpired('ffmpeg', 15)
      self.assertFalse(probe.live_encoder_check()['available'])
