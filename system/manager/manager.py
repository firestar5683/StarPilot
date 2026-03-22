#!/usr/bin/env python3
import datetime
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

from cereal import car, log
import cereal.messaging as messaging
import openpilot.system.sentry as sentry
from openpilot.common.utils import atomic_write
from openpilot.common.params import Params, ParamKeyFlag, ParamKeyType
from openpilot.common.text_window import TextWindow
from openpilot.system.hardware import HARDWARE
from openpilot.system.manager.helpers import unblock_stdout, write_onroad_params, save_bootlog
from openpilot.system.manager.process import ensure_running
from openpilot.system.manager.process_config import managed_processes
from openpilot.system.athena.registration import register, UNREGISTERED_DONGLE_ID
from openpilot.common.swaglog import cloudlog, add_file_handler
from openpilot.system.version import get_build_metadata, terms_version, training_version
from openpilot.system.hardware.hw import Paths

from openpilot.frogpilot.common.frogpilot_functions import frogpilot_boot_functions, install_frogpilot, uninstall_frogpilot
from openpilot.frogpilot.common.frogpilot_variables import get_frogpilot_toggles


LEGACY_BOLT_FP_MIGRATION_FLAG = Path("/data") / "legacy_bolt_fp_migration_v1"
STARPILOT_DEFAULTS_PARITY_MIGRATION_FLAG = Path("/data") / "starpilot_defaults_parity_v1"
STARPILOT_PARAM_CANONICALIZATION_MIGRATION_FLAG = Path("/data") / "starpilot_param_canonicalization_v1"
LEGACY_CARMODEL_MIGRATIONS = {
  "CHEVROLET_BOLT_CC_2019_2021": "CHEVROLET_BOLT_CC_2018_2021",
}


def _to_text(value):
  if value is None:
    return None
  if isinstance(value, bytes):
    return value.decode("utf-8", errors="ignore")
  return str(value)


def migrate_legacy_bolt_fingerprint(params: Params) -> None:
  old_fp, new_fp = next(iter(LEGACY_CARMODEL_MIGRATIONS.items()))
  carparams_keys = ("CarParams", "CarParamsCache", "CarParamsPersistent", "CarParamsPrevRoute")
  keys_to_clear = (
    "CarParams",
    "CarParamsCache",
    "CarParamsPersistent",
    "CarParamsPrevRoute",
    "FrogPilotCarParams",
    "FrogPilotCarParamsPersistent",
  )

  car_model = _to_text(params.get("CarModel"))
  legacy_detected = car_model == old_fp
  if not legacy_detected:
    old_fp_bytes = old_fp.encode()
    for key in carparams_keys:
      raw = params.get(key)
      if raw is None:
        continue

      raw_bytes = raw if isinstance(raw, bytes) else str(raw).encode()
      # Fast path for payloads that still embed the legacy fingerprint string.
      if old_fp_bytes in raw_bytes:
        legacy_detected = True
        break

      # Fallback decode for payloads that don't expose the raw string directly.
      try:
        with car.CarParams.from_bytes(raw_bytes) as cp:
          if cp.carFingerprint == old_fp:
            legacy_detected = True
            break
      except Exception:
        continue

  if not legacy_detected:
    return

  cleared_keys: list[str] = []
  for key in keys_to_clear:
    if params.get(key) is None:
      continue
    params.remove(key)
    cleared_keys.append(key)

  if car_model == old_fp:
    params.put("CarModel", new_fp)
  car_model_name = _to_text(params.get("CarModelName")) or ""
  if "2019-21" in car_model_name:
    params.put("CarModelName", car_model_name.replace("2019-21", "2018-21"))

  cloudlog.warning(
    f"Detected legacy Bolt fingerprint {old_fp}; cleared={cleared_keys}, remapped CarModel to {new_fp}"
  )

  try:
    LEGACY_BOLT_FP_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    LEGACY_BOLT_FP_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {LEGACY_BOLT_FP_MIGRATION_FLAG}")


def migrate_starpilot_default_parity(params: Params, params_cache: Params) -> None:
  if STARPILOT_DEFAULTS_PARITY_MIGRATION_FLAG.exists():
    return

  desired_bool_values = {
    "AdvancedLateralTune": True,
    "ForceAutoTuneOff": True,
    "HumanAcceleration": False,
    "HumanFollowing": False,
    "NNFF": False,
    "NNFFLite": False,
  }

  for key, value in desired_bool_values.items():
    params.put_bool(key, value)
    params_cache.put_bool(key, value)

  params.put_float("CEModelStopTime", 7.0)
  params_cache.put_float("CEModelStopTime", 7.0)

  cloudlog.warning("Applied one-time StarPilot default parity migration for lateral/longitudinal toggles")

  try:
    STARPILOT_DEFAULTS_PARITY_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STARPILOT_DEFAULTS_PARITY_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {STARPILOT_DEFAULTS_PARITY_MIGRATION_FLAG}")


