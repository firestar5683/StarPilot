#!/usr/bin/env python3
"""Diagnose Speed Limit Controller / mapd issues from comma connect routes.

Compares three speed limit signals for a given route:
  1. mapdOut.speedLimit   – speed from offline OSM tiles (mapd)
  2. starpilotPlan.slcSpeedLimit – the SLC-chosen speed limit
  3. OSM Overpass live     – current maxspeed tagged on OpenStreetMap

Produces a table of every speed-limit change, showing discrepancies
between stale mapd tiles, live OSM, and what SLC actually decided.

Usage:
  python scripts/diagnose_slc_mapd.py --route f87125a583626e1b|00000179--b2b5fefb58 [--kmh]
  python scripts/diagnose_slc_mapd.py --route f87125a583626e1b|00000179--b2b5fefb58 --token YOUR_JWT
  COMMA_JWT=TOKEN python scripts/diagnose_slc_mapd.py --route f87125a583626e1b|00000179--b2b5fefb58
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import types
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import requests

# ── StarPilot / openpilot imports ──────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# smbus2 is a hardware I2C library only present on comma's tici device.
# On PC it's never installed, and SMBus is never called (the TICI flag is
# False). Stub it so the eager import chain in openpilot.system.hardware
# succeeds without installing tici-only platform dependencies.
_smbus2 = types.ModuleType('smbus2')
_smbus2.SMBus = None
sys.modules['smbus2'] = _smbus2

from openpilot.common.constants import CV
from openpilot.tools.lib.auth import login as oauth_login
from openpilot.tools.lib.auth_config import get_token, set_token
from openpilot.tools.lib.logreader import LogReader, ReadMode

# ============================================================================
# Constants
# ============================================================================

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_UA = "starpilot-diagnose-slc/1.0 (https://github.com/FrogAi/StarPilot)"

JWT_HELP_URL = "https://jwt.comma.ai/"
JWT_HELP = (
    "Get a JWT token:\n"
    "  1. Visit https://jwt.comma.ai/ in your browser.\n"
    "  2. Sign in with your comma account.\n"
    "  3. Copy the token.\n"
    "  4. Pass it with --token TOKEN or set COMMA_JWT=TOKEN"
)

CACHE_DIR = Path("/tmp/starpilot_overpass_cache")
CACHE_TTL = timedelta(hours=1)

ROUTE_PAD_DEG = 0.02
MAX_SUBBOX_DEG = 0.25
OVERQUERY_INTERVAL_S = 3.0
MAX_BACKOFF_S = 300.0
MATCH_RADIUS_M = 30.0

MS_TO_KPH = 3.6
KPH_TO_MPH = 0.621371

# ============================================================================
# Data structures
# ============================================================================


@dataclass
class MapdSample:
    """One mapdOut event from the log."""

    log_mono_time: int
    speed_limit: float
    next_speed_limit: float
    next_speed_limit_distance: float
    road_name: str
    way_selection_type: str
    tile_loaded: bool
    speed_limit_accepted: bool
    segment: int


@dataclass
class SplanSample:
    """One starpilotPlan event from the log."""

    log_mono_time: int
    slc_speed_limit: float
    slc_speed_limit_source: str
    v_cruise: float
    slc_speed_limit_offset: float
    slc_map_speed_limit: float
    slc_mapbox_speed_limit: float
    slc_overridden_speed: float
    unconfirmed_slc_speed_limit: float
    slc_next_speed_limit: float
    speed_limit_changed: bool
    starpilot_toggles_json: str
    segment: int


@dataclass
class CarSample:
    """One carState event from the log."""

    log_mono_time: int
    v_ego: float
    gas_pressed: bool
    segment: int


@dataclass
class ScsSample:
    """One starpilotCarState event from the log."""

    log_mono_time: int
    accel_pressed: bool
    decel_pressed: bool


@dataclass
class LeadSample:
    """One radarState lead-vehicle event from the log."""

    log_mono_time: int
    has_lead: bool
    d_rel: float   # metres ahead
    v_lead: float  # m/s absolute speed of lead


@dataclass
class GpsSample:
    """One gpsLocationExternal event from the log."""

    log_mono_time: int
    latitude: float
    longitude: float
    speed: float
    bearing_deg: float


@dataclass
class OsmWay:
    """A speed-limited OSM way returned by Overpass."""

    way_id: int
    maxspeed_mps: float
    road_name: str
    nodes: list[tuple[float, float]]


@dataclass
class ChangeRow:
    """One row in the output comparison table."""

    segment: int
    time_offset_s: float
    road_name: str
    mapd_mps: float
    next_mapd_mps: float
    slc_mps: float
    slc_source: str
    v_cruise_mps: float
    v_ego_mps: float
    osm_mps: float
    osm_road_name: str
    way_sel: str
    latitude: float
    longitude: float
    matched_osm: bool
    slc_overridden_mps: float = 0.0
    unconfirmed_mps: float = 0.0
    slc_next_mps: float = 0.0
    speed_limit_changed: bool = False
    tile_loaded: bool = True
    slc_active: bool = True
    slc_mode: str = "active"
    event_type: str = ""
    detail: str = ""
    accel_pressed: bool = False
    decel_pressed: bool = False

    @property
    def stale(self) -> bool:
        return (
            self.matched_osm
            and self.mapd_mps > 0
            and self.osm_mps > 0
            and abs(self.mapd_mps - self.osm_mps) > 1.0
        )

    @property
    def mismatch(self) -> bool:
        if self.lookahead:
            return False
        return (
            self.mapd_mps > 0
            and self.slc_mps > 0
            and abs(self.mapd_mps - self.slc_mps) > 1.0
        )

    @property
    def lookahead(self) -> bool:
        return (
            self.mapd_mps > 0
            and self.slc_mps > self.mapd_mps + 1.0
            and self.slc_next_mps > 0
            and abs(self.slc_mps - self.slc_next_mps) < 1.0
        )

    @property
    def slc_state(self) -> str:
        if self.slc_source.lower() != "none":
            return ""
        # Active override: driver genuinely exceeding the SLC limit
        if self.slc_overridden_mps > self.slc_mps > 0 and self.v_ego_mps > self.slc_mps:
            return "override"
        # Stale override: zombie overridden_speed residue, driver not exceeding
        if self.slc_overridden_mps > self.slc_mps > 0:
            return "stale override"
        if self.unconfirmed_mps > 0:
            return "pending confirm"
        if self.slc_mode == "off":
            return "slc off"
        if self.slc_mode == "display only":
            return "display only"
        if self.slc_mps == 0:
            return "no limit"
        if not self.tile_loaded:
            return "tiles not loaded"
        return "idle"


# ============================================================================
# CLI
# ============================================================================


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Diagnose SLC / mapd speed limit issues from comma connect routes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=JWT_HELP,
    )
    p.add_argument(
        "route_pos",
        nargs="?",
        default=None,
        help="Route name (positional format alternative)."
    )
    p.add_argument(
        "--route",
        default=None,
        help=(
            "Route name (e.g. f07115a587626e1a|00000172--d8b5feab48). "
            "Append /N for a single segment or /N:M for a range. "
            "Also accepts useradmin.comma.ai or connect.comma.ai URLs. "
            "If omitted, you will be prompted."
        ),
    )
    p.add_argument("--token", default=None, help="Comma Connect JWT token.")
    p.add_argument(
        "--kmh",
        action="store_true",
        default=False,
        help="Display speeds in km/h (default: mph).",
    )
    args = p.parse_args(argv)
    if args.route_pos:
        args.route = args.route_pos
    return args


def resolve_route_identifier(raw: str) -> str:
    """Normalise user input to a format LogReader/SegmentRange understands.

    Accepts:
      dongle_id/log_id           →  dongle_id/log_id
      dongle_id/log_id/8         →  dongle_id/log_id/8
      dongle_id/log_id/8:15      →  dongle_id/log_id/8:15
      dongle_id|log_id/...       →  same with /
      connect.comma.ai URLs      →  extracted route + optional seg info
      useradmin.comma.ai URLs    →  extracted route (no seg info)
    """
    text = raw.strip().strip("'\"")

    if "useradmin.comma.ai" in text:
        qs = parse_qs(urlparse(text).query)
        vals = qs.get("onebox")
        if not vals:
            raise ValueError(f"Could not extract 'onebox' from: {text}")
        text = vals[0]
        return resolve_route_identifier(text)

    if "connect.comma.ai" in text:
        parts = urlparse(text).path.strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Could not parse connect URL: {text}")
        return resolve_route_identifier(f"{parts[0]}|{parts[1]}")

    text = text.replace("|", "/")

    # Match dongle_id/log_id optionally followed by /slice-and-selector
    m = re.match(r"^([0-9a-f]{16})/([0-9a-zA-Z_\-]{10,40})" + r"(/.*)?$", text)
    if not m:
        raise ValueError(
            f"Unrecognised route identifier: {raw}\n"
            "Expected: dongle_id|log_id  (16 hex chars | identifier)"
        )
    dongle, log_id, suffix = m.group(1), m.group(2), m.group(3) or ""
    if suffix:
        suffix = re.sub(r"^/(\d+)/(\d+)$", r"/\1:\2", suffix)
    return f"{dongle}/{log_id}{suffix}"


# ============================================================================
# Auth
# ============================================================================


def setup_auth(token: str | None) -> str:
    """Resolve JWT: --token → COMMA_JWT env → auth_config → OAuth login."""
    if token:
        set_token(token)
        return token

    env_t = os.environ.get("COMMA_JWT", "").strip()
    if env_t:
        set_token(env_t)
        return env_t

    file_t = get_token()
    if file_t:
        return file_t

    print("No JWT token found. Starting OAuth login...", file=sys.stderr)
    print(
        "A browser window will open for you to sign in with your comma account.",
        file=sys.stderr,
    )
    try:
        oauth_login("google")
    except Exception as e:
        print(f"OAuth login failed: {e}", file=sys.stderr)
        print(file=sys.stderr)
        print(JWT_HELP, file=sys.stderr)
        raise SystemExit(1)

    file_t = get_token()
    if file_t:
        return file_t

    print("OAuth completed but no token was saved.", file=sys.stderr)
    raise SystemExit(1)


# ============================================================================
# Log parsing
# ============================================================================


def parse_route_logs(
    route_name: str,
) -> tuple[
    list[MapdSample],
    list[SplanSample],
    list[CarSample],
    list[GpsSample],
    list[ScsSample],
    list[LeadSample],
    list[int],
]:
    """Use LogReader to parse qlog and extract all speed-related messages.

    Returns (mapd_events, splan_events, car_events, gps_events, scs_events, lead_events, segments).
    """
    mapd_events: list[MapdSample] = []
    splan_events: list[SplanSample] = []
    car_events: list[CarSample] = []
    gps_events: list[GpsSample] = []
    scs_events: list[ScsSample] = []
    lead_events: list[LeadSample] = []
    segments_found: set[int] = set()
    seg_of_msg: dict[int, int] = {}

    lr = LogReader(route_name, default_mode=ReadMode.QLOG)
    all_msgs = list(lr)

    for msg in all_msgs:
        try:
            which = msg.which()
        except Exception:
            continue

        t = msg.logMonoTime
        # Try to infer segment number from available fields
        # (LogReader doesn't expose it directly, but we track segment boundaries
        #  via gpsLocationExternal which arrives per-segment)

        if which == "mapdOut":
            m = msg.mapdOut
            mapd_events.append(
                MapdSample(
                    log_mono_time=t,
                    speed_limit=float(m.speedLimit or 0),
                    next_speed_limit=float(m.nextSpeedLimit or 0),
                    next_speed_limit_distance=float(m.nextSpeedLimitDistance or 0),
                    road_name=str(m.roadName or "").strip(),
                    way_selection_type=str(m.waySelectionType),
                    tile_loaded=bool(m.tileLoaded),
                    speed_limit_accepted=bool(m.speedLimitAccepted),
                    segment=0,
                )
            )
        elif which == "starpilotPlan":
            s = msg.starpilotPlan
            sp_toggles_raw = str(s.starpilotToggles or "{}").strip()
            splan_events.append(
                SplanSample(
                    log_mono_time=t,
                    slc_speed_limit=float(s.slcSpeedLimit or 0),
                    slc_speed_limit_source=str(s.slcSpeedLimitSource or "").strip(),
                    v_cruise=float(s.vCruise or 0),
                    slc_speed_limit_offset=float(s.slcSpeedLimitOffset or 0),
                    slc_map_speed_limit=float(s.slcMapSpeedLimit or 0),
                    slc_mapbox_speed_limit=float(s.slcMapboxSpeedLimit or 0),
                    slc_overridden_speed=float(s.slcOverriddenSpeed or 0),
                    unconfirmed_slc_speed_limit=float(s.unconfirmedSlcSpeedLimit or 0),
                    slc_next_speed_limit=float(s.slcNextSpeedLimit or 0),
                    speed_limit_changed=bool(s.speedLimitChanged),
                    starpilot_toggles_json=sp_toggles_raw,
                    segment=0,
                )
            )
        elif which == "carState":
            c = msg.carState
            car_events.append(
                CarSample(
                    log_mono_time=t,
                    v_ego=float(c.vEgo or 0),
                    gas_pressed=bool(c.gasPressed),
                    segment=0,
                )
            )
        elif which == "gpsLocationExternal":
            g = msg.gpsLocationExternal
            gps_events.append(
                GpsSample(
                    log_mono_time=t,
                    latitude=float(g.latitude),
                    longitude=float(g.longitude),
                    speed=float(g.speed or 0),
                    bearing_deg=float(g.bearingDeg or 0),
                )
            )
        elif which == "starpilotCarState":
            s = msg.starpilotCarState
            scs_events.append(
                ScsSample(
                    log_mono_time=t,
                    accel_pressed=bool(s.accelPressed),
                    decel_pressed=bool(s.decelPressed),
                )
            )
        elif which == "radarState":
            r = msg.radarState
            lead = r.leadOne
            lead_events.append(
                LeadSample(
                    log_mono_time=t,
                    has_lead=bool(lead.status),
                    d_rel=float(lead.dRel or 0),
                    v_lead=float(lead.vLead or 0),
                )
            )

    if not all_msgs:
        print("Warning: no messages found in route logs.", file=sys.stderr)
    if not mapd_events:
        print(
            "Warning: no mapdOut messages. mapd may not have been running.",
            file=sys.stderr,
        )
    if not splan_events:
        print(
            "Warning: no starpilotPlan messages. SLC may not have been active.",
            file=sys.stderr,
        )
    if not gps_events:
        print("Warning: no GPS data in logs.", file=sys.stderr)

    if not scs_events:
        print(
            "Warning: no starpilotCarState in logs (accel/decel press data unavailable).",
            file=sys.stderr,
        )

    segments = sorted(segments_found) if segments_found else [0]

    return mapd_events, splan_events, car_events, gps_events, scs_events, lead_events, segments


# ============================================================================
# OSM Overpass
# ============================================================================


def parse_maxspeed(raw: str | None) -> Optional[float]:
    """Parse an OSM maxspeed tag to m/s.  Returns None on failure."""
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip().lower()
    if not s or s in ("none", "signals", "variable", "no", "walk", "urban", "rural"):
        return None
    # directional prefix
    dm = re.match(r"^(?:forward|backward)\s*:\s*(.+)$", s)
    if dm:
        return parse_maxspeed(dm.group(1))
    # multi-value: take first
    mm = re.match(r"^(.+?)\s*;", s)
    if mm:
        return parse_maxspeed(mm.group(1).strip())
    # mph
    mph_m = re.match(r"^(\d+(?:\.\d+)?)\s*mph$", s)
    if mph_m:
        return float(mph_m.group(1)) * CV.MPH_TO_MS
    # kph
    kph_m = re.match(r"^(\d+(?:\.\d+)?)\s*(?:kmh?/h?|kph)$", s)
    if kph_m:
        return float(kph_m.group(1)) * CV.KPH_TO_MS
    # knots
    kn_m = re.match(r"^(\d+(?:\.\d+)?)\s*knots?$", s)
    if kn_m:
        return float(kn_m.group(1)) * CV.KNOTS_TO_MS
    # bare number (km/h per OSM spec)
    bn = re.match(r"^\d+(?:\.\d+)?$", s)
    if bn:
        return float(bn.group(0)) * CV.KPH_TO_MS
    # fallback: leading numeric
    ln = re.match(r"^(\d+(?:\.\d+)?)", s)
    if ln:
        return float(ln.group(1)) * CV.KPH_TO_MS
    return None


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def _cross_track_m(lat_p, lon_p, lat_a, lon_a, lat_b, lon_b) -> float:
    """Minimum distance from P to great-circle arc AB in metres.
    Returns inf if projection falls outside segment."""
    R = 6_371_000
    lp_r, la_r, lb_r = map(math.radians, [lat_p, lat_a, lat_b])
    lo_p_r, lo_a_r, lo_b_r = map(math.radians, [lon_p, lon_a, lon_b])

    d_ap = math.acos(
        max(
            -1,
            min(
                1,
                math.sin(la_r) * math.sin(lp_r)
                + math.cos(la_r) * math.cos(lp_r) * math.cos(lo_p_r - lo_a_r),
            ),
        )
    )
    d_ab = math.acos(
        max(
            -1,
            min(
                1,
                math.sin(la_r) * math.sin(lb_r)
                + math.cos(la_r) * math.cos(lb_r) * math.cos(lo_b_r - lo_a_r),
            ),
        )
    )

    if d_ab < 1e-12:
        return float("inf")

    # bearing A→B
    y = math.sin(lo_b_r - lo_a_r) * math.cos(lb_r)
    x = math.cos(la_r) * math.sin(lb_r) - math.sin(la_r) * math.cos(lb_r) * math.cos(
        lo_b_r - lo_a_r
    )
    theta_ab = math.atan2(y, x)

    # bearing A→P
    y = math.sin(lo_p_r - lo_a_r) * math.cos(lp_r)
    x = math.cos(la_r) * math.sin(lp_r) - math.sin(la_r) * math.cos(lp_r) * math.cos(
        lo_p_r - lo_a_r
    )
    theta_ap = math.atan2(y, x)

    sin_xtd = max(-1, min(1, math.sin(d_ap) * math.sin(theta_ap - theta_ab)))
    xtd = abs(math.asin(sin_xtd))

    cos_xtd = math.cos(xtd)
    if cos_xtd < 1e-12:
        return float("inf")

    cos_atd = max(-1, min(1, math.cos(d_ap) / cos_xtd))
    atd = math.acos(cos_atd)
    if atd < 0 or atd > d_ab + 1e-9:
        return float("inf")
    return xtd * R


def _min_dist_to_way(lat: float, lon: float, nodes: list[tuple[float, float]]) -> float:
    if len(nodes) < 2:
        return float("inf")
    best = float("inf")
    for i in range(len(nodes) - 1):
        d = _cross_track_m(
            lat, lon, nodes[i][0], nodes[i][1], nodes[i + 1][0], nodes[i + 1][1]
        )
        if math.isinf(d):
            da = _haversine_m(lat, lon, nodes[i][0], nodes[i][1])
            db = _haversine_m(lat, lon, nodes[i + 1][0], nodes[i + 1][1])
            d = min(da, db)
        if d < best:
            best = d
    return best


class OverpassClient:
    """Fetch OSM ways with speed limits for an area, with caching & rate limiting."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": OVERPASS_UA,
                "Accept": "application/json",
            }
        )
        self._last_query = 0.0
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def fetch_for_route(self, gps: list[tuple[float, float]]) -> dict[int, OsmWay]:
        if not gps:
            return {}

        key = hashlib.sha256(json.dumps(gps, sort_keys=True).encode()).hexdigest()[:16]
        cached = self._load_cache(key)
        if cached is not None:
            return cached

        sub_boxes = self._sub_boxes(gps)
        all_ways: dict[int, OsmWay] = {}

        for idx, (mnlat, mnlon, mxlat, mxlon) in enumerate(sub_boxes):
            self._throttle()
            elements = self._query(mnlat, mnlon, mxlat, mxlon, 0)
            n = 0
            for el in elements:
                if el.get("type") != "way":
                    continue
                tags = el.get("tags", {}) or {}
                ms_raw = tags.get("maxspeed")
                ms = parse_maxspeed(ms_raw)
                if ms is None or ms <= 0:
                    continue
                geom = el.get("geometry") or []
                nodes = [
                    (nd["lat"], nd["lon"]) for nd in geom if "lat" in nd and "lon" in nd
                ]
                if not nodes:
                    continue
                wid = el["id"]
                rn = (tags.get("name") or tags.get("ref") or "").strip()
                all_ways[wid] = OsmWay(wid, ms, rn, nodes)
                n += 1
            print(
                f"  Overpass box {idx + 1}/{len(sub_boxes)}: {n} ways with limits",
                file=sys.stderr,
            )

        self._save_cache(key, all_ways)
        return all_ways

    def _sub_boxes(self, gps):
        lats = [p[0] for p in gps]
        lons = [p[1] for p in gps]
        mnlat, mxlat = min(lats) - ROUTE_PAD_DEG, max(lats) + ROUTE_PAD_DEG
        mnlon, mxlon = min(lons) - ROUTE_PAD_DEG, max(lons) + ROUTE_PAD_DEG
        lat_span, lon_span = mxlat - mnlat, mxlon - mnlon
        if lat_span <= MAX_SUBBOX_DEG and lon_span <= MAX_SUBBOX_DEG:
            return [(mnlat, mnlon, mxlat, mxlon)]
        nlat = max(1, math.ceil(lat_span / MAX_SUBBOX_DEG))
        nlon = max(1, math.ceil(lon_span / MAX_SUBBOX_DEG))
        ls, lns = lat_span / nlat, lon_span / nlon
        boxes = []
        for i in range(nlat):
            for j in range(nlon):
                slat = mnlat + i * ls
                slon = mnlon + j * lns
                boxes.append(
                    (
                        slat,
                        slon,
                        slat + ls if i < nlat - 1 else mxlat,
                        slon + lns if j < nlon - 1 else mxlon,
                    )
                )
        return boxes

    def _build_query(self, mnlat, mnlon, mxlat, mxlon) -> str:
        hw = (
            r"^(motorway|motorway_link|primary|primary_link|"
            r"residential|secondary|secondary_link|tertiary|tertiary_link|"
            r"trunk|trunk_link|unclassified|living_street)$"
        )
        return (
            f"[out:json][timeout:90];"
            f"way({mnlat:.5f},{mnlon:.5f},{mxlat:.5f},{mxlon:.5f})"
            f"[highway~'{hw}'][maxspeed];out geom qt;"
        )

    def _query(self, mnlat, mnlon, mxlat, mxlon, retry):
        q = self._build_query(mnlat, mnlon, mxlat, mxlon)
        try:
            resp = self.session.post(OVERPASS_API_URL, data=q, timeout=90)
        except requests.exceptions.RequestException as e:
            if retry < 3:
                time.sleep(2**retry)
                return self._query(mnlat, mnlon, mxlat, mxlon, retry + 1)
            print(f"  Overpass request failed: {e}", file=sys.stderr)
            return []
        if resp.status_code == 429:
            ra = int(resp.headers.get("Retry-After", min(2**retry, 30)))
            if retry < 5:
                time.sleep(ra)
                return self._query(mnlat, mnlon, mxlat, mxlon, retry + 1)
            print("  Overpass: max retries, skipping", file=sys.stderr)
            return []
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"  Overpass HTTP {resp.status_code}: {e}", file=sys.stderr)
            return []
        return resp.json().get("elements", [])

    def _throttle(self):
        el = time.monotonic() - self._last_query
        if el < OVERQUERY_INTERVAL_S:
            time.sleep(OVERQUERY_INTERVAL_S - el)
        self._last_query = time.monotonic()

    def _load_cache(self, key):
        path = CACHE_DIR / f"{key}.json"
        try:
            age = datetime.now(timezone.utc) - datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc
            )
            if age > CACHE_TTL:
                path.unlink(missing_ok=True)
                return None
            with open(path) as f:
                raw = json.load(f)
            return {
                int(k): OsmWay(
                    v["way_id"],
                    v["maxspeed_mps"],
                    v["road_name"],
                    [tuple(n) for n in v["nodes"]],
                )
                for k, v in raw.items()
            }
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    def _save_cache(self, key, data):
        path = CACHE_DIR / f"{key}.json"
        try:
            serial = {
                str(k): {
                    "way_id": w.way_id,
                    "maxspeed_mps": w.maxspeed_mps,
                    "road_name": w.road_name,
                    "nodes": w.nodes,
                }
                for k, w in data.items()
            }
            with open(path, "w") as f:
                json.dump(serial, f)
        except OSError as e:
            print(f"  Failed to write Overpass cache: {e}", file=sys.stderr)


