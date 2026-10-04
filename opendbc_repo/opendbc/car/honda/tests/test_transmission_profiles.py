import pytest

from opendbc.can import CANPacker
from opendbc.can.dbc import DBC as CANDBC
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.honda.hondacan import CanBus
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, DBC, MANUAL_TRANS_CARS

PLATFORMS = (
  CAR.HONDA_NBOX_2G,
  CAR.HONDA_ACCORD,
  CAR.HONDA_ACCORD_11G,
  CAR.HONDA_CIVIC_BOSCH,
  CAR.HONDA_CIVIC_BOSCH_DIESEL,
  CAR.HONDA_CIVIC_2022,
  CAR.HONDA_CRV_5G,
  CAR.HONDA_CRV_6G,
  CAR.HONDA_CRV_HYBRID,
  CAR.HONDA_HRV_3G,
  CAR.HONDA_CITY_7G,
  CAR.ACURA_RDX_3G,
  CAR.ACURA_RDX_3G_MMR,
  CAR.HONDA_INSIGHT,
  CAR.HONDA_E,
  CAR.HONDA_E_ADVANCE,
  CAR.HONDA_PILOT_4G,
  CAR.HONDA_PASSPORT_4G,
  CAR.ACURA_MDX_4G,
  CAR.ACURA_MDX_4G_MMR,
  CAR.HONDA_ODYSSEY_5G_MMR,
  CAR.ACURA_TLX_2G,
  CAR.ACURA_TLX_2G_MMR,
  CAR.HONDA_FIT_4G,
  CAR.ACURA_INTEGRA,
  CAR.ACURA_ADX,
  CAR.ACURA_ILX,
  CAR.HONDA_CRV,
  CAR.HONDA_CRV_EU,
  CAR.HONDA_CRV_SA,
  CAR.HONDA_FIT,
  CAR.HONDA_FREED,
  CAR.HONDA_HRV,
  CAR.HONDA_CLARITY,
  CAR.HONDA_ODYSSEY,
  CAR.HONDA_ODYSSEY_TWN,
  CAR.ACURA_RDX,
  CAR.HONDA_PILOT,
  CAR.HONDA_RIDGELINE,
  CAR.HONDA_CIVIC,
  CAR.HONDA_ACCORD_9G,
  CAR.ACURA_MDX_3G,
  CAR.ACURA_MDX_3G_MMR,
  CAR.ACURA_TLX_1G,
)

@pytest.mark.parametrize("candidate", PLATFORMS)
@pytest.mark.parametrize("source", ("absent", "GEARBOX_AUTO", "GEARBOX_CVT"))
def test_manual_allowlist_and_actual_gearbox_source(candidate, source):
  messages = CANDBC(DBC[candidate][Bus.pt]).name_to_msg
  fingerprint = gen_empty_fingerprint()
  initial = CarInterface.get_params(candidate, fingerprint, [], False, False, False)
  bus = CanBus(initial).pt
  if source != "absent":
    if source not in messages:
      pytest.skip("Selected gearbox is absent from this platform DBC")
    msg = messages[source]
    fingerprint[bus][msg.address] = msg.size
  cp = CarInterface.get_params(candidate, fingerprint, [], False, False, False)
  expected = structs.CarParams.TransmissionType.automatic
  if candidate in (CAR.HONDA_ACCORD, CAR.HONDA_CIVIC_2022) and not any(addr in fingerprint[bus] for addr in (0x191, 0x1A3)):
    expected = structs.CarParams.TransmissionType.manual
  elif 0x191 in fingerprint[bus] and candidate != CAR.ACURA_RDX:
    expected = structs.CarParams.TransmissionType.cvt
  assert cp.transmissionType == expected
  assert MANUAL_TRANS_CARS == frozenset((CAR.HONDA_ACCORD, CAR.HONDA_CIVIC_2022))

@pytest.mark.parametrize("candidate", (CAR.HONDA_CRV_SA, CAR.HONDA_ACCORD_9G))
def test_named_188_automatic_source_uses_real_gear_decoder(candidate):
  fingerprint = gen_empty_fingerprint()
  fingerprint[0][0x188] = 6
  cp = CarInterface.get_params(candidate, fingerprint, [], False, False, False)
  assert cp.transmissionType == structs.CarParams.TransmissionType.automatic
  ci = CarInterface(cp)
  assert ci.CS.gearbox_msg == "GEARBOX_AUTO"
  assert ci.CS.shifter_values[8] == "D"
  assert ci.CS.shifter_values[2] == "R"
  ci.update([])
  packer = CANPacker(DBC[candidate][Bus.pt])
  for tick, (value, expected) in enumerate(((8, structs.CarState.GearShifter.drive), (2, structs.CarState.GearShifter.reverse))):
    frame = packer.make_can_msg("GEARBOX_AUTO", 0, {"GEAR_SHIFTER": value})
    assert (frame[0], len(frame[1])) == (0x188, 6)
    state = ci.update([(1_000_000_000 + tick * 100_000_000, [frame])])
    assert state.gearShifter == expected
