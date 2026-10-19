from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import pyray as rl

from openpilot.common.constants import CV
from openpilot.common.params import Params
from openpilot.system.ui.lib.application import FontWeight, gui_app
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.text_measure import measure_text_cached


METER_TO_MILE = 1.0 / 1609.344
METER_TO_KILOMETER = 0.001
WEEKDAY_LABELS = ("M", "T", "W", "T", "F", "S", "S")

CARD_COLOR = rl.Color(18, 20, 29, 255)
CARD_BORDER = rl.Color(67, 57, 86, 255)
TEXT_COLOR = rl.Color(250, 248, 255, 255)
MUTED_COLOR = rl.Color(190, 186, 207, 255)
TRACK_COLOR = rl.Color(49, 51, 65, 255)
PURPLE = rl.Color(139, 108, 197, 255)
TEAL = rl.Color(94, 200, 200, 255)
GREEN = rl.Color(108, 197, 110, 255)


@dataclass
class DriveSummary:
  drives: int = 0
  distance: float = 0.0
  hours: float = 0.0
  unit: str = "miles"


@dataclass
class DailyDistance:
  label: str
  distance: float = 0.0
  is_today: bool = False
  is_future: bool = False


@dataclass
class PersonalRecord:
  title: str
  value: str
  detail: str


@dataclass
class DriveStatsData:
  all_time: DriveSummary = field(default_factory=DriveSummary)
  past_week: DriveSummary = field(default_factory=DriveSummary)
  this_week: DriveSummary = field(default_factory=DriveSummary)
  daily_distance: list[DailyDistance] = field(default_factory=list)
  records: list[PersonalRecord] = field(default_factory=list)


@dataclass
class _RouteStat:
  name: str
  date: datetime
  distance_meters: float
  duration: int
  engaged_seconds: float
  attention_known: bool
  clean: bool
  undistracted: bool
  time_source: str


def _json_object(value: Any) -> dict[str, Any]:
  if isinstance(value, dict):
    return value
  if isinstance(value, bytes):
    value = value.decode("utf-8", errors="replace")
  if isinstance(value, str):
    try:
      decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
      return {}
    return decoded if isinstance(decoded, dict) else {}
  return {}


def _number(value: Any, default: float = 0.0) -> float:
  try:
    parsed = float(value)
  except (TypeError, ValueError):
    return default
  return parsed if parsed == parsed else default


def _parse_date(value: Any) -> datetime | None:
  text = str(value or "").strip()
  if not text:
    return None
  try:
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
  except ValueError:
    return None
  if parsed.tzinfo is not None:
    parsed = parsed.astimezone().replace(tzinfo=None)
  return parsed


def _distance_from_meters(distance_meters: float, is_metric: bool) -> float:
  conversion = METER_TO_KILOMETER if is_metric else METER_TO_MILE
  return max(0.0, distance_meters) * conversion


def _cloud_summary(data: dict[str, Any], is_metric: bool) -> DriveSummary:
  distance = max(0.0, _number(data.get("distance", 0.0)))
  if is_metric:
    distance *= CV.MPH_TO_KPH
  return DriveSummary(
    drives=max(0, int(_number(data.get("routes", 0)))),
    distance=distance,
    hours=max(0.0, _number(data.get("minutes", 0.0)) / 60.0),
    unit="kilometers" if is_metric else "miles",
  )


def _summary_has_data(summary: DriveSummary) -> bool:
  return summary.drives > 0 or summary.distance > 0.0 or summary.hours > 0.0


def _route_counter(route_name: str) -> int | None:
  prefix = route_name.split("--", 1)[0]
  try:
    return int(prefix, 16) if len(prefix) == 8 else None
  except ValueError:
    return None