def match_gps_to_ways(
    lat: float, lon: float, ways: dict[int, OsmWay]
) -> tuple[float, str]:
    """Find nearest OSM way within MATCH_RADIUS_M.  Returns (maxspeed_mps, name)."""
    best_d = float("inf")
    best_ms = 0.0
    best_name = ""
    for w in ways.values():
        if not w.nodes:
            continue
        d = _min_dist_to_way(lat, lon, w.nodes)
        if d < best_d:
            best_d = d
            best_ms = w.maxspeed_mps
            best_name = w.road_name
    if best_d <= MATCH_RADIUS_M:
        return best_ms, best_name
    return 0.0, ""


# ============================================================================
# GPS interpolation helper
# ============================================================================


def interpolate_gps(gps_events: list[GpsSample]) -> list[tuple[float, float, float]]:
    """Build a sorted list of (monotime_ns, lat, lon) from GPS events."""
    out = []
    for g in gps_events:
        if abs(g.latitude) > 0.01 or abs(g.longitude) > 0.01:
            out.append((float(g.log_mono_time), g.latitude, g.longitude))
    out.sort(key=lambda x: x[0])
    return out


def gps_at_time(
    t_ns: int, gps_timeline: list[tuple[float, float, float]]
) -> tuple[float, float]:
    """Interpolate GPS position at a given logMonoTime."""
    if not gps_timeline:
        return 0.0, 0.0
    if t_ns <= gps_timeline[0][0]:
        return gps_timeline[0][1], gps_timeline[0][2]
    if t_ns >= gps_timeline[-1][0]:
        return gps_timeline[-1][1], gps_timeline[-1][2]
    lo, hi = 0, len(gps_timeline) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if gps_timeline[mid][0] <= t_ns:
            lo = mid
        else:
            hi = mid
    t0, lat0, lon0 = gps_timeline[lo]
    t1, lat1, lon1 = gps_timeline[hi]
    if t1 == t0:
        return lat0, lon0
    frac = (t_ns - t0) / (t1 - t0)
    return lat0 + frac * (lat1 - lat0), lon0 + frac * (lon1 - lon0)


