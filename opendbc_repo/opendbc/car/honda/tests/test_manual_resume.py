import pytest

from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.can.dbc import DBC as CANDBC
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.honda.hondacan import CanBus
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, DBC


@pytest.mark.parametrize("identity", (CAR.HONDA_ACCORD, CAR.HONDA_CIVIC_2022))
@pytest.mark.parametrize("alpha", (False, True))
@pytest.mark.parametrize("release", (False, True))
@pytest.mark.parametrize("automatic", (False, True))
def test_original_manual_stock_resume_final_factory(identity, alpha, release, automatic):
  fp = gen_empty_fingerprint()
  initial = CarInterface.get_params(identity, fp, [], alpha, release, False)
  if automatic:
    message = CANDBC(DBC[identity][Bus.pt]).name_to_msg["GEARBOX_AUTO"]
    assert message.address == 0x1A3
    fp[CanBus(initial).pt][message.address] = message.size
  cp = CarInterface.get_params(identity, fp, [], alpha, release, False)
  assert cp.transmissionType == (structs.CarParams.TransmissionType.automatic if automatic else structs.CarParams.TransmissionType.manual)
  expected_resume = automatic or cp.openpilotLongitudinalControl
  assert cp.autoResumeSng == expected_resume
  assert cp.minEnableSpeed == pytest.approx(-1.0 if expected_resume else 25.51 * CV.MPH_TO_MS)
  assert cp.pcmCruise == (not cp.openpilotLongitudinalControl)
  assert cp.safetyConfigs[-1].safetyParam == initial.safetyConfigs[-1].safetyParam
  assert cp.flags == initial.flags
  ci = CarInterface(cp)
  assert ci.CC.CP.transmissionType == cp.transmissionType
  assert ci.CC.CP.autoResumeSng == expected_resume


@pytest.mark.parametrize("identity", (CAR.HONDA_CIVIC_BOSCH, CAR.HONDA_FIT_4G, CAR.HONDA_CIVIC, CAR.HONDA_ODYSSEY_TWN))
@pytest.mark.parametrize("alpha", (False, True))
@pytest.mark.parametrize("release", (False, True))
def test_nonmanual_neighbor_resume_unchanged(identity, alpha, release):
  cp = CarInterface.get_params(identity, gen_empty_fingerprint(), [], alpha, release, False)
  assert cp.transmissionType != structs.CarParams.TransmissionType.manual
  if identity == CAR.HONDA_FIT_4G and not cp.openpilotLongitudinalControl:
    expected_resume, minimum = False, 30 * CV.KPH_TO_MS
  elif identity == CAR.HONDA_ODYSSEY_TWN:
    expected_resume, minimum = False, 19 * CV.MPH_TO_MS
  else:
    expected_resume, minimum = True, -1.0
  assert cp.autoResumeSng == expected_resume
  assert cp.minEnableSpeed == pytest.approx(minimum)
