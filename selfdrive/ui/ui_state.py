import json
import pyray as rl
import numpy as np
import time
import threading
from collections.abc import Callable
from enum import Enum
from cereal import messaging, car, log
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.ui.lib.prime_state import PrimeState
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.hardware import HARDWARE, PC

BACKLIGHT_OFFROAD = 65 if HARDWARE.get_device_type() == "mici" else 50


class UIStatus(Enum):
  DISENGAGED = "disengaged"
  ENGAGED = "engaged"
  OVERRIDE = "override"


class UIState:
  _instance: 'UIState | None' = None

  def __new__(cls):
    if cls._instance is None:
      cls._instance = super().__new__(cls)
      cls._instance._initialize()
    return cls._instance

  def _initialize(self):
    self.params = Params()
    self.params_memory = Params(memory=True)
    self.sm = messaging.SubMaster(
      [
        "modelV2",
        "controlsState",
        "onroadEvents",
        "liveCalibration",
        "radarState",
        "deviceState",
        "pandaStates",
        "carParams",
        "driverMonitoringState",
        "carState",
        "driverStateV2",
        "roadCameraState",
        "wideRoadCameraState",
        "managerState",
        "selfdriveState",
        "longitudinalPlan",
        "gpsLocationExternal",
        "mapdOut",
        "carOutput",
        "carControl",
        "liveParameters",
        "rawAudioData",
        "starpilotCarState",
        "starpilotPlan",
        "starpilotRadarState",
        "starpilotSelfdriveState",
        "liveTracks",
        "liveDelay",
        "liveTorqueParameters",
      ]
    )

    self.prime_state = PrimeState()

    # UI Status tracking
    self.status: UIStatus = UIStatus.DISENGAGED
    self.started_frame: int = 0
    self.started_time: float = 0.0
    self._engaged_prev: bool = False
    self._started_prev: bool = False

    # Core state variables
    self.is_metric: bool = self.params.get_bool("IsMetric")
    self.is_release = self.params.get_bool("IsReleaseBranch")
    self.always_on_dm: bool = self.params.get_bool("AlwaysOnDM")
    self.started: bool = False
    self.ignition: bool = False
    self.recording_audio: bool = False
    self.panda_type: log.PandaState.PandaType = log.PandaState.PandaType.unknown
    self.personality: log.LongitudinalPersonality = log.LongitudinalPersonality.standard
    self.has_longitudinal_control: bool = False
    self.CP: car.CarParams | None = None
    self.light_sensor: float = -1.0
    self._param_update_time: float = 0.0
    self.always_on_lateral_active: bool = False
    self.switchback_mode_enabled: bool = False
    self.traffic_mode_enabled: bool = False
    self.conditional_status: int = 0
    self.starpilot_toggles: dict = {
      "debug_mode": False,
      "driver_camera_in_reverse": False,
      "force_offroad": False,
      "force_onroad": False,
      "screen_brightness": 101,
      "screen_brightness_onroad": 101,
      "screen_timeout": 30,
      "screen_timeout_onroad": 10,
      "sidebar_color1": "#FFFFFFFF",
      "sidebar_color2": "#FFFFFFFF",
      "sidebar_color3": "#FFFFFFFF",
      "simple_mode": False,
      "standby_mode": False,
      "tethering_config": 0,
    }

    # Callbacks
    self._offroad_transition_callbacks: list[Callable[[], None]] = []
    self._engaged_transition_callbacks: list[Callable[[], None]] = []

    self.update_params()

  def add_offroad_transition_callback(self, callback: Callable[[], None]):
    self._offroad_transition_callbacks.append(callback)

  def add_engaged_transition_callback(self, callback: Callable[[], None]):
    self._engaged_transition_callbacks.append(callback)

  @property
  def engaged(self) -> bool:
    return self.started and self.sm["selfdriveState"].enabled

  def is_onroad(self) -> bool:
    return self.started

  def is_offroad(self) -> bool:
    return not self.started

  def update(self) -> None:
    self.prime_state.start()  # start thread after manager forks ui
    self.sm.update(0)
    self._update_state()
    self._update_status()
    if time.monotonic() - self._param_update_time > 5.0:
      self.update_params()
    device.update()

  def _update_state(self) -> None:
    # Handle panda states updates
    if self.sm.updated["pandaStates"]:
      panda_states = self.sm["pandaStates"]

      if len(panda_states) > 0:
        # Get panda type from first panda
        self.panda_type = panda_states[0].pandaType
        # Check ignition status across all pandas
        if self.panda_type != log.PandaState.PandaType.unknown:
          self.ignition = any(state.ignitionLine or state.ignitionCan for state in panda_states)
    elif self.sm.frame - self.sm.recv_frame["pandaStates"] > 5 * rl.get_fps():
      self.panda_type = log.PandaState.PandaType.unknown

    # Handle wide road camera state updates
    if self.sm.updated["wideRoadCameraState"]:
      cam_state = self.sm["wideRoadCameraState"]
      self.light_sensor = max(100.0 - cam_state.exposureValPercent, 0.0)
    elif not self.sm.alive["wideRoadCameraState"] or not self.sm.valid["wideRoadCameraState"]:
      self.light_sensor = -1

    # Trust hardwared's filtered started state; raw ignition can flap on Toyota.
    force_onroad = self.params.get_bool("ForceOnroad")
    force_offroad = self.params.get_bool("ForceOffroad")
    started = self.sm["deviceState"].started
    started |= force_onroad
    started &= not force_offroad
    self.started = started

    # Update recording audio state
    self.recording_audio = self.params.get_bool("RecordAudio") and self.started

    self.is_metric = self.params.get_bool("IsMetric")
    self.always_on_dm = self.params.get_bool("AlwaysOnDM")
    self.switchback_mode_enabled = self.params_memory.get_bool("SwitchbackModeEnabled") if self.started else False
    if self.sm.valid.get("starpilotCarState", False):
      starpilot_car_state = self.sm["starpilotCarState"]
      self.always_on_lateral_active = (not self.sm["selfdriveState"].enabled and
                                       starpilot_car_state.alwaysOnLateralEnabled)
      self.traffic_mode_enabled = starpilot_car_state.trafficModeEnabled
    else:
      self.always_on_lateral_active = False
      self.traffic_mode_enabled = False

    self.conditional_status = self.params_memory.get_int("CEStatus", default=0) if self.started else 0

    if self.sm.updated["starpilotPlan"]:
      plan = self.sm["starpilotPlan"]
      toggles_str = plan.starpilotToggles
      if toggles_str:
        try:
          parsed = json.loads(toggles_str)
          if isinstance(parsed, dict):
            self.starpilot_toggles.update(parsed)
        except Exception as e:
          cloudlog.warning(f"Error parsing starpilot_toggles: {e}")

    self.starpilot_toggles["force_offroad"] = force_offroad
    self.starpilot_toggles["force_onroad"] = force_onroad

  def _update_status(self) -> None:
    if self.started and self.sm.updated["selfdriveState"]:
      ss = self.sm["selfdriveState"]
      state = ss.state

      if state in (log.SelfdriveState.OpenpilotState.preEnabled, log.SelfdriveState.OpenpilotState.overriding):
        self.status = UIStatus.OVERRIDE
      else:
        self.status = UIStatus.ENGAGED if ss.enabled else UIStatus.DISENGAGED

    # Check for engagement state changes
    if self.engaged != self._engaged_prev:
      for callback in self._engaged_transition_callbacks:
        callback()
      self._engaged_prev = self.engaged

    # Handle onroad/offroad transition
    if self.started != self._started_prev or self.sm.frame == 1:
      if self.started:
        self.status = UIStatus.DISENGAGED
        self.started_frame = self.sm.frame
        self.started_time = time.monotonic()

      for callback in self._offroad_transition_callbacks:
        callback()

      self._started_prev = self.started

  def update_params(self) -> None:
    # For slower operations
    # Update longitudinal control state
    CP_bytes = self.params.get("CarParamsPersistent")
    if CP_bytes is not None:
      self.CP = messaging.log_from_bytes(CP_bytes, car.CarParams)
      if self.CP.alphaLongitudinalAvailable:
        self.has_longitudinal_control = self.params.get_bool("AlphaLongitudinalEnabled")
      else:
        self.has_longitudinal_control = self.CP.openpilotLongitudinalControl
    self._param_update_time = time.monotonic()


