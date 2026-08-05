import math
import numpy as np
import time
import wave

from pathlib import Path

from cereal import car, custom, log, messaging
from openpilot.common.basedir import BASEDIR
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.params import Params
from openpilot.common.realtime import Ratekeeper
from openpilot.common.utils import retry
from openpilot.common.swaglog import cloudlog

from openpilot.system import micd
from openpilot.system.hardware import HARDWARE

from openpilot.starpilot.common.starpilot_variables import ACTIVE_THEME_PATH, ERROR_LOGS_PATH, RANDOM_EVENTS_PATH, get_starpilot_toggles

SAMPLE_RATE = 48000
SAMPLE_BUFFER = 4096 # (approx 100ms)
MAX_VOLUME = 1.0
MIN_VOLUME = 0.1
SELFDRIVE_STATE_TIMEOUT = 5 # 5 seconds
FILTER_DT = 1. / (micd.SAMPLE_RATE / micd.FFT_SAMPLES)

AMBIENT_DB = 30 # DB where MIN_VOLUME is applied
DB_SCALE = 30 # AMBIENT_DB + DB_SCALE is where MAX_VOLUME is applied

VOLUME_BASE = 20
if HARDWARE.get_device_type() in ("tici", "tizi"):
  VOLUME_BASE = 10

AudibleAlert = log.SelfdriveState.AudibleAlert

StarPilotAudibleAlert = custom.StarPilotCarControl.HUDControl.AudibleAlert

# StarPilot mirrors stock audible alerts at 0-8. Keep those raw values so themed
# stock sounds still work, and only offset custom random-event sounds.
STARPILOT_CUSTOM_ALERT_OFFSET = 1000
STARPILOT_CUSTOM_ALERT_START = int(StarPilotAudibleAlert.angry)


def starpilot_alert_key(alert):
  raw_alert = int(alert)
  return STARPILOT_CUSTOM_ALERT_OFFSET + raw_alert if raw_alert >= STARPILOT_CUSTOM_ALERT_START else raw_alert


sound_list: dict[int, tuple[str, int | None, float]] = {
  # AudibleAlert, file name, play count (none for infinite)
  AudibleAlert.engage: ("engage.wav", 1, MAX_VOLUME),
  AudibleAlert.disengage: ("disengage.wav", 1, MAX_VOLUME),
  AudibleAlert.refuse: ("refuse.wav", 1, MAX_VOLUME),

  AudibleAlert.prompt: ("prompt.wav", 1, MAX_VOLUME),
  AudibleAlert.promptRepeat: ("prompt.wav", None, MAX_VOLUME),
  AudibleAlert.promptDistracted: ("prompt_distracted.wav", None, MAX_VOLUME),

  AudibleAlert.preAlert: ("pre_alert.wav", 1, MAX_VOLUME),

  AudibleAlert.warningSoft: ("warning_soft.wav", None, MAX_VOLUME),
  AudibleAlert.warningImmediate: ("warning_immediate.wav", None, MAX_VOLUME),

  starpilot_alert_key(StarPilotAudibleAlert.angry): ("angry.wav", 1, MAX_VOLUME),
  starpilot_alert_key(StarPilotAudibleAlert.continued): ("continued.wav", 1, MAX_VOLUME),
  starpilot_alert_key(StarPilotAudibleAlert.dejaVu): ("dejaVu.wav", 1, MAX_VOLUME),
  starpilot_alert_key(StarPilotAudibleAlert.doc): ("doc.wav", 1, MAX_VOLUME),
  starpilot_alert_key(StarPilotAudibleAlert.fart): ("fart.wav", 1, MAX_VOLUME),
  starpilot_alert_key(StarPilotAudibleAlert.firefox): ("firefox.wav", 1, MAX_VOLUME),
  starpilot_alert_key(StarPilotAudibleAlert.goat): ("goat.wav", None, MAX_VOLUME),
  starpilot_alert_key(StarPilotAudibleAlert.hal9000): ("hal9000.wav", 1, MAX_VOLUME),
  starpilot_alert_key(StarPilotAudibleAlert.mail): ("mail.wav", 1, MAX_VOLUME),
  starpilot_alert_key(StarPilotAudibleAlert.nessie): ("nessie.wav", 1, MAX_VOLUME),
  starpilot_alert_key(StarPilotAudibleAlert.noice): ("noice.wav", 1, MAX_VOLUME),
  starpilot_alert_key(StarPilotAudibleAlert.startup): ("startup.wav", 1, MAX_VOLUME),
  starpilot_alert_key(StarPilotAudibleAlert.thisIsFine): ("this_is_fine.wav", 1, MAX_VOLUME),
  starpilot_alert_key(StarPilotAudibleAlert.uwu): ("uwu.wav", 1, MAX_VOLUME),
}
if HARDWARE.get_device_type() in ("tici", "tizi"):
  sound_list.update({
    AudibleAlert.engage: ("engage_tizi.wav", 1, MAX_VOLUME),
    AudibleAlert.disengage: ("disengage_tizi.wav", 1, MAX_VOLUME),
  })

