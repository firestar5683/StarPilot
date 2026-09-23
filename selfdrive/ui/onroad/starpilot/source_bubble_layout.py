"""Pure layout decisions for the on-road speed-limit source bubble."""

import math
from collections.abc import Callable, Iterable, Mapping


SOURCE_DISPLAY_ORDER = ("Dashboard", "Map Data", "Vision", "Mapbox", "Upcoming")
SOURCE_PRIORITY_NAMES = frozenset(("Dashboard", "Map Data", "Vision"))


def enabled_source_titles(
  primary_priority: str,
  secondary_priority: str,
  *,
  vision_enabled: bool,
  mapbox_enabled: bool,
  dashboard_available: bool = True,
) -> tuple[str, ...]:
  """Return source rows that are eligible under the current SLC settings.

  ``Highest`` and ``Lowest`` are aggregate priority modes. They consider the
  two non-vision controller inputs directly; Vision is only a controller input
  when it is explicitly selected in one of the priority slots. Mapbox is a
  separate fallback toggle, and Next is derived from the selected map source.
  """
  if primary_priority in ("Highest", "Lowest"):
    enabled = {"Dashboard", "Map Data"}
  else:
    enabled = {
      source
      for source in (primary_priority, secondary_priority)
      if source in SOURCE_PRIORITY_NAMES
    }

  if not dashboard_available:
    enabled.discard("Dashboard")
  if not vision_enabled:
    enabled.discard("Vision")
  if mapbox_enabled:
    enabled.add("Mapbox")

  if "Map Data" in enabled:
    enabled.add("Upcoming")

  return tuple(source for source in SOURCE_DISPLAY_ORDER if source in enabled)


def source_content_metrics(row_count: int) -> tuple[int, int, int]:
  """Return logical text size, icon size, and icon gap for the visible rows."""
  if row_count <= 3:
    return 34, 39, 7
  if row_count == 4:
    return 30, 32, 7
  return 28, 30, 6


def visible_source_rows(
  source_defs: Iterable[tuple[str, str, str, str, str]],
  values: Mapping[str, float],
  active_source: str,
  enabled_sources: Iterable[str],
  active_only: bool = True,
) -> list[tuple[str, str, float, bool]]:
  """Return enabled source rows that possess a valid positive speed reading."""
  enabled = set(enabled_sources)
  rows = []
  for title, _abbrev, value_key, panel_label, icon_key in source_defs:
    if title not in enabled:
      continue
    value = values[value_key]
    has_reading = math.isfinite(value) and value > 0 and round(value) > 0
    if not has_reading:
      continue
    rows.append((
      panel_label,
      icon_key,
      value,
      active_source == title,
    ))
  return rows


def fit_source_label(
  full_label: str,
  compact_label: str,
  max_width: float,
  measure_width: Callable[[str], float],
) -> str:
  """Choose the longest useful label that leaves room for the value column."""
  for label in (full_label, compact_label):
    if measure_width(label) <= max_width:
      return label

  ellipsis = "…"
  candidate = compact_label or full_label
  while candidate and measure_width(candidate + ellipsis) > max_width:
    candidate = candidate[:-1]
  return f"{candidate}{ellipsis}" if candidate else ellipsis


def source_value_text(value: float) -> str:
  """Format a source speed, keeping missing and non-finite values explicit."""
  if not math.isfinite(value) or value <= 0:
    return "–"
  rounded = int(round(value))
  return "–" if rounded <= 0 else str(rounded)


def source_abbreviated_value_text(value: float) -> str:
  """Format a compact source value using the established missing-value marker."""
  value_text = source_value_text(value)
  return "X" if value_text == "–" else value_text
