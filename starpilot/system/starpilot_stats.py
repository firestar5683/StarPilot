import json
import os
import random
import requests
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "third_party"))

from collections import Counter
from datetime import datetime, timezone
from cereal import log
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

try:
  from openpilot.common.conversions import Conversions as CV
except ModuleNotFoundError:
  from openpilot.common.constants import CV
from openpilot.system.hardware import HARDWARE
from openpilot.system.version import get_build_metadata

from openpilot.starpilot.common.starpilot_utilities import clean_model_name, run_cmd
from openpilot.starpilot.common.starpilot_variables import get_starpilot_toggles, params

BASE_URL = "https://nominatim.openstreetmap.org"
MINIMUM_POPULATION = 100_000
SEARCH_RADIUS_DEGREES = 1.45
METER_TO_MILE = getattr(CV, "METER_TO_MILE", 0.000621371192237334)

def get_device_generation(device_type):
  normalized = (device_type or "").lower()
  mapping = {
    "tici": "C3",
    "tizi": "C3X",
    "mici": "C4",
  }
  return mapping.get(normalized, (device_type or "Unknown").upper())

def _json_object(value):
  if value is None:
    return {}
  if isinstance(value, dict):
    return value
  if isinstance(value, bytes):
    value = value.decode("utf-8", errors="replace")
  if isinstance(value, str):
    try:
      parsed = json.loads(value)
      return parsed if isinstance(parsed, dict) else {}
    except Exception:
      return {}
  return {}

def get_live_delay_stats():
  defaults = {
    "lagd_calibration_percent": 0,
    "lagd_valid_blocks": 0,
    "lagd_applied_delay_seconds": 0.0,
    "lagd_learned_delay_seconds": 0.0,
    "lagd_learned_delay_std_seconds": 0.0,
  }

  live_delay_data = params.get("LiveDelay")
  if not live_delay_data:
    return defaults

  try:
    with log.Event.from_bytes(live_delay_data) as live_delay_msg:
      live_delay = live_delay_msg.liveDelay
      return {
        "lagd_calibration_percent": int(getattr(live_delay, "calPerc", 0)),
        "lagd_valid_blocks": int(getattr(live_delay, "validBlocks", 0)),
        "lagd_applied_delay_seconds": float(getattr(live_delay, "lateralDelay", 0.0)),
        "lagd_learned_delay_seconds": float(getattr(live_delay, "lateralDelayEstimate", 0.0)),
        "lagd_learned_delay_std_seconds": float(getattr(live_delay, "lateralDelayEstimateStd", 0.0)),
      }
  except Exception as exception:
    print(f"Failed to parse LiveDelay stats: {exception}")
    return defaults

def get_population_value(population_str):
  if population_str is None:
    return None
  try:
    return int(str(population_str).replace(",", "").split(";")[0].strip())
  except Exception:
    return None

def search_nearby_major_cities(lat, lon, session, state_name, country_name):
  viewbox = f"{lon - SEARCH_RADIUS_DEGREES},{lat + SEARCH_RADIUS_DEGREES},{lon + SEARCH_RADIUS_DEGREES},{lat - SEARCH_RADIUS_DEGREES}"
  cities = (session.get(f"{BASE_URL}/search", params={
    "addressdetails": 1, "bounded": 1, "extratags": 1, "format": "jsonv2", "limit": 20, "q": "city", "viewbox": viewbox
  }, timeout=10).json() or [])

  qualifying = [c for c in cities if (get_population_value((c.get("extratags") or {}).get("population")) or 0) >= MINIMUM_POPULATION]
  if not qualifying:
    return None

  nearest = min(qualifying, key=lambda c: (float(c["lat"]) - lat) ** 2 + (float(c["lon"]) - lon) ** 2)
  addr = nearest.get("address") or {}
  return float(nearest["lat"]), float(nearest["lon"]), addr.get("city") or addr.get("town") or nearest.get("display_name", "").split(",")[0], state_name, country_name


