from cereal import custom
from openpilot.system.vehicle_telemetry import core


def test_starpilot_vehicle_state_schema_exports_route_backed_fields():
  state = custom.StarPilotCarState.new_message()
  state.vehicleTelemetryAvailable = True
  state.vehicleTelemetrySocValid = True
  state.vehicleTelemetryDteValid = True
  state.vehicleTelemetrySourceMonoTime = 1_000_000_000
  state.fuelGauge = 0.73
  state.distanceToEmpty = 281_000.0
  state.vEgo = 12.0
  state.standstill = False

  snapshot = core.build_vehicle_telemetry_snapshot(state, timestamp=1_000.0, vehicle_fingerprint="KIA_EV9")

  assert snapshot["stateOfChargePercent"] == 73.0
  assert snapshot["distanceToEmptyKilometers"] == 281.0
