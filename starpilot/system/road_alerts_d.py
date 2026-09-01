#!/usr/bin/env python3
import asyncio
import base64
import math
import os
import time
import urllib.request
import uuid
import xml.etree.ElementTree as ET
import requests
from cereal import messaging
from openpilot.common.params import Params
from openpilot.starpilot.system.uniden_shm import set_shm_param, get_shm_param
from openpilot.starpilot.system.waze import waze_pb2

CHP_URL = "https://media.chp.ca.gov/sa_xml/sa.xml"
WAZE_RT_HOST = "rt-xlb-am.waze.com"
APP_VERSION = "5.17.1.0"
PROTOCOL_VERSION = 234

# Category definitions
MAJOR_ACCIDENT_CODES = ("1179", "1180", "1181", "1183", "1141", "1144", "20001", "FATAL", "SIG ALERT")
MINOR_ACCIDENT_CODES = ("1182", "20002")
POLICE_CODES = ("1184", "CZP", "MZP", "OFFICER", "COP", "POLICE")
CONGESTION_CODES = ("CLOSURE", "TADV", "CONGESTION")
WEATHER_CODES = ("WIND", "FOG", "SNOW", "ICE", "CHAIN", "1013", "WEATHER", "ROAD CONDITION", "FLOOD")
DEBRIS_CODES = ("1125", "FIRE", "DEBRIS", "STALLED", "OBJECT", "TIRE", "LADDER")

def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
    initial_bearing = math.atan2(x, y)
    initial_bearing = math.degrees(initial_bearing)
    return (initial_bearing + 360) % 360

def parse_chp_latlon(latlon_str):
    try:
        clean = latlon_str.replace('"', '').strip()
        parts = clean.split(':')
        if len(parts) == 2:
            lat = float(parts[0]) / 1000000.0
            lon = -abs(float(parts[1])) / 1000000.0
            return lat, lon
    except Exception:
        pass
    return None, None

def classify_chp_incident(log_type):
    t = log_type.upper()
    if any(code in t for code in MAJOR_ACCIDENT_CODES):
        return "ACCIDENT_MAJOR", "Major Accident", "💥"
    if any(code in t for code in MINOR_ACCIDENT_CODES):
        return "ACCIDENT_MINOR", "Minor Accident", "🚗"
    if any(code in t for code in POLICE_CODES):
        return "POLICE", "Police Active", "🚨"
    if any(code in t for code in CONGESTION_CODES):
        return "CLOSURE", "Road Closure", "⛔"
    if any(code in t for code in WEATHER_CODES):
        return "WEATHER", "Weather Hazard", "🌧️"
    if any(code in t for code in DEBRIS_CODES):
        return "DEBRIS", "Road Hazard", "⚠️"
    return "HAZARD", "Road Incident", "⚠️"

class WazeSessionManager:
    def __init__(self):
        self.session = requests.Session()
        self.session_id = None
        self.secret_key = None
        self.username = None
        self.password = None
        self.seq = 1
        self.device_uuid = str(uuid.uuid4())

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

    def register_and_login(self, lat=37.7749, lon=-122.4194):
        try:
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
            r = self.session.post(url, data=body.encode("utf-8"), headers=headers, timeout=12)
            if r.status_code == 200:
                batch = waze_pb2.Batch()
                batch.ParseFromString(r.content)
                for el in batch.element:
                    if el.HasField("register_successful"):
                        self.username = el.register_successful.username
                        self.password = el.register_successful.password
                        break

            if not self.username or not self.password:
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

            url_login = f"https://{WAZE_RT_HOST}/rtserver/distrib/login"
            r_login = self.session.post(url_login, data=body_login.encode("utf-8"), headers=headers_login, timeout=15)
            if r_login.status_code == 200:
                batch_login = waze_pb2.Batch()
                batch_login.ParseFromString(r_login.content)
                for el in batch_login.element:
                    if el.HasField("login_response") and el.login_response.HasField("login_success"):
                        ls = el.login_response.login_success
                        self.session_id = ls.server_session_id
                        self.secret_key = ls.secret_key
                        return True
            return False
        except Exception as e:
            print(f"[road_alerts_d] Waze login error: {e}")
            return False

    def query(self, lat, lon, box_radius_deg=0.06):
        if not self.session_id:
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
        uid.id = self.session_id
        uid.secret_key = self.secret_key
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
            r = self.session.post(url, data=body.encode("utf-8"), headers=headers, timeout=20)
            if r.status_code != 200:
                self.session_id = None
                return []

            batch = waze_pb2.Batch()
            batch.ParseFromString(r.content)
            alerts = []
            for el in batch.element:
                if el.HasField("add_alert_action"):
                    ra = el.add_alert_action.realtime_alert
                    alert_type = ra.alert_info.type
                    alert_lat = ra.alert_info.position.lat_times1000000 / 1_000_000.0
                    alert_lon = ra.alert_info.position.lon_times1000000 / 1_000_000.0
                    
                    street = ra.alert_reporting_info.alert_address.street if ra.alert_reporting_info.HasField("alert_address") else ""
                    city = ra.alert_reporting_info.alert_address.city if ra.alert_reporting_info.HasField("alert_address") else ""
                    thumbs = ra.alert_reporting_info.thumbs_up_count

                    alert_subtype = ra.alert_info.sub_type if ra.alert_info.HasField("sub_type") else waze_pb2.AlertSubType.NO_SUBTYPE
                    subtype_name = waze_pb2.AlertSubType.Name(alert_subtype) if alert_subtype in waze_pb2.AlertSubType.values() else ""

                    category = "HAZARD"
                    label = "Road Hazard"
                    icon = "⚠️"

                    # Check for verified police presence (POLICE_VISIBLE / POLICE_HIDING / MOBILE_CAMERA with >= 3 thumbs up reports)
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

                        if alert_subtype in (waze_pb2.AlertSubType.POLICE_VISIBLE, waze_pb2.AlertSubType.POLICE_HIDING, waze_pb2.AlertSubType.POLICE_WITH_MOBILE_CAMERA) and (thumbs or 0) >= 3:
                            is_verified_police = True

                    elif alert_type == waze_pb2.AlertType.ACCIDENT:
                        category = "ACCIDENT_MAJOR"
                        label = "Accident Reported"
                        icon = "💥"
                    elif alert_type in (waze_pb2.AlertType.ROAD_CLOSED, waze_pb2.AlertType.SYSTEM_ROAD_CLOSED, waze_pb2.AlertType.TURN_CLOSED):
                        category = "CLOSURE"
                        label = "Road Closure"
                        icon = "⛔"

                    alerts.append({
                        "id": f"waze_{ra.id}",
                        "source": "Waze",
                        "category": category,
                        "label": label,
                        "icon": icon,
                        "type": subtype_name or "Waze Alert",
                        "subtype": alert_subtype,
                        "thumbs": thumbs or 0,
                        "is_verified_police": is_verified_police,
                        "location": f"{street}, {city}" if street and city else (street or city or "Roadway"),
                        "desc": f"Waze crowd report ({thumbs} confirmations)" if thumbs else "Waze crowd report",
                        "area": "Waze Community",
                        "time": time.strftime("%I:%M %p"),
                        "lat": alert_lat,
                        "lon": alert_lon,
                        "detail": f"{thumbs} driver confirmations" if thumbs else ""
                    })
            return alerts
        except Exception as e:
            print(f"[road_alerts_d] Waze query error: {e}")
            self.session_id = None
            return []

