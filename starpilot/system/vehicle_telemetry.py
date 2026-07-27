"""StarPilot storage and compatibility adapter for the shared telemetry core."""

from __future__ import annotations

import os

from pathlib import Path

from openpilot.system.hardware import PC
from openpilot.system.hardware.hw import Paths
from openpilot.system.vehicle_telemetry.core import (  # noqa: F401
  TELEMETRY_MODES,
  VEHICLE_TELEMETRY_CACHE_FILENAME,
  VEHICLE_TELEMETRY_CONFIG_FILENAME,
  VEHICLE_TELEMETRY_HEARTBEAT_SECONDS,
  VEHICLE_TELEMETRY_LEGACY_COMBINED_CONFIG_FILENAME,
  VEHICLE_TELEMETRY_LEGACY_CONFIG_FILENAME,
  VEHICLE_TELEMETRY_LIVE_SECONDS,
  VEHICLE_TELEMETRY_SCHEMA_VERSION,
  VEHICLE_TELEMETRY_STATUS_FILENAME,
  VehicleTelemetryCache,
  VehicleTelemetryPublisher,
  build_vehicle_telemetry_snapshot,
  configure_vehicle_telemetry_runtime,
  default_vehicle_telemetry_config,
  is_fetch_authorized,
  load_vehicle_telemetry_config,
  load_vehicle_telemetry_status,
  public_vehicle_telemetry_config,
  save_vehicle_telemetry_config,
  telemetry_response,
  update_vehicle_telemetry_config,
  validated_vehicle_telemetry_snapshot,
  vehicle_telemetry_activity,
  vehicle_telemetry_cache_path,
  vehicle_telemetry_config_path,
  vehicle_telemetry_config_lock,
  vehicle_telemetry_dir,
  vehicle_telemetry_status_path,
)


def starpilot_vehicle_telemetry_dir() -> Path:
  if override := os.getenv("SP_GALAXY_DIR"):
    return Path(override)
  if override := os.getenv("OPENPILOT_VEHICLE_TELEMETRY_DIR"):
    return Path(override)
  return Path(Paths.comma_home()) / "starpilot" / "data" / "galaxy" if PC else Path("/data/galaxy")


def configure_starpilot_vehicle_telemetry():
  """Point the process-local shared core at StarPilot's existing data."""
  configure_vehicle_telemetry_runtime(
    data_dir_provider=starpilot_vehicle_telemetry_dir,
    legacy_fetch_mode="galaxy",
    source_name="StarPilot carState",
  )


# Galaxy and the StarPilot daemon each run in their own process, so configuring
# at adapter import cannot affect stock openpilot processes.
configure_starpilot_vehicle_telemetry()
