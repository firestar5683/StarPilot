#!/usr/bin/env python3
import base64
import copy
import hashlib
import ipaddress
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time

from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from urllib.parse import quote

from openpilot.common.constants import CV
from openpilot.common.params import Params
from openpilot.system.hardware import HARDWARE
from openpilot.system.loggerd.config import get_available_bytes, get_used_bytes
from openpilot.system.loggerd.deleter import PRESERVE_ATTR_NAME, PRESERVE_ATTR_VALUE
from openpilot.system.loggerd.uploader import listdir_by_creation
from openpilot.tools.lib.route import SegmentName

from openpilot.starpilot.assets.model_manager import canonical_model_key
from openpilot.starpilot.common.starpilot_variables import THEME_SAVE_PATH, VIDEO_CACHE_PATH
from openpilot.starpilot.assets.theme_manager import HOLIDAY_THEME_PATH

LOG_CANDIDATES = [
  "qlog",
  "qlog.zst",
  "qlog.bz2",
  "rlog",
  "rlog.zst",
  "rlog.bz2",
  "raw_log.zst",
  "raw_log.bz2",
]

ROUTE_TIME_LOG_CANDIDATES = [
  "qlog.zst",
  "qlog.bz2",
  "qlog",
  "rlog.zst",
  "rlog.bz2",
  "rlog",
  "raw_log.zst",
  "raw_log.bz2",
]

SEGMENT_RE = re.compile(r"^[0-9a-fA-F]{8}--[0-9a-fA-F]{10}--\d+$")
ROUTE_RE = re.compile(r"^[0-9a-fA-F]{8}--[0-9a-fA-F]{10}$")

TARGET_LOUDNESS = -15.0
METER_TO_MILE = 1.0 / 1609.344
METER_TO_KILOMETER = 0.001
MILE_TO_KILOMETER = CV.MPH_TO_KPH
METER_PER_SECOND_TO_MPH = CV.MS_TO_KPH * CV.KPH_TO_MPH

DASHBOARD_CACHE_TTL_SECONDS = 5.0
DASHBOARD_ROUTE_SCAN_LIMIT = 96
DASHBOARD_ROUTE_ANALYSIS_LIMIT = 0
DASHBOARD_ANALYSIS_TIME_BUDGET_SECONDS = 0.0
DASHBOARD_BACKGROUND_ROUTE_ANALYSIS_LIMIT = 5
DASHBOARD_RECENT_DRIVE_LIMIT = 5
DASHBOARD_ROUTE_SEGMENT_SAMPLE_LIMIT = 2
DASHBOARD_PERSISTED_ROUTE_LIMIT = 5000
DASHBOARD_PERSIST_MIN_ROUTE_AGE_SECONDS = 120
DASHBOARD_PERSISTENT_STATS_PARAM = "GalaxyDashboardStats"
DASHBOARD_ROUTE_ANALYSIS_VERSION = 4
DASHBOARD_PARAMS_DIR = Path("/data/params/d")
DASHBOARD_ANALYZER_LOG_PATH = "/tmp/galaxy_dashboard_analyzer.log"
DASHBOARD_ANALYZER_STATUS_PATH = Path("/tmp/galaxy_dashboard_analyzer_status.json")
DASHBOARD_ANALYZER_STATUS_MAX_AGE_SECONDS = 30 * 60
DASHBOARD_TOP_MODEL_LIMIT = 3
LAN_IP_CACHE_TTL_SECONDS = 10.0
NETWORK_STATUS_CACHE_TTL_SECONDS = 10.0
DASHBOARD_EVENT_DISTRACTED = "driverDistracted2"
DASHBOARD_EVENT_UNRESPONSIVE = "driverUnresponsive3"
DASHBOARD_TIME_SOURCE_LOG = "log"
DASHBOARD_TIME_SOURCE_FILESYSTEM = "filesystem"
DASHBOARD_MIN_VALID_ROUTE_TIME = datetime(2026, 1, 1)
DASHBOARD_ROUTE_FUTURE_GRACE_SECONDS = 6 * 60 * 60
DASHBOARD_LOCAL_ROUTE_MAX_AGE_SECONDS = 45 * 24 * 60 * 60
DASHBOARD_ROUTE_TIME_REPAIR_THRESHOLD_SECONDS = 5 * 60

XOR_KEY = "s8#pL3*Xj!aZ@dWq"

MAX_FILE_SIZE = 5 * 1024 * 1024

_FILENAME_SANITIZE_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_GALAXY_DEPS_PATH = "/data/galaxy_deps"
_LEGACY_GALAXY_DEPS_PATH = "/data/" + "".join(chr(code) for code in (112, 111, 110, 100)) + "_deps"
for deps_path in (_GALAXY_DEPS_PATH, _LEGACY_GALAXY_DEPS_PATH):
  if os.path.isdir(deps_path) and deps_path not in sys.path:
    sys.path.insert(0, deps_path)
_REPO_THIRD_PARTY_PATH = Path(__file__).resolve().parents[2] / "third_party"
if _REPO_THIRD_PARTY_PATH.is_dir() and str(_REPO_THIRD_PARTY_PATH) not in sys.path:
  sys.path.insert(0, str(_REPO_THIRD_PARTY_PATH))

_PIL_IMAGE = None
_PYDUB_AUDIOSEGMENT = None
_DASHBOARD_CACHE = {
  "key": None,
  "updated_at": 0.0,
  "value": None,
}
_LAN_IP_CACHE = {
  "updated_at": 0.0,
  "value": None,
}
_NETWORK_STATUS_CACHE = {
  "updated_at": 0.0,
  "value": None,
}
_DASHBOARD_ANALYZER_LOCK = threading.Lock()
_DASHBOARD_ANALYZER_PROCESS = None
params = Params(return_defaults=True)
_CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")


def _format_lan_ip(ip_text):
  try:
    address = ipaddress.ip_address(str(ip_text).strip())
  except ValueError:
    return ""

  if (
    address.version != 4
    or address.is_loopback
    or address.is_link_local
    or address.is_multicast
    or address.is_unspecified
    or address in _CGNAT_NETWORK
  ):
    return ""

  return str(address)


def _candidate_lan_ips_from_ip_addr():
  try:
    result = subprocess.run(
      ["ip", "-o", "-4", "addr", "show", "scope", "global", "up"],
      check=False,
      capture_output=True,
      text=True,
      timeout=0.5,
    )
  except Exception:
    return []

  candidates = []
  ignored_prefixes = ("lo", "tailscale", "tun", "docker", "br-", "veth", "zt", "wg")
  for line in result.stdout.splitlines():
    parts = line.split()
    if len(parts) < 4:
      continue

    interface = parts[1].rstrip(":")
    if interface.startswith(ignored_prefixes):
      continue

    try:
      inet_index = parts.index("inet")
    except ValueError:
      continue

    candidate = _format_lan_ip(parts[inet_index + 1].split("/", 1)[0] if inet_index + 1 < len(parts) else "")
    if candidate:
      candidates.append(candidate)

  return candidates


def get_current_lan_ip():
  now = time.monotonic()
  if now - _LAN_IP_CACHE["updated_at"] < LAN_IP_CACHE_TTL_SECONDS:
    return _LAN_IP_CACHE["value"]

  candidates = []

  try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
      sock.settimeout(0.2)
      sock.connect(("8.8.8.8", 80))
      candidates.append(sock.getsockname()[0])
  except Exception:
    pass

  candidates.extend(_candidate_lan_ips_from_ip_addr())

  try:
    result = subprocess.run(["hostname", "-I"], check=False, capture_output=True, text=True, timeout=0.5)
    candidates.extend(result.stdout.split())
  except Exception:
    pass

  for candidate in candidates:
    ip = _format_lan_ip(candidate)
    if ip:
      _LAN_IP_CACHE["updated_at"] = time.monotonic()
      _LAN_IP_CACHE["value"] = ip
      return ip

  _LAN_IP_CACHE["updated_at"] = time.monotonic()
  _LAN_IP_CACHE["value"] = None
  return None


def _clean_network_name(value):
  text = "".join(character for character in str(value or "").strip().strip("\x00") if character.isprintable())
  return text[:128]


def _read_active_wifi_ssid():
  commands = (
    (["nmcli", "-t", "--escape", "no", "-f", "IN-USE,SSID", "device", "wifi", "list", "--rescan", "no"], "nmcli"),
    (["iwgetid", "--raw"], "iwgetid"),
    (["iw", "dev", "wlan0", "link"], "iw"),
  )

  for command, source in commands:
    try:
      result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=0.5)
    except Exception:
      continue
    if result.returncode != 0:
      continue

    if source == "nmcli":
      for line in result.stdout.splitlines():
        in_use, separator, ssid = line.partition(":")
        if separator and in_use.strip() == "*":
          name = _clean_network_name(ssid)
          if name:
            return name
    elif source == "iwgetid":
      name = _clean_network_name(result.stdout)
      if name:
        return name
    else:
      for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("SSID:"):
          name = _clean_network_name(stripped.partition(":")[2])
          if name:
            return name

  return None


def _network_type_name(network_type):
  raw_value = getattr(network_type, "raw", network_type)
  try:
    raw_value = int(raw_value)
  except (TypeError, ValueError):
    text = str(network_type or "").strip().lower()
    for name in ("none", "wifi", "cell2g", "cell3g", "cell4g", "cell5g", "ethernet"):
      if text == name or text.endswith(f".{name}"):
        return name
    return "unknown"

  return {
    0: "none",
    1: "wifi",
    2: "cell2g",
    3: "cell3g",
    4: "cell4g",
    5: "cell5g",
    6: "ethernet",
  }.get(raw_value, "unknown")


def get_current_network_name():
  now = time.monotonic()
  if now - _NETWORK_STATUS_CACHE["updated_at"] < NETWORK_STATUS_CACHE_TTL_SECONDS:
    return _NETWORK_STATUS_CACHE["value"]

  try:
    network_type = _network_type_name(HARDWARE.get_network_type())
  except Exception:
    network_type = "unknown"

  if network_type == "wifi":
    value = _read_active_wifi_ssid() or "Wi-Fi"
  elif network_type == "cell2g":
    value = "Cellular (2G)"
  elif network_type == "cell3g":
    value = "Cellular (3G)"
  elif network_type == "cell4g":
    value = "Cellular (LTE)"
  elif network_type == "cell5g":
    value = "Cellular (5G)"
  elif network_type == "ethernet":
    value = "Ethernet"
  else:
    value = _read_active_wifi_ssid() or "No wireless connectivity"

  _NETWORK_STATUS_CACHE["updated_at"] = time.monotonic()
  _NETWORK_STATUS_CACHE["value"] = value
  return value


def secure_filename(filename):
  safe = os.path.basename(str(filename or ""))
  safe = safe.replace(" ", "_").strip()
  safe = _FILENAME_SANITIZE_RE.sub("_", safe)
  safe = safe.strip("._")
  return safe or "file"


def _decode_json_param(value, default):
  if value is None:
    return default
  if isinstance(value, (dict, list)):
    return value
  if isinstance(value, bytes):
    value = value.decode("utf-8", errors="replace")
  if isinstance(value, str):
    text = value.strip()
    if not text:
      return default
    try:
      parsed = json.loads(text)
    except json.JSONDecodeError:
      return default
    if isinstance(default, dict) and isinstance(parsed, dict):
      return parsed
    if isinstance(default, list) and isinstance(parsed, list):
      return parsed
    return default
  return default


def _get_pillow_image():
  global _PIL_IMAGE
  if _PIL_IMAGE is None:
    from PIL import Image as pil_image
    _PIL_IMAGE = pil_image
  return _PIL_IMAGE


def _get_pydub_audio_segment():
  global _PYDUB_AUDIOSEGMENT
  if _PYDUB_AUDIOSEGMENT is None:
    from pydub import AudioSegment as pydub_audio_segment
    _PYDUB_AUDIOSEGMENT = pydub_audio_segment
  return _PYDUB_AUDIOSEGMENT


def check_theme_components(theme_path):
  components = {
    "hasColors": False,
    "hasIcons": False,
    "hasSounds": False,
    "hasTurnSignals": False,
    "hasDistanceIcons": False,
    "hasSteeringWheel": False
  }

  colors_path = theme_path / "colors" / "colors.json"
  if colors_path.exists():
    components["hasColors"] = True

  icons_path = theme_path / "icons"
  if icons_path.exists() and any(icons_path.iterdir()):
    components["hasIcons"] = True

  sounds_path = theme_path / "sounds"
  if sounds_path.exists() and any(sounds_path.iterdir()):
    components["hasSounds"] = True

  signals_path = theme_path / "signals"
  if signals_path.exists() and any(signals_path.iterdir()):
    components["hasTurnSignals"] = True

  distance_icons_path = theme_path / "distance_icons"
  if distance_icons_path.exists() and any(distance_icons_path.iterdir()):
    components["hasDistanceIcons"] = True

  is_holiday_theme = str(HOLIDAY_THEME_PATH) in str(theme_path)

  if is_holiday_theme:
    wheel_path = theme_path / "steering_wheel"
    if wheel_path.exists() and any(f.name.startswith("wheel.") for f in wheel_path.iterdir()):
      components["hasSteeringWheel"] = True
  else:
    wheel_path = THEME_SAVE_PATH / "steering_wheels"
    if wheel_path.exists():
      theme_name = theme_path.name.replace('-user_created', '')
      if any(wheel_path.glob(f"{theme_name}-user_created.*")):
        components["hasSteeringWheel"] = True

  return components

def covert_audio(input_file):
  sound = _get_pydub_audio_segment().from_file(input_file)
  sound = sound.set_frame_rate(48000)
  sound = sound.set_channels(1)

  output_filename = os.path.splitext(input_file)[0] + ".wav"
  sound.export(output_filename, format="wav", parameters=["-acodec", "pcm_s16le"])

  if input_file != output_filename:
    os.remove(input_file)

