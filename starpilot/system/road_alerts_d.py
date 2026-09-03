#!/usr/bin/env python3
import math
import time
import json
import base64
import uuid
import requests
import urllib.request
import xml.etree.ElementTree as ET
from cereal import messaging
from openpilot.common.params import Params
from openpilot.starpilot.system.uniden_shm import set_shm_param, get_shm_param
from openpilot.starpilot.system.waze import waze_pb2

CHP_URL = "https://media.chp.ca.gov/sa_xml/sa.xml"
WAZE_RT_HOST = "rt-xlb-am.waze.com"
APP_VERSION = "5.17.1.0"
PROTOCOL_VERSION = 234

# Thresholds requested by user:
# 1. At least 2 driver confirmations (thumbs-up)
# 2. Reported or confirmed within the last 15 minutes (900 seconds)
WAZE_MIN_THUMBS_UP = 2
WAZE_MAX_AGE_SEC = 900.0  # 15 minutes

def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1, lon1 = math.radians(lat1), math.radians(lon1)
    lat2, lon2 = math.radians(lat2), math.radians(lon2)
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    initial_bearing = math.atan2(y, x)
    initial_bearing = math.degrees(initial_bearing)
    return (initial_bearing + 360) % 360

CHP_TYPE_MAP = {
    # Major Collisions / SigAlerts
    "1179": ("ACCIDENT_MAJOR", "Major Accident - Ambulance Responding", "💥"),
    "1180": ("ACCIDENT_MAJOR", "Major Accident - Severe Injury", "💥"),
    "1181": ("ACCIDENT_MAJOR", "Major Accident - Injury Collision", "💥"),
    "1182": ("ACCIDENT_MINOR", "Property Damage Collision", "🚗"),
    "1183": ("ACCIDENT_MINOR", "Collision - Details Unknown", "🚗"),
    "20001": ("ACCIDENT_MAJOR", "Hit and Run - Severe Injury", "💥"),
    "20002": ("ACCIDENT_MINOR", "Hit and Run - Property Damage", "🚗"),
    "SIG":   ("ACCIDENT_MAJOR", "SigAlert - Severe Traffic Delay", "💥"),
    "FATAL": ("ACCIDENT_MAJOR", "Fatal Collision Reported", "💥"),

    # Hazards / Debris
    "1125": ("DEBRIS", "Traffic Hazard in Lane", "⚠️"),
    "1125A": ("DEBRIS", "Animals on Highway", "⚠️"),
    "23114": ("DEBRIS", "Debris / Objects Falling from Vehicle", "⚠️"),
    "FIRE":  ("HAZARD", "Vehicle Fire on Highway", "🔥"),
    "STALL": ("HAZARD", "Stalled Vehicle in Traffic", "⚠️"),
    "SPIL":  ("DEBRIS", "Chemical / Fuel Spill on Roadway", "⚠️"),
    "FLOOD": ("WEATHER", "Flooding / Standing Water", "🌧️"),
    "FOG":   ("WEATHER", "Dense Fog Advisory", "🌫️"),
    "SNOW":  ("WEATHER", "Snow / Ice on Roadway", "❄️"),
    "WIND":  ("WEATHER", "High Wind Advisory", "💨"),
    "CLOSURE": ("CLOSURE", "Highway / Lane Closure", "⛔"),
    "RAMP":  ("CLOSURE", "Ramp / Connector Blocked", "⛔"),
}

