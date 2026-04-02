#!/usr/bin/env python3
import datetime
import hashlib
import json
import requests
import time

from cereal import messaging
from openpilot.common.api import Api, api_get
from openpilot.common.params import Params
from openpilot.common.realtime import DT_MDL, Priority, Ratekeeper, config_realtime_process
from openpilot.common.time_helpers import system_time_valid
from openpilot.system.sentry import capture_report
from openpilot.system.athena.registration import UNREGISTERED_DONGLE_ID

from openpilot.starpilot.assets.model_manager import MODEL_DOWNLOAD_ALL_PARAM, MODEL_DOWNLOAD_PARAM, ModelManager
from openpilot.starpilot.assets.theme_manager import THEME_COMPONENT_PARAMS, ThemeManager
from openpilot.starpilot.common.starpilot_functions import update_maps, update_openpilot
from openpilot.starpilot.common.safe_mode import (
  SAFE_MODE_ENFORCE_FRAMES,
  apply_safe_mode,
  restore_safe_mode,
  safe_mode_enabled,
)
from openpilot.starpilot.common.starpilot_utilities import ThreadManager, flash_panda, is_url_pingable, lock_doors, use_konik_server
from openpilot.starpilot.common.starpilot_variables import ERROR_LOGS_PATH, StarPilotVariables
from openpilot.starpilot.controls.starpilot_planner import StarPilotPlanner
from openpilot.starpilot.system.starpilot_stats import send_stats
from openpilot.starpilot.system.starpilot_tracking import StarPilotTracking

ASSET_CHECK_RATE = (1 / DT_MDL)
DRIVE_STATS_SYNC_RATE = 30
UPDATE_CHECK_INTERVAL_SECONDS = 60 * 60


def get_update_check_phase_seconds(params_raw):
  for key in ("DongleId", "HardwareSerial"):
    value = params_raw.get(key)
    if isinstance(value, bytes):
      value = value.decode("utf-8", errors="ignore")
    if value and value != UNREGISTERED_DONGLE_ID:
      digest = hashlib.sha1(value.encode("utf-8")).digest()
      return int.from_bytes(digest[:4], "big") % UPDATE_CHECK_INTERVAL_SECONDS

  return 0


