"""Fork-neutral EV Vehicle Telemetry service.

The package intentionally depends only on interfaces available in openpilot.
Forks can supply a different cereal source or storage directory through the
adapter hooks exported by :mod:`openpilot.system.vehicle_telemetry.core`.
"""

from openpilot.system.vehicle_telemetry.core import (  # noqa: F401
  TELEMETRY_MODES,
  VEHICLE_TELEMETRY_SCHEMA_VERSION,
  VehicleTelemetryCache,
  VehicleTelemetryPublisher,
  build_vehicle_telemetry_snapshot,
  configure_vehicle_telemetry_runtime,
  default_vehicle_telemetry_config,
  is_fetch_authorized,
  load_vehicle_telemetry_config,
  load_vehicle_telemetry_status,
  public_vehicle_telemetry_config,
  reset_vehicle_telemetry_runtime,
  save_vehicle_telemetry_config,
  telemetry_response,
  update_vehicle_telemetry_config,
  vehicle_telemetry_activity,
  vehicle_telemetry_cache_path,
  vehicle_telemetry_config_path,
  vehicle_telemetry_config_lock,
  vehicle_telemetry_dir,
  vehicle_telemetry_status_path,
)
