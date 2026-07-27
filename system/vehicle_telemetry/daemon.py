#!/usr/bin/env python3
"""Always-running bridge from generic CarState fields to EV telemetry transports."""

from __future__ import annotations

import time

from openpilot.common.realtime import Ratekeeper
from openpilot.common.time_helpers import system_time_valid
from openpilot.system.vehicle_telemetry.core import (
  VehicleTelemetryCache,
  VehicleTelemetryConfigLoader,
  VehicleTelemetryPublisher,
  build_vehicle_telemetry_snapshot,
  validated_vehicle_telemetry_snapshot,
)
from openpilot.system.vehicle_telemetry.http_server import VehicleTelemetryHTTPService
from openpilot.system.vehicle_telemetry.tailscale import TAILSCALE_STATUS_FILENAME, TailscaleFunnelController
from openpilot.system.vehicle_telemetry.tunnel import FRPC_STATUS_FILENAME, FRPTunnelController


MAXIMUM_CACHED_PUBLISH_AGE_SECONDS = 30 * 24 * 60 * 60
MAXIMUM_SOURCE_SAMPLE_AGE_SECONDS = 1.0
DEFAULT_CAR_STATE_SERVICE = "carState"


def _nanos_since_boot():
  clock_boottime = getattr(time, "CLOCK_BOOTTIME", None)
  return time.clock_gettime_ns(clock_boottime) if clock_boottime is not None else time.monotonic_ns()


def source_mono_time_to_wall_time(source_mono_time, *, wall_time=None, monotonic_now_ns=None):
  """Map a producer's monotonic sample time to wall time without refreshing it."""
  try:
    source_mono_time = int(source_mono_time)
  except (TypeError, ValueError, OverflowError):
    return None
  if source_mono_time <= 0:
    return None

  now_mono_ns = _nanos_since_boot() if monotonic_now_ns is None else int(monotonic_now_ns)
  if source_mono_time > now_mono_ns:
    return None
  age_seconds = (now_mono_ns - source_mono_time) * 1e-9
  if age_seconds > MAXIMUM_SOURCE_SAMPLE_AGE_SECONDS:
    return None

  now_wall = time.time() if wall_time is None else float(wall_time)  # noqa: TID251
  return now_wall - age_seconds


def source_sample_is_new(source_mono_time, last_source_mono_time):
  try:
    return int(source_mono_time) > int(last_source_mono_time)
  except (TypeError, ValueError, OverflowError):
    return False


def select_vehicle_telemetry_state(
  started,
  car_state_service,
  car_state,
  offroad_car_state_service=None,
  offroad_state=None,
  offroad_state_resolver=None,
):
  """Use pandad's derived fallback only after deviceState proves offroad."""
  if started is False and offroad_car_state_service is not None:
    resolved = offroad_state_resolver(offroad_state) if offroad_state_resolver is not None else offroad_state
    return offroad_car_state_service, resolved
  return car_state_service, car_state


def select_vehicle_telemetry_source_name(selected_service, offroad_car_state_service, source_name, offroad_source_name):
  if selected_service == offroad_car_state_service and offroad_source_name is not None:
    return offroad_source_name
  return source_name


def build_clock_valid_vehicle_telemetry_snapshot(
  car_state,
  vehicle_fingerprint="",
  timestamp=None,
  source_name=None,
  source_mono_time=None,
  monotonic_now_ns=None,
):
  """Build telemetry only after the comma has a trustworthy wall clock."""
  if not system_time_valid():
    return None
  wall_time = time.time() if timestamp is None else float(timestamp)  # noqa: TID251
  if source_mono_time is not None:
    wall_time = source_mono_time_to_wall_time(
      source_mono_time,
      wall_time=wall_time,
      monotonic_now_ns=monotonic_now_ns,
    )
    if wall_time is None:
      return None
  return build_vehicle_telemetry_snapshot(car_state, wall_time, vehicle_fingerprint, source_name=source_name)


def cached_snapshot_timestamp_is_plausible(snapshot, now=None):
  if not isinstance(snapshot, dict):
    return False
  try:
    updated_at = float(snapshot.get("updatedAt", 0.0))
  except (TypeError, ValueError):
    return False
  wall_time = time.time() if now is None else float(now)  # noqa: TID251
  age = wall_time - updated_at
  return 0.0 <= age <= MAXIMUM_CACHED_PUBLISH_AGE_SECONDS


def validated_cached_snapshot_for_publish(snapshot, now=None):
  """Apply strict schema and wall-time checks to a startup cache candidate."""
  wall_time = time.time() if now is None else float(now)  # noqa: TID251
  validated = validated_vehicle_telemetry_snapshot(snapshot, now=wall_time)
  if validated is None or not cached_snapshot_timestamp_is_plausible(validated, now=wall_time):
    return None
  return validated