def _repair_filesystem_route_dates(routes: list[_RouteStat]) -> None:
  sequenced = [
    (counter, route)
    for route in routes
    if (counter := _route_counter(route.name)) is not None
  ]
  sequenced.sort(key=lambda item: item[0])
  if sum(route.time_source == "log" for _, route in sequenced) < 2:
    return

  previous_anchors = []
  previous_anchor = None
  for counter, route in sequenced:
    previous_anchors.append(previous_anchor)
    if route.time_source == "log":
      previous_anchor = (counter, route)

  following_anchors = [None] * len(sequenced)
  following_anchor = None
  for index in range(len(sequenced) - 1, -1, -1):
    counter, route = sequenced[index]
    following_anchors[index] = following_anchor
    if route.time_source == "log":
      following_anchor = (counter, route)

  for index, (counter, route) in enumerate(sequenced):
    if route.time_source != "filesystem":
      continue

    previous = previous_anchors[index]
    following = following_anchors[index]
    if previous is None or following is None:
      continue

    previous_counter, previous_route = previous
    following_counter, following_route = following
    if previous_route.date > following_route.date or previous_route.date <= route.date <= following_route.date:
      continue

    if following_counter == counter + 1:
      inferred = following_route.date - timedelta(seconds=route.duration + 5 * 60)
    elif previous_counter == counter - 1:
      inferred = previous_route.date + timedelta(seconds=previous_route.duration + 5 * 60)
    else:
      progress = (counter - previous_counter) / (following_counter - previous_counter)
      inferred = previous_route.date + (following_route.date - previous_route.date) * progress

    lower_bound = previous_route.date + timedelta(seconds=1)
    upper_bound = following_route.date - timedelta(seconds=1)
    route.date = min(max(inferred, lower_bound), upper_bound)


def _load_routes(galaxy_stats: dict[str, Any]) -> list[_RouteStat]:
  raw_routes = galaxy_stats.get("routes", {})
  if not isinstance(raw_routes, dict):
    return []

  ignored = galaxy_stats.get("ignoredRoutes", [])
  ignored_routes = {str(route) for route in ignored} if isinstance(ignored, list) else set()
  routes = []
  for route_name, entry in raw_routes.items():
    if route_name in ignored_routes or not isinstance(entry, dict):
      continue
    route_date = _parse_date(entry.get("date"))
    if route_date is None:
      continue

    attention_known = bool(entry.get("attentionKnown", True))
    distracted = max(0, int(_number(entry.get("distractedMoments", 0))))
    unresponsive = max(0, int(_number(entry.get("unresponsiveMoments", 0))))
    routes.append(_RouteStat(
      name=str(route_name),
      date=route_date,
      distance_meters=max(0.0, _number(entry.get("distanceMeters", 0.0))),
      duration=max(0, int(_number(entry.get("duration", 0)))),
      engaged_seconds=max(0.0, _number(entry.get("engagedSeconds", 0.0))),
      attention_known=attention_known,
      clean=bool(entry.get("clean", unresponsive == 0)),
      undistracted=bool(entry.get("undistracted", distracted == 0)),
      time_source=str(entry.get("timeSource", "") or ""),
    ))
  _repair_filesystem_route_dates(routes)
  return sorted(routes, key=lambda route: route.date)


def _route_summary(routes: list[_RouteStat], is_metric: bool) -> DriveSummary:
  return DriveSummary(
    drives=len(routes),
    distance=_distance_from_meters(sum(route.distance_meters for route in routes), is_metric),
    hours=sum(route.duration for route in routes) / 3600.0,
    unit="kilometers" if is_metric else "miles",
  )


def _date_label(date_value: Any) -> str:
  parsed = date_value if isinstance(date_value, datetime) else _parse_date(date_value)
  if parsed is None:
    return tr("No drives")
  date_format = "%b %d" if parsed.year == datetime.now().year else "%b %d, %Y"
  return parsed.strftime(date_format).replace(" 0", " ")


def _distance_record(distance_meters: float, is_metric: bool) -> str:
  distance = _distance_from_meters(distance_meters, is_metric)
  unit = tr("km") if is_metric else tr("mi")
  return f"{distance:.1f} {unit}"


def _duration_record(seconds: int) -> str:
  seconds = max(0, int(seconds))
  hours, remaining = divmod(seconds, 3600)
  minutes = remaining // 60
  if hours > 0:
    return f"{hours}h {minutes}m"
  return f"{minutes}m"


def _count_record(value: Any, singular: str, plural: str) -> str:
  count = max(0, int(_number(value, 0)))
  return f"{count} {tr(singular) if count == 1 else tr(plural)}"


