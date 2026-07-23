#!/usr/bin/env python3
import dataclasses
import json
import math
import numpy as np
import os
import requests
import shutil
import subprocess
import threading
import time
import zipfile

from functools import cache
from pathlib import Path

from cereal import log, messaging
from opendbc.can.parser import CANParser
from opendbc.car.toyota.carcontroller import LOCK_CMD
from openpilot.common.params import Params
from openpilot.common.realtime import DT_DMON, DT_HW
from openpilot.system.hardware import HARDWARE
from openpilot.system.version import get_build_metadata
from panda import Panda, FW_PATH

from openpilot.starpilot.common.starpilot_variables import EARTH_RADIUS, STARPILOT_API, FROGS_GO_MOO_PATH, KONIK_PATH

DEVICE_BUSY_MAX_CPU_USAGE_PERCENT = 89.0
DEVICE_BUSY_AVG_CPU_USAGE_PERCENT = 74.0
DEVICE_BUSY_HOT_CORE_COUNT = 4

_throttle_state: dict[str, dict] = {}


def capture_exception(exception):
  try:
    import openpilot.system.sentry as sentry
    sentry.capture_exception(exception)
  except Exception:
    pass


class ThreadManager:
  def __init__(self):
    self.thread_lock = threading.Lock()

    self.running_threads = {}

  def run_with_lock(self, target, args=(), report=True):
    name = target.__name__

    if not isinstance(args, (tuple, list)):
      args = (args,)

    with self.thread_lock:
      dead_threads = [key for key, thread in self.running_threads.items() if not thread.is_alive()]
      for key in dead_threads:
        del self.running_threads[key]

      if name in self.running_threads and self.running_threads[name].is_alive():
        return

      def wrapped_target(*t_args):
        try:
          target(*t_args)
        except Exception as exception:
          print(f"Error in thread '{name}': {exception}")
          if report:
            capture_exception(exception)

      thread = threading.Thread(args=args, daemon=True, target=wrapped_target)
      thread.start()
      self.running_threads[name] = thread

  def is_thread_alive(self, name):
    with self.thread_lock:
      thread = self.running_threads.get(name)
      return thread is not None and thread.is_alive()


def calculate_bearing_offset(latitude, longitude, current_bearing, distance):
  bearing = math.radians(current_bearing)
  lat_rad = math.radians(latitude)
  lon_rad = math.radians(longitude)

  delta = distance / EARTH_RADIUS

  new_lat = math.asin(math.sin(lat_rad) * math.cos(delta) + math.cos(lat_rad) * math.sin(delta) * math.cos(bearing))
  new_lon = lon_rad + math.atan2(math.sin(bearing) * math.sin(delta) * math.cos(lat_rad),  math.cos(delta) - math.sin(lat_rad) * math.sin(new_lat))
  return math.degrees(new_lat), math.degrees(new_lon)


def calculate_distance_to_point(lat1, lon1, lat2, lon2):
  lat1_rad = math.radians(lat1)
  lon1_rad = math.radians(lon1)
  lat2_rad = math.radians(lat2)
  lon2_rad = math.radians(lon2)

  delta_lat = lat2_rad - lat1_rad
  delta_lon = lon2_rad - lon1_rad

  a = (math.sin(delta_lat / 2) ** 2) + math.cos(lat1_rad) * math.cos(lat2_rad) * (math.sin(delta_lon / 2) ** 2)
  c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

  return EARTH_RADIUS * c


def calculate_lane_width(lane_line1, lane_line2, road_edge=None):
  lane_line1_x = np.asarray(lane_line1.x)
  lane_line1_y = np.asarray(lane_line1.y)

  lane_line2_x = np.asarray(lane_line2.x)
  lane_line2_y = np.asarray(lane_line2.y)

  lane_y_interp = np.interp(lane_line2_x, lane_line1_x, lane_line1_y)
  distance_to_lane = np.median(np.abs(lane_line2_y - lane_y_interp))

  if road_edge is None:
    return float(distance_to_lane)

  edge_line_x = np.asarray(road_edge.x)
  edge_line_y = np.asarray(road_edge.y)

  edge_y_interp = np.interp(lane_line2_x, edge_line_x, edge_line_y)
  distance_to_road_edge = np.median(np.abs(lane_line2_y - edge_y_interp))

  if distance_to_road_edge < distance_to_lane:
    return 0.0

  return float(distance_to_lane)


