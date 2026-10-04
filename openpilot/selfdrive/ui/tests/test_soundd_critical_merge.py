from types import SimpleNamespace
"""Combined critical escalation/road dismissal; synthetic samples, no audio output."""
from unittest.mock import Mock
from unittest import TestCase
from unittest.mock import patch

import numpy as np

from openpilot.selfdrive.ui.soundd import (ALERT_VOLUME_KEYS, AudibleAlert, CRITICAL_MAX,
                                          Soundd, sound_list)
from openpilot.starpilot.audio.alert_volume import AUTO


WARNINGS = (AudibleAlert.warningSoft, AudibleAlert.warningImmediate)


def soundd(alert, *, builtin=False, saved=AUTO):
  owner = Soundd.__new__(Soundd)
  owner.current_alert = owner.current_sound = alert
  owner.current_sound_frame = 0
  owner.current_volume = owner.ramp_start_volume = .1
  owner.ramp_start_time = 0.
  owner.pending_stop = False
  owner.loaded_sounds = {key: np.array([.2, .4, .2, 0.], dtype=np.float32) for key in sound_list}
  owner.loaded_sounds[CRITICAL_MAX] = np.array([.1, .2, .3, .2, 0., 0.], dtype=np.float32)
  owner.pack_loader = Mock(is_builtin=Mock(return_value=builtin))
  owner.saved_volumes = dict.fromkeys(ALERT_VOLUME_KEYS.values(), saved)
  return owner


class TestCriticalMerge(TestCase):
  def test_both_critical_alerts_ramp_even_with_fixed_volume_and_escalate_once(self):
    for alert in WARNINGS:
      for builtin in (False, True):
        with self.subTest(alert=alert, builtin=builtin):
          owner = soundd(alert, builtin=builtin, saved=25)
          owner.update_critical_sound(2.)
          assert abs(owner.current_volume - .55) < 1e-6
          np.testing.assert_allclose(owner.get_sound_data(1), [.11])
          owner.update_critical_sound(7.999)
          assert owner.current_sound == alert
          owner.update_critical_sound(8.)
          assert owner.current_alert == alert and owner.current_sound == CRITICAL_MAX
          assert owner.current_sound_frame == 0
          np.testing.assert_allclose(owner.get_sound_data(1), [.1])
          owner.update_critical_sound(9.)
          assert owner.current_sound_frame == 1

  def test_builtin_auto_floor_does_not_change_custom_auto_or_fixed_choice(self):
    for builtin, saved, expected in ((True, AUTO, .1), (False, AUTO, .02), (True, 25, .05)):
      with self.subTest(builtin=builtin, saved=saved):
        owner = soundd(AudibleAlert.engage, builtin=builtin, saved=saved)
        np.testing.assert_allclose(owner.get_sound_data(1), [expected])

  def test_escalated_dismissal_uses_active_waveform_boundary(self):
    for alert in WARNINGS:
      for frame in (0, 4, 6, 12):
        with self.subTest(alert=alert, frame=frame):
          owner = soundd(alert)
          owner.current_sound = CRITICAL_MAX
          owner.current_sound_frame = frame
          owner.current_volume = 1.
          owner.update_alert(AudibleAlert.none)
          if frame % 6 == 0:
            assert owner.current_alert == AudibleAlert.none and not owner.pending_stop
            np.testing.assert_array_equal(owner.get_sound_data(8), np.zeros(8))
          else:
            # Frame4 is an ordinary-warning boundary, but is mid-max-waveform.
            assert owner.pending_stop and owner.current_sound_frame == frame
            np.testing.assert_array_equal(owner.get_sound_data(8), np.zeros(8))
            assert owner.current_sound_frame == 6 and owner.current_alert == AudibleAlert.none

  def test_mid_max_dismissal_finishes_tail_then_silence_without_restart(self):
    for alert in WARNINGS:
      with self.subTest(alert=alert):
        owner = soundd(alert)
        owner.current_sound = CRITICAL_MAX
        owner.current_sound_frame = 1
        owner.current_volume = 1.
        owner.update_alert(AudibleAlert.none)
        owner.update_alert(AudibleAlert.none)
        np.testing.assert_allclose(owner.get_sound_data(8), [.2, .3, .2, 0., 0., 0., 0., 0.])
        assert owner.current_sound_frame == 6 and owner.current_alert == AudibleAlert.none

  def test_pending_first_loop_dismissal_cannot_escalate_into_an_extra_loop(self):
    for alert in WARNINGS:
      with self.subTest(alert=alert):
        owner = soundd(alert)
        owner.current_sound_frame = 1
        owner.update_alert(AudibleAlert.none)
        owner.update_critical_sound(8.)
        assert owner.current_sound == alert and owner.current_sound_frame == 1
        np.testing.assert_allclose(owner.get_sound_data(6), [.4, .2, 0., 0., 0., 0.])
        assert owner.current_alert == AudibleAlert.none and owner.current_sound_frame == 4

  def test_reassertion_cancels_stop_then_escalates_and_urgent_replacement_resets(self):
    for alert in WARNINGS:
      with self.subTest(alert=alert):
        owner = soundd(alert)
        owner.current_sound_frame = 1
        owner.update_alert(AudibleAlert.none)
        owner.update_alert(alert)
        assert not owner.pending_stop and owner.current_sound_frame == 1
        owner.update_critical_sound(8.)
        assert owner.current_sound == CRITICAL_MAX and owner.current_sound_frame == 0
        owner.current_sound_frame = 2
        owner.update_alert(AudibleAlert.none)
        other = WARNINGS[1] if alert == WARNINGS[0] else WARNINGS[0]
        with patch("openpilot.selfdrive.ui.soundd.time.monotonic", return_value=20.):
          owner.update_alert(other)
        assert owner.current_alert == owner.current_sound == other
        assert owner.current_sound_frame == 0 and not owner.pending_stop
        assert owner.ramp_start_time == 20.

  def test_timeout_keeps_counters_out_of_audio_callback_logging(self):
    owner = soundd(AudibleAlert.warningImmediate)
    owner.pending_stream_status = None
    owner.stream_status_count = owner.output_underflow_count = 0
    data = np.zeros((1, 1), dtype=np.float32)
    status = SimpleNamespace(output_underflow=True)
    with patch("openpilot.selfdrive.ui.soundd.cloudlog.warning") as warning:
      owner.callback(data, 1, None, status)
      warning.assert_not_called()
    assert owner.pending_stream_status is status
    assert (owner.stream_status_count, owner.output_underflow_count) == (1, 1)