def _longest_day_streak(routes: list[_RouteStat]) -> int:
  days = sorted({route.date.date() for route in routes})
  longest = current = 0
  previous = None
  for day in days:
    current = current + 1 if previous is not None and day == previous + timedelta(days=1) else 1
    longest = max(longest, current)
    previous = day
  return longest


def _computed_record_values(routes: list[_RouteStat]) -> dict[str, dict[str, Any]]:
  if not routes:
    return {}

  longest_drive = max(routes, key=lambda route: route.distance_meters)

  day_totals: dict[Any, dict[str, float]] = {}
  week_totals: dict[Any, float] = {}
  for route in routes:
    day = route.date.date()
    week = day - timedelta(days=day.weekday())
    day_totals.setdefault(day, {"duration": 0.0, "engaged": 0.0})
    day_totals[day]["duration"] += route.duration
    day_totals[day]["engaged"] += min(route.engaged_seconds, route.duration)
    week_totals[week] = week_totals.get(week, 0.0) + route.distance_meters

  most_engaged_day, most_engaged = max(
    day_totals.items(),
    key=lambda item: item[1]["engaged"] / item[1]["duration"] if item[1]["duration"] > 0 else 0.0,
  )
  engaged_percent = round(100 * most_engaged["engaged"] / most_engaged["duration"]) if most_engaged["duration"] > 0 else 0
  best_week, best_week_distance = max(week_totals.items(), key=lambda item: item[1])

  undistracted_routes = [route for route in routes if route.attention_known and route.undistracted]
  longest_undistracted = max(undistracted_routes, key=lambda route: route.duration) if undistracted_routes else None

  longest_clean_count = current_clean_count = 0
  longest_clean_start = longest_clean_end = None
  current_clean_start = None
  for route in routes:
    if route.attention_known and route.clean:
      current_clean_start = current_clean_start or route.date
      current_clean_count += 1
      if current_clean_count > longest_clean_count:
        longest_clean_count = current_clean_count
        longest_clean_start = current_clean_start
        longest_clean_end = route.date
    elif route.attention_known:
      current_clean_count = 0
      current_clean_start = None

  return {
    "longestDrive": {"distanceMeters": longest_drive.distance_meters, "date": longest_drive.date.isoformat()},
    "mostEngagedDay": {"percent": engaged_percent, "date": most_engaged_day.isoformat()},
    "bestWeek": {"distanceMeters": best_week_distance, "weekDate": best_week.isoformat()},
    "highestStreak": {"days": _longest_day_streak(routes)},
    "longestUndistractedDrive": {
      "duration": longest_undistracted.duration if longest_undistracted else 0,
      "date": longest_undistracted.date.isoformat() if longest_undistracted else "",
    },
    "cleanDriveStreak": {
      "drives": longest_clean_count,
      "startDate": longest_clean_start.isoformat() if longest_clean_start else "",
      "endDate": longest_clean_end.isoformat() if longest_clean_end else "",
    },
  }


def _record_source(galaxy_stats: dict[str, Any], routes: list[_RouteStat]) -> dict[str, dict[str, Any]]:
  computed = _computed_record_values(routes)
  persisted = galaxy_stats.get("personalRecords", {})
  if not isinstance(persisted, dict):
    return computed

  metric_keys = {
    "longestDrive": "distanceMeters",
    "mostEngagedDay": "percent",
    "bestWeek": "distanceMeters",
    "highestStreak": "days",
    "longestUndistractedDrive": "duration",
    "cleanDriveStreak": "drives",
  }
  result = dict(computed)
  for key, value in persisted.items():
    metric_key = metric_keys.get(key)
    current_value = result.get(key, {})
    if (
      isinstance(value, dict)
      and metric_key is not None
      and _number(value.get(metric_key, 0.0)) >= _number(current_value.get(metric_key, 0.0))
    ):
      result[key] = value
  return result


