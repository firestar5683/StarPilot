"""Exact observed Palisade responses, without loosening firmware matching."""
from opendbc.car.fw_versions import match_fw_to_car_exact
from opendbc.car.hyundai.values import CAR

LIVE_FW = {
  (0x7d4, None): {b'\xf1\x00LXP MDPS C 1.00 1.00 56310S8620\x00 4LXPC100'},
  (0x7c4, None): {b'\xf1\x00LX2 MFC  AT USA LHD 1.00 1.00 99211-S8700 240221'},
  (0x7d0, None): {b'\xf1\x00LX2_ SCC -----      1.00 1.01 99110-S8700         '},
}


def test_observed_firmware_matches_only_the_palisade():
  assert match_fw_to_car_exact(LIVE_FW, match_brand='hyundai', log=False) == {CAR.HYUNDAI_PALISADE_2023}
  for address in LIVE_FW:
    changed = dict(LIVE_FW)
    changed[address] = {b'unknown firmware'}
    assert CAR.HYUNDAI_PALISADE_2023 not in match_fw_to_car_exact(changed, match_brand='hyundai', log=False)
