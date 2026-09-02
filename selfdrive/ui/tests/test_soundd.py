from cereal import custom, log
from cereal import messaging
from cereal.messaging import SubMaster, PubMaster
from openpilot.selfdrive.ui.soundd import (
  SELFDRIVE_STATE_TIMEOUT,
  SOUNDD_SERVICES,
  Soundd,
  check_selfdrive_timeout_alert,
  is_turn_steering_limit_alert,
  should_mute_turn_steering_limit_alert,
  starpilot_alert_key,
)

import numpy as np
import time
import wave

AudibleAlert = log.SelfdriveState.AudibleAlert
StarPilotAudibleAlert = custom.StarPilotCarControl.HUDControl.AudibleAlert


class TestSoundd:
  def test_does_not_consume_car_state_reader(self):
    assert "carState" not in SOUNDD_SERVICES
    assert "starpilotSelfdriveState" in SOUNDD_SERVICES

  def test_turn_steering_limit_alert_detection(self):
    assert is_turn_steering_limit_alert("steerSaturated/warning")
    assert is_turn_steering_limit_alert("goatSteerSaturated/warning")
    assert is_turn_steering_limit_alert("thisIsFineSteerSaturated/warning")
    assert not is_turn_steering_limit_alert("laneChangeBlocked/warning")

  def test_turn_steering_limit_alert_is_muted_only_below_threshold(self):
    assert should_mute_turn_steering_limit_alert("steerSaturated/warning", 10.0, 25.0)
    assert not should_mute_turn_steering_limit_alert("steerSaturated/warning", 25.0, 25.0)
    assert not should_mute_turn_steering_limit_alert("steerSaturated/warning", 30.0, 25.0)
    assert not should_mute_turn_steering_limit_alert("steerSaturated/warning", 10.0, 0.0)
    assert not should_mute_turn_steering_limit_alert("laneChangeBlocked/warning", 10.0, 25.0)

  def test_load_sounds_skips_missing_custom_clips(self, tmp_path):
    soundd = Soundd.__new__(Soundd)
    soundd.sound_directory = tmp_path / "sounds"
    soundd.sound_directory.mkdir()
    soundd.random_events_directory = tmp_path / "random_events"
    soundd.random_events_directory.mkdir()

    soundd.load_sounds()

    assert AudibleAlert.engage in soundd.loaded_sounds
    assert AudibleAlert.warningImmediate in soundd.loaded_sounds
    assert starpilot_alert_key(StarPilotAudibleAlert.angry) not in soundd.loaded_sounds
    soundd.current_alert = starpilot_alert_key(StarPilotAudibleAlert.angry)
    soundd.current_volume = 1.0
    soundd.current_sound_frame = 0
    np.testing.assert_array_equal(soundd.get_sound_data(4), np.zeros(4, dtype=np.float32))

  def test_load_sounds_falls_back_to_stock_when_custom_is_invalid(self, tmp_path):
    soundd = Soundd.__new__(Soundd)
    soundd.sound_directory = tmp_path / "sounds"
    soundd.sound_directory.mkdir()
    soundd.random_events_directory = tmp_path / "random_events"
    soundd.random_events_directory.mkdir()

    invalid = soundd.sound_directory / "warning_immediate.wav"
    with wave.open(str(invalid), "w") as wav:
      wav.setnchannels(2)
      wav.setsampwidth(2)
      wav.setframerate(44100)
      wav.writeframes(b"\x00\x00" * 64)

    soundd.load_sounds()

    assert AudibleAlert.warningImmediate in soundd.loaded_sounds
    assert soundd.loaded_sounds[AudibleAlert.warningImmediate].size > 0

  def test_load_sounds_skips_empty_wav(self, tmp_path):
    soundd = Soundd.__new__(Soundd)
    soundd.sound_directory = tmp_path / "sounds"
    soundd.sound_directory.mkdir()
    soundd.random_events_directory = tmp_path / "random_events"
    soundd.random_events_directory.mkdir()

    empty = soundd.sound_directory / "engage.wav"
    with wave.open(str(empty), "w") as wav:
      wav.setnchannels(1)
      wav.setsampwidth(2)
      wav.setframerate(48000)
      wav.writeframes(b"")

    soundd.load_sounds()

    assert AudibleAlert.engage in soundd.loaded_sounds
    assert soundd.loaded_sounds[AudibleAlert.engage].size > 0

  def test_load_sounds_falls_back_when_custom_wav_is_truncated(self, tmp_path):
    soundd = Soundd.__new__(Soundd)
    soundd.sound_directory = tmp_path / "sounds"
    soundd.sound_directory.mkdir()
    soundd.random_events_directory = tmp_path / "random_events"
    soundd.random_events_directory.mkdir()

    (soundd.sound_directory / "warning_immediate.wav").write_bytes(b"RIFF")

    soundd.load_sounds()

    assert AudibleAlert.warningImmediate in soundd.loaded_sounds
    assert soundd.loaded_sounds[AudibleAlert.warningImmediate].size > 0

  def test_load_sounds_falls_back_when_custom_wav_has_odd_payload(self, tmp_path):
    soundd = Soundd.__new__(Soundd)
    soundd.sound_directory = tmp_path / "sounds"
    soundd.sound_directory.mkdir()
    soundd.random_events_directory = tmp_path / "random_events"
    soundd.random_events_directory.mkdir()

    odd = soundd.sound_directory / "warning_immediate.wav"
    with wave.open(str(odd), "w") as wav:
      wav.setnchannels(1)
      wav.setsampwidth(2)
      wav.setframerate(48000)
      wav.writeframes(b"\x00\x00\x00\x00")
    odd.write_bytes(odd.read_bytes()[:-1])

    soundd.load_sounds()

    assert AudibleAlert.warningImmediate in soundd.loaded_sounds
    assert soundd.loaded_sounds[AudibleAlert.warningImmediate].size > 0

  def test_missing_goat_keeps_stock_critical_alert(self, tmp_path):
    soundd = Soundd.__new__(Soundd)
    soundd.sound_directory = tmp_path / "sounds"
    soundd.sound_directory.mkdir()
    soundd.random_events_directory = tmp_path / "random_events"
    soundd.random_events_directory.mkdir()
    soundd.load_sounds()

    goat_alert = starpilot_alert_key(StarPilotAudibleAlert.goat)
    assert goat_alert not in soundd.loaded_sounds
    assert AudibleAlert.warningImmediate in soundd.loaded_sounds

    assert soundd.select_critical_alert(AudibleAlert.warningImmediate, True) == AudibleAlert.warningImmediate

    soundd.loaded_sounds[goat_alert] = soundd.loaded_sounds[AudibleAlert.warningImmediate]
    assert soundd.select_critical_alert(AudibleAlert.warningImmediate, True) == goat_alert
    assert soundd.select_critical_alert(AudibleAlert.warningImmediate, False) == AudibleAlert.warningImmediate

  def test_bluetooth_audio_mutes_local_only_while_healthy(self):
    soundd = Soundd.__new__(Soundd)
    samples = np.array([0.25, -0.5], dtype=np.float32)
    soundd.get_sound_data = lambda _frames: samples
    data_out = np.zeros((2, 1), dtype=np.float32)
    soundd.pending_stream_status = None

    soundd.bluetooth_audio = type("Sink", (), {"submit": lambda self, _samples: True})()
    soundd.callback(data_out, 2, None, None)
    np.testing.assert_array_equal(data_out[:, 0], np.zeros(2, dtype=np.float32))

    soundd.bluetooth_audio = type("Sink", (), {"submit": lambda self, _samples: False})()
    soundd.callback(data_out, 2, None, None)
    np.testing.assert_array_equal(data_out[:, 0], samples)

  def test_check_selfdrive_timeout_alert(self):
    sm = SubMaster(['selfdriveState'])
    pm = PubMaster(['selfdriveState'])

    for _ in range(100):
      cs = messaging.new_message('selfdriveState')
      cs.selfdriveState.enabled = True

      pm.send("selfdriveState", cs)

      time.sleep(0.01)

      sm.update(0)

      assert not check_selfdrive_timeout_alert(sm)

    for _ in range(SELFDRIVE_STATE_TIMEOUT * 110):
      sm.update(0)
      time.sleep(0.01)

    assert check_selfdrive_timeout_alert(sm)

  # TODO: add test with micd for checking that soundd actually outputs sounds
