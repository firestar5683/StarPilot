"""Covers assets/components/recordings/dashcam_routes_helpers.js.

The helpers are browser ES modules, so pytest drives them through node rather than
re-implementing the date/sort/grouping rules in Python. Snippets run with helper
exports in scope and return JSON, which keeps every assertion here in pytest.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

HELPERS_PATH = Path(__file__).resolve().parent.parent / "assets" / "components" / "recordings" / "dashcam_routes_helpers.js"
COMPONENT_PATH = HELPERS_PATH.with_name("dashcam_routes.js")
COMPONENT_CSS_PATH = HELPERS_PATH.with_name("dashcam_routes.css")

# node infers ESM from `export` syntax in a bare .js file from 22.7 on, so the helpers
# need no package.json and stay a normal asset next to the component that imports them.
MIN_NODE_MAJOR = 23

HARNESS = f'''
import * as helpers from {json.dumps(HELPERS_PATH.as_uri())}
const run = new Function(...Object.keys(helpers), process.env.DASHCAM_HELPER_SNIPPET)
process.stdout.write(JSON.stringify(run(...Object.values(helpers)) ?? null))
'''

PRELUDE = '''
const route = (name, startedAt, extra = {}) => normalizeRoute({
  name,
  startedAt,
  timestamp: startedAt,
  segmentCount: 1,
  approxDurationSeconds: 60,
  is_preserved: false,
  ...extra,
}, "en-US")
'''


def _node_binary():
  node = shutil.which("node")
  if node is None:
    pytest.skip("node is not installed")

  version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
  try:
    major = int(version.lstrip("v").split(".")[0])
  except ValueError:
    pytest.skip(f"could not read node version from {version!r}")
  if major < MIN_NODE_MAJOR:
    pytest.skip(f"node {version} cannot import a bare .js ES module; need v{MIN_NODE_MAJOR}+")
  return node


def evaluate(snippet):
  """Run a snippet with the helper exports in scope and return its JSON value."""
  node = _node_binary()
  # Fixed TZ so "Today"/"Yesterday" grouping does not depend on the developer's clock.
  environment = {**os.environ, "TZ": "UTC", "DASHCAM_HELPER_SNIPPET": PRELUDE + snippet}
  result = subprocess.run([node, "--input-type=module"], input=HARNESS, env=environment,
                          capture_output=True, text=True, timeout=60)
  assert result.returncode == 0, result.stderr
  return json.loads(result.stdout)


def test_helpers_module_is_a_plain_js_asset():
  assert HELPERS_PATH.is_file()
  assert not list(HELPERS_PATH.parent.glob("*.mjs"))


def test_route_titles_and_custom_name_badges_are_reactive():
  source = COMPONENT_PATH.read_text(encoding="utf-8")

  # Both grid and row views must subscribe directly to the renamed route fields.
  assert source.count('${() => route.displayName}') >= 4
  assert source.count('${() => route.isCustomName ? html`') >= 4


def test_sort_order_select_and_route_items_are_keyed_and_reactive():
  source = COMPONENT_PATH.read_text(encoding="utf-8")

  assert '<select value="${() => state.sortOrder}" @input="${changeSortOrder}" @change="${changeSortOrder}">' in source
  assert 'data-view-key="${renderKey}"' in source
  assert ".key(group.key)" in source
  assert ".key(route.name)" in source


def test_player_shell_keeps_both_quality_levels_at_one_fixed_size():
  source = COMPONENT_CSS_PATH.read_text(encoding="utf-8")
  component = COMPONENT_PATH.read_text(encoding="utf-8")

  assert "aspect-ratio: 526 / 330;" in source
  assert "contain: layout paint;" in source
  assert "height: 100% !important;" in source
  assert "width: 100% !important;" in source
  assert "object-fit: cover;" in source
  assert ".dashcam-video-shell.qcamera-framing video" in source
  assert "object-fit: fill;" in source
  assert 'videoShell.classList.toggle("qcamera-framing", showingPreview)' in component
  assert "deferNativeControlsUntilInteraction" not in component
  assert "stagingVideo.controls = true" in component


def test_groups_routes_into_today_yesterday_dates_and_unknown():
  groups = evaluate('''
    const routes = [
      route("today", "2026-08-26T08:00:00Z"),
      route("yesterday", "2026-08-25T08:00:00Z"),
      route("older", "2026-08-20T08:00:00Z"),
      route("unknown", null, { timestamp: null }),
    ]
    return groupRoutesByDate(routes, new Date("2026-08-26T12:00:00Z"), "en-US")
      .map(group => [group.label, group.routes[0].name])
  ''')

  assert groups == [
    ["Today", "today"],
    ["Yesterday", "yesterday"],
    ["August 20, 2026", "older"],
    ["Unknown date", "unknown"],
  ]


def test_sorts_newest_and_oldest_while_leaving_unknown_dates_last():
  order = evaluate('''
    const routes = [
      route("middle", "2026-08-20T08:00:00Z"),
      route("unknown", null, { timestamp: null }),
      route("new", "2026-08-26T08:00:00Z"),
      route("old", "2026-08-10T08:00:00Z"),
    ]
    return {
      newest: sortRoutes(routes, "newest").map(item => item.name),
      oldest: sortRoutes(routes, "oldest").map(item => item.name),
    }
  ''')

  assert order["newest"] == ["new", "middle", "old", "unknown"]
  assert order["oldest"] == ["old", "middle", "new", "unknown"]


def test_searches_custom_names_displayed_dates_and_route_ids():
  matches = evaluate('''
    const custom = route("0000006a--9f0a7bdf9c", "2026-08-26T08:00:00Z", {
      timestamp: "Morning school run",
      isCustomName: true,
    })
    return ["school", "August 26", "9f0a7b", "evening"]
      .map(searchQuery => buildRouteView([custom], { searchQuery }).matching.length)
  ''')

  assert matches == [1, 1, 1, 0]


def test_search_matches_partial_title_tokens_and_friendly_dates_as_the_user_types():
  result = evaluate('''
    const routes = [
      route("0000006a--9f0a7bdf9c", "2026-08-27T08:00:00Z", { timestamp: "Test_31", isCustomName: true }),
      route("0000006b--9f0a7bdf9d", "2026-08-28T08:00:00Z", { timestamp: "Morning drive", isCustomName: true }),
      route("0000006c--9f0a7bdf9e", "2026-09-27T08:00:00Z", { timestamp: "Test_4", isCustomName: true }),
    ]
    return ["test", "test 3", "aug", "aug 2", "aug 27th", "8/27"]
      .map(searchQuery => buildRouteView(routes, { searchQuery }).matching.map(item => item.name))
  ''')

  assert result == [
    ["0000006c--9f0a7bdf9e", "0000006a--9f0a7bdf9c"],
    ["0000006a--9f0a7bdf9c"],
    ["0000006b--9f0a7bdf9d", "0000006a--9f0a7bdf9c"],
    ["0000006b--9f0a7bdf9d", "0000006a--9f0a7bdf9c"],
    ["0000006a--9f0a7bdf9c"],
    ["0000006a--9f0a7bdf9c"],
  ]


def test_partial_day_does_not_match_the_four_digit_year():
  result = evaluate('''
    const routes = Array.from({ length: 9 }, (_, offset) => {
      const day = 19 + offset
      return route(`aug-${day}`, `2026-08-${day}T12:00:00Z`)
    })
    return {
      partial: buildRouteView(routes, { searchQuery: "aug 2" }).matching.map(item => item.name),
      complete: buildRouteView(routes, { searchQuery: "aug 20" }).matching.map(item => item.name),
    }
  ''')

  assert result == {
    "partial": ["aug-27", "aug-26", "aug-25", "aug-24", "aug-23", "aug-22", "aug-21", "aug-20"],
    "complete": ["aug-20"],
  }


def test_route_search_input_updates_on_every_keystroke():
  source = COMPONENT_PATH.read_text(encoding="utf-8")

  assert '@input="${event => { state.searchQuery = event.target.value }}"' in source


def test_route_summary_only_shows_loading_or_active_search_status():
  source = COMPONENT_PATH.read_text(encoding="utf-8")

  assert "const hasActiveSearch = Boolean(state.searchQuery.trim())" in source
  assert '${state.loading || hasActiveSearch ? html`' in source
  assert '${hasActiveSearch ? html`<span>${view.matching.length} matching drive' in source
  assert '${state.loading ? html`<span>Loading routes</span>` : ""}' in source
  assert "Loading ${state.progress} of ${state.total}" not in source
  assert "total local" not in source


def test_search_indexes_the_displayed_time_for_every_route():
  result = evaluate('''
    const routes = [
      route("0000006a--9f0a7bdf9c", "2026-08-27T12:15:00Z"),
      route("0000006b--9f0a7bdf9d", "2026-08-27T12:50:00Z"),
      route("0000006c--9f0a7bdf9e", "2026-08-27T13:05:00Z"),
    ]
    return ["12", "12:5", "12:15"]
      .map(searchQuery => buildRouteView(routes, { searchQuery }).matching.map(item => item.name))
  ''')

  assert result == [
    ["0000006b--9f0a7bdf9d", "0000006a--9f0a7bdf9c"],
    ["0000006b--9f0a7bdf9d"],
    ["0000006a--9f0a7bdf9c"],
  ]


def test_short_numeric_search_does_not_match_hidden_ids_or_unrelated_dates():
  result = evaluate('''
    const routes = [
      route("00000012--9f0a7bdf9c", "2026-08-27T13:05:00Z", { timestamp: "Morning drive", isCustomName: true }),
      route("0000006b--9f0a7bdf9d", "2026-12-12T13:05:00Z", { timestamp: "Afternoon drive", isCustomName: true }),
      route("0000006c--9f0a7bdf9e", "2026-08-27T13:05:00Z", { timestamp: "Test_12", isCustomName: true }),
    ]
    return {
      plainNumber: buildRouteView(routes, { searchQuery: "12" }).matching.map(item => item.name),
      ordinalDate: buildRouteView(routes, { searchQuery: "dec 12th" }).matching.map(item => item.name),
      explicitId: buildRouteView(routes, { searchQuery: "00000012" }).matching.map(item => item.name),
    }
  ''')

  assert result == {
    "plainNumber": ["0000006c--9f0a7bdf9e"],
    "ordinalDate": ["0000006b--9f0a7bdf9d"],
    "explicitId": ["00000012--9f0a7bdf9c"],
  }


def test_filters_preserved_routes_before_applying_the_render_limit():
  view = evaluate('''
    const routes = Array.from({ length: MAX_RENDERED_ROUTES + 25 }, (_, index) => route(
      `route-${index}`,
      new Date(Date.UTC(2026, 0, 1, 0, index)).toISOString(),
      { is_preserved: index % 2 === 0 },
    ))
    const all = buildRouteView(routes)
    const preserved = buildRouteView(routes, { preservedOnly: true })
    return {
      limit: MAX_RENDERED_ROUTES,
      all: [all.matching.length, all.visible.length, all.truncated],
      preserved: [preserved.matching.length, preserved.visible.length, preserved.truncated],
      allPreserved: preserved.visible.every(item => item.is_preserved),
    }
  ''')

  assert view["limit"] == 250
  assert view["all"] == [275, 250, True]
  assert view["preserved"] == [138, 138, False]
  assert view["allPreserved"] is True


def test_duration_sorts_render_as_one_flat_group():
  result = evaluate("""
    const routes = [
      { name: "a", _startedAtMs: Date.parse("2026-08-20T10:00:00Z"), approxDurationSeconds: 3000 },
      { name: "b", _startedAtMs: Date.parse("2026-08-22T10:00:00Z"), approxDurationSeconds: 2700 },
      { name: "c", _startedAtMs: Date.parse("2026-08-21T10:00:00Z"), approxDurationSeconds: 1800 },
    ]
    const view = buildRouteView(routes, { sortOrder: "longest" })
    const groups = groupRoutesForView(view.visible, "longest", new Date("2026-08-27T12:00:00Z"), "en-US")
    return { labels: groups.map(g => g.label), order: groups.flatMap(g => g.routes.map(r => r.name)) }
  """)

  assert result["labels"] == ["Longest first"]
  assert result["order"] == ["a", "b", "c"]


def test_date_sorts_still_group_by_day():
  labels = evaluate("""
    const routes = [
      { name: "a", _startedAtMs: Date.parse("2026-08-20T10:00:00Z"), approxDurationSeconds: 3000 },
      { name: "b", _startedAtMs: Date.parse("2026-08-22T10:00:00Z"), approxDurationSeconds: 2700 },
    ]
    const view = buildRouteView(routes, { sortOrder: "newest" })
    return groupRoutesForView(view.visible, "newest", new Date("2026-08-27T12:00:00Z"), "en-US").map(g => g.label)
  """)

  assert labels == ["August 22, 2026", "August 20, 2026"]


def test_route_view_render_key_changes_with_displayed_order_and_mode():
  result = evaluate('''
    const routes = [{ name: "a" }, { name: "b" }]
    return [
      routeViewRenderKey(routes, "newest", "list"),
      routeViewRenderKey([...routes].reverse(), "oldest", "list"),
      routeViewRenderKey(routes, "newest", "grid"),
    ]
  ''')

  assert result == ["list:newest:a,b", "list:oldest:b,a", "grid:newest:a,b"]


def test_grouping_an_empty_list_yields_no_groups():
  assert evaluate("""
    return [
      groupRoutesForView([], "longest").length,
      groupRoutesForView([], "newest").length,
    ]
  """) == [0, 0]


def test_segment_status_reports_the_stored_segment_number():
  statuses = evaluate('''
    const segments = [
      "/video/0000006a--9f0a7bdf9c--0",
      "/video/0000006a--9f0a7bdf9c--3",
      "/video/0000006a--9f0a7bdf9c--11",
    ]
    return segments.map((_, index) => getSegmentStatus(segments, index))
  ''')

  assert statuses == ["Segment 0", "Segment 3", "Segment 11"]


def test_segment_options_label_every_clip_for_the_jump_picker():
  options = evaluate("""
    return getSegmentOptions([
      "/video/0000006a--9f0a7bdf9c--12",
      "/video/0000006a--9f0a7bdf9c--13",
      "/video/not-a-segment",
    ])
  """)

  assert options == [
    {"index": 0, "label": "Segment 12"},
    {"index": 1, "label": "Segment 13"},
    {"index": 2, "label": "Clip 3"},
  ]


def test_segment_options_tolerate_a_missing_segment_list():
  assert evaluate("return [getSegmentOptions(undefined), getSegmentOptions([])]") == [[], []]


def test_hides_segment_status_when_the_stored_number_is_unsafe():
  results = evaluate('''
    return [
      parseStoredSegmentNumber("/video/route--9007199254740992"),
      getSegmentStatus(["/video/not-a-segment"], 0),
      getSegmentStatus(undefined, 0),
    ]
  ''')

  assert results == [None, "", ""]


def test_camera_video_url_carries_an_optional_quality_tier():
  result = evaluate("""
    const segment = "/video/0000006a--9f0a7bdf9c--7"
    return { full: cameraVideoUrl(segment, "forward"), low: cameraVideoUrl(segment, "forward", "low") }
  """)

  assert result["full"] == "/video/0000006a--9f0a7bdf9c--7?camera=forward"
  assert result["low"] == "/video/0000006a--9f0a7bdf9c--7?camera=forward&quality=low"


def test_route_metadata_errors_explain_missing_local_segments():
  result = evaluate('''
    return {
      missing: routeMetadataErrorMessage(404, "Route not found"),
      backend: routeMetadataErrorMessage(400, "Invalid route name"),
      fallback: routeMetadataErrorMessage(503),
    }
  ''')

  assert result == {
    "missing": "This route is no longer available on this device. Its local video segments may have been deleted or moved.",
    "backend": "Invalid route name",
    "fallback": "Could not load route details (503).",
  }


def test_only_the_road_camera_has_a_preview():
  """loggerd writes qcamera.ts alongside the road camera only."""
  assert evaluate('return ["forward", "wide", "driver"].map(supportsLowQuality)') == [True, False, False]


def test_upgrade_decision_only_trusts_a_positively_tall_frame():
  """The server falls back to the full stream, so the frame size is what settles it."""
  assert evaluate("""
    return {
      qcamera: shouldUpgradeFromHeight(330),
      full: shouldUpgradeFromHeight(1080),
      unknown: shouldUpgradeFromHeight(0),
      missing: shouldUpgradeFromHeight(undefined),
    }
  """) == {"qcamera": True, "full": False, "unknown": True, "missing": True}


def test_switching_camera_changes_only_the_url_and_not_segment_status():
  result = evaluate('''
    const segments = ["/video/0000006a--9f0a7bdf9c--7"]
    const before = getSegmentStatus(segments, 0)
    return {
      url: cameraVideoUrl(segments[0], "driver"),
      unchanged: getSegmentStatus(segments, 0) === before,
    }
  ''')

  assert result["url"] == "/video/0000006a--9f0a7bdf9c--7?camera=driver"
  assert result["unchanged"] is True
