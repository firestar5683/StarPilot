import os
import operator
import platform
import sys

from types import SimpleNamespace

from cereal import car
from openpilot.common.params import Params
from opendbc.car.gps import car_gps_available
from openpilot.system.hardware import HARDWARE, PC, TICI
from openpilot.system.manager.process import PythonProcess, NativeProcess, DaemonProcess

WEBCAM = os.getenv("USE_WEBCAM") is not None
UI_WATCHDOG_MAX_DT = int(os.getenv("UI_WATCHDOG_MAX_DT", "30"))
CAMERAD_WATCHDOG_MAX_DT = int(os.getenv("CAMERAD_WATCHDOG_MAX_DT", "5"))

def driverview(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return started or params.get_bool("IsDriverViewEnabled")

def notcar(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return started and CP.notCar

def iscar(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return started and not CP.notCar

def logging(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  run = (not CP.notCar) or not params.get_bool("DisableLogging")
  return started and run

def ublox_available() -> bool:
  return os.path.exists('/dev/ttyHS0') and not os.path.exists('/persist/comma/use-quectel-gps')


def update_car_gps_param(params: Params) -> bool | None:
  car_params = params.get("CarParams")
  if car_params is None:
    return None

  with car.CarParams.from_bytes(car_params) as CP:
    available = car_gps_available(CP)
  if available != params.get_bool("CarGpsAvailable"):
    params.put_bool("CarGpsAvailable", available)
  return available

def ublox(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  car_gps = update_car_gps_param(params)
  use_ublox = ublox_available()
  if use_ublox != params.get_bool("UbloxAvailable"):
    params.put_bool("UbloxAvailable", use_ublox)
  return started and use_ublox and car_gps is False

def joystick(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return started and params.get_bool("JoystickDebugMode")

def not_joystick(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return started and not params.get_bool("JoystickDebugMode")

def long_maneuver(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return started and params.get_bool("LongitudinalManeuverMode") and not params.get_bool("LateralManeuverMode")

def lat_maneuver(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return started and params.get_bool("LateralManeuverMode") and not params.get_bool("LongitudinalManeuverMode")

def not_long_maneuver(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return started and not params.get_bool("LongitudinalManeuverMode")

def qcomgps(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  update_car_gps_param(params)
  return started and not ublox_available()

def always_run(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return True

def only_onroad(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return started

def only_offroad(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return not started

def sentry_mode(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return not started and params.get_bool("SentryModeEnabled")

def sensord_run(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return started or params.get_bool("SentryModeEnabled")

def camera_run(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return driverview(started, params, CP, starpilot_toggles) or (not started and params.get_bool("SentryModeCapture"))

def livestream(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return params.get_bool("IsLiveStreaming")

def or_(*fns):
  return lambda *args: operator.or_(*(fn(*args) for fn in fns))

def and_(*fns):
  return lambda *args: operator.and_(*(fn(*args) for fn in fns))

def not_(*fns):
  return lambda *args: operator.not_(*(fn(*args) for fn in fns))

# StarPilot variables
def allow_logging(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return not starpilot_toggles.no_logging

def allow_uploads(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return (params.get_bool("AlwaysAllowUploads") or not starpilot_toggles.no_uploads or
          (starpilot_toggles.no_onroad_uploads and not started))

def run_speed_limit_filler(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return starpilot_toggles.speed_limit_filler

def run_speed_limit_vision(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return starpilot_toggles.vision_speed_limit_detection

def run_navigationd(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return started and params.get("NavDestination") is not None


def bluetooth_enabled(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return params.get_bool("BluetoothEnabled")


def soundd_run(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return driverview(started, params, CP, starpilot_toggles) or params.get_bool("BluetoothAudioTestActive")


def wheel_controls_enabled(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return params.get_bool("WheelControlsEnabled")


def run_v_asm(started: bool, params: Params, CP: car.CarParams, starpilot_toggles: SimpleNamespace) -> bool:
  return started and getattr(starpilot_toggles, "v_asm_enabled", False)


def big_device_ui_process() -> NativeProcess:
  return NativeProcess(
    "ui",
    ".",
    ["/usr/bin/env", "BIG=1", sys.executable, "-m", "openpilot.selfdrive.ui.ui"],
    always_run,
    watchdog_max_dt=UI_WATCHDOG_MAX_DT,
  )


procs = [
  DaemonProcess("manage_athenad", "system.athena.manage_athenad", "AthenadPid"),

  NativeProcess("loggerd", "system/loggerd", ["./loggerd"], and_(allow_logging, logging)),
  NativeProcess("encoderd", "system/loggerd", ["./encoderd"], and_(allow_logging, only_onroad)),
  NativeProcess("stream_encoderd", "system/loggerd", ["./encoderd", "--stream"], or_(and_(livestream, not_(iscar)), notcar)),
  PythonProcess("logmessaged", "system.logmessaged", always_run),

  NativeProcess("camerad", "system/camerad", ["./camerad"], or_(camera_run, livestream), enabled=not WEBCAM,
                watchdog_max_dt=CAMERAD_WATCHDOG_MAX_DT),
  PythonProcess("webcamerad", "tools.webcam.camerad", driverview, enabled=WEBCAM),
  PythonProcess("proclogd", "system.proclogd", and_(allow_logging, only_onroad), enabled=platform.system() != "Darwin"),
  PythonProcess("journald", "system.journald", and_(allow_logging, only_onroad), platform.system() != "Darwin"),
  PythonProcess("micd", "system.micd", iscar),
  PythonProcess("timed", "system.timed", always_run, enabled=not PC),

  PythonProcess("modeld", "selfdrive.modeld.modeld", only_onroad),
  PythonProcess("dmonitoringmodeld", "selfdrive.modeld.dmonitoringmodeld", driverview, enabled=(WEBCAM or not PC)),

  PythonProcess("sensord", "system.sensord.sensord", sensord_run, enabled=not PC),
  PythonProcess("sentryd", "system.sentryd.sentryd", sentry_mode, enabled=not PC),
  PythonProcess("soundd", "selfdrive.ui.soundd", soundd_run),
  PythonProcess("locationd", "selfdrive.locationd.locationd", only_onroad),
  NativeProcess("_pandad", "selfdrive/pandad", ["./pandad"], always_run, enabled=False),
  PythonProcess("calibrationd", "selfdrive.locationd.calibrationd", only_onroad),
  PythonProcess("torqued", "selfdrive.locationd.torqued", only_onroad),
  PythonProcess("controlsd", "selfdrive.controls.controlsd", and_(not_joystick, iscar)),
  PythonProcess("joystickd", "tools.joystick.joystickd", or_(joystick, notcar)),
  PythonProcess("selfdrived", "selfdrive.selfdrived.selfdrived", only_onroad),
  PythonProcess("card", "selfdrive.car.card", only_onroad),
  PythonProcess("deleter", "system.loggerd.deleter", always_run),
  PythonProcess("dmonitoringd", "selfdrive.monitoring.dmonitoringd", driverview, enabled=(WEBCAM or not PC)),
  PythonProcess("qcomgpsd", "system.qcomgpsd.qcomgpsd", qcomgps, enabled=TICI),
  PythonProcess("pandad", "selfdrive.pandad.pandad", always_run),
  PythonProcess("paramsd", "selfdrive.locationd.paramsd", only_onroad),
  PythonProcess("lagd", "selfdrive.locationd.lagd", only_onroad),
  PythonProcess("ubloxd", "system.ubloxd.ubloxd", ublox, enabled=TICI),
  PythonProcess("pigeond", "system.ubloxd.pigeond", ublox, enabled=TICI),
  PythonProcess("plannerd", "selfdrive.controls.plannerd", not_long_maneuver),
  PythonProcess("maneuversd", "tools.longitudinal_maneuvers.maneuversd", long_maneuver),
  PythonProcess("lateral_maneuversd", "tools.lateral_maneuvers.lateral_maneuversd", lat_maneuver),
  PythonProcess("radard", "selfdrive.controls.radard", only_onroad),
  PythonProcess("hardwared", "system.hardware.hardwared", always_run),
  PythonProcess("tombstoned", "system.tombstoned", always_run, enabled=not PC),
  PythonProcess("updated", "system.updated.updated", always_run, enabled=not PC),
  PythonProcess("uploader", "system.loggerd.uploader", allow_uploads, nice=19),
  PythonProcess("statsd", "system.statsd", always_run),
  PythonProcess("feedbackd", "selfdrive.ui.feedback.feedbackd", only_onroad),

  # debug procs
  NativeProcess("bridge", "cereal/messaging", ["./bridge"], notcar),
  PythonProcess("webrtcd", "system.webrtc.webrtcd", or_(and_(livestream, not_(iscar)), notcar)),
  PythonProcess("webjoystick", "tools.bodyteleop.web", notcar),
  PythonProcess("joystick", "tools.joystick.joystick_control", and_(joystick, iscar)),
]

# StarPilot variables
procs += [
  PythonProcess("bluetooth_managerd", "starpilot.system.bluetooth.daemon", bluetooth_enabled, enabled=TICI),
  PythonProcess("wheel_controlsd", "starpilot.system.wheel_controls.wheel_controlsd", wheel_controls_enabled, enabled=TICI, nice=19),
  PythonProcess("the_galaxy", "starpilot.system.the_galaxy.the_galaxy", always_run, nice=10),
  PythonProcess("galaxy", "starpilot.system.galaxy.galaxy", always_run, nice=10),
]

device_type = HARDWARE.get_device_type()
if device_type in ("tici", "tizi"):
  procs.append(big_device_ui_process())
else:
  procs.append(PythonProcess("ui", "selfdrive.ui.ui", always_run, watchdog_max_dt=UI_WATCHDOG_MAX_DT))

procs += [
  PythonProcess("device_syncd", "starpilot.system.device_syncd", always_run),
  PythonProcess("starpilot_process", "starpilot.starpilot_process", always_run),
  PythonProcess("mapd", "starpilot.navigation.mapd_wrapper", always_run, nice=19),
  PythonProcess("navigationd", "starpilot.navigation.navigationd", run_navigationd, nice=19),
  PythonProcess("speed_limit_filler", "starpilot.system.speed_limit_filler", run_speed_limit_filler, nice=19),
  PythonProcess("speed_limit_vision", "starpilot.system.speed_limit_vision", run_speed_limit_vision, nice=19),
  PythonProcess("adj_spot_monitor_vision", "starpilot.system.adj_spot_monitor_vision", run_v_asm, nice=19),
]

managed_processes = {p.name: p for p in procs}
