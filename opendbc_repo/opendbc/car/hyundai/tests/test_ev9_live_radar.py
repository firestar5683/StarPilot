from cereal import car

from opendbc.car.hyundai.radar_interface import RadarInterface
from opendbc.car.hyundai.values import CAR


def radar_interface(candidate):
  cp = car.CarParams.new_message()
  cp.carFingerprint = candidate
  cp.radarUnavailable = True
  return RadarInterface(cp)


def test_ev9_can_explicitly_enable_live_mrr35_tracks():
  ri = radar_interface(CAR.KIA_EV9)
  assert ri.radar_off_can
  assert ri.enable_ev9_live_radar_tracks()
  assert not ri.radar_off_can


def test_other_hyundais_cannot_use_ev9_override():
  ri = radar_interface(CAR.HYUNDAI_IONIQ_9)
  assert not ri.enable_ev9_live_radar_tracks()
  assert ri.radar_off_can