def _personal_records(galaxy_stats: dict[str, Any], routes: list[_RouteStat], is_metric: bool) -> list[PersonalRecord]:
  raw = _record_source(galaxy_stats, routes)

  longest = raw.get("longestDrive", {})
  best_week = raw.get("bestWeek", {})
  most_engaged = raw.get("mostEngagedDay", {})
  highest_streak = raw.get("highestStreak", {})
  undistracted = raw.get("longestUndistractedDrive", {})
  clean_streak = raw.get("cleanDriveStreak", {})

  best_week_date = _parse_date(best_week.get("weekDate"))
  highest_days = max(0, int(_number(highest_streak.get("days", 0))))
  undistracted_duration = max(0, int(_number(undistracted.get("duration", 0))))
  clean_drives = max(0, int(_number(clean_streak.get("drives", 0))))

  clean_start = _parse_date(clean_streak.get("startDate"))
  clean_end = _parse_date(clean_streak.get("endDate"))
  if clean_drives <= 0 or clean_start is None or clean_end is None:
    clean_detail = tr("No clean drives")
  else:
    clean_start_label = _date_label(clean_start)
    clean_end_label = _date_label(clean_end)
    clean_detail = clean_start_label if clean_start_label == clean_end_label else f"{clean_start_label} - {clean_end_label}"

  return [
    PersonalRecord(
      tr("Longest drive"),
      _distance_record(_number(longest.get("distanceMeters", 0.0)), is_metric),
      _date_label(longest.get("date")),
    ),
    PersonalRecord(
      tr("Most engaged day"),
      f"{max(0, int(_number(most_engaged.get('percent', 0))))}%",
      _date_label(most_engaged.get("date")),
    ),
    PersonalRecord(
      tr("Best week"),
      _distance_record(_number(best_week.get("distanceMeters", 0.0)), is_metric),
      f"{tr('Week of')} {_date_label(best_week_date)}" if best_week_date is not None else tr("No drives"),
    ),
    PersonalRecord(
      tr("Highest streak"),
      _count_record(highest_days, "day", "days"),
      tr("Consecutive drive days") if highest_days > 0 else tr("No drives"),
    ),
    PersonalRecord(
      tr("Longest undistracted drive"),
      _duration_record(undistracted_duration),
      _date_label(undistracted.get("date")) if undistracted_duration > 0 else tr("No clean drives"),
    ),
    PersonalRecord(
      tr("Clean-drive streak"),
      _count_record(clean_drives, "drive", "drives"),
      clean_detail,
    ),
  ]


def load_drive_stats_data(params: Params, now: datetime | None = None) -> DriveStatsData:
  now = now or datetime.now()
  if now.tzinfo is not None:
    now = now.astimezone().replace(tzinfo=None)

  is_metric = params.get_bool("IsMetric")
  unit = "kilometers" if is_metric else "miles"
  cloud_stats = _json_object(params.get("ApiCache_DriveStats"))
  starpilot_stats = _json_object(params.get("StarPilotStats"))
  galaxy_stats = _json_object(params.get("GalaxyDashboardStats"))
  routes = _load_routes(galaxy_stats)

  all_time = _cloud_summary(_json_object(cloud_stats.get("all")), is_metric)
  if not _summary_has_data(all_time):
    all_time = DriveSummary(
      drives=max(0, int(_number(starpilot_stats.get("StarPilotDrives", 0)))),
      distance=_distance_from_meters(_number(starpilot_stats.get("StarPilotMeters", 0.0)), is_metric),
      hours=max(0.0, _number(starpilot_stats.get("StarPilotSeconds", 0.0)) / 3600.0),
      unit=unit,
    )

  past_week = _cloud_summary(_json_object(cloud_stats.get("week")), is_metric)
  if not _summary_has_data(past_week):
    earliest_day = now.date() - timedelta(days=6)
    past_week = _route_summary([route for route in routes if earliest_day <= route.date.date() <= now.date()], is_metric)

  week_start = now.date() - timedelta(days=now.weekday())
  week_end = week_start + timedelta(days=7)
  this_week_routes = [route for route in routes if week_start <= route.date.date() < week_end]
  this_week = _route_summary(this_week_routes, is_metric)

  daily = []
  for day_index in range(7):
    day = week_start + timedelta(days=day_index)
    distance_meters = sum(route.distance_meters for route in this_week_routes if route.date.date() == day)
    daily.append(DailyDistance(
      label=WEEKDAY_LABELS[day_index],
      distance=_distance_from_meters(distance_meters, is_metric),
      is_today=day == now.date(),
      is_future=day > now.date(),
    ))

  return DriveStatsData(
    all_time=all_time,
    past_week=past_week,
    this_week=this_week,
    daily_distance=daily,
    records=_personal_records(galaxy_stats, routes, is_metric),
  )


