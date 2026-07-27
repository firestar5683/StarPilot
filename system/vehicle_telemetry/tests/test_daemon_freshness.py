from types import SimpleNamespace

import pytest

from cereal import messaging
from openpilot.starpilot.system.vehicle_telemetryd import resolve_ev9_offroad_vehicle_telemetry
from openpilot.system.vehicle_telemetry import daemon


def telemetry_state(source_mono_time=9_800_000_000):
  return SimpleNamespace(
    vehicleTelemetryAvailable=True,
    vehicleTelemetrySourceMonoTime=source_mono_time,
    vehicleTelemetrySocValid=True,
    vehicleTelemetryDteValid=True,
    vehicleTelemetryChargingValid=True,
    vehicleTelemetryChargePortValid=True,
    fuelGauge=0.775,
    distanceToEmpty=408_000.0,
    charging=True,
    chargingPortConnected=True,
    chargingTimeRemaining=0.0,
    vEgo=0.0,
    standstill=True,
  )


def test_source_timestamp_maps_to_stable_wall_time(monkeypatch):
  monkeypatch.setattr(daemon, "system_time_valid", lambda: True)
  state = telemetry_state()

  first = daemon.build_clock_valid_vehicle_telemetry_snapshot(
    state,
    timestamp=1_000.0,
    source_mono_time=state.vehicleTelemetrySourceMonoTime,
    monotonic_now_ns=10_000_000_000,
  )
  later = daemon.build_clock_valid_vehicle_telemetry_snapshot(
    state,
    timestamp=1_000.5,
    source_mono_time=state.vehicleTelemetrySourceMonoTime,
    monotonic_now_ns=10_500_000_000,
  )

  assert first["updatedAt"] == pytest.approx(999.8)
  assert later["updatedAt"] == pytest.approx(first["updatedAt"])
  assert daemon.source_sample_is_new(state.vehicleTelemetrySourceMonoTime, 0)
  assert not daemon.source_sample_is_new(state.vehicleTelemetrySourceMonoTime, state.vehicleTelemetrySourceMonoTime)


def test_source_timestamp_rejects_future_and_expired_samples(monkeypatch):
  monkeypatch.setattr(daemon, "system_time_valid", lambda: True)
  state = telemetry_state()

  assert daemon.build_clock_valid_vehicle_telemetry_snapshot(
    state,
    timestamp=1_000.0,
    source_mono_time=10_000_000_001,
    monotonic_now_ns=10_000_000_000,
  ) is None
  assert daemon.build_clock_valid_vehicle_telemetry_snapshot(
    state,
    timestamp=1_000.0,
    source_mono_time=8_999_999_999,
    monotonic_now_ns=10_000_000_000,
  ) is None


def test_pending_pre_sync_cache_is_revalidated_before_publish(monkeypatch):
  pending = {
    "schemaVersion": 1,
    "updatedAt": 1_750_000_000.0,
    "stateOfChargePercent": 80.0,
  }

  monkeypatch.setattr(daemon.time, "time", lambda: 1_750_000_001.0)
  assert daemon.validated_cached_snapshot_for_publish(pending) == pending

  monkeypatch.setattr(daemon.time, "time", lambda: 1_749_999_999.0)
  assert daemon.validated_cached_snapshot_for_publish(pending) is None

  assert daemon.validated_cached_snapshot_for_publish({**pending, "stateOfChargePercent": "80"}, now=1_750_000_001.0) is None
  assert daemon.validated_cached_snapshot_for_publish(pending, now=1_750_000_000.0 +
                                                       daemon.MAXIMUM_CACHED_PUBLISH_AGE_SECONDS + 1.0) is None


def test_offroad_fallback_requires_explicit_device_started_false():
  onroad = object()
  offroad = object()
  resolver_calls = []

  def resolver(value):
    resolver_calls.append(value)
    return "derived-offroad"

  assert daemon.select_vehicle_telemetry_state(
    True, "starpilotCarState", onroad, "pandaStates", offroad, resolver,
  ) == ("starpilotCarState", onroad)
  assert daemon.select_vehicle_telemetry_state(
    None, "starpilotCarState", onroad, "pandaStates", offroad, resolver,
  ) == ("starpilotCarState", onroad)
  assert resolver_calls == []

  assert daemon.select_vehicle_telemetry_state(
    False, "starpilotCarState", onroad, "pandaStates", offroad, resolver,
  ) == ("pandaStates", "derived-offroad")
  assert resolver_calls == [offroad]
  assert daemon.select_vehicle_telemetry_source_name(
    "starpilotCarState", "pandaStates", "StarPilot carState", "pandad derived EV9 energy",
  ) == "StarPilot carState"
  assert daemon.select_vehicle_telemetry_source_name(
    "pandaStates", "pandaStates", "StarPilot carState", "pandad derived EV9 energy",
  ) == "pandad derived EV9 energy"


def test_panda_state_resolver_selects_newest_derived_sample():
  older = telemetry_state(100)
  newer = telemetry_state(200)
  empty = telemetry_state(0)
  panda_states = [
    SimpleNamespace(ev9VehicleTelemetry=older),
    SimpleNamespace(ev9VehicleTelemetry=empty),
    SimpleNamespace(ev9VehicleTelemetry=newer),
  ]

  assert resolve_ev9_offroad_vehicle_telemetry(panda_states) is newer
  assert resolve_ev9_offroad_vehicle_telemetry([
    SimpleNamespace(ev9VehicleTelemetry=empty),
  ]) is None


def test_panda_state_resolver_uses_real_nested_derived_schema():
  message = messaging.new_message("pandaStates", 2)
  older = message.pandaStates[0].ev9VehicleTelemetry
  older.vehicleTelemetrySourceMonoTime = 100
  newer = message.pandaStates[1].ev9VehicleTelemetry
  newer.vehicleTelemetryAvailable = True
  newer.vehicleTelemetrySourceMonoTime = 200
  newer.vehicleTelemetrySocValid = True
  newer.vehicleTelemetryDteValid = True
  newer.vehicleTelemetryChargingValid = True
  newer.vehicleTelemetryChargePortValid = True
  newer.fuelGauge = 0.775
  newer.distanceToEmpty = 408_000.0
  newer.charging = True
  newer.chargingPortConnected = True
  newer.vEgo = 0.0
  newer.standstill = True

  resolved = resolve_ev9_offroad_vehicle_telemetry(message.pandaStates)
  assert resolved.vehicleTelemetrySourceMonoTime == 200
  assert resolved.vehicleTelemetryAvailable
  assert resolved.vehicleTelemetrySocValid
  assert resolved.vehicleTelemetryDteValid
  assert resolved.vehicleTelemetryChargingValid
  assert resolved.vehicleTelemetryChargePortValid
  assert resolved.fuelGauge == pytest.approx(0.775)
  assert resolved.distanceToEmpty == pytest.approx(408_000.0)
  assert resolved.charging
  assert resolved.chargingPortConnected
  assert resolved.vEgo == 0.0
  assert resolved.standstill