def get_next_periodic_update_check(monotonic_now, phase_seconds):
  current_period_start = int(monotonic_now // UPDATE_CHECK_INTERVAL_SECONDS) * UPDATE_CHECK_INTERVAL_SECONDS
  next_check = current_period_start + phase_seconds
  if next_check <= monotonic_now:
    next_check += UPDATE_CHECK_INTERVAL_SECONDS
  return next_check

def check_assets(now, model_manager, theme_manager, thread_manager, params, params_memory, starpilot_toggles):
  if params_memory.get_bool(MODEL_DOWNLOAD_ALL_PARAM):
    thread_manager.run_with_lock(model_manager.download_all_models)
  elif params_memory.get_bool("UpdateTinygrad"):
    thread_manager.run_with_lock(model_manager.update_tinygrad)
  else:
    model_to_download = params_memory.get(MODEL_DOWNLOAD_PARAM)
    if isinstance(model_to_download, bytes):
      model_to_download = model_to_download.decode("utf-8", errors="replace")
    if model_to_download:
      thread_manager.run_with_lock(model_manager.download_model, (model_to_download,))

  for asset_type, asset_param in THEME_COMPONENT_PARAMS.items():
    asset_to_download = params_memory.get(asset_param)
    if asset_to_download:
      thread_manager.run_with_lock(theme_manager.download_theme, (asset_type, asset_to_download, asset_param, starpilot_toggles))

  if params_memory.get_bool("FlashPanda"):
    thread_manager.run_with_lock(flash_panda, (params_memory))

  report_data = params_memory.get("IssueReported")
  if report_data:
    capture_report(report_data["DiscordUser"], report_data["Issue"], vars(starpilot_toggles))
    params_memory.remove("IssueReported")

  if params_memory.get_bool("DownloadMaps"):
    thread_manager.run_with_lock(update_maps, (now, params, params_memory, True))

def sync_drive_stats(params, session):
  try:
    dongle_id = params.get("DongleId")
    if isinstance(dongle_id, bytes):
      dongle_id = dongle_id.decode("utf-8", errors="replace")
    if not dongle_id or dongle_id == UNREGISTERED_DONGLE_ID:
      return

    token = Api(dongle_id).get_token(expiry_hours=2)
    if not token:
      return

    response = api_get(f"v1.1/devices/{dongle_id}/stats", timeout=15, access_token=token, session=session)
    if response.status_code != 200:
      print(f"Failed to sync drive stats (HTTP {response.status_code})")
      return

    stats = response.json()
    if not isinstance(stats, dict):
      return

    all_stats = stats.get("all")
    week_stats = stats.get("week")
    if not isinstance(all_stats, dict) or not isinstance(week_stats, dict):
      return

    params.put("ApiCache_DriveStats", stats)

    all_minutes = all_stats.get("minutes")
    if isinstance(all_minutes, (int, float)):
      params.put_int("KonikMinutes" if use_konik_server() else "openpilotMinutes", int(all_minutes))
  except Exception as exception:
    print(f"Failed to sync drive stats: {exception}")

def transition_offroad(starpilot_planner, theme_manager, thread_manager, time_validated, sm, params, starpilot_toggles):
  params.put("LastGPSPosition", json.dumps(starpilot_planner.gps_position))

  if starpilot_toggles.lock_doors_timer != 0:
    thread_manager.run_with_lock(lock_doors, (starpilot_toggles.lock_doors_timer, sm, params), report=False)

  if starpilot_toggles.random_themes:
    theme_manager.update_active_theme(time_validated, starpilot_toggles, randomize_theme=True)

  if time_validated:
    thread_manager.run_with_lock(send_stats)

def transition_onroad(error_log):
  if error_log.is_file():
    error_log.unlink()

def update_checks(now, model_manager, theme_manager, thread_manager, params, params_memory, starpilot_toggles, boot_run=False):
  while not (is_url_pingable("https://github.com") or is_url_pingable("https://gitlab.com")):
    time.sleep(60)

  model_manager.update_models(boot_run)
  theme_manager.update_themes(starpilot_toggles, boot_run)

  thread_manager.run_with_lock(update_maps, (now, params, params_memory))

  if starpilot_toggles.automatic_updates:
    thread_manager.run_with_lock(update_openpilot, (thread_manager, params))

  time.sleep(1)

def update_toggles(starpilot_variables, started, theme_manager, thread_manager, time_validated, params, starpilot_toggles):
  previous_holiday_themes = starpilot_toggles.holiday_themes
  previous_random_themes = starpilot_toggles.random_themes

  starpilot_variables.update(theme_manager.holiday_theme, started)
  starpilot_toggles = starpilot_variables.starpilot_toggles

  randomize_theme = starpilot_toggles.holiday_themes != previous_holiday_themes
  randomize_theme |= starpilot_toggles.random_themes != previous_random_themes

  theme_manager.theme_updated = False
  theme_manager.update_active_theme(time_validated, starpilot_toggles, randomize_theme=randomize_theme)

  return starpilot_toggles

def starpilot_thread():
  rate_keeper = Ratekeeper(1 / DT_MDL, None)

  config_realtime_process(5, Priority.CTRL_LOW)

  pm = messaging.PubMaster(["starpilotPlan"])
  sm = messaging.SubMaster(["carControl", "carState", "controlsState", "deviceState", "driverMonitoringState",
                            "gpsLocation", "gpsLocationExternal", "liveParameters", "managerState", "modelV2",
                            "onroadEvents", "pandaStates", "radarState", "selfdriveState", "starpilotCarState",
                            "starpilotSelfdriveState", "starpilotModelV2", "starpilotOnroadEvents", "mapdOut"],
                            poll="modelV2")

  params = Params(return_defaults=True)
  params_raw = Params()
  params_memory = Params(memory=True)

  starpilot_variables = StarPilotVariables()
  model_manager = ModelManager(params, params_memory)
  theme_manager = ThemeManager(params, params_memory)
  thread_manager = ThreadManager()

  starpilot_toggles = starpilot_variables.starpilot_toggles

  drive_stats_session = requests.Session()
  next_drive_stats_sync = 0.0
  periodic_update_phase = get_update_check_phase_seconds(params_raw)
  next_periodic_update_check = get_next_periodic_update_check(time.monotonic(), periodic_update_phase)

  run_update_checks = False
  safe_mode_active = safe_mode_enabled(params_raw)
  started_previously = False
  time_validated = False

  error_log = ERROR_LOGS_PATH / "error.txt"
  if error_log.is_file():
    error_log.unlink()

  if safe_mode_active:
    apply_safe_mode(params, params_raw, params_memory)

  while True:
    sm.update()

    now = datetime.datetime.now(datetime.timezone.utc)
    monotonic_now = time.monotonic()

    started = sm["deviceState"].started

    if not started and started_previously:
      starpilot_planner.shutdown()

      starpilot_toggles = update_toggles(starpilot_variables, started, theme_manager, thread_manager, time_validated, params, starpilot_toggles)
      transition_offroad(starpilot_planner, theme_manager, thread_manager, time_validated, sm, params, starpilot_toggles)

      run_update_checks = True
    elif started and not started_previously:
      starpilot_planner = StarPilotPlanner(error_log, theme_manager)
      starpilot_tracking = StarPilotTracking(starpilot_planner, starpilot_toggles)

      transition_onroad(error_log)

    if started and sm.updated["modelV2"]:
      starpilot_planner.update(now, time_validated, sm, starpilot_toggles)
      starpilot_planner.publish(theme_manager.theme_updated, sm, pm, starpilot_toggles)

      starpilot_tracking.update(now, time_validated, sm, starpilot_toggles)
    elif not started:
      starpilot_plan_send = messaging.new_message("starpilotPlan")
      starpilot_plan_send.starpilotPlan.starpilotToggles = json.dumps(vars(starpilot_toggles))
      starpilot_plan_send.starpilotPlan.themeUpdated = theme_manager.theme_updated
      pm.send("starpilotPlan", starpilot_plan_send)

    started_previously = started

    if not started and time_validated and sm["deviceState"].screenBrightnessPercent > 0:
      if monotonic_now >= next_drive_stats_sync:
        thread_manager.run_with_lock(sync_drive_stats, (params, drive_stats_session), report=False)
        next_drive_stats_sync = monotonic_now + DRIVE_STATS_SYNC_RATE
    elif started:
      next_drive_stats_sync = 0.0

    if rate_keeper.frame % ASSET_CHECK_RATE == 0:
      check_assets(now, model_manager, theme_manager, thread_manager, params, params_memory, starpilot_toggles)

    current_safe_mode = safe_mode_enabled(params_raw)
    safe_mode_changed = current_safe_mode != safe_mode_active
    if safe_mode_changed:
      if current_safe_mode:
        apply_safe_mode(params, params_raw, params_memory)
      else:
        restore_safe_mode(params_raw, params_memory)
      safe_mode_active = current_safe_mode
    elif current_safe_mode and (params_memory.get_bool("StarPilotTogglesUpdated") or rate_keeper.frame % SAFE_MODE_ENFORCE_FRAMES == 0):
      apply_safe_mode(params, params_raw, params_memory, ensure_backup=False)

    if params_memory.get_bool("StarPilotTogglesUpdated") or theme_manager.theme_updated:
      starpilot_toggles = update_toggles(starpilot_variables, started, theme_manager, thread_manager, time_validated, params, starpilot_toggles)

    periodic_update_due = monotonic_now >= next_periodic_update_check
    if periodic_update_due:
      next_periodic_update_check = get_next_periodic_update_check(monotonic_now, periodic_update_phase)

    run_update_checks |= params_memory.get_bool("ManualUpdateInitiated")
    run_update_checks |= periodic_update_due
    run_update_checks &= time_validated

    if run_update_checks:
      theme_manager.update_active_theme(time_validated, starpilot_toggles)
      thread_manager.run_with_lock(update_checks, (now, model_manager, theme_manager, thread_manager, params, params_memory, starpilot_toggles))

      run_update_checks = False
    elif not time_validated:
      time_validated = system_time_valid()
      if not time_validated:
        continue

      theme_manager.update_active_theme(time_validated, starpilot_toggles)

      if not started:
        thread_manager.run_with_lock(send_stats)
      thread_manager.run_with_lock(update_checks, (now, model_manager, theme_manager, thread_manager, params, params_memory, starpilot_toggles, True))

    rate_keeper.keep_time()

def main():
  starpilot_thread()

if __name__ == "__main__":
  main()
