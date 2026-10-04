import pytest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.fw_versions import match_fw_to_car
from opendbc.car.honda.hondacan import CanBus
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, CarControllerParams, HondaFlags, MODIFIED_EPS_FW

Ecu = structs.CarParams.Ecu
SOURCE_BASELINES = {
  CAR.HONDA_CLARITY: {
    (Ecu.shiftByWire, 0x18da0bf1, None): [
      b'54008-TRW-A910\x00\x00',
    ],
    (Ecu.vsa, 0x18da28f1, None): [
      b'57114-TRW-A010\x00\x00',
      b'57114-TRW-A020\x00\x00',
    ],
    (Ecu.eps, 0x18da30f1, None): [
      b'39990-TRW-A020\x00\x00',
      b'39990-TRW,A020\x00\x00',
    ],
    (Ecu.srs, 0x18da53f1, None): [
      b'77959-TRW-A210\x00\x00',
      b'77959-TRW-A220\x00\x00',
    ],
    (Ecu.gateway, 0x18daeff1, None): [
      b'38897-TRW-A010\x00\x00',
    ],
    (Ecu.fwdRadar, 0x18dab0f1, None): [
      b'36161-TRW-A110\x00\x00',
    ],
  },
  CAR.HONDA_CIVIC: {
    (Ecu.transmission, 416947953, None): b'28101-5CG-A040\x00\x00',
    (Ecu.vsa, 416950513, None): b'57114-TBA-A540\x00\x00',
    (Ecu.eps, 416952561, None): b'39990-TBA,A030\x00\x00',
    (Ecu.srs, 416961521, None): b'77959-TBA-A030\x00\x00',
    (Ecu.fwdRadar, 416985329, None): b'36161-TBA-A020\x00\x00',
    (Ecu.gateway, 417001457, None): b'38897-TBA-A010\x00\x00',
  },
  CAR.HONDA_ACCORD: {
    (Ecu.shiftByWire, 416943089, None): b'54008-TVC-A910\x00\x00',
    (Ecu.transmission, 416947953, None): b'28101-6A7-A220\x00\x00',
    (Ecu.electricBrakeBooster, 416951281, None): b'46114-TVA-A050\x00\x00',
    (Ecu.vsa, 416950513, None): b'57114-TVA-B040\x00\x00',
    (Ecu.eps, 416952561, None): b'39990-TBX-H120\x00\x00',
    (Ecu.srs, 416961521, None): b'77959-TBX-H230\x00\x00',
    (Ecu.hud, 416965105, None): b'78209-TVA-A010\x00\x00',
    (Ecu.fwdRadar, 416985329, None): b'36802-TBX-H140\x00\x00',
    (Ecu.fwdCamera, 416986609, None): b'36161-TBX-H130\x00\x00',
    (Ecu.gateway, 417001457, None): b'38897-TVA-A010\x00\x00',
  },
  CAR.HONDA_CIVIC_BOSCH: {
    (Ecu.transmission, 416947953, None): b'28101-5CG-A920\x00\x00',
    (Ecu.vsa, 416950513, None): b'57114-TBG-A330\x00\x00',
    (Ecu.eps, 416952561, None): b'39990-TBA-C120\x00\x00',
    (Ecu.srs, 416961521, None): b'77959-TBA-A060\x00\x00',
    (Ecu.fwdRadar, 416985329, None): b'36802-TBA-A150\x00\x00',
    (Ecu.fwdCamera, 416986609, None): b'36161-TBA-A130\x00\x00',
    (Ecu.gateway, 417001457, None): b'38897-TBA-A020\x00\x00',
    (Ecu.electricBrakeBooster, 416951281, None): b'39494-TGL-G030\x00\x00',
  },
  CAR.HONDA_CRV_5G: {
    (Ecu.transmission, 416947953, None): b'28101-5RG-A020\x00\x00',
    (Ecu.vsa, 416950513, None): b'57114-TLA-A040\x00\x00',
    (Ecu.eps, 416952561, None): b'39990-TLA,A040\x00\x00',
    (Ecu.electricBrakeBooster, 416951281, None): b'46114-TLA-A040\x00\x00',
    (Ecu.gateway, 417001457, None): b'38897-TLA-A010\x00\x00',
    (Ecu.fwdRadar, 416985329, None): b'36802-TLA-A040\x00\x00',
    (Ecu.fwdCamera, 416986609, None): b'36161-TLA-A060\x00\x00',
    (Ecu.srs, 416961521, None): b'77959-TLA-A240\x00\x00',
  },
}

KNOWN_CASES = (
  (CAR.HONDA_CLARITY, b'39990-TRW,A020\x00\x00'),
  (CAR.HONDA_CIVIC, b'39990-TBA,A030\x00\x00'),
  (CAR.HONDA_ACCORD, b'39990-TVA,A150\x00\x00'),
  (CAR.HONDA_CIVIC_BOSCH, b'39990-TGG,A020\x00\x00'),
  (CAR.HONDA_CIVIC_BOSCH, b'39990-TGG,A120\x00\x00'),
  (CAR.HONDA_CRV_5G, b'39990-TLA,A040\x00\x00'),
)


