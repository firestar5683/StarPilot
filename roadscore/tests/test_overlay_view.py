"""Presentation contracts only; these tests never import the runtime or device tools."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'prototype'))
from overlay_view import display_text, fit_text, overlay_view, hud_bounds, startup_bounds, EventPresentation


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

  def test_legacy_signal_does_not_claim_audible_cue(self):
    view = overlay_view(dict(readiness='READY', job_inflight=True, generation_elapsed_seconds=123.4,
                             turn_signal_music=True))
    self.assertEqual(view['event'], '')
    self.assertIn('123.4s', view['note'])

  def test_active_cue_precedes_queued_and_persistent_signal(self):
    view = overlay_view(dict(turn_signal_music=True, gesture_active=['turn_signal_sustain', 'curve_apex'],
                             gesture_queued=[{'kind': 'arrival'}]))
    self.assertEqual(view['event'], 'Curve apex / impact')
    self.assertEqual(view['event_state'], 'active')

  def test_queued_cue_is_hidden(self):
    view = overlay_view(dict(turn_signal_music=True, gesture_queued=[{'kind': 'turn_signal'}]))
    self.assertEqual(view['event'], '')
    self.assertEqual(view['event_state'], '')

  def test_signal_sequence_and_grid_are_not_proof_of_played_audio(self):
    for rhythm_enabled in (False, True):
      view = overlay_view({'readiness': 'READY', 'signal_shaker': {
        'enabled': True, 'sequence_active': True, 'rhythm_enabled': rhythm_enabled}})
      self.assertEqual(view['event'], '')

  def test_unknown_and_malformed_cues_do_not_invent_a_road_reason(self):
    self.assertEqual(overlay_view({'gesture_active': ['unknown_future_kind']})['event'], 'Music cue')
    self.assertEqual(overlay_view({'gesture_active': 'curve_apex', 'gesture_queued': [None, {}, 3]})['event'], '')
    self.assertEqual(overlay_view({'lead': 4})['event'], '')
    self.assertEqual(overlay_view(dict(kind='navigation', phase='anticipation', lead=4))['event'], '')
    self.assertEqual(overlay_view(dict(kind='curve', phase='anticipation', lead=4))['event'], '')

  def test_startup_badge_clears_home_text_and_visible_footer_icons(self):
    self.assertEqual(startup_bounds(536, 240), (294, 172, 230, 60))
    self.assertEqual(startup_bounds(536, 240, 256), (294, 172, 230, 60))
    self.assertIsNone(startup_bounds(536, 240, 306))
    self.assertIsNone(startup_bounds(320, 240))
    self.assertEqual(hud_bounds(536, 240), (16, 88, 286, 60))

  def test_native_slot_clears_speed_sign_driver_and_steering(self):
    x, y, width, height = hud_bounds(536, 240)
    # Measured native screenshot + native widget dimensions, with safety margins.
    occupied = [(8, 4, 72, 72), (160, 0, 158, 76), (328, 16, 120, 144),
                (0, 160, 80, 80), (472, 0, 64, 240)]
    for ox, oy, ow, oh in occupied:
      self.assertTrue(x + width <= ox or ox + ow <= x or y + height <= oy or oy + oh <= y)
    self.assertLessEqual(x + width, 472)
    self.assertLessEqual(y + height, 240)
    self.assertIsNone(hud_bounds(320, 240))

  def test_recent_linger_is_explicit_and_new_active_cue_is_immediate(self):
    presenter = EventPresentation()
    active = overlay_view(dict(gesture_active=['turn_signal'], readiness='READY'))
    self.assertEqual(presenter.update(active, 0)['event_state'], 'active')
    recent = presenter.update(overlay_view({'readiness': 'READY'}), .2)
    self.assertEqual(recent['event'], 'Recent: Turn signal')
    self.assertEqual(recent['event_state'], 'recent')
    apex = presenter.update(overlay_view(dict(gesture_active=['curve_apex'], readiness='READY')), .3)
    self.assertEqual(apex['event'], 'Curve apex / impact')
    self.assertEqual(presenter.update(overlay_view({'readiness': 'READY'}), 3)['event'], '')

  def test_hidden_queue_and_degraded_never_wait(self):
    presenter = EventPresentation()
    queued = overlay_view(dict(gesture_queued=[{'kind': 'curve_apex'}], readiness='READY'))
    self.assertEqual(presenter.update(queued, 0)['event'], '')
    self.assertEqual(presenter.update(queued, .5)['event'], '')
    degraded = presenter.update(overlay_view(dict(readiness='DEGRADED', holding_accepted_music=True)), .6)
    self.assertEqual(degraded['activity'], 'DEGRADED')
    self.assertEqual(degraded['note'], 'Holding accepted music')

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
