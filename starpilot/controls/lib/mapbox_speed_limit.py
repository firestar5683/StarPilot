import calendar
import json
from concurrent.futures import ThreadPoolExecutor

import requests

from openpilot.common.constants import CV
from openpilot.common.realtime import DT_MDL
from openpilot.starpilot.common.starpilot_utilities import calculate_bearing_offset, is_url_pingable


FREE_MAPBOX_REQUESTS = 100_000


class MapboxSpeedLimit:
  def __init__(self, params):
    self.params = params
    try:
      self.requests = json.loads(params.get("MapBoxRequests", encoding="utf-8") or "{}")
    except (TypeError, ValueError):
      self.requests = {}
    self.requests.setdefault("total_requests", 0)
    self.requests.setdefault("max_requests", FREE_MAPBOX_REQUESTS - 28 * 100)

    self.host = "https://api.mapbox.com"
    self.token = params.get("MapboxSecretKey", encoding="utf-8")
    self.limit = 0.0
    self.segment_distance = 0.0
    self.future = None
    self.executor = ThreadPoolExecutor(max_workers=1)
    self.session = requests.Session()
    self.session.headers.update({"Accept-Language": "en"})
    self.session.headers.update({"User-Agent": "starpilot-mapbox-speed-limit-retriever/1.0 (https://github.com/FrogAi/StarPilot)"})

  def reset(self):
    # A discarded future may still finish, but only update() can publish its result.
    if self.future is not None:
      self.future.cancel()
      self.future = None
    self.limit = 0.0
    self.segment_distance = 0.0

  def shutdown(self):
    self.reset()
    self.executor.shutdown(wait=False, cancel_futures=True)
    self.session.close()

  def _request(self, position, v_ego):
    if not is_url_pingable(self.host):
      return 0.0, v_ego

    self.requests["total_requests"] += 1
    self.params.put_nonblocking("MapBoxRequests", json.dumps(self.requests))

    bearing = position.get("bearing")
    latitude = position.get("latitude")
    longitude = position.get("longitude")
    future_latitude, future_longitude = calculate_bearing_offset(latitude, longitude, bearing, v_ego)
    url = f"{self.host}/matching/v5/mapbox/driving/{longitude},{latitude};{future_longitude},{future_latitude}.json"
    params = {
      "access_token": self.token,
      "annotations": "maxspeed,distance",
      "geometries": "polyline6",
      "overview": "full",
      "steps": "false",
      "radiuses": "10;10",
      "tidy": "true",
    }
    response = self.session.get(url, params=params, timeout=10)
    response.raise_for_status()
    matchings = response.json().get("matchings") or []
    if not matchings:
      return 0.0, v_ego
    legs = (matchings[0] or {}).get("legs") or []
    if not legs:
      return 0.0, v_ego

    annotation = legs[0].get("annotation") or {}
    distances = annotation.get("distance") or [v_ego]
    speeds = annotation.get("maxspeed") or []
    if not speeds:
      return 0.0, v_ego
    first = speeds[0]
    try:
      speed = float(first.get("speed")) if first.get("speed") != "none" else 0.0
    except (TypeError, ValueError):
      speed = 0.0
    if speed <= 0:
      return 0.0, v_ego
    conversion = CV.MPH_TO_MS if first.get("unit", "km/h") == "mph" else CV.KPH_TO_MS
    return speed * conversion, distances[0]

  def update(self, now, time_validated, v_ego, gps_valid, position, steering_angle, angle_offset):
    if not gps_valid or not self.token or abs(steering_angle - angle_offset) >= 45:
      self.reset()
      return

    if time_validated and now.month != self.requests.get("month"):
      self.requests.update({
        "month": now.month,
        "total_requests": 0,
        "max_requests": FREE_MAPBOX_REQUESTS - calendar.monthrange(now.year, now.month)[1] * 100,
      })
    if self.requests["total_requests"] >= self.requests["max_requests"]:
      self.reset()
      return

    if self.future is not None:
      if not self.future.done():
        return
      future = self.future
      self.future = None
      try:
        self.limit, self.segment_distance = future.result()
      except Exception as exception:
        print(f"Unexpected error in Mapbox request: {exception}")
        self.limit, self.segment_distance = 0.0, v_ego
      return

    if v_ego < 1:
      return
    if self.segment_distance > 0:
      self.segment_distance -= v_ego * DT_MDL
      return

    try:
      self.future = self.executor.submit(self._request, dict(position), v_ego)
    except RuntimeError:
      self.segment_distance = v_ego
      return