# Credit goes to Pfeiferj!
def calculate_road_curvature(modelData, v_ego):
  orientation_rate = np.array(modelData.orientationRate.z)
  timebase = np.array(modelData.orientationRate.t)
  velocity = np.array(modelData.velocity.x)

  lateral_acceleration = orientation_rate * velocity
  index = np.argmax(np.abs(lateral_acceleration))
  predicted_lateral_acc = float(lateral_acceleration[index])
  time_to_curve = float(timebase[index])

  return float(predicted_lateral_acc / max(v_ego, 1)**2), max(time_to_curve, 1)


def clean_model_name(name):
  return name.replace("(Default)", "").strip()


def contains_event_type(events, starpilot_events, *event_types):
  return any(events.contains(event_type) or starpilot_events.contains(event_type) for event_type in event_types)


def delete_file(path, print_error=True, report=True):
  path = Path(path)
  if path.is_file() or path.is_symlink():
    try:
      path.unlink(missing_ok=True)
      print(f"Deleted file: {path}")
    except Exception:
      run_cmd(["sudo", "rm", "-f", str(path)], f"Deleted file: {path}", f"Failed to delete file: {path}", report=report)
  elif path.is_dir():
    try:
      shutil.rmtree(path)
      print(f"Deleted directory: {path}")
    except Exception:
      run_cmd(["sudo", "rm", "-rf", str(path)], f"Deleted directory: {path}", f"Failed to delete directory: {path}", report=report)
  elif print_error:
    print(f"File not found: {path}")


def extract_zip(zip_file, extract_path):
  with zipfile.ZipFile(zip_file, "r") as zip:
    print(f"Extracting {zip_file} to {extract_path}")
    zip.extractall(extract_path)

  zip_file.unlink()
  print(f"Extraction completed!")


def get_selected_panda_firmware_name(app_fn, remote_start, hkg_remote_start, ignore_ignition_line):
  if not remote_start and not hkg_remote_start and not ignore_ignition_line:
    return app_fn

  h7 = app_fn == "panda_h7.bin.signed"
  name_parts = ["panda_h7" if h7 else "panda"]
  if hkg_remote_start:
    name_parts.extend(["hkg", "remote"])
  elif remote_start:
    name_parts.append("remote")
  if ignore_ignition_line:
    name_parts.append("can_ignition_only")
  return "_".join(name_parts) + ".bin.signed"


def flash_panda(params_memory):
  params = Params()
  try:
    remote_start = params.get_bool("RemoteStartBootsComma")
  except Exception:
    remote_start = False
  try:
    hkg_remote_start = params.get_bool("HKGRemoteStartBootsComma")
  except Exception:
    hkg_remote_start = False
  try:
    ignore_ignition_line = params.get_bool("IgnoreIgnitionLine")
  except Exception:
    ignore_ignition_line = False

  for serial in Panda.list():
    try:
      with Panda(serial=serial) as panda:
        print(f"Flashing Panda {serial}")
        flash_fn = None
        app_fn = panda.get_mcu_type().config.app_fn
        selected_fn = get_selected_panda_firmware_name(app_fn, remote_start, hkg_remote_start, ignore_ignition_line)
        if selected_fn != app_fn:
          candidate = os.path.join(FW_PATH, selected_fn)
          if os.path.isfile(candidate):
            flash_fn = candidate
          else:
            print(f"Selected panda firmware missing: {candidate}. Falling back to default firmware.")
        panda.flash(fn=flash_fn)
    except Exception as exception:
      print(f"Failed to flash Panda {serial}: {exception}")
      capture_exception(exception)

  params_memory.remove("FlashPanda")


def get_starpilot_api_info():
  params = Params()

  api_token = params.get("StarPilotApiToken")
  build_metadata = dataclasses.asdict(get_build_metadata())
  device_type = HARDWARE.get_device_type()
  dongle_id = params.get("StarPilotDongleId")

  return api_token, build_metadata, device_type, dongle_id