def _read_raw_param_bytes(params: Params, key: str | bytes):
  try:
    path = params.get_param_path(key)
  except Exception:
    return None

  if not path or not os.path.isfile(path):
    return None

  try:
    with open(path, "rb") as f:
      return f.read()
  except Exception:
    return None


def _parse_legacy_time(raw_text: str):
  text = raw_text.strip()
  if not text:
    return None

  try:
    return datetime.datetime.fromisoformat(text)
  except ValueError:
    pass

  for fmt in ("%B %d, %Y - %I:%M%p", "%B %d, %Y - %I:%M %p"):
    try:
      return datetime.datetime.strptime(text, fmt)
    except ValueError:
      continue

  return None


def migrate_param_type_canonicalization(params: Params) -> None:
  if STARPILOT_PARAM_CANONICALIZATION_MIGRATION_FLAG.exists():
    return

  normalized_keys: list[str] = []

  for raw_key in params.all_keys():
    key = raw_key.decode() if isinstance(raw_key, bytes) else str(raw_key)
    raw_value = _read_raw_param_bytes(params, raw_key)
    if not raw_value:
      continue

    try:
      text_value = raw_value.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError:
      continue

    if not text_value:
      continue

    try:
      expected_type = params.get_type(raw_key)
    except Exception:
      continue

    try:
      if expected_type == ParamKeyType.INT:
        parsed = float(text_value)
        # Canonicalize decimal/exponent forms into integer storage.
        canonical = str(int(parsed))
        if canonical != text_value:
          params.put_int(raw_key, int(parsed))
          normalized_keys.append(key)

      elif expected_type == ParamKeyType.FLOAT:
        parsed = float(text_value)
        canonical = str(parsed)
        if canonical != text_value:
          params.put_float(raw_key, parsed)
          normalized_keys.append(key)

      elif expected_type == ParamKeyType.BOOL:
        lowered = text_value.lower()
        if lowered in ("1", "true", "yes", "on"):
          if text_value != "1":
            params.put_bool(raw_key, True)
            normalized_keys.append(key)
        elif lowered in ("0", "false", "no", "off"):
          if text_value != "0":
            params.put_bool(raw_key, False)
            normalized_keys.append(key)

      elif expected_type == ParamKeyType.TIME:
        dt = _parse_legacy_time(text_value)
        if dt is not None:
          if dt.tzinfo is not None:
            dt = dt.astimezone(datetime.UTC).replace(tzinfo=None)
          if text_value != dt.isoformat():
            params.put(raw_key, dt)
            normalized_keys.append(key)

      elif expected_type == ParamKeyType.JSON:
        parsed = json.loads(text_value)
        canonical = json.dumps(parsed, separators=(",", ":"))
        if canonical != text_value:
          params.put(raw_key, parsed)
          normalized_keys.append(key)
    except Exception:
      continue

  if normalized_keys:
    cloudlog.warning(f"Canonicalized legacy param values for {len(normalized_keys)} keys")

  try:
    STARPILOT_PARAM_CANONICALIZATION_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STARPILOT_PARAM_CANONICALIZATION_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {STARPILOT_PARAM_CANONICALIZATION_MIGRATION_FLAG}")


def migrate_legacy_experimental_longitudinal(params: Params, params_cache: Params) -> None:
  legacy_value = params.get("ExperimentalLongitudinalEnabled")
  if legacy_value is None:
    return

  if params.get("AlphaLongitudinalEnabled") is None:
    alpha_long_enabled = params.get_bool("ExperimentalLongitudinalEnabled")
    params.put_bool("AlphaLongitudinalEnabled", alpha_long_enabled)
    params_cache.put_bool("AlphaLongitudinalEnabled", alpha_long_enabled)
    cloudlog.warning("Migrated legacy ExperimentalLongitudinalEnabled to AlphaLongitudinalEnabled")

  params.remove("ExperimentalLongitudinalEnabled")
  params_cache.remove("ExperimentalLongitudinalEnabled")