def create_theme(form_data, files, temporary=False):
  theme_name = form_data.get("themeName")
  if not theme_name:
    return None, "Theme name is required."

  sane_theme_name = secure_filename(theme_name.replace(" ", "_"))

  save_checklist_str = form_data.get("saveChecklist", "{}")
  save_checklist = json.loads(save_checklist_str)

  needs_theme_pack = any([
    save_checklist.get("colors"),
    save_checklist.get("icons"),
    save_checklist.get("sounds"),
    save_checklist.get("turn_signals"),
    save_checklist.get("distance_icons"),
  ])

  if temporary:
    base_path = Path(f"/tmp/{sane_theme_name}_{secrets.token_hex(8)}")
  else:
    base_path = THEME_SAVE_PATH / "theme_packs" if needs_theme_pack else None

  theme_path = (base_path / f"{sane_theme_name}-user_created") if base_path else None
  if theme_path:
    theme_path.mkdir(parents=True, exist_ok=True)

  if save_checklist.get("colors"):
    (theme_path / "colors").mkdir(exist_ok=True)
    colors_str = form_data.get("colors")
    if colors_str:
      color_data = json.loads(colors_str)
      for key, values in color_data.items():
        if "alpha" in values:
          values["alpha"] = values.pop("alpha")
      colors_file = theme_path / "colors" / "colors.json"
      with open(colors_file, "w") as f:
        json.dump(color_data, f, indent=2)

  if save_checklist.get("turn_signals"):
    signals_path = theme_path / "signals"
    signals_path.mkdir(exist_ok=True)

    if turn_signal_length := form_data.get("turnSignalLength"):
      style = form_data.get("turnSignalStyle", "Traditional").lower()
      (signals_path / f"{style}_{turn_signal_length}").touch()

    turn_signal_type = form_data.get("turnSignalType", "Single Image").lower()

    if turn_signal_type == "single image":
      for f in signals_path.glob("turn_signal.*"):
        f.unlink()
      for f in signals_path.glob("turn_signal_blindspot.*"):
        f.unlink()

      file = files.get("turnSignal")
      if file and file.filename:
        if file.content_length > MAX_FILE_SIZE:
          return None, f"File {file.filename} exceeds 1MB limit."
        ext = Path(file.filename).suffix
        file.save(signals_path / f"turn_signal{ext}")

      file = files.get("turnSignalBlindspot")
      if file and file.filename:
        if file.content_length > MAX_FILE_SIZE:
          return None, f"File {file.filename} exceeds 1MB limit."
        ext = Path(file.filename).suffix
        file.save(signals_path / f"turn_signal_blindspot{ext}")

    elif turn_signal_type == "sequential":
      for f in signals_path.glob("turn_signal_*"):
        f.unlink()

      signal_map = {
        "turnSignal": "turn_signal",
        "turnSignalBlindspot": "turn_signal_blindspot",
      }
      for field, base_name in signal_map.items():
        file = files.get(field)
        if file and file.filename:
          if file.content_length > MAX_FILE_SIZE:
            return None, f"File {file.filename} exceeds 1MB limit."
          for f in signals_path.glob(f"{base_name}.*"):
            f.unlink()
          ext = Path(file.filename).suffix.lower()
          file.save(signals_path / f"{base_name}{ext}")

      for f in signals_path.glob("turn_signal.*"):
        f.unlink()
      for f in signals_path.glob("turn_signal_blindspot.*"):
        f.unlink()

      sequential_keys = sorted(
        [k for k in files if k.startswith("turn_signal_")],
        key=lambda name: int(name.split("_")[-1])
      )

      for key in sequential_keys:
        file = files.get(key)
        if file and file.filename:
          if file.content_length > MAX_FILE_SIZE:
            return None, f"File {file.filename} exceeds 1MB limit."
          idx = key.split("_")[-1]
          ext = Path(file.filename).suffix
          file.save(signals_path / f"turn_signal_{idx}{ext}")

  if save_checklist.get("icons"):
    (theme_path / "icons").mkdir(exist_ok=True)

    icon_map = {
      "settingsButton": (theme_path / "icons", "button_settings", (169, 104)),
      "homeButton": (theme_path / "icons", "button_home", (250, 250)),
    }

    for field, (dest_path, base_name, resize_dims) in icon_map.items():
      file = files.get(field)
      if file and file.filename:
        if file.content_length > MAX_FILE_SIZE:
          return None, f"File {file.filename} exceeds 1MB limit."

        for f in dest_path.glob(f"{base_name}.*"):
          f.unlink()

        ext = Path(file.filename).suffix.lower()
        save_path = dest_path / f"{base_name}{ext}"
        file.save(save_path)

        if resize_dims:
          if ext == ".gif":
            width, height = resize_dims
            palette_path = save_path.with_suffix(".palette.png")
            temp_output_path = save_path.with_suffix(".resized.gif")
            subprocess.run(["ffmpeg", "-i", str(save_path), "-vf", "palettegen", "-y", str(palette_path)], check=True)
            subprocess.run(["ffmpeg", "-i", str(save_path), "-i", str(palette_path), "-lavfi", f"fps=20,scale={width}:{height}:flags=lanczos[x];[x][1:v]paletteuse", "-y", str(temp_output_path)], check=True)
            palette_path.unlink()
            temp_output_path.rename(save_path)
          else:
            pil_image = _get_pillow_image()
            img = pil_image.open(save_path).resize(resize_dims, pil_image.Resampling.LANCZOS)
            if ext != ".png":
              save_path.unlink()
              save_path = save_path.with_suffix(".png")
            img.save(save_path, "PNG")

  if save_checklist.get("steering_wheel"):
    wheels_dir = THEME_SAVE_PATH / "steering_wheels"
    wheels_dir.mkdir(parents=True, exist_ok=True)
    file = files.get("steeringWheel")
    saved_wheel_path = None
    if file and file.filename:
      if file.content_length > MAX_FILE_SIZE:
        return None, f"File {file.filename} exceeds 1MB limit."
      for f in wheels_dir.glob(f"{sane_theme_name}-user_created.*"):
        f.unlink()
      ext = Path(file.filename).suffix.lower()
      saved_wheel_path = wheels_dir / f"{sane_theme_name}-user_created{ext}"
      file.save(saved_wheel_path)
      if ext == ".gif":
        width, height = (250, 250)
        palette_path = saved_wheel_path.with_suffix(".palette.png")
        temp_output_path = saved_wheel_path.with_suffix(".resized.gif")
        subprocess.run(["ffmpeg", "-i", str(saved_wheel_path), "-vf", "palettegen", "-y", str(palette_path)], check=True)
        subprocess.run(["ffmpeg", "-i", str(saved_wheel_path), "-i", str(palette_path), "-lavfi", f"fps=20,scale={width}:{height}:flags=lanczos[x];[x][1:v]paletteuse", "-y", str(temp_output_path)], check=True)
        palette_path.unlink()
        temp_output_path.rename(saved_wheel_path)
      else:
        pil_image = _get_pillow_image()
        img = pil_image.open(saved_wheel_path).resize((250, 250), pil_image.Resampling.LANCZOS)
        if ext != ".png":
          saved_wheel_path.unlink()
          saved_wheel_path = saved_wheel_path.with_suffix(".png")
        img.save(saved_wheel_path, "PNG")
    if temporary and (theme_path is not None):
      existing = saved_wheel_path if saved_wheel_path is not None else next(wheels_dir.glob(f"{sane_theme_name}-user_created.*"), None)
      if existing:
        wheel_icon_dir = theme_path / "WheelIcon"
        wheel_icon_dir.mkdir(parents=True, exist_ok=True)
        dest = wheel_icon_dir / f"wheel{existing.suffix.lower()}"
        if dest.exists():
          dest.unlink()
        dest.symlink_to(existing)

  if save_checklist.get("distance_icons"):
    dist_path = theme_path / "distance_icons"
    dist_path.mkdir(exist_ok=True)
    for name in ["traffic", "aggressive", "standard", "relaxed"]:
      file = files.get(f"distanceIcons_{name}")
      if file and file.filename:
        if file.content_length > MAX_FILE_SIZE:
          return None, f"File {file.filename} exceeds 1MB limit."

        for f in dist_path.glob(f"{name}.*"):
          f.unlink()

        ext = Path(file.filename).suffix.lower()
        save_path = dist_path / f"{name}{ext}"
        file.save(save_path)
        if ext == ".gif":
          width, height = (250, 250)
          palette_path = save_path.with_suffix(".palette.png")
          temp_output_path = save_path.with_suffix(".resized.gif")
          subprocess.run(["ffmpeg", "-i", str(save_path), "-vf", "palettegen", "-y", str(palette_path)], check=True)
          subprocess.run(["ffmpeg", "-i", str(save_path), "-i", str(palette_path), "-lavfi", f"fps=20,scale={width}:{height}:flags=lanczos[x];[x][1:v]paletteuse", "-y", str(temp_output_path)], check=True)
          palette_path.unlink()
          temp_output_path.rename(save_path)
        else:
          pil_image = _get_pillow_image()
          img = pil_image.open(save_path).resize((250, 250), pil_image.Resampling.LANCZOS)
          if ext != ".png":
            save_path.unlink()
            save_path = save_path.with_suffix(".png")
          img.save(save_path, "PNG")

  if save_checklist.get("sounds"):
    sounds_path = theme_path / "sounds"
    sounds_path.mkdir(exist_ok=True)
    for name in ["engage", "disengage", "prompt", "startup"]:
      file = files.get(name)
      if file and file.filename:
        if file.content_length > MAX_FILE_SIZE:
          return None, f"File {file.filename} exceeds 1MB limit."

        save_path = sounds_path / f"{name}{Path(file.filename).suffix}"
        file.save(save_path)
        covert_audio(str(save_path))

  return theme_path, None

def decode_parameters(encoded_string):
  obfuscated_data = base64.b64decode(encoded_string.encode("utf-8")).decode("utf-8")
  decrypted_data = xor_encrypt_decrypt(obfuscated_data, XOR_KEY)
  return json.loads(decrypted_data)

def encode_parameters(params_dict):
  serialized_data = json.dumps(params_dict)
  obfuscated_data = xor_encrypt_decrypt(serialized_data, XOR_KEY)
  encoded_data = base64.b64encode(obfuscated_data.encode("utf-8")).decode("utf-8")
  return encoded_data

def ffmpeg_concat_segments_to_mp4(input_files, cache_key=None):
  if not input_files:
    raise ValueError("No input files provided for concatenation")

  VIDEO_CACHE_PATH.mkdir(exist_ok=True)

  key_str = "|".join(str(p) for p in input_files)
  if cache_key:
    key_str = f"{cache_key}|{key_str}"
  file_hash = hashlib.md5(key_str.encode()).hexdigest()
  cache_path = VIDEO_CACHE_PATH / f"{file_hash}.mp4"

  if cache_path.exists() and all(cache_path.stat().st_mtime > Path(f).stat().st_mtime for f in input_files):
    return open(cache_path, "rb")

  list_file = VIDEO_CACHE_PATH / f"{file_hash}.txt"
  with open(list_file, "w") as f:
    for seg in input_files:
      f.write(f"file '{Path(seg)}'\n")

  try:
    subprocess.run(
      ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
       "-i", str(list_file), "-c", "copy", "-movflags", "faststart", "-y", str(cache_path)],
      check=True
    )
  except subprocess.CalledProcessError:
    try:
      subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(list_file), "-c:v", "libx264", "-movflags", "faststart", "-y", str(cache_path)],
        check=True
      )
    except subprocess.CalledProcessError:
      if cache_path.exists():
        cache_path.unlink()
      raise ValueError(f"Cannot process concatenated video segments: {input_files}")
  finally:
    if list_file.exists():
      list_file.unlink()

  return open(cache_path, "rb")

def ffmpeg_mp4_wrap_process_builder(filename):
  input_path = Path(filename)

  if not input_path.exists():
    raise FileNotFoundError(f"Input file does not exist: {input_path}")

  if input_path.stat().st_size == 0:
    raise ValueError(f"Input file is empty: {input_path}")

  lock_file = input_path.parent / "rlog.lock"
  if lock_file.exists():
    raise ValueError(f"File is still being recorded: {input_path}")

  VIDEO_CACHE_PATH.mkdir(exist_ok=True)

  total, used, free = shutil.disk_usage(VIDEO_CACHE_PATH)
  if free < 500 * 1024 * 1024:
    for cache_file in VIDEO_CACHE_PATH.glob("*.mp4"):
      try:
        cache_file.unlink()
      except:
        pass

  file_hash = hashlib.md5(str(input_path).encode()).hexdigest()
  cache_path = VIDEO_CACHE_PATH / f"{file_hash}.mp4"

  if cache_path.exists() and cache_path.stat().st_mtime > input_path.stat().st_mtime:
    return open(cache_path, "rb")

  try:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(input_path), "-c", "copy", "-movflags", "faststart", "-y", str(cache_path)], check=True)
  except subprocess.CalledProcessError:
    try:
      subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(input_path), "-c:v", "libx264", "-movflags", "faststart", "-y", str(cache_path)], check=True)
    except subprocess.CalledProcessError:
      if cache_path.exists():
        cache_path.unlink()
      raise ValueError(f"Cannot process video file: {input_path}")

  return open(cache_path, "rb")

def format_git_date(raw_date: str):
  date_object = datetime.strptime(raw_date.split()[1], "%Y-%m-%d")

  day = date_object.day
  suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

  return date_object.strftime(f"%B {day}{suffix}, %Y")

def get_all_segment_names(footage_path):
  entries = listdir_by_creation(footage_path)

  segment_names = []
  for entry in entries:
    if not SEGMENT_RE.fullmatch(entry):
      continue

    segment_names.append(segment_to_segment_name(footage_path, entry))
  return segment_names

def get_available_cameras(segment_path):
  segment_path = Path(segment_path)
  return [
    name for name, file in {
      "driver": "dcamera.hevc",
      "forward": "fcamera.hevc",
      "wide": "ecamera.hevc"
    }.items() if (segment_path / file).exists()
  ]

def get_disk_usage():
  free = get_available_bytes(default=0)
  used = get_used_bytes(default=0)
  total = used + free

  def to_gb(b):
    return f"{b // (2**30)} GB"

  return [{
    "free": to_gb(free),
    "size": to_gb(total),
    "used": to_gb(used),
    "usedPercentage": f"{(used / total) * 100:.2f}%" if total > 0 else "0.00%"
  }]

def get_drive_stats():
  stats = _decode_json_param(params.get("ApiCache_DriveStats"), {})
  starpilot_stats = _decode_json_param(params.get("StarPilotStats"), {})

  is_metric = params.get_bool("IsMetric")
  unit = "kilometers" if is_metric else "miles"

  def numeric(value, default=0.0):
    try:
      parsed = float(value)
    except (TypeError, ValueError):
      return default
    return parsed if parsed == parsed else default

  def process(timeframe):
    data = stats.get(timeframe, {})
    distance_miles = numeric(data.get("distance", 0))
    return {
      "distance": distance_miles * (MILE_TO_KILOMETER if is_metric else 1),
      "drives": numeric(data.get("routes", 0)),
      "hours": numeric(data.get("minutes", 0)) / 60,
      "unit": unit
    }

  stats["all"] = process("all")
  stats["week"] = process("week")
  stats["starpilot"] = {
    "distance": numeric(starpilot_stats.get("StarPilotMeters", 0)) * (METER_TO_KILOMETER if is_metric else METER_TO_MILE),
    "hours": numeric(starpilot_stats.get("StarPilotSeconds", 0)) / (60 * 60),
    "drives": numeric(starpilot_stats.get("StarPilotDrives", 0)),
    "unit": unit
  }

  return stats