# ============================================================================
# Change detection
# ============================================================================


def _nearest(events, t_ns, prefer_after=True):
    """Return event nearest to t_ns. Prefers events at/after t_ns."""
    if not events:
        return None
    # (group, delta): group=0 for >=t, group=1 for <t.  min picks group 0 first.
    return min(
        events,
        key=lambda e: (
            0 if e.log_mono_time >= t_ns else 1,
            abs(e.log_mono_time - t_ns),
        ),
    )


def _parse_toggles(splan) -> tuple[bool, str]:
    """Return (slc_active, slc_mode) from starpilotPlan toggles."""
    active, mode = True, "active"
    if splan and splan.starpilot_toggles_json:
        try:
            toggles = json.loads(splan.starpilot_toggles_json)
            sc = toggles.get("speed_limit_controller", False)
            ss = toggles.get("show_speed_limits", False)
            active = sc or ss
            mode = "active" if sc else ("display only" if ss else "off")
        except (json.JSONDecodeError, TypeError):
            pass
    return active, mode


def detect_changes(
    mapd_events: list[MapdSample],
    splan_events: list[SplanSample],
    car_events: list[CarSample],
    scs_events: list[ScsSample],
    osm_ways: dict[int, OsmWay],
    gps_timeline: list[tuple[float, float, float]],
    base_time_ns: int,
    lead_events: list[LeadSample] | None = None,
) -> list[ChangeRow]:
    """Walk starpilotPlan events to detect every SLC state transition,
    correlating with mapd, carState, starpilotCarState, and radarState for full context.

    Produces a timeline of SLC decisions: limits, overrides, prompts, lookaheads.
    """
    if not splan_events:
        return []

    rows: list[ChangeRow] = []
    splan_sorted = sorted(splan_events, key=lambda e: e.log_mono_time)
    mapd_sorted = (
        sorted(mapd_events, key=lambda e: e.log_mono_time) if mapd_events else []
    )
    lead_sorted = (
        sorted(lead_events, key=lambda e: e.log_mono_time) if lead_events else []
    )

    prev_slc = -1.0
    prev_source_key = ""
    prev_overridden = 0.0
    prev_unconfirmed = 0.0
    prev_road = ""
    ov_phase = ""  # "", "active", or "stale"
    sent_events: set[tuple[str, int, float]] = set()

    for ev in splan_sorted:
        t_ns = ev.log_mono_time
        slc = ev.slc_speed_limit
        source_raw = ev.slc_speed_limit_source
        source_key = source_raw.strip().lower()
        overridden = ev.slc_overridden_speed
        unconfirmed = ev.unconfirmed_slc_speed_limit
        slc_next = ev.slc_next_speed_limit
        v_cruise = ev.v_cruise

        m = _nearest(mapd_sorted, t_ns)
        c = _nearest(car_events, t_ns)
        s = _nearest(scs_events, t_ns)
        lv = _nearest(lead_sorted, t_ns) if lead_sorted else None

        mapd_sl = m.speed_limit if m else 0
        mapd_next = m.next_speed_limit if m else 0
        road = (m.road_name or "").strip() if m else ""
        way_sel = str(m.way_selection_type) if m else ""
        tile_loaded = bool(m.tile_loaded) if m else True
        v_ego = c.v_ego if c else 0
        gas = bool(c.gas_pressed) if c else False
        accel = bool(s.accel_pressed) if s else False
        decel = bool(s.decel_pressed) if s else False
        has_lead = bool(lv.has_lead) if lv else False
        lead_d_rel = lv.d_rel if lv and lv.has_lead else 0.0
        lead_v = lv.v_lead if lv and lv.has_lead else 0.0

        lat, lon = gps_at_time(t_ns, gps_timeline) if gps_timeline else (0, 0)
        osm_sl, osm_name = (
            match_gps_to_ways(lat, lon, osm_ways) if osm_ways else (0.0, "")
        )
        slc_active, slc_mode = _parse_toggles(ev)

        # ── Transition detection ──────────────────────────────────────
        limit_changed = prev_slc > 0 and abs(slc - prev_slc) >= 0.5
        source_changed = (
            source_key
            and prev_source_key
            and source_key != prev_source_key
            and abs(slc - prev_slc) < 0.5
        )
        road_changed = road and prev_road and road != prev_road
        ov_start = overridden > 0.1 and prev_overridden <= 0.1
        ov_end = overridden <= 0.1 and prev_overridden > 0.1
        prom_start = unconfirmed > 0.1 and prev_unconfirmed <= 0.1
        prom_clear = unconfirmed <= 0.1 and prev_unconfirmed > 0.1
        lookahead = (
            source_key
            and source_key != "none"
            and slc > mapd_sl + 1.0
            and slc_next > 0
            and abs(slc - slc_next) < 1.0
        )
        active_ov = overridden > slc > 0 and v_ego > slc + 0.5
        stale_ov = overridden > slc > 0 and v_ego < slc - 0.5

        event_type = ""
        detail = ""

        if limit_changed:
            if unconfirmed > 0.1:
                event_type = "PROMPT"
                detail = f"confirm {unconfirmed * KPH_TO_MPH * MS_TO_KPH:.0f} mph"
            elif lookahead:
                event_type = "LOOKAHEAD"
                detail = f"pre-adopted {slc * KPH_TO_MPH * MS_TO_KPH:.0f} (mapd shows {mapd_sl * KPH_TO_MPH * MS_TO_KPH:.0f})"
            elif source_key and source_key != "none":
                event_type = "LIMIT"
                detail = "auto-accepted"
                if road_changed:
                    detail += f", road → {road}"
            elif active_ov:
                event_type = "LIMIT (ov)"
                detail = "override active, source suppressed"
            elif stale_ov:
                event_type = "LIMIT (stale ov)"
                detail = f"stale overridden > limit"
            elif source_key == "none":
                event_type = "LIMIT (none)"
                detail = "source unknown"
            else:
                event_type = "LIMIT"
                detail = source_raw

        elif prom_start:
            event_type = "PROMPT START"
            detail = f"confirm {unconfirmed * KPH_TO_MPH * MS_TO_KPH:.0f} mph?"
            if accel:
                detail += " (accel pressed)"
            if decel:
                detail += " (decel pressed)"

        elif prom_clear:
            if limit_changed:
                pass  # handled above
            elif source_key and source_key != "none":
                event_type = "ACCEPTED"
                detail = f"driver confirmed {slc * KPH_TO_MPH * MS_TO_KPH:.0f} mph"
            elif unconfirmed <= 0.1:
                event_type = "REJECTED"
                detail = f"driver rejected {prev_unconfirmed * KPH_TO_MPH * MS_TO_KPH:.0f} mph"

        elif ov_start:
            event_type = "OVERRIDE"
            detail = f"gas pressed: {v_ego * KPH_TO_MPH * MS_TO_KPH:.0f} > {slc * KPH_TO_MPH * MS_TO_KPH:.0f}"
            if accel:
                detail += " (accel)"
            if has_lead:
                detail += f" [lead {lead_d_rel:.0f}m ahead]"

        elif ov_end and not limit_changed and has_lead and not gas:
            event_type = "OVERRIDE CLEAR"
            detail = f"ACC decel behind lead ({lead_d_rel:.0f}m, {lead_v * KPH_TO_MPH * MS_TO_KPH:.0f} mph) — not driver brake"

        elif ov_end and not limit_changed:
            if ov_phase:
                event_type = "OVERRIDE CLEAR"
                detail = "override ended" + (f" [lead {lead_d_rel:.0f}m, {lead_v * KPH_TO_MPH * MS_TO_KPH:.0f} mph]" if has_lead else "")

        elif active_ov and ov_phase != "active":
            event_type = "OVERRIDE ACTIVE"
            detail = f"overriding: {v_ego * KPH_TO_MPH * MS_TO_KPH:.0f} > {slc * KPH_TO_MPH * MS_TO_KPH:.0f}"

        elif stale_ov and ov_phase != "stale":
            event_type = "STALE OVERRIDE"
            detail = f"overridden > {slc * KPH_TO_MPH * MS_TO_KPH:.0f}, v_ego={v_ego * KPH_TO_MPH * MS_TO_KPH:.0f}"
            if has_lead:
                detail += f" [ACC: lead {lead_d_rel:.0f}m, {lead_v * KPH_TO_MPH * MS_TO_KPH:.0f} mph]"

        elif source_changed:
            event_type = "SOURCE"
            detail = f"→ {source_raw}"

        elif road_changed:
            if not limit_changed:
                event_type = "ROAD"
                detail = f"→ {road}"

        # ── Emit row if event detected ─────────────────────────────────
        if event_type:
            key = (event_type, int(t_ns / 1e9), int(slc * 10))
            if key not in sent_events:
                sent_events.add(key)
                rows.append(
                    ChangeRow(
                        segment=0,
                        time_offset_s=(t_ns - base_time_ns) / 1e9
                        if base_time_ns
                        else 0,
                        road_name=road or osm_name or "Unknown",
                        mapd_mps=mapd_sl,
                        next_mapd_mps=mapd_next,
                        slc_mps=slc,
                        slc_source=source_raw,
                        v_cruise_mps=v_cruise,
                        v_ego_mps=v_ego,
                        osm_mps=osm_sl,
                        osm_road_name=osm_name,
                        way_sel=way_sel,
                        latitude=lat,
                        longitude=lon,
                        matched_osm=osm_sl > 0,
                        slc_overridden_mps=overridden,
                        unconfirmed_mps=unconfirmed,
                        slc_next_mps=slc_next,
                        speed_limit_changed=limit_changed,
                        tile_loaded=tile_loaded,
                        slc_active=slc_active,
                        slc_mode=slc_mode,
                        event_type=event_type,
                        detail=detail,
                        accel_pressed=accel,
                        decel_pressed=decel,
                    )
                )

        prev_slc = slc
        prev_source_key = source_key
        prev_overridden = overridden
        prev_unconfirmed = unconfirmed
        prev_road = road
        if active_ov:
            ov_phase = "active"
        elif stale_ov:
            ov_phase = "stale"
        elif overridden <= 0.1:
            ov_phase = ""

    return rows


