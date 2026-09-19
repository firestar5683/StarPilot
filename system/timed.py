#!/usr/bin/env python3
import datetime
import os
import subprocess
import time
from typing import NoReturn

import cereal.messaging as messaging
from openpilot.common.time_helpers import min_date, MAX_DATE, system_time_valid
from openpilot.common.swaglog import cloudlog
from openpilot.common.params import Params
from openpilot.common.gps import get_gps_location_service
from openpilot.system.hardware import AGNOS

try:
  from timezonefinder import TimezoneFinder
except Exception:
  TimezoneFinder = None

try:
  from zoneinfo import ZoneInfo
except Exception:
  ZoneInfo = None

# StarPilot variables
# Hyundai/Kia cluster wall clock, local time. Fallback when GPS has no fix.
CAR_CLOCK_ADDR = 0x4F0
CAR_CLOCK_BUS = 1


def parse_car_clock(dat: bytes):
  # cluster sends all 0xFF until initialized
  if len(dat) < 7:
    return None
  if all(b == 0xFF for b in dat) or all(b == 0 for b in dat):
    return None

  hour, minute, second = dat[1], dat[2], dat[3]
  month = (dat[4] >> 2) & 0x0F
  year = 2000 + dat[5]
  day = dat[6]

  try:
    return datetime.datetime(year, month, day, hour, minute, second)
  except ValueError:
    return None


def read_car_clock(can_sock, timezone):
  latest = None
  for msg in messaging.drain_sock(can_sock):
    for frame in msg.can:
      if frame.address == CAR_CLOCK_ADDR and frame.src == CAR_CLOCK_BUS:
        parsed = parse_car_clock(bytes(frame.dat))
        if parsed is not None:
          latest = parsed

  if latest is None:
    return None

  utc = car_clock_to_utc(latest, timezone)
  if utc is None or not (min_date() <= utc <= MAX_DATE):
    return None
  return utc


def car_clock_to_utc(local_dt, timezone):
  # timezone comes from the last GPS fix, so this needs one to have happened once
  if ZoneInfo is None or not timezone:
    return None
  if isinstance(timezone, bytes):
    timezone = timezone.decode("utf-8", errors="replace")
  try:
    tz = ZoneInfo(timezone)
  except Exception:
    cloudlog.exception("timed.bad_timezone")
    return None
  # fold=0: on the duplicated hour of a DST fall back, assume the first pass
  return local_dt.replace(tzinfo=tz, fold=0).astimezone(datetime.UTC).replace(tzinfo=None)


def set_time(new_time):
  diff = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) - new_time
  if abs(diff) < datetime.timedelta(seconds=10):
    cloudlog.debug(f"Time diff too small: {diff}")
    return

  cloudlog.debug(f"Setting time to {new_time}")
  try:
    subprocess.run(f"TZ=UTC date -s '{new_time}'", shell=True, check=True)
  except subprocess.CalledProcessError:
    cloudlog.exception("timed.failed_setting_time")


# StarPilot variables
def set_timezone(timezone):
  valid_timezones = subprocess.check_output("timedatectl list-timezones", shell=True, encoding="utf8").strip().split("\n")
  if timezone not in valid_timezones:
    cloudlog.error(f"Timezone not supported {timezone}")
    return

  cloudlog.debug(f"Setting timezone to {timezone}")
  try:
    if AGNOS:
      tzpath = os.path.join("/usr/share/zoneinfo/", timezone)
      subprocess.check_call(f"sudo su -c 'ln -snf {tzpath} /data/etc/tmptime && mv /data/etc/tmptime /data/etc/localtime'", shell=True)
      subprocess.check_call(f"sudo su -c 'echo \'{timezone}\' > /data/etc/timezone'", shell=True)
    else:
      subprocess.check_call(f"sudo timedatectl set-timezone {timezone}", shell=True)
  except subprocess.CalledProcessError:
    cloudlog.exception(f"Error setting timezone to {timezone}")


def main() -> NoReturn:
  """
    timed has two responsibilities:
    - getting the current time from GPS
    - publishing the time in the logs

    AGNOS will also use NTP to update the time.
  """

  params = Params()
  gps_location_service = get_gps_location_service(params)

  pm = messaging.PubMaster(['clocks'])
  sm = messaging.SubMaster([gps_location_service])
  # StarPilot variables
  can_sock = messaging.sub_sock('can', timeout=100)

  # StarPilot variables
  tf = TimezoneFinder() if TimezoneFinder is not None else None
  timezonefinder_logged = False
  car_clock_tz_logged = False

  last_timezone = params.get("Timezone")
  if last_timezone is not None:
    set_timezone(last_timezone)

  while True:
    sm.update(1000)

    msg = messaging.new_message('clocks')
    msg.valid = system_time_valid()
    msg.clocks.wallTimeNanos = time.time_ns()
    pm.send('clocks', msg)

    gps = sm[gps_location_service]
    gps_time = datetime.datetime.fromtimestamp(gps.unixTimestampMillis / 1000., datetime.UTC).replace(tzinfo=None)
    gps_usable = (sm.updated[gps_location_service] and
                  (time.monotonic() - sm.logMonoTime[gps_location_service] / 1e9) <= 2.0 and
                  gps.hasFix and min_date() <= gps_time <= MAX_DATE)

    # StarPilot variables
    # only corrects an invalid clock, so GPS and NTP always win
    if not gps_usable and not system_time_valid():
      if not last_timezone and not car_clock_tz_logged:
        cloudlog.warning("timed: no saved timezone, cannot use car clock fallback")
        car_clock_tz_logged = True
      car_time = read_car_clock(can_sock, last_timezone)
      if car_time is not None:
        cloudlog.warning(f"timed: setting time from car clock: {car_time}")
        set_time(car_time)
      continue

    if not gps_usable:
      continue

    set_time(gps_time)

    # StarPilot variables
    if tf is not None:
      timezone = tf.timezone_at(lng=gps.longitude, lat=gps.latitude)
      if timezone is not None and timezone != last_timezone:
        set_timezone(timezone)
        params.put_nonblocking("Timezone", timezone)
        last_timezone = timezone
    elif not timezonefinder_logged:
      cloudlog.warning("TimezoneFinder unavailable, skipping automatic timezone updates")
      timezonefinder_logged = True

    time.sleep(10)

if __name__ == "__main__":
  main()
