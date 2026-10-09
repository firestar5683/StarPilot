import math

import numpy as np
import pytest

from opendbc.car.hyundai.values import CAR as HYUNDAI_CAR
from openpilot.common.constants import CV
from openpilot.selfdrive.controls.lib.latcontrol_vehicle_tunes import (
  GENESIS_GV70_CARS,
  GenesisGV70HighwayCommandStabilizer,
)


def update_accel(stabilizer: GenesisGV70HighwayCommandStabilizer, lateral_accel: float,
                 speed: float = 30.0, enabled: bool = True) -> float:
  return stabilizer.update(lateral_accel / speed ** 2, speed, enabled, 0.01) * speed ** 2


def test_only_electrified_gv70_selected():
  assert GENESIS_GV70_CARS == (HYUNDAI_CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN,)
  assert HYUNDAI_CAR.GENESIS_G70_2020 not in GENESIS_GV70_CARS


@pytest.mark.parametrize('speed', [10.0, 30.0 * CV.MPH_TO_MS, 40.0 * CV.MPH_TO_MS])
def test_no_change_at_low_speed(speed):
  stabilizer = GenesisGV70HighwayCommandStabilizer()
  for i in range(1200):
    accel = 0.3 * math.sin(2.0 * math.pi * 0.5 * i * 0.01)
    assert update_accel(stabilizer, accel, speed) == pytest.approx(accel)


def test_repeated_highway_reversals_are_bounded_and_damped():
  stabilizer = GenesisGV70HighwayCommandStabilizer()
  raw, shaped = [], []
  for i in range(1200):
    accel = 0.15 + 0.3 * math.sin(2.0 * math.pi * 0.5 * i * 0.01)
    raw.append(accel)
    shaped.append(update_accel(stabilizer, accel))

  assert np.std(shaped[600:]) < 0.75 * np.std(raw[600:])
  assert np.max(np.abs(np.array(raw) - np.array(shaped))) <= 0.20 + 1e-6


def test_repeated_moderate_curve_reversals_are_damped():
  stabilizer = GenesisGV70HighwayCommandStabilizer()
  raw, shaped = [], []
  for i in range(1200):
    accel = 0.55 + 0.25 * math.sin(2.0 * math.pi * 0.5 * i * 0.01)
    raw.append(accel)
    shaped.append(update_accel(stabilizer, accel))

  assert np.std(shaped[600:]) < 0.75 * np.std(raw[600:])
  assert np.max(np.abs(np.array(raw) - np.array(shaped))) <= 0.20 + 1e-6


def test_sustained_curve_is_unchanged():
  stabilizer = GenesisGV70HighwayCommandStabilizer()
  curve = np.concatenate((np.linspace(0.0, 0.8, 150), np.full(300, 0.8), np.linspace(0.8, 0.0, 150)))
  for accel in curve:
    assert update_accel(stabilizer, float(accel)) == pytest.approx(accel)


def test_strong_turn_and_driver_input_reset_stabilizer():
  stabilizer = GenesisGV70HighwayCommandStabilizer()
  for i in range(1000):
    accel = 0.3 * math.sin(2.0 * math.pi * 0.5 * i * 0.01)
    update_accel(stabilizer, accel)

  for _ in range(100):
    assert update_accel(stabilizer, 1.2) == pytest.approx(1.2)
  for _ in range(100):
    assert update_accel(stabilizer, 0.4) == pytest.approx(0.4)

  assert update_accel(stabilizer, -0.3, enabled=False) == pytest.approx(-0.3)
  assert update_accel(stabilizer, 0.3) == pytest.approx(0.3)