class Device:
  def __init__(self):
    self._ignition = False
    self._interaction_time: float = -1
    self._override_interactive_timeout: int | None = None
    self._interactive_timeout_callbacks: list[Callable] = []
    self._prev_timed_out = False
    self._awake: bool = True
    self._params = Params()

    self._offroad_brightness: int = BACKLIGHT_OFFROAD
    self._last_brightness: int = 0
    self._brightness_filter = FirstOrderFilter(BACKLIGHT_OFFROAD, 10.00, 1 / gui_app.target_fps)
    self._brightness_thread: threading.Thread | None = None

  @property
  def awake(self) -> bool:
    return self._awake

  def set_override_interactive_timeout(self, timeout: int | None) -> None:
    # Override the interactive timeout duration temporarily
    self._override_interactive_timeout = timeout
    self._reset_interactive_timeout()

  @property
  def interactive_timeout(self) -> int:
    if self._override_interactive_timeout is not None:
      return self._override_interactive_timeout

    timeout_onroad = self._params.get_int("ScreenTimeoutOnroad", return_default=True)
    timeout_offroad = self._params.get_int("ScreenTimeout", return_default=True)

    if timeout_onroad <= 0:
      timeout_onroad = 10 if gui_app.big_ui() else 5
    if timeout_offroad <= 0:
      timeout_offroad = 30

    return int(timeout_onroad if ui_state.ignition else timeout_offroad)

  def _reset_interactive_timeout(self) -> None:
    self._interaction_time = time.monotonic() + self.interactive_timeout

  def reset_interactive_timeout(self) -> None:
    self._reset_interactive_timeout()

  def add_interactive_timeout_callback(self, callback: Callable):
    self._interactive_timeout_callbacks.append(callback)

  def update(self):
    # do initial reset
    if self._interaction_time <= 0:
      self._reset_interactive_timeout()

    self._update_brightness()
    self._update_wakefulness()

  def set_offroad_brightness(self, brightness: int | None):
    if brightness is None:
      brightness = BACKLIGHT_OFFROAD
    self._offroad_brightness = min(max(brightness, 0), 100)

  def _update_brightness(self):
    clipped_brightness = self._offroad_brightness

    if ui_state.started and ui_state.light_sensor >= 0:
      clipped_brightness = ui_state.light_sensor

      # CIE 1931 - https://www.photonstophotos.net/GeneralTopics/Exposure/Psychometric_Lightness_and_Gamma.htm
      if clipped_brightness <= 8:
        clipped_brightness = clipped_brightness / 903.3
      else:
        clipped_brightness = ((clipped_brightness + 16.0) / 116.0) ** 3.0

      clipped_brightness = float(np.interp(clipped_brightness, [0, 1], [30, 100]))

    brightness = round(self._brightness_filter.update(clipped_brightness))
    if not self._awake:
      brightness = 0

    if brightness != self._last_brightness:
      if self._brightness_thread is None or not self._brightness_thread.is_alive():
        self._brightness_thread = threading.Thread(target=HARDWARE.set_screen_brightness, args=(brightness,))
        self._brightness_thread.start()
        self._last_brightness = brightness

  def _update_wakefulness(self):
    # Handle interactive timeout
    ignition_just_turned_off = not ui_state.ignition and self._ignition
    self._ignition = ui_state.ignition

    if ignition_just_turned_off or any(ev.left_down for ev in gui_app.mouse_events):
      self._reset_interactive_timeout()

    interaction_timeout = time.monotonic() > self._interaction_time
    if interaction_timeout and not self._prev_timed_out:
      for callback in self._interactive_timeout_callbacks:
        callback()
    self._prev_timed_out = interaction_timeout

    self._set_awake(ui_state.started or not interaction_timeout or PC)

  def _set_awake(self, on: bool):
    if on != self._awake:
      self._awake = on
      cloudlog.debug(f"setting display power {int(on)}")
      HARDWARE.set_display_power(on)
      gui_app.set_should_render(on)


# Global instance
ui_state = UIState()
device = Device()