# ============================================================================
# Output
# ============================================================================


def fmt_speed(mps: float, use_mph: bool, width: int = 5) -> str:
    if mps <= 0:
        return "—".center(width)
    if use_mph:
        return f"{mps * KPH_TO_MPH * MS_TO_KPH:>{width - 4}.0f} mph"
    return f"{mps * MS_TO_KPH:>{width - 4}.0f} km/h"


def print_header(
    route_name: str, mapd_n: int, splan_n: int, gps_n: int, scs_n: int, lead_n: int = 0
) -> None:
    sep = "=" * 82
    print(f"\n{sep}")
    print(f"  SLC / mapd Diagnostic Timeline")
    print(f"  Route: {route_name}")
    print(
        f"  Events: mapdOut={mapd_n} | starpilotPlan={splan_n} | starpilotCarState={scs_n} | GPS={gps_n} | radarState={lead_n}"
    )
    print(f"{sep}")


def print_table(rows: list[ChangeRow], use_mph: bool) -> None:
    if not rows:
        print("\n  No SLC events detected.")
        return

    unit = "mph" if use_mph else "km/h"
    hdr = (
        f"  {'Time':>7}  {'Event':<16}  {'Road':<22}  "
        f"{'SLC':>8}  {'Src':<8}  {'vEgo':>6}  Notes"
    )
    sep = "  " + "-" * (len(hdr) - 2)

    print(f"\n  SLC Decision Timeline (values in {unit}):")
    print(hdr)
    print(sep)

    stale_count = 0
    mismatch_count = 0

    for r in rows:
        notes: list[str] = []
        detail = r.detail

        if r.stale:
            notes.append("*stale OSM")
            stale_count += 1
        if r.lookahead:
            detail = detail or "pre-adopt"
        elif r.mismatch:
            notes.append("!mismatch")
            mismatch_count += 1

        src = r.slc_source.strip().lower() if r.slc_source else "none"
        if src == "none":
            slc_state = r.slc_state
            if slc_state and slc_state not in ("idle",):
                notes.append(slc_state)

        if r.accel_pressed:
            notes.append("accel")
        if r.decel_pressed:
            notes.append("decel")

        sc = fmt_speed(r.slc_mps, use_mph, 6)
        ve = fmt_speed(r.v_ego_mps, use_mph, 5)

        t_min = int(r.time_offset_s) // 60
        t_sec = int(r.time_offset_s) % 60
        ts = f"{t_min}:{t_sec:02d}"

        event = r.event_type[:16]
        road = (r.road_name[:22] + "..") if len(r.road_name) > 22 else r.road_name
        src_label = (r.slc_source[:8] or "—") if r.slc_source else "—"
        note_str = detail or ", ".join(notes) if notes else ""

        print(
            f"  {ts:>7}  {event:<16}  {road:<22}  "
            f"{sc:>8}  {src_label:<8}  {ve:>6}  {note_str}"
        )

    print(sep)
    parts = []
    if stale_count:
        parts.append(f"{stale_count} stale (mapd != OSM)")
    if mismatch_count:
        parts.append(f"{mismatch_count} mismatch (mapd != SLC)")
    if parts:
        print(f"  {' | '.join(parts)}")
    print()


