#!/usr/bin/env python3
"""StarPilot adapter from its single-consumer vehicle state to telemetry."""

from openpilot.starpilot.system.vehicle_telemetry import configure_starpilot_vehicle_telemetry
from openpilot.system.vehicle_telemetry.daemon import (  # noqa: F401
  MAXIMUM_CACHED_PUBLISH_AGE_SECONDS,
  build_clock_valid_vehicle_telemetry_snapshot,
  cached_snapshot_timestamp_is_plausible,
  vehicle_telemetry_thread as core_vehicle_telemetry_thread,
)


VEHICLE_TELEMETRY_SERVICES = ["starpilotCarState", "pandaStates", "carParams", "deviceState"]


def resolve_ev9_offroad_vehicle_telemetry(panda_states):
  """Select only pandad's already-derived EV9 state; never open raw CAN/Panda."""
  candidates = [state.ev9VehicleTelemetry for state in panda_states]
  candidates = [state for state in candidates if int(state.vehicleTelemetrySourceMonoTime) > 0]
  return max(candidates, key=lambda state: int(state.vehicleTelemetrySourceMonoTime), default=None)


def vehicle_telemetry_thread():
  configure_starpilot_vehicle_telemetry()
  core_vehicle_telemetry_thread(
    car_state_service="starpilotCarState",
    telemetry_available_field="vehicleTelemetryAvailable",
    source_mono_time_field="vehicleTelemetrySourceMonoTime",
    source_name="StarPilot carState",
    offroad_car_state_service="pandaStates",
    offroad_state_resolver=resolve_ev9_offroad_vehicle_telemetry,
    offroad_source_name="pandad derived EV9 energy",
  )


def main():
  vehicle_telemetry_thread()


if __name__ == "__main__":
  main()