def params(candidate, firmware):
  fingerprint = gen_empty_fingerprint()
  initial = CarInterface.get_params(candidate, fingerprint, [], False, False, False)
  fingerprint[CanBus(initial).pt][0x1A3] = 8
  return CarInterface.get_params(candidate, fingerprint, firmware, False, False, False)


def eps(version, address=0x18DA30F1, sub=0):
  return structs.CarParams.CarFw(ecu=Ecu.eps, address=address, subAddress=sub, fwVersion=version, brand="honda")


@pytest.mark.parametrize("candidate,version", KNOWN_CASES)
def test_exact_modified_eps_full_cohort_joint_matcher_and_final_cp(candidate, version):
  cohort = {key: values[0] if isinstance(values, list) else values for key, values in SOURCE_BASELINES[candidate].items()}
  cohort[(Ecu.eps, 0x18DA30F1, None)] = version
  firmware = [
    structs.CarParams.CarFw(ecu=ecu, address=address, subAddress=0 if sub is None else sub, fwVersion=value, brand="honda")
    for (ecu, address, sub), value in cohort.items()
  ]
  for allow_exact in (True, False):
    assert match_fw_to_car(firmware, "", allow_exact=allow_exact, log=False)[1] == {candidate}
  stock = params(candidate, [])
  cp = params(candidate, firmware)
  assert cp.flags & HondaFlags.EPS_MODIFIED
  assert not cp.dashcamOnly
  assert [(config.safetyModel.raw, config.safetyParam) for config in cp.safetyConfigs] == [
    (config.safetyModel.raw, config.safetyParam) for config in stock.safetyConfigs
  ]
  assert cp.openpilotLongitudinalControl == stock.openpilotLongitudinalControl
  assert cp.pcmCruise == stock.pcmCruise
  expected = {
    CAR.HONDA_CLARITY: (0.8, 0.24),
    CAR.HONDA_CIVIC: (0.3, 0.1),
    CAR.HONDA_ACCORD: (0.3, 0.09),
    CAR.HONDA_CIVIC_BOSCH: (0.8, 0.24),
    CAR.HONDA_CRV_5G: (0.21, 0.07),
  }[candidate]
  assert list(cp.lateralTuning.pid.kpV) == pytest.approx([expected[0]])
  assert list(cp.lateralTuning.pid.kiV) == pytest.approx([expected[1]])
  lookup = CarControllerParams(cp)
  if candidate == CAR.HONDA_CIVIC:
    assert lookup.STEER_MAX == 8000
    assert lookup.STEER_LOOKUP == [-8000, -2560, 0, 2560, 8000]
    assert lookup.STEER_LOOKUP_V == [-3840, -2560, 0, 2560, 3840]
  elif candidate == CAR.HONDA_CRV_5G:
    assert lookup.STEER_MAX == 10000
    assert lookup.STEER_LOOKUP == [-10000, -2560, 0, 2560, 10000]
    assert lookup.STEER_LOOKUP_V == [-3840, -2560, 0, 2560, 3840]
  else:
    assert lookup.STEER_LOOKUP_V == lookup.STEER_LOOKUP


@pytest.mark.parametrize("candidate,version", KNOWN_CASES)
@pytest.mark.parametrize("case", ("unknown", "wrong-identity", "wrong-address", "wrong-subaddress", "mixed", "mixed-stock"))
def test_unrecognized_or_inconsistent_modified_eps_remains_dashcam(candidate, version, case):
  actual_candidate = CAR.HONDA_CRV_HYBRID if case == "wrong-identity" else candidate
  value = b"39990-UNKNOWN,0000\x00\x00" if case == "unknown" else version
  firmware = [eps(value, 0x18DA31F1 if case == "wrong-address" else 0x18DA30F1, 1 if case == "wrong-subaddress" else 0)]
  if case == "mixed":
    firmware.append(eps(b"39990-UNKNOWN,0000\x00\x00"))
  if case == "mixed-stock":
    firmware.append(eps(b"39990-UNKNOWN-0000\x00\x00"))
  cp = params(actual_candidate, firmware)
  assert cp.dashcamOnly
  assert not cp.flags & HondaFlags.EPS_MODIFIED


@pytest.mark.parametrize("candidate", tuple(SOURCE_BASELINES))
def test_stock_lookup_and_tunes_do_not_acquire_modified_marker(candidate):
  cp = params(candidate, [])
  assert not cp.flags & HondaFlags.EPS_MODIFIED
  lookup = CarControllerParams(cp)
  assert lookup.STEER_LOOKUP_V == lookup.STEER_LOOKUP


def test_recognized_modified_eps_inventory_is_exact_original_subset():
  assert set(KNOWN_CASES) == {(car, version) for car, versions in MODIFIED_EPS_FW.items() for version in versions}