def _params_get_value(params_obj, key, default=None):
  if params_obj is None:
    return default
  try:
    value = params_obj.get(key, encoding="utf-8")
  except TypeError:
    try:
      value = params_obj.get(key)
    except Exception:
      return default
  except Exception:
    return default

  if value is None:
    return default
  return value


def _params_get_text(params_obj, key, default=""):
  value = _params_get_value(params_obj, key, default)
  if value is None:
    return default
  if isinstance(value, bytes):
    return value.decode("utf-8", errors="replace")
  if isinstance(value, (dict, list)):
    return json.dumps(value, separators=(",", ":"))
  return str(value)


def _params_get_bool(params_obj, key):
  if params_obj is None:
    return False
  try:
    return bool(params_obj.get_bool(key))
  except Exception:
    value = _params_get_text(params_obj, key, "")
    return value.strip().lower() in ("1", "true", "yes", "on")


def _dashboard_param_file_path(key):
  if key != DASHBOARD_PERSISTENT_STATS_PARAM:
    return None
  return DASHBOARD_PARAMS_DIR / key


def _read_dashboard_param_file(key):
  path = _dashboard_param_file_path(key)
  if path is None or not path.is_file():
    return None
  try:
    return path.read_text(encoding="utf-8")
  except Exception:
    return None


def _write_dashboard_param_file(key, value):
  path = _dashboard_param_file_path(key)
  if path is None:
    return False
  try:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp_path.write_text(str(value), encoding="utf-8")
    os.replace(tmp_path, path)
    return True
  except Exception:
    return False


def _params_put_text(params_obj, key, value):
  if params_obj is None:
    return _write_dashboard_param_file(key, value)
  try:
    params_obj.put(key, value)
    return True
  except Exception:
    return _write_dashboard_param_file(key, value)


def _split_csv(value):
  return [entry.strip() for entry in str(value or "").split(",") if entry.strip()]


def _safe_int(value, default=0):
  try:
    return int(float(value))
  except (TypeError, ValueError):
    return default


def _safe_float(value, default=0.0):
  try:
    parsed = float(value)
  except (TypeError, ValueError):
    return default
  return parsed if parsed == parsed else default


def _clean_model_label(value):
  clean = re.sub(r"[\U0001f5fa\ufe0f\U0001f440\U0001f4e1]", "", str(value or ""))
  return clean.replace("(Default)", "").strip()


def _jsonable_time(value):
  if isinstance(value, datetime):
    return value.isoformat()
  return ""


def _coerce_dashboard_time(value):
  if isinstance(value, datetime):
    return value
  if isinstance(value, str):
    try:
      return datetime.fromisoformat(value)
    except ValueError:
      return None
  return None


def _dashboard_time_is_valid(value, now=None, require_recent=False):
  parsed = _coerce_dashboard_time(value)
  if parsed is None:
    return False
  if parsed < DASHBOARD_MIN_VALID_ROUTE_TIME:
    return False

  now = now or datetime.now()
  if now < DASHBOARD_MIN_VALID_ROUTE_TIME:
    return True

  if parsed > now + timedelta(seconds=DASHBOARD_ROUTE_FUTURE_GRACE_SECONDS):
    return False
  if require_recent and parsed < now - timedelta(seconds=DASHBOARD_LOCAL_ROUTE_MAX_AGE_SECONDS):
    return False
  return True


def _timestamp_to_dashboard_time(timestamp, require_recent=False):
  timestamp = _safe_float(timestamp, 0.0)
  if timestamp <= 0.0:
    return None
  try:
    parsed = datetime.fromtimestamp(timestamp)
  except (OSError, OverflowError, ValueError):
    return None
  return parsed if _dashboard_time_is_valid(parsed, require_recent=require_recent) else None


def _parse_segment_dir_name(name):
  if not SEGMENT_RE.fullmatch(name):
    return None
  route_name, segment_num_text = name.rsplit("--", 1)
  try:
    segment_num = int(segment_num_text)
  except ValueError:
    return None
  return route_name, segment_num


def _segment_mtime(segment_path):
  try:
    return Path(segment_path).stat().st_mtime
  except OSError:
    return 0.0


def _segment_has_dashboard_log(segment_path):
  path = Path(segment_path)
  if not path.is_dir():
    return False
  return any((path / candidate).is_file() for candidate in ROUTE_TIME_LOG_CANDIDATES)


def _select_dashboard_segment_candidate(candidates):
  if not candidates:
    return None
  return next((candidate for candidate in candidates if _segment_has_dashboard_log(candidate)), candidates[0])


def _estimate_route_start_details(segments):
  # Reading a compressed qlog materializes the complete log in memory. Route
  # log analysis happens in the bounded background worker; the synchronous
  # dashboard path must only use filesystem metadata.
  filesystem_estimates = []
  for segment in segments:
    segment_num = max(0, _safe_int(segment.get("num", 0), 0))
    # Segment directory mtimes normally land at the end of their one-minute segment.
    estimate = _segment_mtime(segment.get("path")) - (segment_num + 1) * 60
    parsed = _timestamp_to_dashboard_time(estimate)
    if parsed is not None:
      filesystem_estimates.append(parsed.timestamp())

  # Dashboard analysis can touch a segment directory later, but cannot make it older.
  if filesystem_estimates:
    return datetime.fromtimestamp(min(filesystem_estimates)), DASHBOARD_TIME_SOURCE_FILESYSTEM

  return None, ""


def _estimate_route_started_at(segments):
  return _estimate_route_start_details(segments)[0]


def _list_dashboard_routes(footage_paths, limit=DASHBOARD_ROUTE_SCAN_LIMIT):
  routes = {}

  for footage_path in footage_paths or []:
    root = Path(footage_path)
    if not root.is_dir():
      continue

    try:
      entries = list(root.iterdir())
    except OSError:
      continue

    for entry in entries:
      if not entry.is_dir():
        continue

      parsed = _parse_segment_dir_name(entry.name)
      if parsed is None:
        continue

      route_name, segment_num = parsed
      route = routes.setdefault(route_name, {
        "name": route_name,
        "segments_by_num": {},
        "modified_at": 0.0,
        "started_at": None,
      })
      route["segments_by_num"].setdefault(segment_num, []).append(entry)
      route["modified_at"] = max(route["modified_at"], _segment_mtime(entry))

  # Route IDs are monotonically increasing on-device and remain reliable when
  # the wall clock is wrong. Bound the candidate set before inspecting segment
  # contents so old route history cannot make every homepage request unbounded.
  def route_sequence(route):
    try:
      return int(str(route["name"]).split("--", 1)[0], 16)
    except (KeyError, TypeError, ValueError):
      return -1

  candidates = sorted(
    routes.values(),
    key=lambda route: (route_sequence(route), route["modified_at"], route["name"]),
    reverse=True,
  )
  if limit is not None:
    candidates = candidates[:max(0, limit)]

  route_infos = []
  for route in candidates:
    segments = []
    for segment_num, candidates in sorted(route["segments_by_num"].items()):
      selected = _select_dashboard_segment_candidate(candidates)
      if selected is not None:
        segments.append({"num": segment_num, "path": selected})

    if not segments:
      continue

    started_at, time_source = _estimate_route_start_details(segments)

    route_infos.append({
      "name": route["name"],
      "segments": segments,
      "segmentCount": len(segments),
      "startedAt": started_at,
      "modifiedAt": route["modified_at"],
      "timeSource": time_source,
    })

  route_infos.sort(key=lambda route: (
    route["startedAt"].timestamp() if isinstance(route["startedAt"], datetime) else 0.0,
    route["modifiedAt"],
    route["name"],
  ), reverse=True)
  return route_infos[:limit]


def _dashboard_cache_key(route_infos, params_obj):
  param_keys = (
    "IsMetric",
    "Model",
    "DrivingModel",
    "DrivingModelName",
  )
  route_sig = tuple(
    (route["name"], route["segmentCount"], round(route["modifiedAt"], 3))
    for route in route_infos
  )
  param_sig = tuple(_params_get_text(params_obj, key, "") for key in param_keys)
  return route_sig, param_sig


def _model_lookup(params_obj):
  model_keys = _split_csv(_params_get_text(params_obj, "AvailableModels", ""))
  model_names = _split_csv(_params_get_text(params_obj, "AvailableModelNames", ""))
  model_series = _split_csv(_params_get_text(params_obj, "AvailableModelSeries", ""))

  lookup = {}
  for idx, key in enumerate(model_keys):
    canonical_key = canonical_model_key(key)
    if not canonical_key:
      continue
    name = model_names[idx] if idx < len(model_names) else key
    series = model_series[idx] if idx < len(model_series) else ""
    lookup[canonical_key] = {
      "key": canonical_key,
      "name": _clean_model_label(name) or canonical_key,
      "series": series or "Custom Series",
    }
  return lookup


def _decode_init_param_value(value):
  if value is None:
    return ""
  if isinstance(value, bytes):
    return value.decode("utf-8", errors="replace").strip()
  if isinstance(value, bytearray):
    return bytes(value).decode("utf-8", errors="replace").strip()
  try:
    if not isinstance(value, str):
      value = bytes(value)
      return value.decode("utf-8", errors="replace").strip()
  except Exception:
    pass
  return str(value).strip()


def _init_params_items(init_params):
  if init_params is None:
    return []
  if hasattr(init_params, "items"):
    return list(init_params.items())

  entries = getattr(init_params, "entries", None)
  if entries is not None:
    items = []
    try:
      for entry in entries:
        key = getattr(entry, "key", None)
        value = getattr(entry, "value", None)
        if key is not None:
          items.append((key, value))
    except Exception:
      return []
    return items

  items = []
  try:
    for item in init_params:
      key = getattr(item, "key", None)
      value = getattr(item, "value", None)
      if key is not None:
        items.append((key, value))
  except Exception:
    return []
  return items


def _route_model_from_init_data(init_data, model_names):
  values = {}
  for key, value in _init_params_items(getattr(init_data, "params", None)):
    values[str(key)] = _decode_init_param_value(value)

  display_name = _clean_model_label(values.get("DrivingModelName", ""))
  if display_name:
    return display_name

  for key in ("DrivingModel", "Model"):
    model_key = canonical_model_key(values.get(key, ""))
    if model_key:
      return model_names.get(model_key, {}).get("name", model_key)

  return ""


def _event_name_text(value):
  return str(value or "").split(".")[-1]


def _message_type(message):
  try:
    return message.which()
  except Exception:
    return getattr(message, "type", "")


def _message_payload(message, message_type):
  return getattr(message, message_type, None)


def _deadline_reached(deadline):
  return deadline is not None and time.monotonic() >= deadline


def _numeric_attr(value, attr):
  try:
    return getattr(value, attr)
  except Exception:
    return None


def _wall_time_seconds_from_payload(payload):
  if payload is None:
    return None

  for attr in ("wallTimeNanos", "wallTimeNs", "unixTimestampNanos"):
    value = _safe_float(_numeric_attr(payload, attr), 0.0)
    if value > 1e12:
      return value / 1e9

  for attr in ("wallTimeMillis", "unixTimestampMillis"):
    value = _safe_float(_numeric_attr(payload, attr), 0.0)
    if value > 1e9:
      return value / 1000.0

  for attr in ("wallTime", "unixTimestamp"):
    value = _safe_float(_numeric_attr(payload, attr), 0.0)
    if value > 1e8:
      return value

  return None


def _log_wall_time_range(first_time, last_time, wall_time_offset, duration_seconds):
  if first_time is None or wall_time_offset is None:
    return None

  start_seconds = first_time + wall_time_offset
  end_seconds = (last_time + wall_time_offset) if last_time is not None else start_seconds
  if end_seconds <= start_seconds and duration_seconds > 0:
    end_seconds = start_seconds + duration_seconds

  try:
    start_time = datetime.fromtimestamp(start_seconds)
    end_time = datetime.fromtimestamp(end_seconds)
  except (OSError, OverflowError, ValueError):
    return None
  if not _dashboard_time_is_valid(start_time) or not _dashboard_time_is_valid(end_time):
    return None
  return _jsonable_time(start_time), _jsonable_time(end_time)


def _sample_route_info(route_info, limit=DASHBOARD_ROUTE_SEGMENT_SAMPLE_LIMIT):
  segments = route_info.get("segments", [])
  segment_count = len(segments)
  if segment_count <= limit:
    sampled = dict(route_info)
    sampled["analysisSegmentCount"] = segment_count
    return sampled

  indices = []
  if limit <= 1:
    indices = [segment_count - 1]
  else:
    for idx in range(limit):
      candidate = round(idx * (segment_count - 1) / (limit - 1))
      if candidate not in indices:
        indices.append(candidate)

  if len(indices) < limit:
    for candidate in range(segment_count - 1, -1, -1):
      if candidate not in indices:
        indices.append(candidate)
      if len(indices) >= limit:
        break

  sampled = dict(route_info)
  sampled["segments"] = [segments[idx] for idx in sorted(indices[:limit])]
  sampled["analysisSegmentCount"] = len(sampled["segments"])
  return sampled


