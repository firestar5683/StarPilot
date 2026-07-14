from cereal import car
from opendbc.can.packer import CANPacker
from opendbc.can.parser import CANParser

from opendbc.car.hyundai.radar_interface import MRR35_RADAR_MSG_COUNT, MRR35_RADAR_START_ADDR, RadarInterface, \
                                                ev9_mrr35_cluster_display_candidate, \
                                                ev9_mrr35_side_display_retention_candidate, \
                                                ev9_mrr35_strict_side_display_candidate
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


def test_ev9_display_discriminator_rejects_observed_garage_tracks():
  for discriminator in (124, 125, 126, 200):
    assert not ev9_mrr35_cluster_display_candidate({"UNKNOWN_7": discriminator})
  assert ev9_mrr35_cluster_display_candidate({"UNKNOWN_7": 201})


def test_ev9_strict_side_discriminator_requires_mature_lifecycle():
  mature = {"UNKNOWN_7": 281, "NEW_SIGNAL_3": 2, "NEW_SIGNAL_12": 10,
            "NEW_SIGNAL_15": 2, "NEW_SIGNAL_17": 1}
  assert ev9_mrr35_strict_side_display_candidate(mature)
  assert not ev9_mrr35_strict_side_display_candidate({**mature, "UNKNOWN_7": 280})
  assert not ev9_mrr35_strict_side_display_candidate({**mature, "NEW_SIGNAL_12": 9})
  assert ev9_mrr35_side_display_retention_candidate({"UNKNOWN_7": 281})
  assert not ev9_mrr35_side_display_retention_candidate({"UNKNOWN_7": 280})


def test_mrr35_display_discriminator_uses_neutral_name_on_all_tracks():
  dbc = "hyundai_mrr35_radar_generated"
  packer = CANPacker(dbc)

  for addr in range(MRR35_RADAR_START_ADDR, MRR35_RADAR_START_ADDR + MRR35_RADAR_MSG_COUNT):
    name = f"RADAR_TRACK_{addr:x}"
    parser = CANParser(dbc, [(name, 0)], 0)
    msg = packer.make_can_msg(name, 0, {"UNKNOWN_7": 321})
    parser.update([(1, [msg])])
    assert parser.vl[name]["UNKNOWN_7"] == 321
