#!/usr/bin/env python3
import asyncio
import math
import os
import time
import urllib.request
import xml.etree.ElementTree as ET
from cereal import messaging
from openpilot.common.params import Params
from openpilot.starpilot.system.uniden_shm import set_shm_param, get_shm_param

CHP_URL = "https://media.chp.ca.gov/sa_xml/sa.xml"
SHM_PARAMS_PATH = "/dev/shm/params/d"

# Category definitions based on Sabre Plus / AlertMapper
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

def classify_incident(log_type):
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

class RoadAlertsDaemon:
    def __init__(self):
        self.sm = messaging.SubMaster(["gpsLocationExternal", "livePose"])
        self.cached_incidents = []
        self.last_fetch_time = 0.0
        self.current_lat = 0.0
        self.current_lon = 0.0
        self.current_bearing = 0.0
        self.has_gps = False

    def fetch_feed(self):
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

                category, label, icon = classify_incident(log_type)

                incidents.append({
                    "id": log_id,
                    "category": category,
                    "label": label,
                    "icon": icon,
                    "type": log_type,
                    "location": location,
                    "desc": desc,
                    "area": area,
                    "time": log_time,
                    "lat": lat,
                    "lon": lon,
                    "detail": last_detail
                })
            self.cached_incidents = incidents
            self.last_fetch_time = time.monotonic()
        except Exception as e:
            print(f"[road_alerts_d] Error fetching feed: {e}")

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

        upcoming = []
        for inc in self.cached_incidents:
            dist = haversine_miles(self.current_lat, self.current_lon, inc["lat"], inc["lon"])
            if dist <= max_radius_miles:
                # Calculate relative bearing to check if ahead of car (within 75 degrees cone)
                target_bearing = calculate_bearing(self.current_lat, self.current_lon, inc["lat"], inc["lon"])
                bearing_diff = abs((target_bearing - self.current_bearing + 180) % 360 - 180)
                
                is_ahead = bearing_diff <= 75.0 or dist <= 0.3  # immediate proximity or forward cone
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
            set_shm_param("RoadAlertCount", len(upcoming))
        else:
            set_shm_param("RoadAlertActive", False)
            set_shm_param("RoadAlertCategory", "")
            set_shm_param("RoadAlertLabel", "")
            set_shm_param("RoadAlertIcon", "")
            set_shm_param("RoadAlertDistance", 0.0)
            set_shm_param("RoadAlertLocation", "")
            set_shm_param("RoadAlertDetail", "")
            set_shm_param("RoadAlertCount", 0)

    def run(self):
        print("[road_alerts_d] Starting Road Alerts daemon...")
        while True:
            try:
                # Refresh feed every 45 seconds
                if time.monotonic() - self.last_fetch_time > 45.0:
                    self.fetch_feed()

                self.update_gps()
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