def _analyze_route_messages(messages, route_info, model_names, is_metric, deadline=None):
  first_time = None
  last_time = None
  previous_car_time = None
  previous_speed = 0.0
  previous_state_time = None
  previous_enabled = False
  previous_events = set()

  distance_m = 0.0
  engaged_seconds = 0.0
  distracted_moments = 0
  unresponsive_moments = 0
  model = ""
  wall_time_offset = None

  for message in messages:
    if _deadline_reached(deadline):
      break

    mono_time = getattr(message, "logMonoTime", None)
    seconds = (mono_time / 1e9) if isinstance(mono_time, (int, float)) else None
    if seconds is not None:
      first_time = seconds if first_time is None else min(first_time, seconds)
      last_time = seconds if last_time is None else max(last_time, seconds)

    message_type = _message_type(message)
    payload = _message_payload(message, message_type)
    if seconds is not None and wall_time_offset is None:
      wall_seconds = _wall_time_seconds_from_payload(payload)
      if wall_seconds is None:
        wall_seconds = _wall_time_seconds_from_payload(message)
      if wall_seconds is not None:
        wall_time_offset = wall_seconds - seconds

    if message_type == "initData" and payload is not None and not model:
      model = _route_model_from_init_data(payload, model_names)

    elif message_type == "carState" and payload is not None and seconds is not None:
      if previous_car_time is not None and seconds > previous_car_time:
        distance_m += max(previous_speed, 0.0) * min(seconds - previous_car_time, 10.0)
      previous_speed = _safe_float(getattr(payload, "vEgo", 0.0), 0.0)
      previous_car_time = seconds

    elif message_type == "selfdriveState" and payload is not None and seconds is not None:
      if previous_state_time is not None and seconds > previous_state_time and previous_enabled:
        engaged_seconds += min(seconds - previous_state_time, 10.0)
      previous_enabled = bool(getattr(payload, "enabled", False))
      previous_state_time = seconds

    elif message_type == "onroadEvents":
      current_events = {
        _event_name_text(getattr(event, "name", ""))
        for event in (payload or [])
      }
      if DASHBOARD_EVENT_DISTRACTED in current_events and DASHBOARD_EVENT_DISTRACTED not in previous_events:
        distracted_moments += 1
      if DASHBOARD_EVENT_UNRESPONSIVE in current_events and DASHBOARD_EVENT_UNRESPONSIVE not in previous_events:
        unresponsive_moments += 1
      previous_events = current_events

  if previous_state_time is not None and last_time is not None and last_time > previous_state_time and previous_enabled:
    engaged_seconds += min(last_time - previous_state_time, 10.0)

  segment_count = max(0, int(route_info.get("segmentCount", 0)))
  analysis_segment_count = max(0, int(route_info.get("analysisSegmentCount", segment_count)))
  scale = (segment_count / analysis_segment_count) if analysis_segment_count > 0 and analysis_segment_count < segment_count else 1.0
  fallback_duration = segment_count * 60
  log_duration = max(0.0, (last_time - first_time) if first_time is not None and last_time is not None else 0.0)
  if first_time is None or last_time is None:
    duration_seconds = fallback_duration
  elif scale > 1.0:
    duration_seconds = max(log_duration, fallback_duration)
  else:
    duration_seconds = log_duration

  if scale > 1.0:
    distance_m *= scale
    engaged_seconds = min(engaged_seconds * scale, duration_seconds)

  engaged_percent = round((engaged_seconds / duration_seconds) * 100) if duration_seconds > 0 else 0
  distance = distance_m * (METER_TO_KILOMETER if is_metric else METER_TO_MILE)
  avg_speed = (distance_m / duration_seconds) * (CV.MS_TO_KPH if is_metric else METER_PER_SECOND_TO_MPH) if duration_seconds > 0 else 0.0
  time_range = _log_wall_time_range(first_time, last_time, wall_time_offset, duration_seconds)
  start_date, end_date = time_range if time_range is not None else _route_time_range(route_info, duration_seconds)
  time_source = DASHBOARD_TIME_SOURCE_LOG if time_range is not None else (DASHBOARD_TIME_SOURCE_FILESYSTEM if start_date else "")

  return {
    "name": route_info.get("name", ""),
    "routeNames": [route_info.get("name", "")],
    "date": start_date,
    "endDate": end_date,
    "distance": round(distance, 1),
    "distanceMeters": round(distance_m, 1),
    "duration": int(round(duration_seconds)),
    "avgSpeed": int(round(avg_speed)),
    "engagedPercent": max(0, min(100, engaged_percent)),
    "engagedSeconds": round(engaged_seconds, 1),
    "model": model or "Unknown model",
    "segmentCount": int(route_info.get("segmentCount", 0)),
    "distractedMoments": distracted_moments,
    "unresponsiveMoments": unresponsive_moments,
    "routeModifiedAt": _safe_float(route_info.get("modifiedAt", 0.0), 0.0),
    "timeSource": time_source,
    "attentionKnown": True,
    "analysisComplete": analysis_segment_count >= segment_count,
    "analysisVersion": DASHBOARD_ROUTE_ANALYSIS_VERSION,
  }


def _iter_route_log_messages(route_info, deadline=None):
  try:
    from openpilot.tools.lib.logreader import LogReader
  except Exception:
    return

  for segment in route_info.get("segments", []):
    if _deadline_reached(deadline):
      return

    log_path = get_route_log_path(segment.get("path"))
    if log_path is None:
      continue
    try:
      for message in LogReader(str(log_path), sort_by_time=False):
        if _deadline_reached(deadline):
          return
        yield message
    except Exception:
      continue


def _empty_drive(is_metric):
  return {
    "name": "",
    "routeNames": [],
    "ignored": False,
    "date": "",
    "endDate": "",
    "distance": 0,
    "duration": 0,
    "avgSpeed": 0,
    "engagedPercent": 0,
    "model": "Unknown model",
    "segmentCount": 0,
    "distractedMoments": 0,
    "unresponsiveMoments": 0,
    "attentionKnown": True,
    "analysisComplete": False,
    "distanceUnit": "kilometers" if is_metric else "miles",
    "speedUnit": "kph" if is_metric else "mph",
  }


def _public_drive(drive, is_metric):
  public = _empty_drive(is_metric)
  for key in public:
    if key in drive:
      public[key] = drive[key]
  return public


def _route_time_range(route_info, duration_seconds):
  modified_at = _safe_float(route_info.get("modifiedAt", 0.0), 0.0)
  duration_seconds = max(0.0, _safe_float(duration_seconds, 0.0))
  started_at = route_info.get("startedAt")
  if _dashboard_time_is_valid(started_at, require_recent=True):
    end_time = started_at + timedelta(seconds=duration_seconds) if duration_seconds > 0.0 else None
    return _jsonable_time(started_at), _jsonable_time(end_time)

  modified_time = _timestamp_to_dashboard_time(modified_at, require_recent=True)
  if modified_time is not None and duration_seconds > 0.0:
    end_time = modified_time
    start_time = end_time - timedelta(seconds=duration_seconds)
    return _jsonable_time(start_time), _jsonable_time(end_time)
  return "", ""


def _distance_from_meters(distance_m, is_metric):
  return distance_m * (METER_TO_KILOMETER if is_metric else METER_TO_MILE)


def _route_shell_drive(route_info, params_obj, model_names, is_metric):
  segment_count = max(0, _safe_int(route_info.get("segmentCount", 0), 0))
  duration_seconds = segment_count * 60
  start_date, end_date = _route_time_range(route_info, duration_seconds)
  return {
    "name": route_info.get("name", ""),
    "routeNames": [route_info.get("name", "")],
    "ignored": False,
    "date": start_date,
    "endDate": end_date,
    "distance": 0,
    "distanceMeters": 0.0,
    "duration": duration_seconds,
    "avgSpeed": 0,
    "engagedPercent": 0,
    "engagedSeconds": 0.0,
    "model": "Unknown model",
    "segmentCount": segment_count,
    "distractedMoments": 0,
    "unresponsiveMoments": 0,
    "routeModifiedAt": _safe_float(route_info.get("modifiedAt", 0.0), 0.0),
    "timeSource": DASHBOARD_TIME_SOURCE_FILESYSTEM if start_date else "",
    "attentionKnown": False,
    "analysisComplete": False,
    "analysisVersion": 0,
  }


def _drive_from_persistent_route(route_name, entry, is_metric):
  duration = max(0, _safe_int(entry.get("duration", 0), 0))
  distance_m = max(0.0, _safe_float(entry.get("distanceMeters", 0.0), 0.0))
  engaged_seconds = max(0.0, _safe_float(entry.get("engagedSeconds", 0.0), 0.0))
  engaged_percent = round((engaged_seconds / duration) * 100) if duration > 0 else 0
  avg_speed = (distance_m / duration) * (CV.MS_TO_KPH if is_metric else METER_PER_SECOND_TO_MPH) if duration > 0 else 0.0
  return {
    "name": route_name,
    "routeNames": [route_name],
    "ignored": False,
    "date": entry.get("date", ""),
    "endDate": entry.get("endDate", ""),
    "distance": round(_distance_from_meters(distance_m, is_metric), 1),
    "distanceMeters": round(distance_m, 1),
    "duration": duration,
    "avgSpeed": int(round(avg_speed)),
    "engagedPercent": max(0, min(100, engaged_percent)),
    "engagedSeconds": round(engaged_seconds, 1),
    "model": _clean_model_label(entry.get("model", "")) or "Unknown model",
    "segmentCount": max(0, _safe_int(entry.get("segmentCount", 0), 0)),
    "distractedMoments": max(0, _safe_int(entry.get("distractedMoments", 0), 0)),
    "unresponsiveMoments": max(0, _safe_int(entry.get("unresponsiveMoments", 0), 0)),
    "routeModifiedAt": _safe_float(entry.get("modifiedAt", 0.0), 0.0),
    "timeSource": str(entry.get("timeSource", "") or ""),
    "attentionKnown": bool(entry.get("attentionKnown", True)),
    "analysisComplete": bool(entry.get("analysisComplete", False)),
    "analysisVersion": max(0, _safe_int(entry.get("analysisVersion", 0), 0)),
  }


def _persistent_drives(stats, is_metric):
  routes = stats.get("routes", {}) if isinstance(stats, dict) else {}
  if not isinstance(routes, dict):
    return []
  ignored_routes = set(stats.get("ignoredRoutes", [])) if isinstance(stats.get("ignoredRoutes", []), list) else set()
  drives = [
    _drive_from_persistent_route(route_name, entry, is_metric)
    for route_name, entry in routes.items()
    if isinstance(entry, dict) and _dashboard_time_is_valid(entry.get("date", ""))
  ]
  for drive in drives:
    drive["ignored"] = drive["name"] in ignored_routes
  return drives


def _merge_dashboard_drives(*drive_lists):
  merged = {}
  for drives in drive_lists:
    for drive in drives or []:
      route_name = str(drive.get("name", "")).strip()
      if not route_name:
        continue
      existing = merged.get(route_name)
      if existing is None:
        merged[route_name] = dict(drive)
        continue

      existing_distance = _safe_float(existing.get("distanceMeters", existing.get("distance", 0.0)), 0.0)
      drive_distance = _safe_float(drive.get("distanceMeters", drive.get("distance", 0.0)), 0.0)
      existing_attention = bool(existing.get("attentionKnown", False))
      drive_attention = bool(drive.get("attentionKnown", False))
      if drive_distance > existing_distance or (drive_attention and not existing_attention):
        merged[route_name] = dict(drive)

  return sorted(merged.values(), key=_drive_sort_time, reverse=True)


def _drive_display_group_key(drive):
  start_text = str(drive.get("date", "")).strip()
  end_text = str(drive.get("endDate", "")).strip()
  model_key = _model_usage_key(drive.get("model", ""))
  if not start_text or not end_text or not model_key:
    return None
  return start_text, end_text, model_key


def _coalesced_drive_group(group, is_metric):
  if len(group) == 1:
    return dict(group[0])

  ordered = sorted(group, key=_drive_sort_time, reverse=True)
  primary = dict(ordered[0])
  total_distance_m = sum(max(0.0, _safe_float(drive.get("distanceMeters", 0.0), 0.0)) for drive in ordered)
  total_duration = sum(max(0, _safe_int(drive.get("duration", 0), 0)) for drive in ordered)
  total_engaged = sum(max(0.0, _safe_float(drive.get("engagedSeconds", 0.0), 0.0)) for drive in ordered)

  if total_distance_m > 0.0:
    primary["distanceMeters"] = round(total_distance_m, 1)
    primary["distance"] = round(_distance_from_meters(total_distance_m, is_metric), 1)
  else:
    primary["distance"] = round(sum(max(0.0, _safe_float(drive.get("distance", 0.0), 0.0)) for drive in ordered), 1)
  primary["duration"] = total_duration
  primary["engagedSeconds"] = round(total_engaged, 1)
  primary["engagedPercent"] = max(0, min(100, round((total_engaged / total_duration) * 100))) if total_duration > 0 else 0
  primary["avgSpeed"] = int(round((total_distance_m / total_duration) * (CV.MS_TO_KPH if is_metric else METER_PER_SECOND_TO_MPH))) if total_distance_m > 0.0 and total_duration > 0 else 0
  primary["segmentCount"] = sum(max(0, _safe_int(drive.get("segmentCount", 0), 0)) for drive in ordered)
  primary["distractedMoments"] = sum(max(0, _safe_int(drive.get("distractedMoments", 0), 0)) for drive in ordered)
  primary["unresponsiveMoments"] = sum(max(0, _safe_int(drive.get("unresponsiveMoments", 0), 0)) for drive in ordered)
  primary["routeModifiedAt"] = max(_safe_float(drive.get("routeModifiedAt", 0.0), 0.0) for drive in ordered)
  primary["attentionKnown"] = any(bool(drive.get("attentionKnown", True)) for drive in ordered)
  primary["analysisComplete"] = all(bool(drive.get("analysisComplete", False)) for drive in ordered)
  route_names = []
  for drive in ordered:
    for route_name in drive.get("routeNames", [drive.get("name", "")]):
      route_name = str(route_name or "").strip()
      if route_name and route_name not in route_names:
        route_names.append(route_name)
  primary["routeNames"] = route_names
  primary["name"] = ",".join(route_names)
  primary["ignored"] = bool(route_names) and all(bool(drive.get("ignored", False)) for drive in ordered)
  return primary


def _coalesce_display_drives(drives, is_metric):
  groups = {}
  fallback = []
  for drive in drives or []:
    group_key = _drive_display_group_key(drive)
    if group_key is None:
      fallback.append(dict(drive))
      continue
    groups.setdefault(group_key, []).append(drive)

  coalesced = [_coalesced_drive_group(group, is_metric) for group in groups.values()]
  coalesced.extend(fallback)
  return sorted(coalesced, key=_drive_sort_time, reverse=True)


def _drive_has_stale_analysis(drive):
  if not bool(drive.get("attentionKnown", True)) or not bool(drive.get("analysisComplete", False)):
    return False
  return _safe_int(drive.get("analysisVersion", 0), 0) < DASHBOARD_ROUTE_ANALYSIS_VERSION


def _week_summary_drives(drives, pending_route_names=None):
  pending_route_names = pending_route_names or set()
  return [
    drive for drive in drives or []
    if not (_drive_has_stale_analysis(drive) and str(drive.get("name", "")).strip() in pending_route_names)
  ]