class WazeSessionManager:
    def __init__(self):
        self.session = requests.Session()
        self.session_id = get_shm_param("WazeSessionId", None)
        self.secret_key = get_shm_param("WazeSecretKey", None)
        self.username = get_shm_param("WazeUsername", None)
        self.password = get_shm_param("WazePassword", None)
        self.seq = 1
        self.device_uuid = str(uuid.uuid4())
        self.last_login_attempt = 0.0
        self.login_backoff_sec = 15.0

    def _next_seq(self):
        s = str(self.seq)
        self.seq += 1
        return s

    def _proto_base64_line(self, element):
        batch = waze_pb2.Batch()
        batch.element.extend([element])
        data = batch.SerializeToString()
        b64 = base64.b64encode(data).decode("ascii")
        return f"ProtoBase64,{b64}"

    def register_and_login(self, lat=37.7749, lon=-122.4194, force=False):
        if not force and (time.monotonic() - self.last_login_attempt < self.login_backoff_sec):
            return False

        self.last_login_attempt = time.monotonic()
        set_shm_param("WazeAuthStatus", "Registering guest session...")
        try:
            self.device_uuid = str(uuid.uuid4())
            element_ci = waze_pb2.Element()
            ci = element_ci.client_info
            ci.protocol = PROTOCOL_VERSION
            ci.client_version = APP_VERSION
            ci.last_position.lon_times1000000 = int(round(lon * 1_000_000))
            ci.last_position.lat_times1000000 = int(round(lat * 1_000_000))
            ci.manufacturer = "Google"
            ci.model = "Pixel"
            ci.os_version = "14"
            ci.locale = "en"
            ci.installation_id = self.device_uuid
            ci.device_type = waze_pb2.DeviceType.ANDROID_DEVICE
            ci.app_type = waze_pb2.AppType.WAZE
            ci.os_language_id = "en"
            ci.session_uuid = str(uuid.uuid4())
            ci.current_time_millis = int(time.time() * 1000)
            ci.app_flavor = waze_pb2.AppFlavor.ALPHA

            element_reg = waze_pb2.Element()
            element_reg.register.SetInParent()

            body = self._proto_base64_line(element_ci) + "\n" + self._proto_base64_line(element_reg)
            headers = {
                "User-Agent": APP_VERSION,
                "x-waze-network-version": "3",
                "sequence-number": self._next_seq(),
                "Content-Type": "binary/octet-stream"
            }

            url = f"https://{WAZE_RT_HOST}/rtserver/distrib/static"
            r = self.session.post(url, data=body.encode("utf-8"), headers=headers, timeout=10)
            if r.status_code == 200:
                batch = waze_pb2.Batch()
                batch.ParseFromString(r.content)
                for el in batch.element:
                    if el.HasField("register_successful"):
                        self.username = el.register_successful.username
                        self.password = el.register_successful.password
                        set_shm_param("WazeUsername", self.username)
                        set_shm_param("WazePassword", self.password)
                        self.login_backoff_sec = 15.0
                        break

            if not self.username or not self.password:
                set_shm_param("WazeAuthStatus", "Rate limited by Waze (429). Use token injection or wait cooldown.")
                self.login_backoff_sec = min(self.login_backoff_sec * 1.5, 300.0)
                return False

            element_login = waze_pb2.Element()
            lr = element_login.login_request
            lr.password_credential.username = self.username
            lr.password_credential.password = self.password
            lr.reason = waze_pb2.LoginRequest.LoginReason.NORMAL

            element_ads = waze_pb2.Element()
            element_ads.report_ads_setting.SetInParent()

            body_login = (
                self._proto_base64_line(element_ci) + "\n"
                + self._proto_base64_line(element_login) + "\n"
                + self._proto_base64_line(element_ads)
            )
            headers_login = {
                "User-Agent": APP_VERSION,
                "x-waze-network-version": "3",
                "sequence-number": self._next_seq(),
                "x-waze-wait-timeout": "8500",
                "Content-Type": "binary/octet-stream"
            }

            r_login = self.session.post(url, data=body_login.encode("utf-8"), headers=headers_login, timeout=12)
            if r_login.status_code == 200:
                batch_res = waze_pb2.Batch()
                batch_res.ParseFromString(r_login.content)
                for el in batch_res.element:
                    if el.HasField("login_response"):
                        resp = el.login_response
                        if resp.HasField("login_success"):
                            self.server_session_id = resp.login_success.server_session_id
                            self.session_id = resp.login_success.session_id
                            self.secret_key = resp.login_success.secret_key
                            set_shm_param("WazeSessionId", str(self.server_session_id or self.session_id))
                            set_shm_param("WazeSecretKey", str(self.secret_key))
                            set_shm_param("WazeAuthStatus", f"Guest Active (ID: {self.server_session_id or self.session_id})")
                            return True
                        elif resp.HasField("login_error"):
                            err_msg = str(resp.login_error)
                            set_shm_param("WazeAuthStatus", f"Login Error: {err_msg}")
                            return False

            set_shm_param("WazeAuthStatus", "Login challenge failed. Retrying...")
            return False
        except Exception as e:
            set_shm_param("WazeAuthStatus", f"Error: {e}")
            return False

    def query(self, lat, lon, box_radius_deg=0.06):
        # Reload from shared memory if manually injected via UI
        saved_session = get_shm_param("WazeSessionId", "")
        saved_key = get_shm_param("WazeSecretKey", "")
        if saved_session and saved_key:
            try:
                self.session_id = int(saved_session) if str(saved_session).isdigit() else saved_session
                self.secret_key = int(saved_key) if str(saved_key).isdigit() else saved_key
            except Exception:
                pass

        if not self.session_id or not self.secret_key:
            if not self.register_and_login(lat, lon):
                return []

        lon_min = lon - box_radius_deg
        lon_max = lon + box_radius_deg
        lat_min = lat - (box_radius_deg * 0.8)
        lat_max = lat + (box_radius_deg * 0.8)
        mid_lon = (lon_min + lon_max) / 2.0
        mid_lat = (lat_min + lat_max) / 2.0

        cmd_map = (
            f"MapDisplayed,{lon_min:.6f},{lat_max:.6f},{lon_max:.6f},{lat_max:.6f},"
            f"{lon_max:.6f},{lat_min:.6f},{lon_min:.6f},{lat_min:.6f},"
            f"{mid_lon:.6f},{mid_lat:.6f},67186,"
            f"{lon_min:.6f},{lat_max:.6f},{lon_max:.6f},{lat_max:.6f},"
            f"{lon_max:.6f},{lat_min:.6f},{lon_min:.6f},{lat_min:.6f}"
        )
        body = f"SeeMe,1,2,T,T,T,1,-1,1,7\nSetMood,1\nLocation,{lon:.6f},{lat:.6f}\n{cmd_map}"

        uid = waze_pb2.UID()
        try:
            uid.id = int(getattr(self, "server_session_id", None) or self.session_id)
        except Exception:
            uid.id = 0
        uid.secret_key = str(self.secret_key)
        uid_hdr = base64.b64encode(uid.SerializeToString()).decode("ascii")

        headers = {
            "User-Agent": APP_VERSION,
            "x-waze-network-version": "3",
            "sequence-number": self._next_seq(),
            "x-waze-wait-timeout": "10500",
            "uid": uid_hdr,
            "Content-Type": "binary/octet-stream"
        }

        try:
            url = f"https://{WAZE_RT_HOST}/rtserver/distrib/command"
            r = self.session.post(url, data=body.encode("utf-8"), headers=headers, timeout=15)
            if r.status_code != 200:
                self.session_id = None
                return []

            batch = waze_pb2.Batch()
            batch.ParseFromString(r.content)
            alerts = []
            now_epoch = time.time()

            for el in batch.element:
                if el.HasField("add_alert_action"):
                    ra = el.add_alert_action.realtime_alert
                    alert_type = ra.alert_info.type
                    alert_lat = ra.alert_info.position.lat_times1000000 / 1_000_000.0
                    alert_lon = ra.alert_info.position.lon_times1000000 / 1_000_000.0
                    
                    street = ra.alert_reporting_info.alert_address.street if ra.alert_reporting_info.HasField("alert_address") else ""
                    city = ra.alert_reporting_info.alert_address.city if ra.alert_reporting_info.HasField("alert_address") else ""
                    thumbs = int(ra.alert_reporting_info.thumbs_up_count or 0)
                    
                    # Report timestamp (seconds or milliseconds)
                    report_time_raw = ra.alert_reporting_info.report_time
                    report_time_sec = (report_time_raw / 1000.0) if report_time_raw > 1_000_000_000_000 else float(report_time_raw)
                    age_seconds = (now_epoch - report_time_sec) if report_time_sec > 0 else 0.0

                    # User Filter: Require >= 2 thumbs up AND confirmed within last 15 minutes (900s)
                    if thumbs < WAZE_MIN_THUMBS_UP:
                        continue
                    if report_time_sec > 0 and age_seconds > WAZE_MAX_AGE_SEC:
                        continue

                    alert_subtype = ra.alert_info.sub_type if ra.alert_info.HasField("sub_type") else waze_pb2.AlertSubType.NO_SUBTYPE
                    subtype_name = waze_pb2.AlertSubType.Name(alert_subtype) if alert_subtype in waze_pb2.AlertSubType.values() else ""

                    category = "HAZARD"
                    label = "Road Hazard"
                    icon = "⚠️"

                    is_verified_police = False
                    if alert_type == waze_pb2.AlertType.POLICE:
                        category = "POLICE"
                        if alert_subtype == waze_pb2.AlertSubType.POLICE_HIDING:
                            label = "Police Hidden (Speed Trap)"
                        elif alert_subtype == waze_pb2.AlertSubType.POLICE_VISIBLE:
                            label = "Police Visible"
                        elif alert_subtype == waze_pb2.AlertSubType.POLICE_WITH_MOBILE_CAMERA:
                            label = "Police Camera"
                        else:
                            label = "Police Reported"
                        icon = "🚨"

                        if alert_subtype in (waze_pb2.AlertSubType.POLICE_VISIBLE, waze_pb2.AlertSubType.POLICE_HIDING, waze_pb2.AlertSubType.POLICE_WITH_MOBILE_CAMERA):
                            is_verified_police = True

                    elif alert_type == waze_pb2.AlertType.ACCIDENT:
                        category = "ACCIDENT_MAJOR"
                        label = "Accident Reported"
                        icon = "💥"
                    elif alert_type in (waze_pb2.AlertType.ROAD_CLOSED, waze_pb2.AlertType.SYSTEM_ROAD_CLOSED, waze_pb2.AlertType.TURN_CLOSED):
                        category = "CLOSURE"
                        label = "Road Closure"
                        icon = "⛔"
                    elif alert_subtype in (waze_pb2.AlertSubType.HAZARD_ON_SHOULDER_CAR_STOPPED, waze_pb2.AlertSubType.HAZARD_ON_ROAD_CAR_STOPPED):
                        category = "HAZARD"
                        label = "Stalled Vehicle"
                        icon = "⚠️"
                    elif alert_subtype in (waze_pb2.AlertSubType.HAZARD_ON_ROAD_OBJECT, waze_pb2.AlertSubType.HAZARD_ON_SHOULDER):
                        category = "DEBRIS"
                        label = "Debris on Road"
                        icon = "⚠️"
                    elif alert_subtype == waze_pb2.AlertSubType.HAZARD_ON_ROAD_WEATHER:
                        category = "WEATHER"
                        label = "Severe Weather"
                        icon = "🌧️"

                    age_mins = max(1, int(round(age_seconds / 60.0))) if age_seconds > 0 else 1
                    time_str = f"{age_mins}m ago" if age_seconds > 0 else time.strftime("%I:%M %p")

                    alerts.append({
                        "id": f"waze_{ra.id}",
                        "source": "Waze",
                        "category": category,
                        "label": label,
                        "icon": icon,
                        "type": subtype_name or "Waze Alert",
                        "subtype": alert_subtype,
                        "thumbs": thumbs,
                        "is_verified_police": is_verified_police,
                        "location": f"{street}, {city}" if street and city else (street or city or "Roadway"),
                        "desc": f"Waze crowd report ({thumbs} confirmations, {time_str})",
                        "area": "Waze Community",
                        "time": time_str,
                        "lat": alert_lat,
                        "lon": alert_lon,
                        "detail": f"{thumbs} driver confirmations ({time_str})"
                    })
            return alerts
        except Exception:
            self.session_id = None
            return []