def manager_init() -> None:
  save_bootlog()

  build_metadata = get_build_metadata()

  params = Params()
  params.clear_all(ParamKeyFlag.CLEAR_ON_MANAGER_START)
  params.clear_all(ParamKeyFlag.CLEAR_ON_ONROAD_TRANSITION)
  params.clear_all(ParamKeyFlag.CLEAR_ON_OFFROAD_TRANSITION)
  params.clear_all(ParamKeyFlag.CLEAR_ON_IGNITION_ON)
  if build_metadata.release_channel:
    params.clear_all(ParamKeyFlag.DEVELOPMENT_ONLY)

  if params.get_bool("RecordFrontLock"):
    params.put_bool("RecordFront", True)

  # FrogPilot variables
  cache_params_path = "/cache/params"
  if HARDWARE.get_device_type() == "pc":
    cache_params_path = os.path.join(Paths.comma_home(), "cache", "params")
  params_cache = Params(cache_params_path, return_defaults=True)

  # Preserve StarPilot's legacy longitudinal toggle when switching branches.
  migrate_legacy_experimental_longitudinal(params, params_cache)

  # Canonicalize legacy string encodings (e.g. INT params stored as "26.000000")
  # before bulk reads below to avoid repeated cast warnings and UI-side churn.
  migrate_param_type_canonicalization(params)

  # set unset params to their default value
  for k in params.all_keys():
    current_value = params.get(k)
    if current_value is None:
      cached_value = params_cache.get(k)
      if cached_value is not None:
        params.put(k, cached_value)
    else:
      params_cache.put(k, current_value)

  # Create folders needed for msgq
  try:
    os.mkdir(Paths.shm_path())
  except FileExistsError:
    pass
  except PermissionError:
    print(f"WARNING: failed to make {Paths.shm_path()}")

  # set params
  serial = HARDWARE.get_serial()
  params.put("Version", build_metadata.openpilot.version)
  params.put("TermsVersion", terms_version)
  params.put("TrainingVersion", training_version)
  params.put("GitCommit", build_metadata.openpilot.git_commit)
  params.put("GitCommitDate", build_metadata.openpilot.git_commit_date)
  params.put("GitBranch", build_metadata.channel)
  params.put("GitRemote", build_metadata.openpilot.git_origin)
  params.put_bool("IsTestedBranch", build_metadata.tested_channel)
  params.put_bool("IsReleaseBranch", build_metadata.release_channel)
  params.put("HardwareSerial", serial)

  # Branch migration: rename legacy Bolt fingerprint persisted in CarParams.
  migrate_legacy_bolt_fingerprint(params)
  migrate_starpilot_default_parity(params, params_cache)

  # set dongle id
  reg_res = register(show_spinner=True)
  if reg_res:
    dongle_id = reg_res
  else:
    raise Exception(f"Registration failed for device {serial}")
  os.environ['DONGLE_ID'] = dongle_id  # Needed for swaglog
  os.environ['GIT_ORIGIN'] = build_metadata.openpilot.git_normalized_origin # Needed for swaglog
  os.environ['GIT_BRANCH'] = build_metadata.channel # Needed for swaglog
  os.environ['GIT_COMMIT'] = build_metadata.openpilot.git_commit # Needed for swaglog

  if not build_metadata.openpilot.is_dirty:
    os.environ['CLEAN'] = '1'

  # init logging
  sentry.init(sentry.SentryProject.SELFDRIVE)
  cloudlog.bind_global(dongle_id=dongle_id,
                       version=build_metadata.openpilot.version,
                       origin=build_metadata.openpilot.git_normalized_origin,
                       branch=build_metadata.channel,
                       commit=build_metadata.openpilot.git_commit,
                       dirty=build_metadata.openpilot.is_dirty,
                       device=HARDWARE.get_device_type())

  # preimport all processes
  for p in managed_processes.values():
    p.prepare()

  # FrogPilot variables
  install_frogpilot(build_metadata, params)
  frogpilot_boot_functions(build_metadata, params)


def manager_cleanup() -> None:
  # send signals to kill all procs
  for p in managed_processes.values():
    p.stop(block=False)

  # ensure all are killed
  for p in managed_processes.values():
    p.stop(block=True)

  cloudlog.info("everything is dead")