class StandaloneTransportController:
  def __init__(self, *, config_path=None, data_dir=None):
    self.frp = FRPTunnelController(data_dir=data_dir)
    self.tailscale = TailscaleFunnelController(data_dir=data_dir)
    self.http = VehicleTelemetryHTTPService(config_path=config_path)

  def reconcile(self, config):
    mode = config["mode"]
    fetch = config["fetch"]
    standalone = mode in ("local", "tailscale", "frp") and fetch["enabled"]
    status_path = self.tailscale.data_dir / TAILSCALE_STATUS_FILENAME if mode == "tailscale" else self.frp.data_dir / FRPC_STATUS_FILENAME
    self.http.set_tunnel_status_path(status_path)
    if standalone:
      bind_address = "127.0.0.1" if mode in ("tailscale", "frp") else fetch["bindAddress"]
      try:
        self.http.start(bind_address, fetch["port"])
      except OSError as error:
        self.http.stop()
        self.frp.stop(state="http-failed", error=error)
        self.tailscale.reconcile(False, config["tailscale"], fetch)
        return
    else:
      self.http.stop()
    self.frp.reconcile(mode == "frp" and standalone, config["tunnel"], fetch)
    self.tailscale.reconcile(mode == "tailscale" and standalone, config["tailscale"], fetch)

  def stop(self):
    self.http.stop()
    self.frp.stop()
    self.tailscale.stop()


def vehicle_telemetry_thread(
  *,
  car_state_service=DEFAULT_CAR_STATE_SERVICE,
  telemetry_available_field=None,
  source_mono_time_field=None,
  source_name=None,
  offroad_car_state_service=None,
  offroad_state_resolver=None,
  offroad_source_name=None,
  config_path=None,
  data_dir=None,
):
  # Keep importing this module side-effect free for config tooling and unit
  # tests; only the actual daemon process needs the native msgq extension.
  from cereal import messaging

  services = [car_state_service]
  if offroad_car_state_service is not None:
    services.append(offroad_car_state_service)
  services += ["carParams", "deviceState"]
  sm = messaging.SubMaster(services)
  clock_valid = system_time_valid()
  cache = VehicleTelemetryCache()
  publisher = VehicleTelemetryPublisher(config_path=config_path)
  publisher.start()
  transports = StandaloneTransportController(config_path=config_path, data_dir=data_dir)
  config_loader = VehicleTelemetryConfigLoader(config_path)
  # A valid persisted Unix timestamp normally looks "future" while the device
  # clock is still at its pre-sync value. Retain the schema-bounded record in
  # memory, then apply strict time validation before its one publish attempt.
  cached_snapshot_pending = cache.latest if clock_valid else cache.load_before_clock_sync()

  fingerprint = ""
  started = None
  last_source_mono_time = 0
  ratekeeper = Ratekeeper(1.0, None)
  try:
    while True:
      sm.update(0)
      clock_valid = system_time_valid()
      if clock_valid and cached_snapshot_pending is not None:
        validated_cached_snapshot = validated_cached_snapshot_for_publish(cached_snapshot_pending)
        if validated_cached_snapshot is not None:
          publisher.submit(validated_cached_snapshot)
        cached_snapshot_pending = None

      if sm.updated["deviceState"] and sm.valid["deviceState"]:
        started = bool(sm["deviceState"].started)
        publisher.set_onroad(started)
      if sm.updated["carParams"] and sm.valid["carParams"]:
        fingerprint = str(sm["carParams"].carFingerprint)

      selected_service, car_state = select_vehicle_telemetry_state(
        started,
        car_state_service,
        sm[car_state_service],
        offroad_car_state_service,
        sm[offroad_car_state_service] if offroad_car_state_service is not None else None,
        offroad_state_resolver,
      )

      if car_state is None:
        transports.reconcile(config_loader.get())
        ratekeeper.keep_time()
        continue

      telemetry_available = telemetry_available_field is None or bool(getattr(car_state, telemetry_available_field, False))
      source_mono_time = int(getattr(car_state, source_mono_time_field, 0)) if source_mono_time_field is not None else None
      source_advanced = source_mono_time is None or source_sample_is_new(source_mono_time, last_source_mono_time)
      if (clock_valid and sm.updated[selected_service] and sm.alive[selected_service] and sm.valid[selected_service] and
          telemetry_available and source_advanced):
        selected_source_name = select_vehicle_telemetry_source_name(
          selected_service, offroad_car_state_service, source_name, offroad_source_name,
        )
        snapshot = build_clock_valid_vehicle_telemetry_snapshot(
          car_state,
          fingerprint,
          source_name=selected_source_name,
          source_mono_time=source_mono_time,
        )
        if snapshot is not None:
          if source_mono_time is not None:
            last_source_mono_time = source_mono_time
          cache.store(snapshot)
          publisher.submit(snapshot)

      transports.reconcile(config_loader.get())
      ratekeeper.keep_time()
  finally:
    transports.stop()


def main():
  vehicle_telemetry_thread()


if __name__ == "__main__":
  main()