def _persistent_route_needs_time_refresh(entry):
  source = str(entry.get("timeSource", "") or "")
  version = _safe_int(entry.get("analysisVersion", 0), 0)
  if not source:
    return version < DASHBOARD_ROUTE_ANALYSIS_VERSION
  if source == DASHBOARD_TIME_SOURCE_FILESYSTEM:
    return not _dashboard_time_is_valid(entry.get("date", ""), require_recent=True)
  if source == DASHBOARD_TIME_SOURCE_LOG:
    return not _dashboard_time_is_valid(entry.get("date", ""))
  return True


def _analysis_candidates(route_infos, persistent_stats):
  routes = persistent_stats.get("routes", {}) if isinstance(persistent_stats, dict) else {}
  routes = routes if isinstance(routes, dict) else {}
  ignored_routes = set(persistent_stats.get("ignoredRoutes", [])) if isinstance(persistent_stats, dict) else set()

  def needs_analysis(route_info):
    route_name = route_info.get("name", "")
    entry = routes.get(route_name, {})
    if not isinstance(entry, dict):
      return True
    if _safe_float(entry.get("modifiedAt", 0.0), 0.0) < _safe_float(route_info.get("modifiedAt", 0.0), 0.0):
      return True
    if _persistent_route_needs_time_refresh(entry):
      return True
    if _safe_int(entry.get("analysisVersion", 0), 0) < DASHBOARD_ROUTE_ANALYSIS_VERSION:
      return True
    return not bool(entry.get("attentionKnown", True)) or not bool(entry.get("analysisComplete", False))

  missing = [
    route_info for route_info in route_infos
    if route_info.get("name", "") not in ignored_routes and needs_analysis(route_info)
  ]
  return missing


def _mark_ignored_drives(drives, persistent_stats):
  ignored_routes = set(persistent_stats.get("ignoredRoutes", [])) if isinstance(persistent_stats, dict) else set()
  for drive in drives or []:
    route_names = drive.get("routeNames", [drive.get("name", "")])
    route_names = [str(route_name or "").strip() for route_name in route_names if str(route_name or "").strip()]
    drive["routeNames"] = route_names
    drive["ignored"] = bool(route_names) and all(route_name in ignored_routes for route_name in route_names)
  return drives


def _invalidate_dashboard_cache():
  _DASHBOARD_CACHE.update({
    "key": None,
    "updated_at": 0.0,
    "value": None,
  })


def clear_dashboard_route_history(params_obj):
  """Remove route-backed dashboard history while keeping durable records."""
  stats = _load_dashboard_persistent_stats(params_obj)
  route_count = len(stats.get("routes", {}))
  stats["routes"] = {}
  stats["ignoredRoutes"] = []
  serialized = json.dumps(stats, separators=(",", ":"))

  persisted_to_params = False
  if params_obj is not None:
    try:
      params_obj.put(DASHBOARD_PERSISTENT_STATS_PARAM, serialized)
      persisted_to_params = True
    except Exception:
      pass

  fallback_path = _dashboard_param_file_path(DASHBOARD_PERSISTENT_STATS_PARAM)
  if persisted_to_params:
    try:
      fallback_path.unlink()
    except (FileNotFoundError, OSError):
      pass
  elif not _write_dashboard_param_file(DASHBOARD_PERSISTENT_STATS_PARAM, serialized):
    raise RuntimeError("Unable to clear persisted dashboard route history.")

  _invalidate_dashboard_cache()
  return route_count


def warm_dashboard_stats(footage_paths=None):
  params_obj = params
  if params_obj.get_bool("IsOnroad"):
    return

  route_infos = _list_dashboard_routes(footage_paths or [])

  if not route_infos:
    return

  is_metric = _params_get_bool(params_obj, "IsMetric")
  model_names = _model_lookup(params_obj)
  shell_drives = [
    _route_shell_drive(route_info, params_obj, model_names, is_metric)
    for route_info in route_infos
  ]
  if shell_drives:
    _update_dashboard_persistent_stats(params_obj, shell_drives, time.time())

  persistent_stats = _load_dashboard_persistent_stats(params_obj)
  candidates = _analysis_candidates(route_infos, persistent_stats)[:DASHBOARD_BACKGROUND_ROUTE_ANALYSIS_LIMIT]
  for route_info in candidates:
    if params_obj.get_bool("IsOnroad"):
      break
    full_route_info = dict(route_info)
    full_route_info["analysisSegmentCount"] = max(0, _safe_int(route_info.get("segmentCount", 0), 0))
    messages = _iter_route_log_messages(full_route_info)
    drive = _analyze_route_messages(messages, full_route_info, model_names, is_metric)
    _update_dashboard_persistent_stats(params_obj, [drive], time.time())


def _dashboard_worker_env(repo_root):
  env = os.environ.copy()
  pythonpath = [
    "/usr/local/venv/lib/python3.12/site-packages",
    str(repo_root / "starpilot" / "third_party"),
    str(repo_root),
  ]
  if env.get("PYTHONPATH"):
    pythonpath.append(env["PYTHONPATH"])
  env["PYTHONPATH"] = os.pathsep.join(pythonpath)
  env.setdefault("OPENBLAS_NUM_THREADS", "1")
  env.setdefault("OMP_NUM_THREADS", "1")
  env.setdefault("MKL_NUM_THREADS", "1")
  env.setdefault("NUMEXPR_NUM_THREADS", "1")
  return env


def _dashboard_analyzer_running():
  process = _DASHBOARD_ANALYZER_PROCESS
  if process is not None and process.poll() is None:
    return True

  status = _read_dashboard_analyzer_status()
  pid = _safe_int(status.get("pid", 0), 0)
  started_at = _safe_float(status.get("startedAt", 0.0), 0.0)
  if pid <= 0 or started_at <= 0:
    return False
  if (time.time() - started_at) > DASHBOARD_ANALYZER_STATUS_MAX_AGE_SECONDS:
    _clear_dashboard_analyzer_status()
    return False

  try:
    os.kill(pid, 0)
  except ProcessLookupError:
    _clear_dashboard_analyzer_status()
    return False
  except PermissionError:
    return True
  except OSError:
    return False
  return True