class RoadAlertsDaemon:
    def __init__(self):
        self.sm = messaging.SubMaster(["gpsLocationExternal", "livePose"])
        self.waze = WazeSessionManager()
        self.chp_incidents = []
        self.waze_incidents = []
        self.last_chp_fetch = 0.0
        self.last_waze_fetch = 0.0
        self.current_lat = 0.0
        self.current_lon = 0.0
        self.current_bearing = 0.0
        self.has_gps = False

    def fetch_chp(self):
        try:
            req = urllib.request.Request(CHP_URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw_bytes = resp.read()
            text = raw_bytes.decode("utf-8", errors="ignore")

            root = ET.fromstring(text)
            incidents = []
            for center in root.findall(".//Center"):
                area = center.get("ID", "")
                for inc in center.findall(".//Dispatch"):
                    log_id = inc.get("ID", "")
                    log_time = inc.findtext("LogTime", "")
                    log_type = inc.findtext("LogType", "")
                    location = inc.findtext("Location", "")
                    area_name = inc.findtext("Area", "")
                    lat_str = inc.findtext("LATITUDE", "")
                    lon_str = inc.findtext("LONGITUDE", "")

                    if not lat_str or not lon_str:
                        continue

                    try:
                        lat = float(lat_str)
                        lon = float(lon_str)
                    except ValueError:
                        continue

                    category = "HAZARD"
                    label = "CHP Traffic Incident"
                    icon = "⚠️"

                    matched = False
                    for code, (cat, lbl, icn) in CHP_TYPE_MAP.items():
                        if code in log_type.upper() or code in log_id.upper():
                            category = cat
                            label = lbl
                            icon = icn
                            matched = True
                            break

                    if not matched:
                        if "COLLISION" in log_type.upper() or "ACCIDENT" in log_type.upper():
                            category = "ACCIDENT_MAJOR" if "INJURY" in log_type.upper() else "ACCIDENT_MINOR"
                            label = log_type
                            icon = "💥" if category == "ACCIDENT_MAJOR" else "🚗"
                        elif "HAZARD" in log_type.upper() or "DEBRIS" in log_type.upper():
                            category = "DEBRIS"
                            label = log_type
                            icon = "⚠️"
                        elif "CLOSURE" in log_type.upper():
                            category = "CLOSURE"
                            label = log_type
                            icon = "⛔"
                        elif "WEATHER" in log_type.upper() or "SNOW" in log_type.upper() or "FLOOD" in log_type.upper():
                            category = "WEATHER"
                            label = log_type
                            icon = "🌧️"

                    details = []
                    for log_entry in inc.findall(".//Log"):
                        detail_text = log_entry.findtext("LogText", "")
                        if detail_text:
                            details.append(detail_text)
                    last_detail = details[-1] if details else ""

                    desc = f"{log_type} - {location}"
                    if area_name:
                        desc += f" ({area_name})"

                    incidents.append({
                        "id": f"chp_{log_id}",
                        "source": "CHP",
                        "category": category,
                        "label": label,
                        "icon": icon,
                        "type": log_type,
                        "subtype": 0,
                        "thumbs": 0,
                        "is_verified_police": False,
                        "location": location,
                        "desc": desc,
                        "area": area,
                        "time": log_time,
                        "lat": lat,
                        "lon": lon,
                        "detail": last_detail
                    })

            self.chp_incidents = incidents
            self.last_chp_fetch = time.monotonic()
        except Exception as e:
            print(f"[road_alerts_d] Error fetching CHP feed: {e}")

    def fetch_waze(self):
        if not self.has_gps or self.current_lat == 0:
            return
        waze_alerts = self.waze.query(self.current_lat, self.current_lon)
        if waze_alerts:
            self.waze_incidents = waze_alerts
        self.last_waze_fetch = time.monotonic()

    def update_gps(self):
        self.sm.update(0)
        if self.sm.updated["gpsLocationExternal"]:
            gps = self.sm["gpsLocationExternal"]
            if gps.flags & 1:  # Position valid
                self.current_lat = gps.latitude
                self.current_lon = gps.longitude
                self.current_bearing = gps.bearingDeg
                self.has_gps = True

    def process_upcoming_alerts(self, max_radius_miles=15.0):
        if not self.has_gps or self.current_lat == 0:
            return None

        # Category enablement toggles
        cat_police = get_shm_param("RoadAlertShowPolice", True)
        cat_major_acc = get_shm_param("RoadAlertShowMajorAccidents", True)
        cat_minor_acc = get_shm_param("RoadAlertShowMinorAccidents", True)
        cat_debris = get_shm_param("RoadAlertShowDebris", True)
        cat_closures = get_shm_param("RoadAlertShowClosures", True)
        cat_weather = get_shm_param("RoadAlertShowWeather", True)

        combined = getattr(self, "chp_incidents", []) + getattr(self, "waze_incidents", [])
        upcoming = []
        for inc in combined:
            cat = inc.get("category", "")
            if cat == "POLICE" and not cat_police:
                continue
            if cat == "ACCIDENT_MAJOR" and not cat_major_acc:
                continue
            if cat == "ACCIDENT_MINOR" and not cat_minor_acc:
                continue
            if cat in ("DEBRIS", "HAZARD") and not cat_debris:
                continue
            if cat == "CLOSURE" and not cat_closures:
                continue
            if cat == "WEATHER" and not cat_weather:
                continue

            dist = haversine_miles(self.current_lat, self.current_lon, inc["lat"], inc["lon"])
            if dist <= max_radius_miles:
                target_bearing = calculate_bearing(self.current_lat, self.current_lon, inc["lat"], inc["lon"])
                bearing_diff = abs((target_bearing - self.current_bearing + 180) % 360 - 180)
                
                is_ahead = bearing_diff <= 75.0 or dist <= 0.3
                if is_ahead:
                    inc_copy = dict(inc)
                    inc_copy["distance_miles"] = round(dist, 1)
                    inc_copy["bearing_diff"] = round(bearing_diff, 1)
                    upcoming.append(inc_copy)

        upcoming.sort(key=lambda x: x["distance_miles"])
        return upcoming

    def publish_to_shm(self, upcoming):
        if upcoming:
            closest = upcoming[0]
            set_shm_param("RoadAlertActive", True)
            set_shm_param("RoadAlertCategory", closest["category"])
            set_shm_param("RoadAlertLabel", closest["label"])
            set_shm_param("RoadAlertIcon", closest["icon"])
            set_shm_param("RoadAlertDistance", closest["distance_miles"])
            set_shm_param("RoadAlertLocation", closest["location"])
            set_shm_param("RoadAlertDetail", closest["detail"])
            set_shm_param("RoadAlertSource", closest["source"])
            set_shm_param("RoadAlertCount", len(upcoming))

            # 1. Waze Police Auto-Slowdown
            slowdown_police = get_shm_param("WazePoliceAutoSlowdown", True)
            min_confirmations = int(get_shm_param("WazePoliceMinConfirmations", 3) or 3)
            trigger_distance = float(get_shm_param("WazePoliceTriggerDistance", 1.0) or 1.0)

            police_active = False
            police_dist = 0.0
            if slowdown_police:
                for u in upcoming:
                    if u.get("source") == "Waze" and u.get("category") == "POLICE":
                        sub = u.get("subtype", 0)
                        if sub in (waze_pb2.AlertSubType.POLICE_VISIBLE, waze_pb2.AlertSubType.POLICE_HIDING, waze_pb2.AlertSubType.POLICE_WITH_MOBILE_CAMERA):
                            if (u.get("thumbs", 0) >= min_confirmations) and (u.get("distance_miles", 99.0) <= trigger_distance):
                                police_active = True
                                police_dist = u["distance_miles"]
                                break
            set_shm_param("WazePoliceSlowdownActive", police_active)
            set_shm_param("WazePoliceSlowdownDist", police_dist)

            # 2. Hazard Auto-Slowdown (Major Accidents, Minor Accidents, Debris, Closures, Weather within 0.5 miles)
            slowdown_major_acc = get_shm_param("RoadAlertSlowdownMajorAccidents", True)
            slowdown_minor_acc = get_shm_param("RoadAlertSlowdownMinorAccidents", False)
            slowdown_debris = get_shm_param("RoadAlertSlowdownDebris", True)
            slowdown_closures = get_shm_param("RoadAlertSlowdownClosures", True)
            slowdown_weather = get_shm_param("RoadAlertSlowdownWeather", False)

            hazard_slowdown_active = False
            for u in upcoming:
                cat = u.get("category", "")
                dist = u.get("distance_miles", 99.0)
                if dist <= 0.5:
                    if cat == "ACCIDENT_MAJOR" and slowdown_major_acc:
                        hazard_slowdown_active = True
                        break
                    elif cat == "ACCIDENT_MINOR" and slowdown_minor_acc:
                        hazard_slowdown_active = True
                        break
                    elif cat in ("DEBRIS", "HAZARD") and slowdown_debris:
                        hazard_slowdown_active = True
                        break
                    elif cat == "CLOSURE" and slowdown_closures:
                        hazard_slowdown_active = True
                        break
                    elif cat == "WEATHER" and slowdown_weather:
                        hazard_slowdown_active = True
                        break

            set_shm_param("RoadHazardSlowdownActive", hazard_slowdown_active)

        else:
            set_shm_param("RoadAlertActive", False)
            set_shm_param("RoadAlertCategory", "")
            set_shm_param("RoadAlertLabel", "")
            set_shm_param("RoadAlertIcon", "")
            set_shm_param("RoadAlertDistance", 0.0)
            set_shm_param("RoadAlertLocation", "")
            set_shm_param("RoadAlertDetail", "")
            set_shm_param("RoadAlertSource", "")
            set_shm_param("RoadAlertCount", 0)
            set_shm_param("WazePoliceSlowdownActive", False)
            set_shm_param("WazePoliceSlowdownDist", 0.0)
            set_shm_param("RoadHazardSlowdownActive", False)

    def run(self):
        print("[road_alerts_d] Starting Unified Road Alerts daemon (CHP + Waze RT)...")
        while True:
            try:
                self.update_gps()
                
                # Fetch CHP every 45s
                if time.monotonic() - self.last_chp_fetch > 45.0:
                    self.fetch_chp()

                # Fetch Waze every 30s
                if time.monotonic() - self.last_waze_fetch > 30.0:
                    self.fetch_waze()

                upcoming = self.process_upcoming_alerts()
                self.publish_to_shm(upcoming)
                time.sleep(1.0)
            except Exception as e:
                print(f"[road_alerts_d] Loop error: {e}")
                time.sleep(2.0)

def main():
    daemon = RoadAlertsDaemon()
    daemon.run()

if __name__ == "__main__":
    main()
