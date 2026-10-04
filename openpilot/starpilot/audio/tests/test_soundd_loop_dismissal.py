"""Dismissal preserves the current loop's tail; urgent alert changes interrupt it."""
from unittest.mock import Mock

import numpy as np
import pytest

from openpilot.selfdrive.ui import soundd


def daemon_for(samples, *, builtin):
  daemon = soundd.Soundd.__new__(soundd.Soundd)
  daemon.current_alert = soundd.AudibleAlert.warningSoft
  daemon.current_sound = daemon.current_alert
  daemon.current_sound_frame = 0
  daemon.current_volume = 1.0
  daemon.pending_stop = False
  daemon.loaded_sounds = {soundd.AudibleAlert.warningSoft: samples,
                          soundd.AudibleAlert.warningImmediate: -samples}
  daemon.pack_loader = Mock(is_builtin=Mock(return_value=builtin))
  daemon.saved_volumes = {"WarningSoftVolume": 100, "WarningImmediateVolume": 100}
  return daemon


@pytest.mark.parametrize("builtin", [False, True], ids=["stock-or-custom", "builtin-starpilot"])
def test_first_loop_dismissal_repeated_updates_finish_exact_tail_once(builtin):
  # Continuous periodic tone with exact zero endpoints. The chosen dismissal is
  # deliberately away from zero, exposing the old step to silence.
  samples = np.sin(np.linspace(0., 8. * np.pi, 8193)).astype(np.float32)
  samples[0] = samples[-1] = 0.
  daemon = daemon_for(samples, builtin=builtin)
  consumed = 401
  np.testing.assert_array_equal(daemon.get_sound_data(consumed), samples[:consumed])
  assert abs(samples[consumed - 1]) > .5
  daemon.update_alert(soundd.AudibleAlert.none)
  daemon.update_alert(soundd.AudibleAlert.none)
  assert daemon.pending_stop and daemon.current_alert == soundd.AudibleAlert.warningSoft
  remaining = len(samples) - consumed
  output = daemon.get_sound_data(remaining + 32)
  np.testing.assert_array_equal(output[:remaining], samples[consumed:])
  np.testing.assert_array_equal(output[remaining:], np.zeros(32, dtype=np.float32))
  assert daemon.current_sound_frame == len(samples)
  assert daemon.current_alert == soundd.AudibleAlert.none and not daemon.pending_stop
  assert not np.any(daemon.get_sound_data(len(samples)))


@pytest.mark.parametrize("builtin", [False, True], ids=["stock-or-custom", "builtin-starpilot"])
def test_urgent_replacement_interrupts_pending_tail_immediately(builtin):
  samples = np.linspace(0., 1., 8193, dtype=np.float32)
  daemon = daemon_for(samples, builtin=builtin)
  daemon.get_sound_data(400)
  daemon.update_alert(soundd.AudibleAlert.none)
  assert daemon.pending_stop
  daemon.update_alert(soundd.AudibleAlert.warningImmediate)
  assert not daemon.pending_stop and daemon.current_sound_frame == 0
  assert daemon.current_alert == soundd.AudibleAlert.warningImmediate
  np.testing.assert_array_equal(daemon.get_sound_data(128), -samples[:128])


@pytest.mark.parametrize("builtin", [False, True], ids=["stock-or-custom", "builtin-starpilot"])
@pytest.mark.parametrize("loops", [0, 1, 2])
def test_dismissal_at_completed_boundary_does_not_start_an_extra_loop(builtin, loops):
  samples = np.linspace(0., 1., 1024, dtype=np.float32)
  daemon = daemon_for(samples, builtin=builtin)
  daemon.get_sound_data(len(samples) * loops)
  assert daemon.current_sound_frame == len(samples) * loops
  daemon.update_alert(soundd.AudibleAlert.none)
  assert daemon.current_alert == soundd.AudibleAlert.none and not daemon.pending_stop
  assert not np.any(daemon.get_sound_data(len(samples)))
  assert daemon.current_sound_frame == len(samples) * loops


@pytest.mark.parametrize("builtin", [False, True], ids=["stock-or-custom", "builtin-starpilot"])
def test_same_alert_reassertion_cancels_pending_stop_without_restarting(builtin):
  samples = np.sin(np.linspace(0., 8. * np.pi, 8193)).astype(np.float32)
  daemon = daemon_for(samples, builtin=builtin)
  consumed = 401
  daemon.get_sound_data(consumed)
  daemon.update_alert(soundd.AudibleAlert.none)
  assert daemon.pending_stop
  daemon.update_alert(soundd.AudibleAlert.warningSoft)
  assert not daemon.pending_stop and daemon.current_sound_frame == consumed
  remaining = len(samples) - consumed
  output = daemon.get_sound_data(remaining + 128)
  np.testing.assert_array_equal(output[:remaining], samples[consumed:])
  np.testing.assert_array_equal(output[remaining:], samples[:128])
  assert daemon.current_alert == soundd.AudibleAlert.warningSoft