def demo_drive_stats_data(is_metric: bool, now: datetime | None = None) -> DriveStatsData:
  now = now or datetime.now()
  distance_scale = CV.MPH_TO_KPH if is_metric else 1.0
  unit = "kilometers" if is_metric else "miles"
  daily_miles = (19.4, 43.2, 28.6, 51.8, 12.7, 35.1, 8.9)

  daily = [
    DailyDistance(
      label=WEEKDAY_LABELS[index],
      distance=distance * distance_scale,
      is_today=index == now.weekday(),
    )
    for index, distance in enumerate(daily_miles)
  ]

  longest_drive_meters = 218.7 / METER_TO_MILE
  best_week_meters = 812.4 / METER_TO_MILE
  return DriveStatsData(
    all_time=DriveSummary(drives=584, distance=14632.8 * distance_scale, hours=419.0, unit=unit),
    past_week=DriveSummary(drives=18, distance=347.6 * distance_scale, hours=11.8, unit=unit),
    this_week=DriveSummary(drives=7, distance=sum(daily_miles) * distance_scale, hours=6.9, unit=unit),
    daily_distance=daily,
    records=[
      PersonalRecord(tr("Longest drive"), _distance_record(longest_drive_meters, is_metric), _date_label(now - timedelta(days=64))),
      PersonalRecord(tr("Most engaged day"), "96%", _date_label(now - timedelta(days=22))),
      PersonalRecord(tr("Best week"), _distance_record(best_week_meters, is_metric), f"{tr('Week of')} {_date_label(now - timedelta(days=105))}"),
      PersonalRecord(tr("Highest streak"), f"19 {tr('days')}", tr("Consecutive drive days")),
      PersonalRecord(tr("Longest undistracted drive"), "3h 34m", _date_label(now - timedelta(days=38))),
      PersonalRecord(
        tr("Clean-drive streak"),
        f"27 {tr('drives')}",
        f"{_date_label(now - timedelta(days=80))} - {_date_label(now - timedelta(days=59))}",
      ),
    ],
  )


def _format_count(value: int) -> str:
  if value >= 10000:
    return f"{value / 1000:.1f}k"
  return f"{value:,}"


def _format_decimal(value: float) -> str:
  if value >= 10000:
    return f"{value / 1000:.1f}k"
  if value >= 100:
    return f"{value:,.0f}"
  return f"{value:.1f}"