def get_city_center(latitude, longitude):
  try:
    with requests.Session() as session:
      session.headers.update({"Accept-Language": "en"})
      session.headers.update({"User-Agent": "starpilot-city-center-checker/1.0 (https://github.com/FrogAi/StarPilot)"})

      response = session.get(f"{BASE_URL}/reverse", params={"addressdetails": 1, "extratags": 0, "format": "jsonv2", "lat": latitude, "lon": longitude, "namedetails": 0, "zoom": 14}, timeout=10)
      response.raise_for_status()
      data = response.json() or {}

      address = data.get("address") or {}
      city_name = address.get("city") or address.get("hamlet") or address.get("town") or address.get("village")
      country_code = (address.get("country_code") or "").lower()
      country_name = address.get("country") or "N/A"
      state_name = address.get("province") or address.get("region") or address.get("state") or address.get("state_district") or "N/A"

      if city_name:
        response = session.get(f"{BASE_URL}/search", params={"addressdetails": 1, "extratags": 1, "format": "jsonv2", "limit": 1, "q": f"{city_name}, {state_name}, {country_name}"}, timeout=10)
        response.raise_for_status()
        data = response.json() or []

        if data:
          tags = data[0]
          population_value = get_population_value((tags.get("extratags") or {}).get("population"))

          if population_value is not None and population_value >= MINIMUM_POPULATION:
            latitude_value = float(tags["lat"])
            longitude_value = float(tags["lon"])

            resolved_address = tags.get("address") or {}
            city_label = resolved_address.get("city") or resolved_address.get("town") or city_name

            return latitude_value, longitude_value, city_label, state_name, country_name

      nearby_result = search_nearby_major_cities(latitude, longitude, session, state_name, country_name)
      if nearby_result:
        return nearby_result

      query = f"{state_name} state capital" if country_code == "us" else f"capital of {state_name}, {country_name}"
      response = session.get(f"{BASE_URL}/search", params={"addressdetails": 1, "extratags": 1, "format": "jsonv2", "limit": 5, "q": query}, timeout=10)
      response.raise_for_status()
      candidates = response.json() or []

      chosen_candidate = None
      for candidate in candidates:
        address = candidate.get("address") or {}
        capital = (candidate.get("extratags") or {}).get("capital")
        country = address.get("country")
        state = address.get("province") or address.get("region") or address.get("state") or address.get("state_district")

        if (state == state_name or state_name == "N/A") and country == country_name and (capital in ("administrative", "state", "yes") or address.get("city") or address.get("town")):
          chosen_candidate = candidate
          break

      if not chosen_candidate and candidates:
        chosen_candidate = candidates[0]

      if chosen_candidate:
        latitude_value = float(chosen_candidate["lat"])
        longitude_value = float(chosen_candidate["lon"])

        chosen_address = chosen_candidate.get("address") or {}
        city_label = chosen_address.get("city") or chosen_address.get("town") or (chosen_candidate.get("display_name") or "").split(",")[0]

        return latitude_value, longitude_value, city_label, state_name, country_name

      print(f"Falling back to (0, 0) for {latitude}, {longitude}")
      return float(0.0), float(0.0), "N/A", "N/A", "N/A"

  except Exception as exception:
    print(f"Falling back to (0, 0) for {latitude}, {longitude}")
    return float(0.0), float(0.0), "N/A", "N/A", "N/A"

def update_branch_commits(now):
  points = []
  branch = get_build_metadata().channel  # Current running branch
  try:
    response = requests.get(f"https://api.github.com/repos/firestar5683/StarPilot/commits/{branch}")
    response.raise_for_status()
    sha = response.json()["sha"]
    points.append(Point("branch_commits").field("commit", sha).tag("branch", branch).time(now))
  except Exception as e:
    print(f"Failed to fetch commit for {branch}: {e}")

  return points

def is_up_to_date(build_metadata):
  remote_commit = run_cmd(["git", "ls-remote", "origin", build_metadata.channel], f"Fetched remote commit", "Failed to fetch remote commit", report=False)

  if remote_commit:
    return build_metadata.openpilot.git_commit == remote_commit.strip().split()[0]

  return True

