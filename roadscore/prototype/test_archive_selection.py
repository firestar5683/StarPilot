import unittest
from score_archive import prefer_new_score
class ArchiveSelectionTest(unittest.TestCase):
 def test_short_regression_does_not_replace_complete_demo(self):
  self.assertFalse(prefer_new_score({'full_route':False,'audio_seconds':60},{'full_route':True,'audio_seconds':572}))
 def test_longer_coverage_wins(self):
  self.assertTrue(prefer_new_score({'full_route':False,'audio_seconds':180},{'full_route':False,'audio_seconds':60}))
 def test_new_complete_score_replaces_previous(self):
  self.assertTrue(prefer_new_score({'full_route':True,'audio_seconds':571.7},{'full_route':True,'audio_seconds':572}))
 def test_eof_from_midroute_is_not_full_coverage(self):
  self.assertFalse(prefer_new_score({'full_route':True,'audio_seconds':300,'replay_start_seconds':120},{'full_route':True,'audio_seconds':572,'replay_start_seconds':0}))
