import os,unittest
from unittest.mock import patch
from settings import Settings
from audio_policy import allow_output
class SettingsTest(unittest.TestCase):
 def test_product_default(self):
  with patch('settings.session_muted',return_value=False):
   self.assertFalse(Settings().effective_muted())
   self.assertTrue(Settings().effective_muted(headless=True))
   self.assertTrue(Settings(muted=True).effective_muted())
 def test_session_lock_wins(self):
  with patch('settings.session_muted',return_value=True):self.assertTrue(Settings().effective_muted())
  with patch('audio_policy.session_muted',return_value=True):self.assertFalse(allow_output(True))