def manager_thread() -> None:
  cloudlog.bind(daemon="manager")
  cloudlog.info("manager start")
  cloudlog.info({"environ": os.environ})

  params = Params()

  ignore: list[str] = []
  if params.get("DongleId") in (None, UNREGISTERED_DONGLE_ID):
    ignore += ["manage_athenad", "uploader"]
  if os.getenv("NOBOARD") is not None:
    ignore.append("pandad")
  ignore += [x for x in os.getenv("BLOCK", "").split(",") if len(x) > 0]

  sm = messaging.SubMaster(['deviceState', 'carParams', 'pandaStates'], poll='deviceState')
  pm = messaging.PubMaster(['managerState'])

  write_onroad_params(False, params)
  ensure_running(managed_processes.values(), False, params=params, CP=sm['carParams'], not_run=ignore, frogpilot_toggles=get_frogpilot_toggles())

  started_prev = False
  ignition_prev = False

  # FrogPilot variables
  sm = sm.extend(['frogpilotPlan'])

  params_memory = Params(memory=True)

  frogpilot_toggles = get_frogpilot_toggles()

  while True:
    sm.update(1000)

    started = sm['deviceState'].started

    if started and not started_prev and not frogpilot_toggles.force_onroad:
      params.clear_all(ParamKeyFlag.CLEAR_ON_ONROAD_TRANSITION)

      # FrogPilot variables
      params_memory.clear_all(ParamKeyFlag.CLEAR_ON_ONROAD_TRANSITION)
    elif not started and started_prev:
      params.clear_all(ParamKeyFlag.CLEAR_ON_OFFROAD_TRANSITION)

      # FrogPilot variables
      params_memory.clear_all(ParamKeyFlag.CLEAR_ON_OFFROAD_TRANSITION)

    ignition = any(ps.ignitionLine or ps.ignitionCan for ps in sm['pandaStates'] if ps.pandaType != log.PandaState.PandaType.unknown)
    if ignition and not ignition_prev:
      params.clear_all(ParamKeyFlag.CLEAR_ON_IGNITION_ON)

    # update onroad params, which drives pandad's safety setter thread
    if started != started_prev:
      write_onroad_params(started, params)

    started_prev = started
    ignition_prev = ignition

    ensure_running(managed_processes.values(), started, params=params, CP=sm['carParams'], not_run=ignore, frogpilot_toggles=frogpilot_toggles)

    running = ' '.join("{}{}\u001b[0m".format("\u001b[32m" if p.proc.is_alive() else "\u001b[31m", p.name)
                       for p in managed_processes.values() if p.proc)
    print(running)
    cloudlog.debug(running)

    # send managerState
    msg = messaging.new_message('managerState', valid=True)
    msg.managerState.processes = [p.get_process_state_msg() for p in managed_processes.values()]
    pm.send('managerState', msg)

    # kick AGNOS power monitoring watchdog
    try:
      if sm.all_checks(['deviceState']):
        with atomic_write("/var/tmp/power_watchdog", "w", overwrite=True) as f:
          f.write(str(time.monotonic()))
    except Exception:
      pass

    # Exit main loop when uninstall/shutdown/reboot is needed
    shutdown = False
    for param in ("DoUninstall", "DoShutdown", "DoReboot"):
      if params.get_bool(param):
        shutdown = True
        params.put("LastManagerExitReason", f"{param} {datetime.datetime.now()}")
        cloudlog.warning(f"Shutting down manager - {param} set")

    if shutdown:
      break

    # FrogPilot variables
    frogpilot_toggles = get_frogpilot_toggles(sm)


def main() -> None:
  manager_init()
  if os.getenv("PREPAREONLY") is not None:
    return

  # SystemExit on sigterm
  signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(1))

  try:
    manager_thread()
  except Exception:
    traceback.print_exc()
    sentry.capture_exception()
  finally:
    manager_cleanup()

  params = Params()
  if params.get_bool("DoUninstall"):
    cloudlog.warning("uninstalling")
    uninstall_frogpilot()
  elif params.get_bool("DoReboot"):
    cloudlog.warning("reboot")
    HARDWARE.reboot()
  elif params.get_bool("DoShutdown"):
    cloudlog.warning("shutdown")
    HARDWARE.shutdown()


if __name__ == "__main__":
  unblock_stdout()

  try:
    main()
  except KeyboardInterrupt:
    print("got CTRL-C, exiting")
  except Exception:
    add_file_handler(cloudlog)
    cloudlog.exception("Manager failed to start")

    try:
      managed_processes['ui'].stop()
    except Exception:
      pass

    # Show last 3 lines of traceback
    error = traceback.format_exc(-3)
    error = "Manager failed to start\n\n" + error
    with TextWindow(error) as t:
      t.wait_for_exit()

    raise

  # manual exit because we are forked
  sys.exit(0)