def send_stats():
  try:
    build_metadata = get_build_metadata()
    starpilot_toggles = get_starpilot_toggles()

    frogs_go_moo = getattr(starpilot_toggles, "frogs_go_moo", False)
    if frogs_go_moo:
      return

    if starpilot_toggles.car_make == "mock":
      return

    bucket = "StarPilot"
    org_ID = "StarPilot"
    url = "https://stats.firestar.link"
    starpilot_stats = _json_object(params.get("StarPilotStats"))

    location = _json_object(params.get("LastGPSPosition"))
    if not (location.get("latitude") and location.get("longitude")):
      return
    original_latitude = location.get("latitude")
    original_longitude = location.get("longitude")
    latitude, longitude, city, state, country = get_city_center(original_latitude, original_longitude)

    theme_sources = [
      starpilot_toggles.icon_pack.replace("-animated", ""),
      starpilot_toggles.color_scheme,
      starpilot_toggles.distance_icons.replace("-animated", ""),
      starpilot_toggles.signal_icons.replace("-animated", ""),
      starpilot_toggles.sound_pack
    ]

    theme_counter = Counter(theme_sources)
    most_common = theme_counter.most_common()
    max_count = most_common[0][1]

    selected_theme = random.choice([item for item, count in most_common if count == max_count]).replace("-user_created", "").replace("_", " ")

    now = datetime.now(timezone.utc)

    device_type = HARDWARE.get_device_type()
    stats_dongle_id = params.get("StarPilotDongleId", encoding="utf-8") or params.get("DongleId", encoding="utf-8") or "unknown"
    live_delay_stats = get_live_delay_stats()

    user_point = (
      Point("user_stats")
      .tag("car_make", "GM" if starpilot_toggles.car_make == "gm" else starpilot_toggles.car_make.title())
      .tag("car_model", starpilot_toggles.car_model)
      .tag("city", city)
      .tag("country", country)
      .tag("device", device_type)
      .tag("device_generation", get_device_generation(device_type))
      .tag("driving_model", clean_model_name(starpilot_toggles.model_name))
      .tag("state", state)
      .tag("theme", selected_theme.title())
      .tag("branch", build_metadata.channel)
      .tag("dongle_id", stats_dongle_id)

      .field("blocked_user", False)
      .field("current_months_kilometers", int(starpilot_stats.get("CurrentMonthsKilometers", 0)))
      .field("event", 1)
      .field("starpilot_drives", int(starpilot_stats.get("StarPilotDrives", 0)))
      .field("starpilot_hours", float(starpilot_stats.get("StarPilotSeconds", 0)) / (60 * 60))
      .field("starpilot_miles", float(starpilot_stats.get("StarPilotMeters", 0)) * METER_TO_MILE)
      .field("goat_scream", starpilot_toggles.goat_scream_alert)
      .field("has_cc_long", starpilot_toggles.has_cc_long)
      .field("has_openpilot_longitudinal", starpilot_toggles.openpilot_longitudinal)
      .field("has_pedal", starpilot_toggles.has_pedal)
      .field("has_sdsu", starpilot_toggles.has_sdsu)
      .field("has_sascm", getattr(starpilot_toggles, "has_sascm", False))
      .field("has_zss", starpilot_toggles.has_zss)
      .field("latitude", latitude)
      .field("lagd_applied_delay_seconds", live_delay_stats["lagd_applied_delay_seconds"])
      .field("lagd_calibration_percent", live_delay_stats["lagd_calibration_percent"])
      .field("lagd_learned_delay_seconds", live_delay_stats["lagd_learned_delay_seconds"])
      .field("lagd_learned_delay_std_seconds", live_delay_stats["lagd_learned_delay_std_seconds"])
      .field("lagd_valid_blocks", live_delay_stats["lagd_valid_blocks"])
      .field("longitude", longitude)
      .field("rainbow_path", starpilot_toggles.rainbow_path)
      .field("random_events", starpilot_toggles.random_events)
      .field("total_aol_seconds", float(starpilot_stats.get("AOLTime", 0)))
      .field("total_lateral_seconds", float(starpilot_stats.get("LateralTime", 0)))
      .field("total_longitudinal_seconds", float(starpilot_stats.get("LongitudinalTime", 0)))
      .field("total_tracked_seconds", float(starpilot_stats.get("TrackedTime", 0)))
      .field("tuning_level", params.get_int("TuningLevel") + 1 if params.get_bool("TuningLevelConfirmed") else 0)
      .field("up_to_date", is_up_to_date(build_metadata))
      .field("using_stock_acc", not (starpilot_toggles.has_cc_long or starpilot_toggles.openpilot_longitudinal))

      .time(now)
    )

    all_points = [user_point] + update_branch_commits(now)

    client = InfluxDBClient(org=org_ID, token=org_ID, url=url)
    client.write_api(write_options=SYNCHRONOUS).write(bucket=bucket, org=org_ID, record=all_points)
    print("Successfully sent StarPilot stats!")
  except Exception as exception:
    print(f"Failed to send StarPilot stats: {exception}")
