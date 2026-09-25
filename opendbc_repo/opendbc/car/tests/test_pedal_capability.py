import pytest

from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.pedal import supported_pedal_detected
from opendbc.car.gm.interface import CarInterface as GMInterface
from opendbc.car.gm.values import PEDAL_BOLT_CAR, GMFlags
from opendbc.car.honda.interface import CarInterface as HondaInterface
from opendbc.car.honda.tests.test_nidec_interceptor import IDENTITIES
from opendbc.car.honda.values import HondaFlags


@pytest.mark.parametrize("bus,length,supported,expected", ((0, 6, True, True), (0, 5, True, False),
    (0, 8, True, False), (1, 6, True, False), (2, 6, True, False), (0, 6, False, False)))
def test_exact_supported_physical_layout(bus, length, supported, expected):
  fp = gen_empty_fingerprint()
  fp[bus][0x201] = length
  assert supported_pedal_detected(fp, 0, supported=supported) == expected


@pytest.mark.parametrize("identity", tuple(PEDAL_BOLT_CAR))
@pytest.mark.parametrize("length", (None, 5, 6, 8))
def test_bolt_factory_hardware_drives_activation(identity, length):
  fp = gen_empty_fingerprint()
  if length is not None:
    fp[0][0x201] = length
  cp = GMInterface.get_params(identity, fp, [], False, False, False)
  assert bool(cp.flags & GMFlags.PEDAL_LONG) == (length == 6)
  if length == 6:
    # Hardware detection alone does not qualify a removed-camera installation.
    assert cp.dashcamOnly and not cp.openpilotLongitudinalControl
    assert cp.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.noOutput


@pytest.mark.parametrize("identity", tuple(PEDAL_BOLT_CAR))
@pytest.mark.parametrize("removed", (False, True))
def test_bolt_factory_requires_selected_physical_topology(identity, removed):
  fp = gen_empty_fingerprint()
  fp[0][0x201] = 6
  required = {0x184: 8, 0x34A: 5, 0x348: 5, 0xC9: 8, 0x1C4: 8, 0x1E1: 7,
              0x1F5: 8, 0xBD: 7, 0x232: 8, 0x3D1: 8, 0xBE: 6}
  if removed:
    fp[0].update(required)
  else:
    fp[2][0x320] = 8
  cp = GMInterface.get_params(identity, fp, [], False, False, False)
  assert cp.flags & GMFlags.PEDAL_LONG
  assert cp.openpilotLongitudinalControl and not cp.pcmCruise and not cp.dashcamOnly
  assert cp.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.gm
  ci = GMInterface(cp)
  assert 0x201 in ci.can_parsers[Bus.pt].message_states
  if removed:
    for address in required:
      incomplete = gen_empty_fingerprint()
      incomplete[0].update({key: value for key, value in fp[0].items() if key != address})
      denied = GMInterface.get_params(identity, incomplete, [], False, False, False)
      assert denied.flags & GMFlags.PEDAL_LONG
      assert denied.dashcamOnly and not denied.openpilotLongitudinalControl
      assert denied.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.noOutput


@pytest.mark.parametrize("identity", IDENTITIES)
def test_honda_native_owner_unchanged_automatic(identity):
  fp = gen_empty_fingerprint()
  fp[0][0x201] = 6
  cp = HondaInterface.get_params(identity, fp, [], False, False, False)
  assert cp.flags & HondaFlags.GAS_INTERCEPTOR
  assert cp.openpilotLongitudinalControl and not cp.pcmCruise
  ci = HondaInterface(cp)
  assert ci.CC.nidec_interceptor is not None
  assert 0x201 in ci.can_parsers[Bus.pt].message_states


def test_restarted_factory_never_carries_previous_pedal_flag():
  identity = next(iter(PEDAL_BOLT_CAR))
  fp = gen_empty_fingerprint()
  fp[0][0x201] = 6
  connected = GMInterface.get_params(identity, fp, [], False, False, False)
  disconnected = GMInterface.get_params(identity, gen_empty_fingerprint(), [], False, False, False)
  assert connected.flags & GMFlags.PEDAL_LONG
  assert not disconnected.flags & GMFlags.PEDAL_LONG
  assert GMInterface.get_params(identity, fp, [], False, False, False).to_dict() == connected.to_dict()


@pytest.mark.parametrize("identity", ("CHEVROLET_BOLT_EUV", "CHEVROLET_BOLT_ACC_2022_2023"))
@pytest.mark.parametrize("alpha", (False, True))
@pytest.mark.parametrize("release", (False, True))
@pytest.mark.parametrize("saved", (None, False, True))
def test_stock_acc_alias_uses_existing_pedal_profile_despite_saved_preference(identity, alpha, release, saved):
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from opendbc.car.gm.values import CAR
  with OpenpilotPrefix():
    store = Params()
    if saved is not None:
      store.put_bool('GMPedalLongitudinal', saved, block=True)
    fp = gen_empty_fingerprint()
    fp[0][0x201] = 6
    actual = GMInterface.get_params(getattr(CAR, identity), fp, [], alpha, release, False)
    expected = GMInterface.get_params(CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL, fp, [], alpha, release, False)
    assert actual.to_dict() == expected.to_dict()
    assert actual.flags & GMFlags.PEDAL_LONG


@pytest.mark.parametrize("bus,length", ((0, 5), (0, 8), (1, 6), (2, 6)))
def test_stock_acc_wrong_sensor_never_changes_vehicle_identity(bus, length):
  from opendbc.car.gm.values import CAR
  fp = gen_empty_fingerprint()
  fp[bus][0x201] = length
  cp = GMInterface.get_params(CAR.CHEVROLET_BOLT_EUV, fp, [], False, False, False)
  assert cp.carFingerprint == CAR.CHEVROLET_BOLT_EUV
  assert not cp.flags & GMFlags.PEDAL_LONG


@pytest.mark.parametrize("identity", ("CHEVROLET_BOLT_EUV", "CHEVROLET_BOLT_ACC_2022_2023"))
def test_real_get_car_final_identity_keeps_observed_firmware_and_vin(identity, monkeypatch):
  from opendbc.car import car_helpers, structs
  from opendbc.car.gm.values import CAR
  fp = gen_empty_fingerprint()
  fp[0][0x201] = 6
  firmware = [structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.fwdCamera, address=0x24b,
                                    fwVersion=b'fixture-observed-camera', brand='gm')]
  monkeypatch.setattr(car_helpers, 'fingerprint', lambda *_args: (getattr(CAR, identity), fp,
                      'fixture-observed-vin', firmware, structs.CarParams.FingerprintSource.can, True))
  ci = car_helpers.get_car(list, lambda _frames: None, lambda _enabled: None,
                           alpha_long_allowed=False, is_release=False)
  assert ci.CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL
  assert ci.CP.carVin == 'fixture-observed-vin'
  assert ci.CP.carFw[0].fwVersion == b'fixture-observed-camera'
  assert ci.CP.fingerprintSource == structs.CarParams.FingerprintSource.can
  assert ci.CP.flags & GMFlags.PEDAL_LONG