def test_slow_highway_oscillation_stays_damped_between_reversals():
  stabilizer = GenesisGV70HighwayCommandStabilizer()
  raw, shaped, blends = [], [], []
  for i in range(3000):
    accel = 0.50 + 0.20 * math.sin(2.0 * math.pi * 0.28 * i * 0.01)
    raw.append(accel)
    shaped.append(update_accel(stabilizer, accel))
    blends.append(stabilizer.blend)

  assert min(blends[1500:]) > 0.99
  assert np.std(shaped[1500:]) < 0.70 * np.std(raw[1500:])
  assert np.mean(shaped[1500:]) == pytest.approx(np.mean(raw[1500:]), abs=0.015)


def test_stabilizer_recovers_after_oscillation_ends():
  stabilizer = GenesisGV70HighwayCommandStabilizer()
  for i in range(1600):
    update_accel(stabilizer, 0.50 + 0.20 * math.sin(2.0 * math.pi * 0.4 * i * 0.01))
  assert stabilizer.blend > 0.9

  for _ in range(1500):
    shaped = update_accel(stabilizer, 0.50)
  assert stabilizer.blend < 0.001
  assert shaped == pytest.approx(0.50, abs=1e-6)


@pytest.mark.parametrize('direction', [-1.0, 1.0])
def test_real_curve_direction_change_bypasses_recovery(direction):
  stabilizer = GenesisGV70HighwayCommandStabilizer()
  for i in range(1600):
    update_accel(stabilizer, direction * (0.55 + 0.20 * math.sin(2.0 * math.pi * 0.4 * i * 0.01)))
  assert stabilizer.blend > 0.9

  assert update_accel(stabilizer, -direction * 0.60) == pytest.approx(-direction * 0.60)
  assert stabilizer.blend == 0.0
  assert not stabilizer.reversals
  assert stabilizer.active_until == 0.0
  assert stabilizer.curve_direction == 0


@pytest.mark.parametrize('direction', [-1.0, 1.0])
def test_gradual_s_curve_does_not_delay_direction_change(direction):
  stabilizer = GenesisGV70HighwayCommandStabilizer()
  for i in range(1600):
    update_accel(stabilizer, direction * (0.55 + 0.20 * math.sin(2.0 * math.pi * 0.4 * i * 0.01)))
  assert stabilizer.blend > 0.9

  raw = direction * np.linspace(0.55, -0.65, 500)
  shaped = np.array([update_accel(stabilizer, float(accel)) for accel in raw])
  raw_crossing = np.flatnonzero(direction * raw < 0.0)[0]
  shaped_crossing = np.flatnonzero(direction * shaped < 0.0)[0]
  assert shaped_crossing == raw_crossing
  assert shaped[raw_crossing:] == pytest.approx(raw[raw_crossing:])


def test_inactive_reset_clears_recovery_and_reengages_cleanly():
  stabilizer = GenesisGV70HighwayCommandStabilizer()
  for i in range(1600):
    update_accel(stabilizer, 0.50 + 0.20 * math.sin(2.0 * math.pi * 0.4 * i * 0.01))
  assert stabilizer.active_until > stabilizer.elapsed

  assert update_accel(stabilizer, 0.60, enabled=False) == pytest.approx(0.60)
  assert stabilizer.active_until == 0.0
  assert stabilizer.baseline is None
  assert update_accel(stabilizer, -0.60) == pytest.approx(-0.60)


@pytest.mark.parametrize('speed', [40.1, 45.0, 50.0, 65.0])
def test_recovery_respects_speed_gate_and_correction_bound(speed):
  stabilizer = GenesisGV70HighwayCommandStabilizer()
  speed *= CV.MPH_TO_MS
  max_delta = 0.0
  for i in range(1600):
    accel = 0.3 * math.sin(2.0 * math.pi * 0.4 * i * 0.01)
    shaped = update_accel(stabilizer, accel, speed)
    max_delta = max(max_delta, abs(shaped-accel))
  speed_weight = np.interp(speed, [40.0*CV.MPH_TO_MS,50.0*CV.MPH_TO_MS], [0.0,1.0])
  assert 0.0 < max_delta <= 0.20*speed_weight+1e-6