def check_selfdrive_timeout_alert(sm):
  ss_missing = time.monotonic() - sm.recv_time['selfdriveState']

  if ss_missing > SELFDRIVE_STATE_TIMEOUT:
    if sm['selfdriveState'].enabled and (ss_missing - SELFDRIVE_STATE_TIMEOUT) < 10:
      return True

  return False


class Soundd:
  def __init__(self):
    self.current_alert = AudibleAlert.none
    self.current_alert_type = ""
    self.current_volume = MIN_VOLUME
    self.current_sound_frame = 0

    self.selfdrive_timeout_alert = False

    self.spl_filter_weighted = FirstOrderFilter(0, 2.5, FILTER_DT, initialized=False)

    self.params_memory = Params(memory=True)

    self.starpilot_toggles = get_starpilot_toggles()

    self.openpilot_crashed_played = False

    self.auto_volume = 0

    self.previous_sound_pack = None
    self.previous_sound_source_signature = None

    self.error_log = ERROR_LOGS_PATH / "error.txt"
    self.random_events_directory = RANDOM_EVENTS_PATH / "sounds"

    self.update_starpilot_sounds()

  def get_sound_source_signature(self):
    try:
      resolved_path = self.sound_directory.resolve()
    except OSError:
      resolved_path = self.sound_directory

    sound_files = ()
    try:
      if self.sound_directory.exists():
        sound_files = tuple(sorted(
          (entry.name, entry.stat().st_mtime_ns)
          for entry in self.sound_directory.iterdir()
          if entry.is_file()
        ))
    except OSError:
      sound_files = ()

    return str(resolved_path), sound_files

  def load_sounds(self):
    self.loaded_sounds: dict[int, np.ndarray] = {}

    # Load all sounds
    for sound in sound_list:
      filename, play_count, volume = sound_list[sound]

      random_events_path = self.random_events_directory / filename
      sounds_path = self.sound_directory / filename

      if not sounds_path.exists() and "_tizi" in filename:
        standard_path = self.sound_directory / filename.replace("_tizi", "")
        if standard_path.exists():
          sounds_path = standard_path

      if random_events_path.exists():
        wavefile = wave.open(str(random_events_path), 'r')
      elif sounds_path.exists():
        wavefile = wave.open(str(sounds_path), 'r')
      else:
        if filename == "startup.wav":
          filename = "engage.wav"
        wavefile = wave.open(BASEDIR + "/selfdrive/assets/sounds/" + filename, 'r')

      assert wavefile.getnchannels() == 1
      assert wavefile.getsampwidth() == 2
      assert wavefile.getframerate() == SAMPLE_RATE

      length = wavefile.getnframes()
      self.loaded_sounds[sound] = np.frombuffer(wavefile.readframes(length), dtype=np.int16).astype(np.float32) / (2**16/2)

  def get_sound_data(self, frames): # get "frames" worth of data from the current alert sound, looping when required

    ret = np.zeros(frames, dtype=np.float32)

    if self.current_alert != AudibleAlert.none:
      num_loops = sound_list[self.current_alert][1]
      sound_data = self.loaded_sounds[self.current_alert]
      written_frames = 0

      current_sound_frame = self.current_sound_frame % len(sound_data)
      loops = self.current_sound_frame // len(sound_data)

      while written_frames < frames and (num_loops is None or loops < num_loops):
        available_frames = sound_data.shape[0] - current_sound_frame
        frames_to_write = min(available_frames, frames - written_frames)
        ret[written_frames:written_frames+frames_to_write] = sound_data[current_sound_frame:current_sound_frame+frames_to_write]
        written_frames += frames_to_write
        self.current_sound_frame += frames_to_write

    return ret * self.current_volume

  def callback(self, data_out: np.ndarray, frames: int, time, status) -> None:
    if status:
      cloudlog.warning(f"soundd stream over/underflow: {status}")
    data_out[:frames, 0] = self.get_sound_data(frames)

  def update_alert(self, new_alert):
    current_alert_played_once = self.current_alert == AudibleAlert.none or self.current_sound_frame > len(self.loaded_sounds[self.current_alert])
    if self.current_alert != new_alert and (new_alert != AudibleAlert.none or current_alert_played_once):
      self.current_alert = new_alert
      self.current_sound_frame = 0

  def get_audible_alert(self, sm):
    if self.params_memory.get("TestAlert"):
      test_alert = self.params_memory.get("TestAlert")
      if isinstance(test_alert, bytes):
        test_alert = test_alert.decode("utf-8", "ignore")

      if test_alert == "belowSteerSpeed":
        self.current_alert_type = "belowSteerSpeed/warning"
        self.update_alert(AudibleAlert.prompt)
      else:
        self.current_alert_type = ""
        self.update_alert(getattr(AudibleAlert, test_alert))
      self.params_memory.remove("TestAlert")
    elif not self.openpilot_crashed_played and self.error_log.is_file():
      self.current_alert_type = ""
      self.update_alert(AudibleAlert.prompt)
      self.openpilot_crashed_played = True
    elif sm.updated['selfdriveState']:
      new_alert = sm['selfdriveState'].alertSound.raw
      new_alert_type = sm['selfdriveState'].alertType

      critical_full_alert = sm['selfdriveState'].alertStatus == log.SelfdriveState.AlertStatus.critical
      critical_full_alert &= sm['selfdriveState'].alertSize == log.SelfdriveState.AlertSize.full
      if self.starpilot_toggles.goat_scream_critical_alerts and critical_full_alert:
        new_alert = starpilot_alert_key(StarPilotAudibleAlert.goat)

      new_starpilot_alert = sm['starpilotSelfdriveState'].alertSound.raw
      if new_alert == AudibleAlert.none and new_starpilot_alert != StarPilotAudibleAlert.none:
        new_alert = starpilot_alert_key(new_starpilot_alert)
        new_alert_type = sm['starpilotSelfdriveState'].alertType

      self.current_alert_type = new_alert_type
      self.update_alert(new_alert)
    elif check_selfdrive_timeout_alert(sm):
      self.current_alert_type = ""
      self.update_alert(AudibleAlert.warningImmediate)
      self.selfdrive_timeout_alert = True
    elif self.selfdrive_timeout_alert:
      self.current_alert_type = ""
      self.update_alert(AudibleAlert.none)
      self.selfdrive_timeout_alert = False

  def get_volume_override(self):
    if self.current_alert_type.startswith("belowSteerSpeed/"):
      return self.starpilot_toggles.below_steer_speed_volume / 100.0

    return self.volume_map.get(self.current_alert, 1.01)

  def calculate_volume(self, weighted_db):
    volume = ((weighted_db - AMBIENT_DB) / DB_SCALE) * (MAX_VOLUME - MIN_VOLUME) + MIN_VOLUME
    return math.pow(VOLUME_BASE, (np.clip(volume, MIN_VOLUME, MAX_VOLUME) - 1))

  @retry(attempts=10, delay=3)
  def get_stream(self, sd):
    # reload sounddevice to reinitialize portaudio
    sd._terminate()
    sd._initialize()
    return sd.OutputStream(channels=1, samplerate=SAMPLE_RATE, callback=self.callback, blocksize=SAMPLE_BUFFER)

  def start_stream(self, sd):
    stream = self.get_stream(sd)
    stream.start()
    cloudlog.info(f"soundd stream started: {stream.samplerate=} {stream.channels=} {stream.dtype=} {stream.device=}, {stream.blocksize=}")
    return stream

  def describe_stream(self, stream) -> str:
    attrs = {
      "active": getattr(stream, "active", None),
      "stopped": getattr(stream, "stopped", None),
      "closed": getattr(stream, "closed", None),
      "samplerate": getattr(stream, "samplerate", None),
      "channels": getattr(stream, "channels", None),
      "dtype": getattr(stream, "dtype", None),
      "device": getattr(stream, "device", None),
      "blocksize": getattr(stream, "blocksize", None),
    }
    return " ".join(f"{k}={v!r}" for k, v in attrs.items())

  def soundd_thread(self):
    # sounddevice must be imported after forking processes
    import sounddevice as sd

    sm = messaging.SubMaster(['selfdriveState', 'soundPressure'])

    sm = sm.extend(['starpilotSelfdriveState', 'starpilotPlan'])

    while True:
      stream = None
      try:
        stream = self.start_stream(sd)
        rk = Ratekeeper(20)

        while True:
          sm.update(0)

          if sm.updated['soundPressure'] and self.current_alert == AudibleAlert.none: # only update volume filter when not playing alert
            self.spl_filter_weighted.update(sm["soundPressure"].soundPressureWeightedDb)
            self.current_volume = self.calculate_volume(float(self.spl_filter_weighted.x))

            if self.starpilot_toggles.alert_volume_controller:
              self.auto_volume = self.current_volume
              self.current_volume = 0.0

          elif self.current_alert != AudibleAlert.none and self.starpilot_toggles.alert_volume_controller:
            self.current_volume = self.get_volume_override()
            if self.current_volume == 1.01:
              self.current_volume = self.auto_volume

          self.get_audible_alert(sm)

          rk.keep_time()

          if not stream.active:
            raise RuntimeError(f"soundd stream inactive: {self.describe_stream(stream)}")

          starpilot_toggles = get_starpilot_toggles(sm)
          if starpilot_toggles != self.starpilot_toggles:
            self.starpilot_toggles = starpilot_toggles

            stream = self.update_starpilot_sounds(sd, stream)
          elif rk.frame % 5 == 0:
            stream = self.update_starpilot_sounds(sd, stream)
      except Exception:
        cloudlog.exception("soundd: stream failed, restarting")
        time.sleep(1)
      finally:
        if stream is not None:
          try:
            stream.close()
          except Exception:
            cloudlog.exception("soundd: failed to close stream")

  def update_starpilot_sounds(self, sd=None, stream=None):
    self.volume_map = {
      AudibleAlert.engage: self.starpilot_toggles.engage_volume / 100.0,
      AudibleAlert.disengage: self.starpilot_toggles.disengage_volume / 100.0,
      AudibleAlert.refuse: self.starpilot_toggles.refuse_volume / 100.0,

      AudibleAlert.prompt: self.starpilot_toggles.prompt_volume / 100.0,
      AudibleAlert.promptRepeat: self.starpilot_toggles.prompt_volume / 100.0,
      AudibleAlert.promptDistracted: self.starpilot_toggles.promptDistracted_volume / 100.0,

      AudibleAlert.preAlert: self.starpilot_toggles.promptDistracted_volume / 100.0,

      AudibleAlert.warningSoft: self.starpilot_toggles.warningSoft_volume / 100.0,
      AudibleAlert.warningImmediate: self.starpilot_toggles.warningImmediate_volume / 100.0,

      starpilot_alert_key(StarPilotAudibleAlert.goat): self.starpilot_toggles.prompt_volume / 100.0,
      starpilot_alert_key(StarPilotAudibleAlert.startup): self.starpilot_toggles.engage_volume / 100.0
    }

    for sound in sound_list:
      if sound not in self.volume_map:
        self.volume_map[sound] = 1.01

    if self.starpilot_toggles.sound_pack != "stock":
      self.sound_directory = ACTIVE_THEME_PATH / "sounds"
    else:
      self.sound_directory = Path(BASEDIR) / "selfdrive" / "assets" / "sounds"

    sound_source_signature = self.get_sound_source_signature()
    should_reload = self.starpilot_toggles.sound_pack != self.previous_sound_pack
    should_reload |= sound_source_signature != self.previous_sound_source_signature

    if should_reload:
      self.load_sounds()

      self.previous_sound_pack = self.starpilot_toggles.sound_pack
      self.previous_sound_source_signature = sound_source_signature

      if stream is not None:
        stream.close()
        stream = self.get_stream(sd)
        stream.start()

    return stream


def main():
  s = Soundd()
  s.soundd_thread()


if __name__ == "__main__":
  main()