def get_lock_status(can_parser, can_sock):
  update_can_parser(can_parser, can_sock)
  return can_parser.vl["DOOR_LOCKS"]["LOCK_STATUS"]


def get_sentry_dsn():
  try:
    api_token, build_metadata, device_type, dongle_id = get_starpilot_api_info()

    payload = {
      "api_token": api_token,
      "build_metadata": build_metadata,
      "device": device_type,
      "starpilot_dongle_id": dongle_id,
    }

    response = requests.post(f"{STARPILOT_API}/sentry", json=payload, headers={"Content-Type": "application/json", "User-Agent": "starpilot-api/1.0"}, timeout=10)
    response.raise_for_status()
    return response.json().get("dsn", "")
  except Exception:
    return ""


@cache
def is_FrogsGoMoo():
  return FROGS_GO_MOO_PATH.is_file()


def is_url_pingable(url):
  if not url:
    return False

  if not hasattr(is_url_pingable, "session"):
    is_url_pingable.session = requests.Session()
    is_url_pingable.session.headers.update({"User-Agent": "starpilot-ping-test/1.0 (https://github.com/FrogAi/StarPilot)"})

  try:
    response = is_url_pingable.session.head(url, timeout=10, allow_redirects=True)
    if response.status_code in (405, 501):
      response = is_url_pingable.session.get(url, timeout=10, allow_redirects=True, stream=True)

    is_accessible = response.ok
    response.close()
    return is_accessible

  except (requests.exceptions.ConnectionError, requests.exceptions.SSLError):
    return False
  except requests.exceptions.RequestException as error:
    print(f"{error.__class__.__name__} while pinging {url}: {error}")
    return False
  except Exception as exception:
    print(f"Unexpected error while pinging {url}: {exception}")
    return False


def load_json_file(path):
  if path.is_file():
    try:
      with open(path) as file:
        return json.load(file)
    except json.JSONDecodeError:
      print(f"Failed to load JSON file: {path}")
      return {}
  return {}


def lock_doors(lock_doors_timer, sm, params):
  wait_for_no_driver(params, sm, door_checks=True, time_threshold=lock_doors_timer)

  sm.update()
  if any(ps.ignitionLine or ps.ignitionCan for ps in sm["pandaStates"] if ps.pandaType != log.PandaState.PandaType.unknown):
    return

  can_parser = CANParser("toyota_nodsu_pt_generated", [("DOOR_LOCKS", 3)], bus=0)
  can_sock = messaging.sub_sock("can", timeout=100)

  pm = messaging.PubMaster(["sendcan"])

  while True:
    sm.update()

    if any(ps.ignitionLine or ps.ignitionCan for ps in sm["pandaStates"] if ps.pandaType != log.PandaState.PandaType.unknown):
      break

    sendcan_send = messaging.new_message("sendcan", 1)
    sendcan_send.sendcan[0].address = 0x750
    sendcan_send.sendcan[0].dat = LOCK_CMD
    sendcan_send.sendcan[0].src = 0
    pm.send("sendcan", sendcan_send)

    time.sleep(1)

    lock_status = get_lock_status(can_parser, can_sock)
    if lock_status == 0:
      break


def run_cmd(cmd, success_message, fail_message, env=None, report=True):
  try:
    result = subprocess.run(cmd, capture_output=True, check=True, env=env, text=True)
    print(success_message)
    return result.stdout.strip()
  except subprocess.CalledProcessError as exception:
    print(f"Command failed with error: {exception.stderr}")
    print(fail_message)
    if report:
      capture_exception(exception.stderr)
    return None
  except Exception as exception:
    print(f"Unexpected error occurred: {exception}")
    print(fail_message)
    if report:
      capture_exception(exception)
    return None


def update_can_parser(can_parser, can_sock):
  can_msgs = messaging.drain_sock(can_sock, wait_for_one=True)
  can_parser.update([(msg.logMonoTime, [[frame.address, frame.dat, frame.src] for frame in msg.can]) for msg in can_msgs if msg.which() == "can"])


def update_json_file(path, data):
  temp_path = f"{path}.tmp"
  with open(temp_path, "w") as file:
    json.dump(data, file, indent=2, sort_keys=True)
    file.flush()
    os.fsync(file.fileno())

  os.replace(temp_path, path)