def _read_dashboard_analyzer_status():
  try:
    status = json.loads(DASHBOARD_ANALYZER_STATUS_PATH.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return {}
  return status if isinstance(status, dict) else {}


def _write_dashboard_analyzer_status(process, pending_count):
  status = {
    "pid": process.pid,
    "startedAt": time.time(),
    "pendingRoutes": max(0, _safe_int(pending_count, 0)),
    "batchSize": min(DASHBOARD_BACKGROUND_ROUTE_ANALYSIS_LIMIT, max(0, _safe_int(pending_count, 0))),
  }
  tmp_path = DASHBOARD_ANALYZER_STATUS_PATH.with_suffix(".tmp")
  try:
    tmp_path.write_text(json.dumps(status, separators=(",", ":")), encoding="utf-8")
    tmp_path.replace(DASHBOARD_ANALYZER_STATUS_PATH)
  except OSError:
    pass


def _clear_dashboard_analyzer_status():
  try:
    DASHBOARD_ANALYZER_STATUS_PATH.unlink()
  except FileNotFoundError:
    pass
  except OSError:
    pass


def _dashboard_analyzer_pid_matches(pid):
  try:
    command = Path(f"/proc/{pid}/cmdline").read_bytes()
  except OSError:
    return False
  return b"warm_dashboard_stats" in command


def stop_dashboard_background_analysis():
  global _DASHBOARD_ANALYZER_PROCESS

  stopped = False
  with _DASHBOARD_ANALYZER_LOCK:
    process = _DASHBOARD_ANALYZER_PROCESS
    if process is not None and process.poll() is None:
      process.terminate()
      stopped = True
    else:
      status = _read_dashboard_analyzer_status()
      pid = _safe_int(status.get("pid", 0), 0)
      if pid > 0 and _dashboard_analyzer_pid_matches(pid):
        try:
          os.kill(pid, signal.SIGTERM)
          stopped = True
        except (ProcessLookupError, PermissionError, OSError):
          pass

    _DASHBOARD_ANALYZER_PROCESS = None
    _clear_dashboard_analyzer_status()

  return stopped


def _dashboard_analysis_status(candidates):
  pending_count = len(candidates or [])
  return {
    "pendingRoutes": pending_count,
    "running": _dashboard_analyzer_running(),
    "batchSize": min(DASHBOARD_BACKGROUND_ROUTE_ANALYSIS_LIMIT, pending_count),
  }


def _start_dashboard_background_analysis(footage_paths, route_infos, persistent_stats, candidates=None):
  global _DASHBOARD_ANALYZER_PROCESS

  candidates = candidates if candidates is not None else _analysis_candidates(route_infos, persistent_stats)
  if params.get_bool("IsOnroad") or not route_infos or not candidates:
    return False

  with _DASHBOARD_ANALYZER_LOCK:
    if params.get_bool("IsOnroad"):
      return False
    if _dashboard_analyzer_running():
      return True
    repo_root = Path(__file__).resolve().parents[3]
    worker_code = (
      "import json, sys;"
      "from openpilot.starpilot.system.the_galaxy import utilities;"
      "utilities.warm_dashboard_stats(json.loads(sys.argv[1]))"
    )
    command = [
      "nice",
      "-n",
      "19",
      sys.executable or "python3",
      "-c",
      worker_code,
      json.dumps([str(path) for path in (footage_paths or [])]),
    ]
    log_file = None
    try:
      log_file = open(DASHBOARD_ANALYZER_LOG_PATH, "ab")
      _DASHBOARD_ANALYZER_PROCESS = subprocess.Popen(
        command,
        cwd=str(repo_root),
        env=_dashboard_worker_env(repo_root),
        stdout=log_file,
        stderr=log_file,
        start_new_session=True,
      )
      _write_dashboard_analyzer_status(_DASHBOARD_ANALYZER_PROCESS, len(candidates))
    except Exception:
      _DASHBOARD_ANALYZER_PROCESS = None
    finally:
      if log_file is not None:
        log_file.close()

  return _dashboard_analyzer_running()


def _start_of_week(now):
  return datetime(now.year, now.month, now.day) - timedelta(days=now.weekday())


def _build_week_summary(drives, now, is_metric):
  week_start = _start_of_week(now)
  week_end = week_start + timedelta(days=7)
  day_buckets = [
    {
      "date": (week_start + timedelta(days=idx)).date().isoformat(),
      "label": (week_start + timedelta(days=idx)).strftime("%a"),
      "distance": 0.0,
    }
    for idx in range(7)
  ]

  total_distance = 0.0
  total_duration = 0
  total_engaged = 0.0
  total_drives = 0

  for drive in drives:
    try:
      drive_date = datetime.fromisoformat(drive.get("date", ""))
    except ValueError:
      continue
    if not (week_start <= drive_date < week_end):
      continue

    day_index = (drive_date.date() - week_start.date()).days
    if 0 <= day_index < len(day_buckets):
      day_buckets[day_index]["distance"] += _safe_float(drive.get("distance", 0.0), 0.0)
    total_distance += _safe_float(drive.get("distance", 0.0), 0.0)
    total_duration += _safe_int(drive.get("duration", 0), 0)
    total_engaged += _safe_float(drive.get("engagedSeconds", 0.0), 0.0)
    total_drives += 1

  for bucket in day_buckets:
    bucket["distance"] = round(bucket["distance"], 1)

  return {
    "distance": round(total_distance, 1),
    "duration": total_duration,
    "hours": round(total_duration / 3600, 1),
    "drives": total_drives,
    "engagedPercent": round((total_engaged / total_duration) * 100) if total_duration > 0 else 0,
    "dailyDistance": day_buckets,
    "distanceUnit": "kilometers" if is_metric else "miles",
  }


def _format_record_date(date_text):
  try:
    parsed = datetime.fromisoformat(date_text)
    if datetime.now().year == parsed.year:
      return parsed.strftime("%b %-d")
    return parsed.strftime("%b %-d, %Y")
  except ValueError:
    return "Unknown date"


def _format_record_hours(seconds):
  hours = max(0.0, _safe_float(seconds, 0.0) / 3600.0)
  return f"{hours:.1f} hour" if round(hours, 1) == 1.0 else f"{hours:.1f} hours"


def _drive_is_clean(drive):
  return _safe_int(drive.get("unresponsiveMoments", 0), 0) == 0


def _drive_is_undistracted(drive):
  return _safe_int(drive.get("distractedMoments", 0), 0) == 0


def _drive_sort_time(drive):
  try:
    return datetime.fromisoformat(drive.get("date", ""))
  except ValueError:
    return datetime.min


def _display_attention_records(stats):
  records = {}
  attention = stats.get("attentionRecords", {}) if isinstance(stats, dict) else {}
  longest = attention.get("longestUndistractedDrive", {}) if isinstance(attention, dict) else {}
  clean_streak = attention.get("cleanDriveStreak", {}) if isinstance(attention, dict) else {}

  longest_duration = _safe_int(longest.get("duration", 0), 0) if isinstance(longest, dict) else 0
  if longest_duration > 0:
    records["longestUndistractedDrive"] = {
      "value": _format_record_hours(longest_duration),
      "detail": _format_record_date(longest.get("date", "")),
    }

  streak_drives = _safe_int(clean_streak.get("drives", 0), 0) if isinstance(clean_streak, dict) else 0
  if streak_drives > 0:
    start = _format_record_date(clean_streak.get("startDate", ""))
    end = _format_record_date(clean_streak.get("endDate", ""))
    detail = start if start == end else f"{start} - {end}"
    records["cleanDriveStreak"] = {
      "value": f"{streak_drives} drive" if streak_drives == 1 else f"{streak_drives} drives",
      "detail": detail,
    }

  return records


def _display_distance_record_value(distance_m, is_metric):
  distance = max(0.0, _safe_float(distance_m, 0.0)) * (METER_TO_KILOMETER if is_metric else METER_TO_MILE)
  return f"{distance:.1f}"


def _display_personal_records(stats, is_metric):
  records = _build_records([], is_metric)
  if not isinstance(stats, dict):
    return records

  raw_records = stats.get("personalRecords", {})
  if not isinstance(raw_records, dict) or not raw_records:
    raw_records = _merge_personal_records(_build_personal_records_raw(stats.get("routes", {})), {}, stats.get("attentionRecords", {}))

  unit = "kilometers" if is_metric else "miles"

  longest_drive = raw_records.get("longestDrive", {}) if isinstance(raw_records, dict) else {}
  longest_distance_m = _safe_float(longest_drive.get("distanceMeters", 0.0), 0.0) if isinstance(longest_drive, dict) else 0.0
  if longest_distance_m > 0.0:
    records["longestDrive"] = {
      "value": _display_distance_record_value(longest_distance_m, is_metric),
      "detail": f"{unit} - {_format_record_date(longest_drive.get('date', ''))}",
    }

  most_engaged = raw_records.get("mostEngagedDay", {}) if isinstance(raw_records, dict) else {}
  most_engaged_percent = _safe_int(most_engaged.get("percent", 0), 0) if isinstance(most_engaged, dict) else 0
  if most_engaged_percent > 0:
    records["mostEngagedDay"] = {
      "value": f"{most_engaged_percent}%",
      "detail": _format_record_date(most_engaged.get("date", "")),
    }

  best_week = raw_records.get("bestWeek", {}) if isinstance(raw_records, dict) else {}
  best_week_distance_m = _safe_float(best_week.get("distanceMeters", 0.0), 0.0) if isinstance(best_week, dict) else 0.0
  if best_week_distance_m > 0.0:
    records["bestWeek"] = {
      "value": _display_distance_record_value(best_week_distance_m, is_metric),
      "detail": f"{unit} - week of {_format_record_date(best_week.get('weekDate', ''))}",
    }

  highest_streak = raw_records.get("highestStreak", {}) if isinstance(raw_records, dict) else {}
  highest_days = _safe_int(highest_streak.get("days", 0), 0) if isinstance(highest_streak, dict) else 0
  if highest_days > 0:
    records["highestStreak"] = {
      "value": f"{highest_days} day" if highest_days == 1 else f"{highest_days} days",
      "detail": "Consecutive drive days",
    }

  longest_undistracted = raw_records.get("longestUndistractedDrive", {}) if isinstance(raw_records, dict) else {}
  longest_undistracted_duration = _safe_int(longest_undistracted.get("duration", 0), 0) if isinstance(longest_undistracted, dict) else 0
  if longest_undistracted_duration > 0:
    records["longestUndistractedDrive"] = {
      "value": _format_record_hours(longest_undistracted_duration),
      "detail": _format_record_date(longest_undistracted.get("date", "")),
    }

  clean_streak = raw_records.get("cleanDriveStreak", {}) if isinstance(raw_records, dict) else {}
  clean_drives = _safe_int(clean_streak.get("drives", 0), 0) if isinstance(clean_streak, dict) else 0
  if clean_drives > 0:
    start = _format_record_date(clean_streak.get("startDate", ""))
    end = _format_record_date(clean_streak.get("endDate", ""))
    detail = start if start == end else f"{start} - {end}"
    records["cleanDriveStreak"] = {
      "value": f"{clean_drives} drive" if clean_drives == 1 else f"{clean_drives} drives",
      "detail": detail,
    }

  return records


def _build_records(drives, is_metric):
  unit = "kilometers" if is_metric else "miles"
  empty = {"value": "0", "detail": unit}
  if not drives:
    return {
      "longestDrive": empty,
      "mostEngagedDay": {"value": "0%", "detail": "No drives"},
      "bestWeek": empty,
      "highestStreak": {"value": "0 days", "detail": "No drives"},
      "longestUndistractedDrive": {"value": "0.0 hours", "detail": "No clean drives"},
      "cleanDriveStreak": {"value": "0 drives", "detail": "No clean drives"},
    }

  longest = max(drives, key=lambda drive: _safe_float(drive.get("distance", 0), 0))

  days = {}
  weeks = {}
  for drive in drives:
    try:
      drive_date = datetime.fromisoformat(drive.get("date", ""))
    except ValueError:
      continue
    day_key = drive_date.date()
    week_key = _start_of_week(drive_date).date()
    days.setdefault(day_key, {"duration": 0, "engaged": 0.0})
    days[day_key]["duration"] += _safe_int(drive.get("duration", 0), 0)
    days[day_key]["engaged"] += _safe_float(drive.get("engagedSeconds", 0.0), 0.0)
    weeks[week_key] = weeks.get(week_key, 0.0) + _safe_float(drive.get("distance", 0.0), 0.0)

  if days:
    most_engaged_date, most_engaged_data = max(
      days.items(),
      key=lambda item: (item[1]["engaged"] / item[1]["duration"]) if item[1]["duration"] > 0 else 0,
    )
    most_engaged_percent = round((most_engaged_data["engaged"] / most_engaged_data["duration"]) * 100) if most_engaged_data["duration"] > 0 else 0
  else:
    most_engaged_date = None
    most_engaged_percent = 0

  if weeks:
    best_week_date, best_week_distance = max(weeks.items(), key=lambda item: item[1])
  else:
    best_week_date, best_week_distance = None, 0.0

  longest_streak = 0
  current_streak = 0
  previous_day = None
  for day in sorted(days):
    if previous_day is not None and (day - previous_day).days == 1:
      current_streak += 1
    else:
      current_streak = 1
    longest_streak = max(longest_streak, current_streak)
    previous_day = day

  undistracted_drives = [drive for drive in drives if _drive_is_undistracted(drive)]
  longest_undistracted = max(undistracted_drives, key=lambda drive: _safe_int(drive.get("duration", 0), 0)) if undistracted_drives else None
  longest_undistracted_duration = _safe_int(longest_undistracted.get("duration", 0), 0) if longest_undistracted else 0

  longest_clean_streak = 0
  current_clean_streak = 0
  for drive in sorted(drives, key=_drive_sort_time):
    if _drive_is_clean(drive):
      current_clean_streak += 1
    else:
      current_clean_streak = 0
    longest_clean_streak = max(longest_clean_streak, current_clean_streak)

  return {
    "longestDrive": {
      "value": f"{_safe_float(longest.get('distance'), 0):.1f}",
      "detail": f"{unit} - {_format_record_date(longest.get('date', ''))}",
    },
    "mostEngagedDay": {
      "value": f"{most_engaged_percent}%",
      "detail": most_engaged_date.strftime("%b %-d") if most_engaged_date else "No drives",
    },
    "bestWeek": {
      "value": f"{best_week_distance:.1f}",
      "detail": f"{unit} - week of {best_week_date.strftime('%b %-d')}" if best_week_date else unit,
    },
    "highestStreak": {
      "value": f"{longest_streak} day" if longest_streak == 1 else f"{longest_streak} days",
      "detail": "Consecutive drive days",
    },
    "longestUndistractedDrive": {
      "value": _format_record_hours(longest_undistracted_duration),
      "detail": _format_record_date(longest_undistracted.get("date", "")) if longest_undistracted else "No undistracted drives",
    },
    "cleanDriveStreak": {
      "value": f"{longest_clean_streak} drive" if longest_clean_streak == 1 else f"{longest_clean_streak} drives",
      "detail": "No attention warnings",
    },
  }


def _normalize_persistent_routes(raw_routes):
  if not isinstance(raw_routes, dict):
    return {}

  routes = {}
  for route_name, entry in raw_routes.items():
    if not isinstance(entry, dict):
      continue
    name = str(route_name or entry.get("name", "")).strip()
    date = str(entry.get("date", "")).strip()
    if not name or not date or not _dashboard_time_is_valid(date):
      continue
    routes[name] = {
      "date": date,
      "endDate": str(entry.get("endDate", "")).strip(),
      "distanceMeters": max(0.0, _safe_float(entry.get("distanceMeters", 0.0), 0.0)),
      "duration": max(0, _safe_int(entry.get("duration", 0), 0)),
      "clean": bool(entry.get("clean", False)),
      "undistracted": bool(entry.get("undistracted", entry.get("clean", False))),
      "engagedSeconds": max(0.0, _safe_float(entry.get("engagedSeconds", 0.0), 0.0)),
      "distractedMoments": max(0, _safe_int(entry.get("distractedMoments", 0), 0)),
      "unresponsiveMoments": max(0, _safe_int(entry.get("unresponsiveMoments", 0), 0)),
      "model": _clean_model_label(entry.get("model", "")),
      "modelKey": canonical_model_key(entry.get("modelKey", "")),
      "segmentCount": max(0, _safe_int(entry.get("segmentCount", 0), 0)),
      "modifiedAt": _safe_float(entry.get("modifiedAt", 0.0), 0.0),
      "timeSource": str(entry.get("timeSource", "") or ""),
      "attentionKnown": bool(entry.get("attentionKnown", True)),
      "analysisComplete": bool(entry.get("analysisComplete", False)),
      "analysisVersion": max(0, _safe_int(entry.get("analysisVersion", 0), 0)),
    }
  return routes


def _load_dashboard_persistent_stats(params_obj):
  raw_data = _read_dashboard_param_file(DASHBOARD_PERSISTENT_STATS_PARAM)
  if raw_data is None:
    raw_data = _params_get_value(params_obj, DASHBOARD_PERSISTENT_STATS_PARAM, None)
  data = _decode_json_param(raw_data, {})
  if not isinstance(data, dict):
    data = {}
  data["version"] = 1
  data["routes"] = _normalize_persistent_routes(data.get("routes", {}))
  ignored_routes = data.get("ignoredRoutes", [])
  data["ignoredRoutes"] = sorted({
    str(route_name).strip()
    for route_name in ignored_routes
    if ROUTE_RE.fullmatch(str(route_name).strip())
  }) if isinstance(ignored_routes, list) else []
  attention = data.get("attentionRecords", {})
  data["attentionRecords"] = attention if isinstance(attention, dict) else {}
  personal_records = data.get("personalRecords", {})
  data["personalRecords"] = personal_records if isinstance(personal_records, dict) else {}
  model_usage = data.get("modelUsage", {})
  data["modelUsage"] = model_usage if isinstance(model_usage, dict) else {}
  return data


def _route_entry_sort_key(item):
  route_name, entry = item
  try:
    route_time = datetime.fromisoformat(entry.get("date", ""))
  except ValueError:
    route_time = datetime.min
  return route_time, route_name


def _model_usage_key(model_name):
  clean_name = _clean_model_label(model_name)
  if not clean_name or clean_name == "Unknown model":
    return ""
  return re.sub(r"[^a-z0-9]+", "-", clean_name.lower()).strip("-")


def _better_record(current, previous, metric_key):
  if not isinstance(previous, dict):
    return current
  if _safe_float(previous.get(metric_key, 0.0), 0.0) > _safe_float(current.get(metric_key, 0.0), 0.0):
    return dict(previous)
  return current


def _record_with_valid_dates(record, metric_key, *date_keys):
  if not isinstance(record, dict):
    return None
  if _safe_float(record.get(metric_key, 0.0), 0.0) <= 0.0:
    return record
  for key in date_keys:
    if not _dashboard_time_is_valid(record.get(key, "")):
      return None
  return record


def _build_personal_records_raw(routes):
  ordered_routes = sorted((routes or {}).items(), key=_route_entry_sort_key)
  records = {
    "longestDrive": {"distanceMeters": 0.0, "date": ""},
    "mostEngagedDay": {"percent": 0, "date": ""},
    "bestWeek": {"distanceMeters": 0.0, "weekDate": ""},
    "highestStreak": {"days": 0},
    "longestUndistractedDrive": {"duration": 0, "date": ""},
    "cleanDriveStreak": {"drives": 0, "startDate": "", "endDate": ""},
  }
  if not ordered_routes:
    return records

  days = {}
  weeks = {}
  current_clean_streak = 0
  current_clean_start = ""

  for _, entry in ordered_routes:
    date_text = str(entry.get("date", "")).strip()
    if not _dashboard_time_is_valid(date_text):
      continue
    try:
      drive_date = datetime.fromisoformat(date_text)
    except ValueError:
      drive_date = None

    distance_m = max(0.0, _safe_float(entry.get("distanceMeters", 0.0), 0.0))
    duration = max(0, _safe_int(entry.get("duration", 0), 0))
    engaged_seconds = max(0.0, _safe_float(entry.get("engagedSeconds", 0.0), 0.0))

    if distance_m > _safe_float(records["longestDrive"].get("distanceMeters", 0.0), 0.0):
      records["longestDrive"] = {"distanceMeters": distance_m, "date": date_text}

    if drive_date is not None:
      day_key = drive_date.date()
      week_key = _start_of_week(drive_date).date()
      days.setdefault(day_key, {"duration": 0, "engaged": 0.0})
      days[day_key]["duration"] += duration
      days[day_key]["engaged"] += engaged_seconds
      weeks[week_key] = weeks.get(week_key, 0.0) + distance_m

    attention_known = bool(entry.get("attentionKnown", True))
    if attention_known and bool(entry.get("undistracted", False)) and duration > _safe_int(records["longestUndistractedDrive"].get("duration", 0), 0):
      records["longestUndistractedDrive"] = {"duration": duration, "date": date_text}

    if bool(entry.get("clean", False)) and attention_known:
      if current_clean_streak == 0:
        current_clean_start = date_text
      current_clean_streak += 1
      if current_clean_streak > _safe_int(records["cleanDriveStreak"].get("drives", 0), 0):
        records["cleanDriveStreak"] = {
          "drives": current_clean_streak,
          "startDate": current_clean_start,
          "endDate": date_text,
        }
    elif attention_known:
      current_clean_streak = 0
      current_clean_start = ""

  for day, data in days.items():
    duration = _safe_int(data.get("duration", 0), 0)
    if duration <= 0:
      continue
    percent = round((_safe_float(data.get("engaged", 0.0), 0.0) / duration) * 100)
    if percent > _safe_int(records["mostEngagedDay"].get("percent", 0), 0):
      records["mostEngagedDay"] = {"percent": percent, "date": day.isoformat()}

  if weeks:
    best_week_date, best_week_distance = max(weeks.items(), key=lambda item: item[1])
    records["bestWeek"] = {
      "distanceMeters": max(0.0, _safe_float(best_week_distance, 0.0)),
      "weekDate": best_week_date.isoformat(),
    }

  current_day_streak = 0
  previous_day = None
  for day in sorted(days):
    if previous_day is not None and (day - previous_day).days == 1:
      current_day_streak += 1
    else:
      current_day_streak = 1
    records["highestStreak"]["days"] = max(_safe_int(records["highestStreak"].get("days", 0), 0), current_day_streak)
    previous_day = day

  return records


def _merge_personal_records(current, previous, legacy_attention=None):
  previous = previous if isinstance(previous, dict) else {}
  merged = {
    "longestDrive": _better_record(
      current.get("longestDrive", {}),
      _record_with_valid_dates(previous.get("longestDrive"), "distanceMeters", "date"),
      "distanceMeters",
    ),
    "mostEngagedDay": _better_record(
      current.get("mostEngagedDay", {}),
      _record_with_valid_dates(previous.get("mostEngagedDay"), "percent", "date"),
      "percent",
    ),
    "bestWeek": _better_record(
      current.get("bestWeek", {}),
      _record_with_valid_dates(previous.get("bestWeek"), "distanceMeters", "weekDate"),
      "distanceMeters",
    ),
    "highestStreak": _better_record(current.get("highestStreak", {}), previous.get("highestStreak"), "days"),
    "longestUndistractedDrive": _better_record(
      current.get("longestUndistractedDrive", {}),
      _record_with_valid_dates(previous.get("longestUndistractedDrive"), "duration", "date"),
      "duration",
    ),
    "cleanDriveStreak": _better_record(
      current.get("cleanDriveStreak", {}),
      _record_with_valid_dates(previous.get("cleanDriveStreak"), "drives", "startDate", "endDate"),
      "drives",
    ),
  }

  if isinstance(legacy_attention, dict):
    merged["longestUndistractedDrive"] = _better_record(
      merged["longestUndistractedDrive"],
      _record_with_valid_dates(legacy_attention.get("longestUndistractedDrive"), "duration", "date"),
      "duration",
    )
    merged["cleanDriveStreak"] = _better_record(
      merged["cleanDriveStreak"],
      _record_with_valid_dates(legacy_attention.get("cleanDriveStreak"), "drives", "startDate", "endDate"),
      "drives",
    )

  return merged


def _recalculate_persistent_stats(stats, reset_personal_records=False):
  routes = stats.get("routes", {})
  ordered_routes = sorted(routes.items(), key=_route_entry_sort_key)
  if len(ordered_routes) > DASHBOARD_PERSISTED_ROUTE_LIMIT:
    ordered_routes = ordered_routes[-DASHBOARD_PERSISTED_ROUTE_LIMIT:]
    routes = dict(ordered_routes)
    stats["routes"] = routes

  ignored_routes = set(stats.get("ignoredRoutes", []))
  included_routes = {
    route_name: entry
    for route_name, entry in routes.items()
    if route_name not in ignored_routes
  }
  included_ordered_routes = [
    (route_name, entry)
    for route_name, entry in ordered_routes
    if route_name not in ignored_routes
  ]
  model_usage = {}

  for _, entry in included_ordered_routes:
    if not _dashboard_time_is_valid(entry.get("date", "")):
      continue
    if not bool(entry.get("analysisComplete", False)):
      continue
    model_name = _clean_model_label(entry.get("model", ""))
    model_key = canonical_model_key(entry.get("modelKey", "")) or _model_usage_key(model_name)
    if model_key:
      usage = model_usage.setdefault(model_key, {
        "key": model_key,
        "name": model_name or model_key,
        "drives": 0,
        "lastUsed": "",
      })
      usage["drives"] += 1
      usage["lastUsed"] = entry.get("date", "") or usage["lastUsed"]
      if model_name:
        usage["name"] = model_name

  previous_attention = stats.get("attentionRecords", {}) if isinstance(stats.get("attentionRecords", {}), dict) else {}
  current_records = _build_personal_records_raw(included_routes)
  if reset_personal_records:
    stats["personalRecords"] = current_records
  else:
    stats["personalRecords"] = _merge_personal_records(current_records, stats.get("personalRecords", {}), previous_attention)

  stats["attentionRecords"] = {
    "longestUndistractedDrive": stats["personalRecords"]["longestUndistractedDrive"],
    "cleanDriveStreak": stats["personalRecords"]["cleanDriveStreak"],
  }
  stats["modelUsage"] = model_usage
  return stats


def set_dashboard_routes_ignored(params_obj, route_names, ignored):
  normalized_names = {
    str(route_name or "").strip()
    for route_name in (route_names or [])
    if ROUTE_RE.fullmatch(str(route_name or "").strip())
  }
  if not normalized_names:
    raise ValueError("No valid dashboard routes were provided.")

  stats = _load_dashboard_persistent_stats(params_obj)
  ignored_routes = set(stats.get("ignoredRoutes", []))
  if ignored:
    ignored_routes.update(normalized_names)
  else:
    ignored_routes.difference_update(normalized_names)
  stats["ignoredRoutes"] = sorted(ignored_routes)
  stats = _recalculate_persistent_stats(stats, reset_personal_records=True)
  _params_put_text(params_obj, DASHBOARD_PERSISTENT_STATS_PARAM, json.dumps(stats, separators=(",", ":")))
  _invalidate_dashboard_cache()
  return sorted(normalized_names)


def ignore_dashboard_routes(params_obj, route_names):
  return set_dashboard_routes_ignored(params_obj, route_names, True)


def include_dashboard_routes(params_obj, route_names):
  return set_dashboard_routes_ignored(params_obj, route_names, False)


def _drive_stable_for_persistence(drive, wall_now):
  modified_at = _safe_float(drive.get("routeModifiedAt", 0.0), 0.0)
  return modified_at <= 0.0 or wall_now - modified_at >= DASHBOARD_PERSIST_MIN_ROUTE_AGE_SECONDS


def _drive_time_reliable_for_persistence(drive):
  source = str(drive.get("timeSource", "") or "")
  date_text = str(drive.get("date", "")).strip()
  if source == DASHBOARD_TIME_SOURCE_FILESYSTEM:
    return _dashboard_time_is_valid(date_text, require_recent=True)
  if source == DASHBOARD_TIME_SOURCE_LOG:
    return _dashboard_time_is_valid(date_text)
  return bool(date_text)


def _filesystem_route_time_changed(existing_entry, next_entry):
  if (
    str(existing_entry.get("timeSource", "") or "") != DASHBOARD_TIME_SOURCE_FILESYSTEM
    or str(next_entry.get("timeSource", "") or "") != DASHBOARD_TIME_SOURCE_FILESYSTEM
  ):
    return False
  existing_date = _coerce_dashboard_time(existing_entry.get("date", ""))
  next_date = _coerce_dashboard_time(next_entry.get("date", ""))
  if existing_date is None or next_date is None:
    return False
  return abs((next_date - existing_date).total_seconds()) > DASHBOARD_ROUTE_TIME_REPAIR_THRESHOLD_SECONDS


def _update_dashboard_persistent_stats(params_obj, drives, wall_now):
  stats = _load_dashboard_persistent_stats(params_obj)
  before = json.dumps(stats, sort_keys=True, separators=(",", ":"))
  routes = stats.setdefault("routes", {})
  changed = False

  for drive in sorted(drives, key=_drive_sort_time):
    route_name = str(drive.get("name", "")).strip()
    route_date = str(drive.get("date", "")).strip()
    if not route_name or not route_date or not _drive_stable_for_persistence(drive, wall_now) or not _drive_time_reliable_for_persistence(drive):
      continue

    model_name = _clean_model_label(drive.get("model", ""))
    model_key = _model_usage_key(model_name)
    attention_known = bool(drive.get("attentionKnown", True))
    time_source = str(drive.get("timeSource", "") or "")
    next_entry = {
      "date": route_date,
      "endDate": str(drive.get("endDate", "")).strip(),
      "distanceMeters": max(0.0, _safe_float(drive.get("distanceMeters", 0.0), 0.0)),
      "duration": max(0, _safe_int(drive.get("duration", 0), 0)),
      "clean": attention_known and _drive_is_clean(drive),
      "undistracted": attention_known and _drive_is_undistracted(drive),
      "engagedSeconds": max(0.0, _safe_float(drive.get("engagedSeconds", 0.0), 0.0)),
      "distractedMoments": max(0, _safe_int(drive.get("distractedMoments", 0), 0)),
      "unresponsiveMoments": max(0, _safe_int(drive.get("unresponsiveMoments", 0), 0)),
      "model": model_name,
      "modelKey": model_key,
      "segmentCount": max(0, _safe_int(drive.get("segmentCount", 0), 0)),
      "modifiedAt": _safe_float(drive.get("routeModifiedAt", 0.0), 0.0),
      "timeSource": time_source,
      "attentionKnown": attention_known,
      "analysisComplete": bool(drive.get("analysisComplete", False)),
      "analysisVersion": _safe_int(drive.get("analysisVersion", 0), 0),
    }
    if attention_known and next_entry["analysisComplete"]:
      next_entry["analysisVersion"] = DASHBOARD_ROUTE_ANALYSIS_VERSION
    existing_entry = routes.get(route_name)
    if isinstance(existing_entry, dict):
      replace_filesystem_time = _filesystem_route_time_changed(existing_entry, next_entry)
      existing_distance = max(0.0, _safe_float(existing_entry.get("distanceMeters", 0.0), 0.0))
      next_distance = max(0.0, _safe_float(next_entry.get("distanceMeters", 0.0), 0.0))
      existing_current = _safe_float(existing_entry.get("modifiedAt", 0.0), 0.0) >= _safe_float(next_entry.get("modifiedAt", 0.0), 0.0)
      existing_attention_known = bool(existing_entry.get("attentionKnown", True))
      existing_model = _clean_model_label(existing_entry.get("model", ""))
      if not attention_known and existing_current and existing_model and existing_model != "Unknown model":
        next_entry["model"] = existing_model
        next_entry["modelKey"] = canonical_model_key(existing_entry.get("modelKey", "")) or _model_usage_key(existing_model)
      if not attention_known and existing_current and existing_attention_known:
        next_entry["clean"] = bool(existing_entry.get("clean", False))
        next_entry["undistracted"] = bool(existing_entry.get("undistracted", existing_entry.get("clean", False)))
        next_entry["attentionKnown"] = True
        next_entry["analysisComplete"] = bool(existing_entry.get("analysisComplete", False))
        next_entry["analysisVersion"] = max(0, _safe_int(existing_entry.get("analysisVersion", 0), 0))
      if not attention_known and existing_current and existing_distance >= next_distance:
        next_entry["distanceMeters"] = existing_distance
        existing_duration = _safe_int(existing_entry.get("duration", 0), 0)
        next_entry["duration"] = existing_duration if existing_attention_known else max(existing_duration, next_entry["duration"])
        if existing_attention_known and str(existing_entry.get("date", "")).strip() and not replace_filesystem_time:
          next_entry["date"] = str(existing_entry.get("date", "")).strip()
          next_entry["timeSource"] = str(existing_entry.get("timeSource", "") or next_entry["timeSource"])
        if str(existing_entry.get("endDate", "")).strip() and not replace_filesystem_time:
          next_entry["endDate"] = str(existing_entry.get("endDate", "")).strip()
        elif replace_filesystem_time:
          corrected_start = _coerce_dashboard_time(next_entry.get("date", ""))
          next_entry["endDate"] = _jsonable_time(corrected_start + timedelta(seconds=next_entry["duration"])) if corrected_start else ""
        next_entry["engagedSeconds"] = max(0.0, _safe_float(existing_entry.get("engagedSeconds", 0.0), 0.0))
        next_entry["distractedMoments"] = max(0, _safe_int(existing_entry.get("distractedMoments", 0), 0))
        next_entry["unresponsiveMoments"] = max(0, _safe_int(existing_entry.get("unresponsiveMoments", 0), 0))
        next_entry["analysisComplete"] = bool(existing_entry.get("analysisComplete", False))
        next_entry["analysisVersion"] = max(0, _safe_int(existing_entry.get("analysisVersion", 0), 0))
      if (not model_name or model_name == "Unknown model") and _clean_model_label(existing_entry.get("model", "")):
        next_entry["model"] = _clean_model_label(existing_entry.get("model", ""))
        next_entry["modelKey"] = canonical_model_key(existing_entry.get("modelKey", "")) or _model_usage_key(next_entry["model"])
    if routes.get(route_name) != next_entry:
      routes[route_name] = next_entry
      changed = True

  stats = _recalculate_persistent_stats(stats)
  after = json.dumps(stats, sort_keys=True, separators=(",", ":"))
  if changed or after != before:
    _params_put_text(params_obj, DASHBOARD_PERSISTENT_STATS_PARAM, json.dumps(stats, separators=(",", ":")))
  return stats


def _storage_category(path):
  path_text = str(path)
  if "realdata_HD" in path_text:
    return "highResolution"
  if "realdata_konik" in path_text:
    return "alternate"
  return "standard"


def _build_storage_summary(footage_paths):
  free = get_available_bytes(default=0)
  used = get_used_bytes(default=0)
  total = free + used
  counts = {"standard": 0, "highResolution": 0, "alternate": 0}

  for footage_path in footage_paths or []:
    root = Path(footage_path)
    if not root.is_dir():
      continue
    category = _storage_category(root)
    try:
      counts[category] += sum(1 for entry in root.iterdir() if entry.is_dir() and _parse_segment_dir_name(entry.name))
    except OSError:
      continue

  return {
    "freeBytes": free,
    "usedBytes": used,
    "totalBytes": total,
    "usedPercent": round((used / total) * 100) if total > 0 else 0,
    "segmentCounts": counts,
  }


def _read_uptime_seconds():
  try:
    with open("/proc/uptime", encoding="utf-8") as f:
      return int(float(f.read().split()[0]))
  except Exception:
    return None


def _normalize_temp_c(value):
  try:
    raw = float(value)
  except (TypeError, ValueError):
    return None
  if raw > 1000:
    raw /= 1000.0
  return raw if 0 < raw < 150 else None


def _read_hardware_cpu_temps():
  try:
    from openpilot.system.hardware import HARDWARE
    thermal_config = HARDWARE.get_thermal_config()
    thermal_msg = thermal_config.get_msg()
  except Exception:
    return []

  cpu_temps = thermal_msg.get("cpuTempC", [])
  if not isinstance(cpu_temps, (list, tuple)):
    cpu_temps = [cpu_temps]
  return [
    temp for temp in (_normalize_temp_c(value) for value in cpu_temps)
    if temp is not None
  ]


def _read_cpu_temp_c(thermal_root=None):
  if thermal_root is None:
    hardware_temps = _read_hardware_cpu_temps()
    if hardware_temps:
      return round(max(hardware_temps))
    thermal_root = Path("/sys/class/thermal")

  try:
    zones = sorted(thermal_root.glob("thermal_zone*/temp"))
  except Exception:
    return None

  values = []
  for temp_path in zones:
    try:
      zone_type = temp_path.with_name("type").read_text(encoding="utf-8").strip().lower()
    except Exception:
      zone_type = ""
    if "cpu" not in zone_type:
      continue
    try:
      raw = temp_path.read_text().strip()
    except Exception:
      continue
    temp = _normalize_temp_c(raw)
    if temp is not None:
      values.append(temp)

  return round(max(values)) if values else None


def _build_device_summary(params_obj):
  is_onroad = _params_get_bool(params_obj, "IsOnroad")
  uptime_seconds = _read_uptime_seconds()
  cpu_temp_c = _read_cpu_temp_c()
  lan_ip = get_current_lan_ip()
  network_name = get_current_network_name()
  return {
    "status": "Driving" if is_onroad else "Parked",
    "online": True,
    "uptimeSeconds": uptime_seconds,
    "cpuTempC": cpu_temp_c,
    "lanIp": lan_ip,
    "networkName": network_name,
  }


def _build_favorite_models(params_obj, persistent_stats=None):
  lookup = _model_lookup(params_obj)
  user_favorites = {canonical_model_key(entry) for entry in _split_csv(_params_get_text(params_obj, "UserFavorites", ""))}
  listed_favorites = {canonical_model_key(entry) for entry in _split_csv(_params_get_text(params_obj, "CommunityFavorites", ""))}
  usage = (persistent_stats or {}).get("modelUsage", {})
  usage = usage if isinstance(usage, dict) else {}

  top_models = []
  for raw_key, usage_entry in usage.items():
    if not isinstance(usage_entry, dict):
      continue

    drives = _safe_int(usage_entry.get("drives", 0), 0)
    if drives <= 0:
      continue

    key = canonical_model_key(usage_entry.get("key", "")) or canonical_model_key(raw_key)
    name = _clean_model_label(usage_entry.get("name", ""))
    if not key:
      key = _model_usage_key(name)
    if not key:
      continue

    model = lookup.get(key, {"key": key, "name": name or key, "series": "Custom Series"})
    top_models.append({
      "key": key,
      "name": model["name"],
      "series": model["series"],
      "userFavorite": key in user_favorites,
      "listedFavorite": key in listed_favorites,
      "drives": drives,
      "weight": drives,
    })

  top_models.sort(key=lambda model: (
    -model["drives"],
    model["name"].lower(),
  ))
  return top_models[:DASHBOARD_TOP_MODEL_LIMIT]


def _dashboard_empty(is_metric, now, footage_paths, params_obj, persistent_stats=None):
  records = _display_personal_records(persistent_stats or {}, is_metric)
  return {
    "lastDrive": _empty_drive(is_metric),
    "recentDrives": [],
    "week": _build_week_summary([], now, is_metric),
    "records": records,
    "device": _build_device_summary(params_obj),
    "storage": _build_storage_summary(footage_paths),
    "favoriteModels": _build_favorite_models(params_obj, persistent_stats),
  }


def get_dashboard_stats(footage_paths, params_obj=None, now=None):
  params_obj = params_obj or params
  now = now or datetime.now()
  route_infos = _list_dashboard_routes(footage_paths)
  cache_key = _dashboard_cache_key(route_infos, params_obj)
  cache_now = time.monotonic()

  if (
    _DASHBOARD_CACHE["key"] == cache_key
    and _DASHBOARD_CACHE["value"] is not None
    and cache_now - _DASHBOARD_CACHE["updated_at"] < DASHBOARD_CACHE_TTL_SECONDS
  ):
    cached_dashboard = copy.deepcopy(_DASHBOARD_CACHE["value"])
    cached_analysis = cached_dashboard.get("analysis", {}) if isinstance(cached_dashboard, dict) else {}
    if isinstance(cached_analysis, dict):
      cached_analysis["running"] = _dashboard_analyzer_running()
      cached_dashboard["analysis"] = cached_analysis
    return cached_dashboard

  is_metric = _params_get_bool(params_obj, "IsMetric")
  model_names = _model_lookup(params_obj)
  analysis_deadline = cache_now + DASHBOARD_ANALYSIS_TIME_BUDGET_SECONDS

  persistent_stats = _load_dashboard_persistent_stats(params_obj)
  shell_drives = [
    _route_shell_drive(route_info, params_obj, model_names, is_metric)
    for route_info in route_infos
  ]
  if shell_drives:
    persistent_stats = _update_dashboard_persistent_stats(params_obj, shell_drives, time.time())

  analyzed_drives = []
  if DASHBOARD_ROUTE_ANALYSIS_LIMIT > 0 and DASHBOARD_ANALYSIS_TIME_BUDGET_SECONDS > 0:
    for route_info in _analysis_candidates(route_infos, persistent_stats)[:DASHBOARD_ROUTE_ANALYSIS_LIMIT]:
      if _deadline_reached(analysis_deadline):
        break
      sampled_route_info = _sample_route_info(route_info)
      messages = _iter_route_log_messages(sampled_route_info, analysis_deadline)
      analyzed_drives.append(_analyze_route_messages(messages, sampled_route_info, model_names, is_metric, analysis_deadline))
    if analyzed_drives:
      persistent_stats = _update_dashboard_persistent_stats(params_obj, analyzed_drives, time.time())

  persisted_drives = _persistent_drives(persistent_stats, is_metric)
  combined_drives = _merge_dashboard_drives(shell_drives, persisted_drives, analyzed_drives)
  _mark_ignored_drives(combined_drives, persistent_stats)
  display_drives = _coalesce_display_drives(combined_drives, is_metric)
  included_display_drives = [drive for drive in display_drives if not bool(drive.get("ignored", False))]
  pending_candidates = _analysis_candidates(route_infos, persistent_stats)
  pending_route_names = {str(route.get("name", "")).strip() for route in pending_candidates}
  included_drives = [drive for drive in combined_drives if not bool(drive.get("ignored", False))]
  week_drives = _week_summary_drives(included_drives, pending_route_names)
  _start_dashboard_background_analysis(footage_paths, route_infos, persistent_stats, pending_candidates)
  analysis_status = _dashboard_analysis_status(pending_candidates)

  if not display_drives:
    dashboard = _dashboard_empty(is_metric, now, footage_paths, params_obj, persistent_stats)
  else:
    records = _display_personal_records(persistent_stats, is_metric)
    dashboard = {
      "lastDrive": _public_drive(included_display_drives[0], is_metric) if included_display_drives else _empty_drive(is_metric),
      "recentDrives": [_public_drive(drive, is_metric) for drive in display_drives[:DASHBOARD_RECENT_DRIVE_LIMIT]],
      "week": _build_week_summary(week_drives, now, is_metric),
      "records": records,
      "device": _build_device_summary(params_obj),
      "storage": _build_storage_summary(footage_paths),
      "favoriteModels": _build_favorite_models(params_obj, persistent_stats),
    }
  dashboard["analysis"] = analysis_status

  _DASHBOARD_CACHE.update({
    "key": cache_key,
    "updated_at": time.monotonic(),
    "value": copy.deepcopy(dashboard),
  })
  return dashboard


def get_repo_owner(git_normalized_origin):
  parts = git_normalized_origin.split("/")
  return parts[1] if len(parts) >= 2 else "unknown"


def normalize_github_remote(remote):
  remote = str(remote or "").strip()
  if remote.startswith("git@github.com:"):
    remote = "https://github.com/" + remote.split(":", 1)[1]
  elif remote.startswith("ssh://git@github.com/"):
    remote = "https://github.com/" + remote.split("ssh://git@github.com/", 1)[1]
  elif remote.startswith("github.com/"):
    remote = "https://" + remote
  elif remote.startswith("http://github.com/"):
    remote = "https://github.com/" + remote.split("http://github.com/", 1)[1]
  elif re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", remote):
    remote = f"https://github.com/{remote}"

  if not remote.startswith("https://github.com/"):
    return ""
  remote = remote.rstrip("/")
  if remote.endswith(".git"):
    remote = remote[:-4]
  return remote


def get_github_changelog_url(git_normalized_origin, branch):
  remote = normalize_github_remote(git_normalized_origin)
  if not remote or not branch:
    return ""
  return f"{remote}/commits/{quote(str(branch), safe='')}/"


def get_github_commit_url(git_normalized_origin, commit):
  remote = normalize_github_remote(git_normalized_origin)
  if not remote or not commit:
    return ""
  return f"{remote}/commit/{quote(str(commit), safe='')}"

def get_route_log_path(path):
  target = Path(path)
  if target.is_dir():
    for candidate in ROUTE_TIME_LOG_CANDIDATES:
      candidate_path = target / candidate
      if candidate_path.exists():
        return candidate_path
    return None

  if target.exists():
    return target

  if target.parent.is_dir():
    for candidate in ROUTE_TIME_LOG_CANDIDATES:
      candidate_path = target.parent / candidate
      if candidate_path.exists():
        return candidate_path

  return None


def _route_logged_start_time(log_path, reader=None):
  """Recover a route's wall-clock start when filesystem time was reset at boot."""
  try:
    if reader is None:
      from openpilot.tools.lib.logreader import _LogFileReader
      reader = _LogFileReader(str(log_path))

    first_mono_time = None
    for message in reader:
      mono_time = _safe_float(getattr(message, "logMonoTime", 0), 0.0) / 1e9
      if mono_time <= 0.0:
        continue
      first_mono_time = mono_time if first_mono_time is None else min(first_mono_time, mono_time)

      message_type = _message_type(message)
      payload = _message_payload(message, message_type)
      wall_time = _wall_time_seconds_from_payload(payload)
      if wall_time is None:
        wall_time = _wall_time_seconds_from_payload(message)
      if wall_time is None:
        continue

      start_seconds = wall_time - (mono_time - first_mono_time)
      start_time = datetime.fromtimestamp(start_seconds)
      if _dashboard_time_is_valid(start_time):
        return start_time
  except Exception:
    return None
  return None


def get_route_start_time(path):
  log_path = get_route_log_path(path)
  if log_path is None:
    target = Path(path)
    if not target.exists():
      return None
    log_path = target

  try:
    modified_time = log_path.stat().st_mtime
  except OSError:
    return None

  if modified_time <= 0:
    return None

  filesystem_time = _timestamp_to_dashboard_time(modified_time)
  if filesystem_time is not None:
    return filesystem_time

  # Recover dates from logs only for files created while the system clock was
  # genuinely invalid. Normal route browsing stays metadata-only.
  logged_time = _route_logged_start_time(log_path)
  if logged_time is not None:
    return logged_time

  return datetime.fromtimestamp(modified_time)

def get_routes_names(footage_path):
  segments = get_all_segment_names(footage_path)
  route_times = {segment.route_name.time_str for segment in segments}
  return sorted(route_times, reverse=True)

def get_routes_with_segment_counts(footage_path):
  route_counts = {}
  for segment in get_all_segment_names(footage_path):
    route_name = segment.route_name.time_str
    route_counts[route_name] = route_counts.get(route_name, 0) + 1
  return sorted(route_counts.items(), reverse=True)

def get_segments_in_route(route_time_str, footage_path):
  return [
    f"{segment.time_str}--{segment.segment_num}"
    for segment in get_all_segment_names(footage_path)
    if segment.time_str == route_time_str
  ]

def get_video_duration(input_path):
  try:
    result = subprocess.run([
      "ffprobe", "-v", "error", "-show_entries", "format=duration",
      "-of", "default=noprint_wrappers=1:nokey=1", str(input_path)
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    return float(result.stdout)
  except (ValueError, subprocess.CalledProcessError):
    return 60

def has_preserve_attr(path: str):
  return PRESERVE_ATTR_NAME in os.listxattr(path) and os.getxattr(path, PRESERVE_ATTR_NAME) == PRESERVE_ATTR_VALUE

def list_file(path):
  return sorted(os.listdir(path), reverse=True)

def normalize_theme_name(name, for_path=False):
  name = name.replace("-user_created", "")
  if for_path:
    return name.lower().replace(" (", "-").replace(")", "").replace(" ", "-").replace("'", "").replace(".", "")

  parts = re.split(r'[-_]', name)
  normalized_parts = [part.capitalize() for part in parts]

  if '-' in name and len(normalized_parts) > 1:
    return f"{normalized_parts[0]} ({' '.join(normalized_parts[1:])})".replace(" Week", "")
  return ' '.join(normalized_parts).replace(" Week", "")

def process_route(footage_path, route_name, segment_count=0):
  segment_path = f"{footage_path}{route_name}--0"
  qcamera_path = f"{segment_path}/qcamera.ts"

  png_output_path = os.path.join(segment_path, "preview.png")
  if not os.path.exists(png_output_path):
    video_to_png(qcamera_path, png_output_path)

  custom_name = None
  if os.path.isdir(segment_path):
    for item in os.listdir(segment_path):
      if not item.endswith((".hevc", ".ts", ".png", ".gif")) and item not in LOG_CANDIDATES:
        custom_name = item
        break

  route_timestamp_str = custom_name
  if not custom_name:
    route_timestamp_dt = get_route_start_time(segment_path)
    route_timestamp_str = route_timestamp_dt.isoformat() if route_timestamp_dt else None

  return {
    "name": route_name,
    "png": f"/thumbnails/{route_name}--0/preview.png",
    "timestamp": route_timestamp_str,
    "is_preserved": has_preserve_attr(segment_path),
    "segmentCount": max(0, int(segment_count)),
    "approxDurationSeconds": max(0, int(segment_count)) * 60,
  }

def process_screen_recording(mp4):
  stem = mp4.with_suffix("")
  png_path = stem.with_suffix(".png")

  if not png_path.exists():
    video_to_png(mp4, png_path)

  is_custom_name = False
  try:
    datetime.strptime(stem.name, "%B_%d_%Y-%I-%M%p")
  except ValueError:
    is_custom_name = True

  return {
    "filename": mp4.name,
    "png": f"/screen_recordings/{png_path.name}",
    "timestamp": datetime.fromtimestamp(mp4.stat().st_mtime).isoformat(),
    "is_custom_name": is_custom_name
  }

def segment_to_segment_name(data_dir, segment):
  full_path = os.path.join(data_dir, f"FakeDongleID1337|{segment}")
  return SegmentName(full_path)

def video_to_png(input_path, output_path):
  try:
    subprocess.run([
      "ffmpeg", "-hide_banner", "-loglevel", "error",
      "-ss", "1",
      "-i", str(input_path),
      "-frames:v", "1",
      "-y",
      str(output_path)
    ], capture_output=True, check=True, text=True)
  except subprocess.CalledProcessError as e:
    print(f"Failed to generate PNG for {input_path}")
    if e.stderr:
      print(e.stderr)

def xor_encrypt_decrypt(data, key):
  return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))
