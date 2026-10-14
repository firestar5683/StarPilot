"""Private qualification: execute only after root assembles source and native candidate."""

import math
import pytest
from opendbc.car.hyundai.ray_pedal import get_ray_pedal_target, ray_pedal_gas, pedal_checksum
from opendbc.car.hyundai.tests.test_ray_pedal import ray_controller
from opendbc.safety.tests.test_hyundai_ray_pedal import TestHyundaiRayPedal


@pytest.mark.parametrize("speed,cap", [(0, 0.55), (12, 0.55), (20, 0.65), (25, 0.70), (35, 0.70)])
def test_speed_cap_and_slew(speed, cap):
  assert get_ray_pedal_target(10, speed, min(speed + 2, 40)) == pytest.approx(cap)
  assert ray_pedal_gas(0, speed, 10, min(speed + 2, 40)) == pytest.approx(0.02)


@pytest.mark.parametrize("field", ["accel", "speed", "set_speed"])
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_nonfinite_target_is_zero(field, bad):
  values = dict(accel=0.5, speed=20, set_speed=25)
  values[field] = bad
  assert get_ray_pedal_target(**values) == 0


@pytest.mark.parametrize("gate", ["gasPressed", "brakePressed", "override", "longActive", "fault", "invalid"])
def test_actual_controller_disabled_frames_on_gates(gate):
  cp, controller, cc, cs = ray_controller()
  controller._ray_pedal_gas_last = 0.7
  if gate in ("gasPressed", "brakePressed"):
    setattr(cs.out, gate, True)
  elif gate == "override":
    cc.cruiseControl.override = True
  elif gate == "longActive":
    cc.longActive = False
  elif gate == "fault":
    cs.ray_pedal_state = 1
  else:
    cs.ray_pedal_valid = False
  controller.frame = 4
  _, frames = controller.update(cc.as_reader(), cs, 1_000_000_000)
  data = next(f[1] for f in frames if f[0] == 0x200)
  assert data[:4] == bytes(4)
  assert data[4] & 0x80 == 0
  assert controller._ray_pedal_gas_last == 0


class TestNativeWafflesBoundaries(TestHyundaiRayPedal):
  def test_each_raw_track_boundary(self):
    self.arm()
    for a, b, allowed in [(530, 1035, True), (531, 1035, False), (530, 1036, False), (263, 497, False), (264, 496, False), (530, 980, False)]:
      data = bytearray(a.to_bytes(2, "big") + b.to_bytes(2, "big") + bytes([0x81, 0]))
      data[-1] = pedal_checksum(0, None, data)
      self.assertEqual(self.safety.safety_tx_hook(self.packet((0x200, bytes(data), 0))), allowed)