@cache
def use_konik_server():
  # Prefer the persistent toggle over volatile cache files.
  return Params().get_bool("UseKonikServer")


def wait_for_no_driver(params, sm, door_checks=False, time_threshold=60):
  can_parser = CANParser("toyota_nodsu_pt_generated", [("BODY_CONTROL_STATE", 3)], bus=0)
  can_sock = messaging.sub_sock("can", timeout=100)

  while sm["deviceState"].screenBrightnessPercent != 0 or any(proc.name == "dmonitoringd" and proc.running for proc in sm["managerState"].processes):
    sm.update()

    if any(ps.ignitionLine or ps.ignitionCan for ps in sm["pandaStates"] if ps.pandaType != log.PandaState.PandaType.unknown):
      return

    time.sleep(DT_HW)

  params.put_bool("IsDriverViewEnabled", True)

  while not any(proc.name == "dmonitoringd" and proc.running for proc in sm["managerState"].processes):
    sm.update()

    time.sleep(DT_HW)

  start_time = time.monotonic()
  while True:
    sm.update()

    elapsed_time = time.monotonic() - start_time
    if elapsed_time >= time_threshold:
      break

    if any(ps.ignitionLine or ps.ignitionCan for ps in sm["pandaStates"] if ps.pandaType != log.PandaState.PandaType.unknown):
      break

    if sm["driverMonitoringState"].visionPolicyState.faceDetected or not sm.alive["driverMonitoringState"]:
      start_time = time.monotonic()

    if door_checks:
      update_can_parser(can_parser, can_sock)

      door_open = any([can_parser.vl["BODY_CONTROL_STATE"]["DOOR_OPEN_FL"], can_parser.vl["BODY_CONTROL_STATE"]["DOOR_OPEN_FR"],
                       can_parser.vl["BODY_CONTROL_STATE"]["DOOR_OPEN_RL"], can_parser.vl["BODY_CONTROL_STATE"]["DOOR_OPEN_RR"]])
      if door_open:
        start_time = time.monotonic()

    time.sleep(DT_DMON)

  params.remove("IsDriverViewEnabled")


def device_cpu_throttle_factor(cpu_usage, name="SpeedLimit"):
  """Smooth low-pass filtered CPU throttle controller."""
  usage = list(cpu_usage)
  if not usage:
    return 1.0

  now = time.monotonic()
  key = "_shared"
  if key not in _throttle_state:
    _throttle_state[key] = {
      "factor": 1.0,
      "last_time": now,
      "last_logged_factor": 1.0,
    }

  state = _throttle_state[key]
  dt = max(0.0, now - state["last_time"])
  state["last_time"] = now

  avg = sum(usage) / len(usage)
  hot_cores = sum(c >= DEVICE_BUSY_MAX_CPU_USAGE_PERCENT for c in usage)

  target_factor = _compute_throttle_factor(avg, hot_cores)

  # Low-pass filter (rate = 0.8): smooths out 100ms background system spikes
  rate = 0.8
  alpha = 1.0 - math.exp(-rate * dt)
  alpha = min(alpha, 1.0)
  state["factor"] = target_factor * alpha + state["factor"] * (1.0 - alpha)
  state["factor"] = max(1.0, min(5.0, state["factor"]))

  if state["factor"] >= state["last_logged_factor"] + 0.6:
    print(f"[{name}] CPU throttle factor={state['factor']:.1f}x (avg={avg:.0f}%, hot={hot_cores})")
    state["last_logged_factor"] = state["factor"]
  elif state["factor"] <= 1.05 and state["last_logged_factor"] > 1.05:
    print(f"[{name}] CPU recovered")
    state["last_logged_factor"] = 1.0

  return state["factor"]


def _compute_throttle_factor(avg, hot_cores):
  if avg < DEVICE_BUSY_AVG_CPU_USAGE_PERCENT:
    avg_factor = 1.0
  else:
    avg_factor = 1.0 + (avg - DEVICE_BUSY_AVG_CPU_USAGE_PERCENT) / 8.0

  hot_factor = 1.0 + max(0, hot_cores - DEVICE_BUSY_HOT_CORE_COUNT + 1) * 0.5
  return min(max(avg_factor, hot_factor), 4.0)