# ============================================================================
# Main
# ============================================================================


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        if not args.route:
            try:
                args.route = input("Route identifier: ").strip()
            except (EOFError, KeyboardInterrupt):
                print(file=sys.stderr)
                return 1
            if not args.route:
                print("No route provided.", file=sys.stderr)
                return 1
        canonical = resolve_route_identifier(args.route)
        token = setup_auth(args.token)

        print(f"\nProcessing route: {canonical}", file=sys.stderr)

        # ── Parse qlog ──────────────────────────────────────────────────
        mapd_ev, splan_ev, car_ev, gps_ev, scs_ev, lead_ev, segments = parse_route_logs(
            canonical
        )

        if not mapd_ev and not splan_ev:
            print("No relevant events found in route logs.", file=sys.stderr)
            return 1

        base_time = 0
        for lst in [mapd_ev, splan_ev, car_ev, gps_ev, scs_ev]:
            if lst:
                base_time = lst[0].log_mono_time
                break

        gps_timeline = interpolate_gps(gps_ev)

        # ── Query Overpass ──────────────────────────────────────────
        osm_ways: dict[int, OsmWay] = {}
        if gps_timeline:
            print("Querying Overpass API for OSM speed limits...", file=sys.stderr)
            oc = OverpassClient()
            gps_pts = [(lat, lon) for _, lat, lon in gps_timeline]
            osm_ways = oc.fetch_for_route(gps_pts)
            print(f"  Found {len(osm_ways)} speed-limited OSM ways", file=sys.stderr)
        else:
            print("No GPS data available, skipping OSM comparison.", file=sys.stderr)

        # ── Detect changes ──────────────────────────────────────────
        rows = detect_changes(
            mapd_ev, splan_ev, car_ev, scs_ev, osm_ways, gps_timeline, base_time,
            lead_events=lead_ev,
        )

        # ── Output ─────────────────────────────────────────────────
        print_header(canonical, len(mapd_ev), len(splan_ev), len(gps_ev), len(scs_ev), len(lead_ev))
        print_table(rows, not args.kmh)

        stale = sum(1 for r in rows if r.stale)
        match = sum(1 for r in rows if r.mismatch)
        print(
            f"  Summary: {len(rows)} SLC events | {stale} stale OSM | {match} mapd≠SLC"
        )
        if match:
            print("    (mapd≠SLC includes lookaheads and timing-correlation lag)")
        print()

        if not mapd_ev:
            print(
                "  Note: No mapdOut events — mapd may not have been running "
                "during this route.",
                file=sys.stderr,
            )
        if not splan_ev:
            print(
                "  Note: No starpilotPlan events — SLC may not have been active.",
                file=sys.stderr,
            )
        if not osm_ways:
            print(
                "  Note: No OSM data retrieved. Comparison limited to "
                "mapd vs SLC only.",
                file=sys.stderr,
            )

        return 0

    except (ValueError, FileNotFoundError, PermissionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except requests.RequestException as e:
        print(f"Network error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unhandled error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