class RoadAlertsDaemon:
    def __init__(self):
        self.sm = messaging.SubMaster(["gpsLocationExternal", "livePose"])
        self.waze = WazeSessionManager()
        self.cached_incidents = []
        self.last_chp_fetch = 0.0
        self.last_waze_fetch = 0.0
        self.current_lat = 0.0
        self.current_lon = 0.0
        self.current_bearing = 0.0
        self.has_gps = False

    def fetch_chp(self):
        try:
            req = urllib.request.Request(CHP_URL, headers={"User-Agent": "starpilot/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            incidents = []

            for log in root.findall(".//Log"):
                log_id = log.get("ID", "")
                log_type = (log.findtext("LogType") or "").replace('"', '').strip()
                if "SILVER" in log_type.upper() or "MISSING" in log_type.upper():
                    continue

                location = (log.findtext("Location") or "").replace('"', '').strip()
                desc = (log.findtext("LocationDesc") or "").replace('"', '').strip()
                area = (log.findtext("Area") or "").replace('"', '').strip()
                log_time = (log.findtext("LogTime") or "").replace('"', '').strip()
                latlon_raw = (log.findtext("LATLON") or "")

                lat, lon = parse_chp_latlon(latlon_raw)
                if not lat or not lon or lat == 0:
                    continue

                details = [d.findtext("IncidentDetail", "").replace('"', '') for d in log.findall(".//details")]
                clean_details = [d.strip() for d in details if d.strip()]
                last_detail = clean_details[-1] if clean_details else desc

                category, label, icon = classify_chp_incident(log_type)

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

            # Configurable Auto-Slowdown trigger for Waze Police Ahead
            slowdown_enabled = get_shm_param("WazePoliceAutoSlowdown", True)
            min_confirmations = get_shm_param("WazePoliceMinConfirmations", 3)
            trigger_distance = get_shm_param("WazePoliceTriggerDistance", 1.0)

            police_threats = []
            if slowdown_enabled:
                for u in upcoming:
                    if u.get("source") == "Waze" and u.get("category") == "POLICE":
                        sub = u.get("subtype", 0)
                        # Must be POLICE_VISIBLE (201), POLICE_HIDING (202), or POLICE_CAMERA (203)
                        if sub in (waze_pb2.AlertSubType.POLICE_VISIBLE, waze_pb2.AlertSubType.POLICE_HIDING, waze_pb2.AlertSubType.POLICE_WITH_MOBILE_CAMERA):
                            if (u.get("thumbs", 0) >= min_confirmations) and (u.get("distance_miles", 99.0) <= trigger_distance):
                                police_threats.append(u)

            if police_threats:
                set_shm_param("WazePoliceSlowdownActive", True)
                set_shm_param("WazePoliceSlowdownDist", police_threats[0]["distance_miles"])
            else:
                set_shm_param("WazePoliceSlowdownActive", False)
                set_shm_param("WazePoliceSlowdownDist", 0.0)
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

    def run(self):
        print("[road_alerts_d] Starting Unified Road Alerts daemon (CHP + Waze RT)...")
        while True:
            try:
                self.update_gps()
                
                # Fetch CHP every 45s
                if time.monotonic() - self.last_chp_fetch > 45.0:
                    self.fetch_chp()

                # Fetch Waze every 25s
                if time.monotonic() - self.last_waze_fetch > 25.0:
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
