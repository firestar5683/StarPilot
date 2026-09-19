"""Presentation contracts only; these tests never import the runtime or device tools."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'prototype'))
from overlay_view import display_text, fit_text, overlay_view


class OverlayTests(unittest.TestCase):
  def test_degradation_takes_priority_over_generation(self):
    for reason in ('worker_failed', 'holding_accepted_music', 'quality_failures'):
      with self.subTest(reason=reason):
        view = overlay_view(dict(readiness='READY', job_inflight=True, **{reason: True}))
        self.assertEqual(view['activity'], 'DEGRADED')
        self.assertFalse(view['ready'])
    self.assertEqual(overlay_view(dict(readiness='DEGRADED', job_inflight=True))['activity'], 'DEGRADED')

  def test_active_generation_preserves_playback_readiness(self):
    view = overlay_view(dict(readiness='READY', job_inflight=True, generation_elapsed_seconds=12.3))
    self.assertEqual(view['activity'], 'GENERATING')
    self.assertTrue(view['ready'])
    self.assertIn('12.3s', view['note'])

  def test_gesture_remains_separate_from_generation_timing(self):
    view = overlay_view(dict(readiness='READY', job_inflight=True, generation_elapsed_seconds=123.4,
                             turn_signal_music=True))
    self.assertEqual(view['event'], 'Signal percussion')
    self.assertIn('123.4s', view['note'])

  def test_missing_buffer_is_not_zero(self):
    for value in (None, float('nan'), float('inf'), '12', True):
      self.assertIsNone(overlay_view({'buffered': value})['buffered'])
    self.assertEqual(overlay_view({'buffered': -1})['buffered'], 0)
    self.assertEqual(overlay_view({})['activity'], 'PREPARING')

  def test_stored_score_never_claims_chestnut_compute(self):
    view = overlay_view(dict(composer='ace', compute='none', readiness='READY'))
    self.assertEqual(view['backend'], ('STORED SCORE', 'NO COMPUTE'))

  def test_profile_and_section_intent(self):
    view = overlay_view(dict(profile='prism', composer='ace', section='VERSE / CONTINUOUS',
                             next_section='PRECHORUS', form_labels_are_intent=True))
    self.assertEqual(view['profile'], 'Prism')
    self.assertEqual(view['section'], 'INTENT: VERSE > PRECHORUS')
    self.assertEqual(view['backend'], ('ACE', 'CHESTNUT'))

  def test_native_labels_and_truncation_use_supported_characters(self):
    self.assertEqual(display_text('Prism · VERSE → CHORUS — café'), 'Prism / VERSE > CHORUS - cafe')
    result = fit_text('A long section label', 10, len)
    self.assertLessEqual(len(result), 10)
    self.assertTrue(result.endswith('...'))
    self.assertEqual(fit_text('long', 2, len), '')


if __name__ == '__main__':
  unittest.main()
