import itertools

import pytest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.fw_versions import match_fw_to_car
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, HondaFlags

Ecu = structs.CarParams.Ecu
SOURCE_VERSIONS = (
  (Ecu.eps, 416952561, b'39990-T14-B510\x00\x00', b'39990-T14-B030\x00\x00'),
  (Ecu.gateway, 417001457, b'38897-T14-M210\x00\x00', b'38897-T14-M110\x00\x00'),
  (Ecu.srs, 416961521, b'77959-T14-B810\x00\x00', b'77959-T00-B830\x00\x00'),
  (Ecu.fwdRadar, 416985329, b'8S102-T14-P020\x00\x00', b'36161-T14-P050\x00\x00'),
  (Ecu.vsa, 416950513, b'57114-T14-M510\x00\x00', b'57114-T14-B030\x00\x00'),
  (Ecu.transmission, 416947953, b'28101-63B-M510\x00\x00', b'28101-63B-M420\x00\x00'),
)


def cohort(choices):
  return [structs.CarParams.CarFw(ecu=ecu, address=address, subAddress=0,
                                 fwVersion=old if choice else new, brand="honda")
          for (ecu, address, new, old), choice in zip(SOURCE_VERSIONS, choices, strict=True)]


@pytest.mark.parametrize("choices", tuple(itertools.product((False, True), repeat=6)))
def test_city_original_and_retained_firmware_joint_discovery_and_factory(choices):
  firmware = cohort(choices)
  for allow_exact in (True, False):
    assert match_fw_to_car(firmware, "", allow_exact=allow_exact, log=False)[1] == {CAR.HONDA_CITY_7G}
  fp = gen_empty_fingerprint()
  fp[0][0x191] = 8
  for alpha in (False, True):
    actual = CarInterface.get_params(CAR.HONDA_CITY_7G, fp, firmware, alpha, False, False)
    baseline = CarInterface.get_params(CAR.HONDA_CITY_7G, fp, [], alpha, False, False)
    assert actual.to_dict() == baseline.to_dict()
    assert not actual.dashcamOnly
    assert not actual.flags & HondaFlags.EPS_MODIFIED


@pytest.mark.parametrize("index", range(6))
def test_city_exact_match_rejects_unknown_present_ecu(index):
  firmware = cohort((False,) * 6)
  firmware[index].fwVersion = b"UNKNOWN-CITY-FIRMWARE"
  assert CAR.HONDA_CITY_7G not in match_fw_to_car(firmware, "", allow_fuzzy=False, log=False)[1]