class DriveStatsDashboard:
  def __init__(self, params: Params):
    self._params = params
    self._data = DriveStatsData()
    self._font_bold = gui_app.font(FontWeight.BOLD)
    self._font_semi_bold = gui_app.font(FontWeight.SEMI_BOLD)
    self._font_medium = gui_app.font(FontWeight.MEDIUM)
    self.refresh()

  def refresh(self) -> None:
    demo_enabled = os.getenv("SP_C3_FAKE_DRIVE_STATS", "0").lower() in ("1", "true", "yes", "on")
    self._data = demo_drive_stats_data(self._params.get_bool("IsMetric")) if demo_enabled else load_drive_stats_data(self._params)

  @staticmethod
  def _draw_card(rect: rl.Rectangle, accent: rl.Color | None = None) -> None:
    rl.draw_rectangle_rounded(rect, 0.04, 12, CARD_COLOR)
    rl.draw_rectangle_rounded_lines_ex(rect, 0.04, 12, 2, CARD_BORDER)
    if accent is not None:
      accent_rect = rl.Rectangle(rect.x + 18, rect.y + 12, rect.width - 36, 5)
      rl.draw_rectangle_rounded(accent_rect, 1.0, 8, accent)

  @staticmethod
  def _draw_week_bar(rect: rl.Rectangle) -> None:
    x = int(round(rect.x))
    y = int(round(rect.y))
    width = max(1, int(round(rect.width)))
    height = max(1, int(round(rect.height)))
    radius = max(1, min(6, width // 2, height // 2))

    blend = radius / height
    body_top = rl.Color(
      round(PURPLE.r + (TEAL.r - PURPLE.r) * blend),
      round(PURPLE.g + (TEAL.g - PURPLE.g) * blend),
      round(PURPLE.b + (TEAL.b - PURPLE.b) * blend),
      255,
    )

    rl.draw_circle(x + radius, y + radius, radius, PURPLE)
    rl.draw_circle(x + width - radius, y + radius, radius, PURPLE)
    rl.draw_rectangle(x + radius, y, max(1, width - 2 * radius), radius + 1, PURPLE)
    rl.draw_rectangle_gradient_v(x, y + radius, width, max(1, height - radius), body_top, TEAL)

  @staticmethod
  def _draw_record_icon(index: int, rect: rl.Rectangle) -> None:
    rl.draw_rectangle_rounded(rect, 0.18, 8, rl.Color(40, 33, 68, 255))
    cx = rect.x + rect.width / 2
    cy = rect.y + rect.height / 2
    color = PURPLE
    scale = min(rect.width, rect.height) / 64.0
    thickness = 2.5 * scale

    def line(x1: float, y1: float, x2: float, y2: float) -> None:
      rl.draw_line_ex(rl.Vector2(x1, y1), rl.Vector2(x2, y2), thickness, color)

    if index == 0:
      line(cx - 13 * scale, cy, cx + 12 * scale, cy)
      line(cx + 12 * scale, cy, cx + 5 * scale, cy - 7 * scale)
      line(cx + 12 * scale, cy, cx + 5 * scale, cy + 7 * scale)
    elif index == 1:
      rl.draw_circle_lines(int(cx), int(cy), 13 * scale, color)
      rl.draw_circle_lines(int(cx), int(cy), 12 * scale, color)
      line(cx - 7 * scale, cy, cx - 2 * scale, cy + 5 * scale)
      line(cx - 2 * scale, cy + 5 * scale, cx + 8 * scale, cy - 7 * scale)
    elif index == 2:
      line(cx - 13 * scale, cy - 12 * scale, cx - 13 * scale, cy + 12 * scale)
      line(cx - 13 * scale, cy + 12 * scale, cx + 13 * scale, cy + 12 * scale)
      line(cx - 9 * scale, cy + 6 * scale, cx - 2 * scale, cy - 2 * scale)
      line(cx - 2 * scale, cy - 2 * scale, cx + 4 * scale, cy + 3 * scale)
      line(cx + 4 * scale, cy + 3 * scale, cx + 13 * scale, cy - 8 * scale)
    elif index == 3:
      points = (
        (cx + 2 * scale, cy - 15 * scale), (cx - 10 * scale, cy + 2 * scale), (cx - 2 * scale, cy + 2 * scale),
        (cx - 5 * scale, cy + 15 * scale), (cx + 11 * scale, cy - 5 * scale), (cx + 3 * scale, cy - 5 * scale),
      )
      for point_index, point in enumerate(points):
        next_point = points[(point_index + 1) % len(points)]
        line(point[0], point[1], next_point[0], next_point[1])
    elif index == 4:
      points = (
        (cx, cy - 14 * scale), (cx + 12 * scale, cy - 9 * scale), (cx + 10 * scale, cy + 3 * scale),
        (cx, cy + 14 * scale), (cx - 10 * scale, cy + 3 * scale), (cx - 12 * scale, cy - 9 * scale),
      )
      for point_index, point in enumerate(points):
        next_point = points[(point_index + 1) % len(points)]
        line(point[0], point[1], next_point[0], next_point[1])
      line(cx - 5 * scale, cy, cx - scale, cy + 4 * scale)
      line(cx - scale, cy + 4 * scale, cx + 6 * scale, cy - 4 * scale)
    else:
      def sparkle(x: float, y: float, radius: float) -> None:
        inner = radius * 0.22
        points = (
          (x, y - radius), (x + inner, y - inner),
          (x + radius, y), (x + inner, y + inner),
          (x, y + radius), (x - inner, y + inner),
          (x - radius, y), (x - inner, y - inner),
        )
        for point_index, point in enumerate(points):
          next_point = points[(point_index + 1) % len(points)]
          line(point[0], point[1], next_point[0], next_point[1])

      sparkle(cx + 3 * scale, cy + 2 * scale, 10 * scale)
      sparkle(cx - 9 * scale, cy - 9 * scale, 5 * scale)
      sparkle(cx + 12 * scale, cy - 10 * scale, 4 * scale)

  def _draw_fitted_centered(self, text: str, rect: rl.Rectangle, font_size: int, minimum_size: int, color: rl.Color) -> None:
    size = font_size
    while size > minimum_size and measure_text_cached(self._font_bold, text, size).x > rect.width:
      size -= 2
    text_size = measure_text_cached(self._font_bold, text, size)
    position = rl.Vector2(
      rect.x + (rect.width - text_size.x) / 2,
      rect.y + (rect.height - text_size.y) / 2,
    )
    rl.draw_text_ex(self._font_bold, text, position, size, 0, color)

  def _draw_summary_card(self, rect: rl.Rectangle, title: str, summary: DriveSummary, accent: rl.Color) -> None:
    self._draw_card(rect, accent)
    title_pos = rl.Vector2(rect.x + 24, rect.y + 28)
    rl.draw_text_ex(self._font_semi_bold, title, title_pos, 30, 0, MUTED_COLOR)

    values = (
      (_format_count(summary.drives), tr("drives")),
      (_format_decimal(summary.distance), tr("km") if summary.unit == "kilometers" else tr("miles")),
      (_format_decimal(summary.hours), tr("hours")),
    )
    column_width = (rect.width - 32) / len(values)
    for index, (value, label) in enumerate(values):
      if index > 0:
        divider_x = rect.x + 16 + index * column_width
        rl.draw_line_ex(
          rl.Vector2(divider_x, rect.y + 76),
          rl.Vector2(divider_x, rect.y + rect.height - 23),
          2,
          TRACK_COLOR,
        )

      column_rect = rl.Rectangle(rect.x + 16 + index * column_width, rect.y + 64, column_width, 72)
      self._draw_fitted_centered(value, column_rect, 48, 30, TEXT_COLOR)
      label_size = measure_text_cached(self._font_medium, label, 23)
      label_pos = rl.Vector2(
        column_rect.x + (column_rect.width - label_size.x) / 2,
        rect.y + rect.height - 38,
      )
      rl.draw_text_ex(self._font_medium, label, label_pos, 23, 0, MUTED_COLOR)

  def render_overview(self, rect: rl.Rectangle) -> None:
    gap = 18
    summary_height = 184
    card_width = (rect.width - gap) / 2
    summaries = (
      (tr("ALL TIME"), self._data.all_time, PURPLE),
      (tr("PAST WEEK"), self._data.past_week, TEAL),
    )
    for index, (title, summary, accent) in enumerate(summaries):
      card_rect = rl.Rectangle(rect.x + index * (card_width + gap), rect.y, card_width, summary_height)
      self._draw_summary_card(card_rect, title, summary, accent)

    graph_rect = rl.Rectangle(rect.x, rect.y + summary_height + gap, rect.width, rect.height - summary_height - gap)
    self._draw_distance_graph(graph_rect)

  def _draw_distance_graph(self, rect: rl.Rectangle) -> None:
    self._draw_card(rect)
    title = tr("DISTANCE THIS WEEK")
    rl.draw_text_ex(self._font_semi_bold, title, rl.Vector2(rect.x + 30, rect.y + 26), 32, 0, TEXT_COLOR)

    unit = tr("km") if self._data.this_week.unit == "kilometers" else tr("miles")
    total_text = f"{_format_decimal(self._data.this_week.distance)} {unit}"
    total_size = measure_text_cached(self._font_bold, total_text, 34)
    rl.draw_text_ex(
      self._font_bold,
      total_text,
      rl.Vector2(rect.x + rect.width - total_size.x - 30, rect.y + 24),
      34,
      0,
      TEAL,
    )

    plot = rl.Rectangle(rect.x + 42, rect.y + 92, rect.width - 84, rect.height - 142)
    for line_index in range(4):
      y = plot.y + line_index * plot.height / 3
      rl.draw_line(int(plot.x), int(y), int(plot.x + plot.width), int(y), TRACK_COLOR)

    max_distance = max((day.distance for day in self._data.daily_distance), default=0.0)
    max_distance = max(max_distance, 1.0)
    slot_width = plot.width / max(len(self._data.daily_distance), 1)
    bar_width = min(78.0, slot_width * 0.52)
    value_headroom = 48.0
    bar_area_height = max(1.0, plot.height - value_headroom)
    for index, day in enumerate(self._data.daily_distance):
      center_x = plot.x + slot_width * (index + 0.5)
      bar_height = max(5.0, bar_area_height * day.distance / max_distance) if day.distance > 0.0 else 5.0
      bar_rect = rl.Rectangle(center_x - bar_width / 2, plot.y + plot.height - bar_height, bar_width, bar_height)
      self._draw_week_bar(bar_rect)

      if day.distance > 0.0:
        value_text = _format_decimal(day.distance)
        value_size = measure_text_cached(self._font_medium, value_text, 26)
        value_y = max(plot.y + 4, bar_rect.y - value_size.y - 8)
        rl.draw_text_ex(
          self._font_medium,
          value_text,
          rl.Vector2(center_x - value_size.x / 2, value_y),
          26,
          0,
          MUTED_COLOR,
        )

      label_color = TEXT_COLOR if day.is_today else MUTED_COLOR
      label_size = measure_text_cached(self._font_semi_bold, day.label, 28)
      label_pos = rl.Vector2(center_x - label_size.x / 2, plot.y + plot.height + 16)
      rl.draw_text_ex(self._font_semi_bold, day.label, label_pos, 28, 0, label_color)

  def render_records(self, rect: rl.Rectangle) -> None:
    self._draw_card(rect)
    rl.draw_text_ex(
      self._font_semi_bold,
      tr("PERSONAL RECORDS"),
      rl.Vector2(rect.x + 30, rect.y + 26),
      32,
      0,
      TEXT_COLOR,
    )

    displayed_records = [
      (record_index, self._data.records[record_index])
      for record_index in (0, 3, 5)
      if record_index < len(self._data.records)
    ]
    header_height = 82
    row_height = (rect.height - header_height - 12) / max(len(displayed_records), 1)
    for row_index, (record_index, record) in enumerate(displayed_records):
      row_y = rect.y + header_height + row_index * row_height
      if row_index > 0:
        rl.draw_line(int(rect.x + 24), int(row_y), int(rect.x + rect.width - 24), int(row_y), TRACK_COLOR)

      icon_size = min(120.0, row_height - 34)
      icon_rect = rl.Rectangle(rect.x + 28, row_y + (row_height - icon_size) / 2, icon_size, icon_size)
      self._draw_record_icon(record_index, icon_rect)

      text_x = rect.x + 170
      content_center_y = row_y + row_height / 2
      title_pos = rl.Vector2(text_x, content_center_y - 66)
      rl.draw_text_ex(self._font_medium, record.title, title_pos, 38, 0, MUTED_COLOR)

      value_pos = rl.Vector2(text_x, content_center_y - 10)
      rl.draw_text_ex(self._font_bold, record.value, value_pos, 56, 0, TEXT_COLOR)

      detail_font_size = 34
      detail_min_x = text_x + 250
      detail_width = rect.x + rect.width - detail_min_x - 30
      while detail_font_size > 29 and measure_text_cached(self._font_medium, record.detail, detail_font_size).x > detail_width:
        detail_font_size -= 1
      detail_size = measure_text_cached(self._font_medium, record.detail, detail_font_size)
      detail_x = rect.x + rect.width - detail_size.x - 30
      detail_pos = rl.Vector2(detail_x, content_center_y + 52)
      rl.draw_text_ex(self._font_medium, record.detail, detail_pos, detail_font_size, 0, MUTED_COLOR)
