import pytest

from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.tesla.teslacan import TeslaCAN


class RecordingPacker:
  def make_can_msg(self, name, bus, values):
    return name, bus, values


@pytest.mark.parametrize("active", [False, True])
@pytest.mark.parametrize(
  ("v_ego", "accel", "expected_set_speed"),
  [
    (20.0, 1.0, 21.0 * CV.MS_TO_KPH),
    (20.0, -2.0, 18.0 * CV.MS_TO_KPH),
    (1.0, -2.0, 0.0),
    (120.0, 2.0, 400.0),
  ],
)
def test_longitudinal_set_speed_tracks_accel_continuously(active, v_ego, accel, expected_set_speed):
  _, _, values = TeslaCAN(RecordingPacker()).create_longitudinal_command(4, accel, 0, v_ego, active)

  assert values["DAS_setSpeed"] == pytest.approx(expected_set_speed)
