"""Positive modern marker admission never infers legacy encoding from absence."""
import pytest
from opendbc.car import gen_empty_fingerprint
from opendbc.car.structs import CarParams
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.values import CAR, CANBUS, TeslaSafetyFlags


@pytest.mark.parametrize('alpha', [False, True])
@pytest.mark.parametrize('marker', [None, (CANBUS.autopilot_party, 0x489), (CANBUS.party, 0x054), (1, 0x489), (2, 0x054)])
def test_fresh_positive_marker_controls_modern_admission(alpha, marker):
  fingerprint = gen_empty_fingerprint()
  if marker is not None:
    fingerprint[marker[0]][marker[1]] = 8
  cp = CarInterface.get_params(CAR.TESLA_MODEL_3, fingerprint, [], alpha, False, False)
  assert cp.dashcamOnly == (marker not in ((CANBUS.autopilot_party, 0x489), (CANBUS.party, 0x054)))
  assert cp.safetyConfigs[0].safetyParam == int(alpha)
  assert not cp.flags & 2


@pytest.mark.parametrize('old_word', [2, 3, 8, 0x8000])
def test_old_serialized_cp_bits_require_fresh_marker_revalidation(old_word):
  cp = CarInterface.get_params(CAR.TESLA_MODEL_3, gen_empty_fingerprint(), [], False, False, False)
  cp.flags |= 2
  cp.safetyConfigs[0].safetyParam = old_word
  with CarParams.from_bytes(cp.to_bytes()) as old:
    restored = old.as_builder()
  restored = CarInterface._get_params(restored, CAR.TESLA_MODEL_3, gen_empty_fingerprint(), [], False, False, False)
  assert restored.dashcamOnly, 'old flags/firmware/cache cannot substitute for current marker'
  assert restored.safetyConfigs[0].safetyParam == 0, 'fresh production rebuilds modern exact word'


@pytest.mark.parametrize('alpha', [False, True])
def test_hw1_and_model_x_stay_independent_of_modern_marker(alpha):
  fingerprint = gen_empty_fingerprint()
  hw1 = CarInterface.get_params(CAR.TESLA_MODEL_S_HW1, fingerprint, [], alpha, False, False)
  assert not hw1.dashcamOnly
  assert hw1.safetyConfigs[0].safetyParam == TeslaSafetyFlags.HW1 | int(alpha)
  fingerprint[CANBUS.autopilot_party][0x489] = 8
  model_x = CarInterface.get_params(CAR.TESLA_MODEL_X, fingerprint, [], alpha, False, False)
  assert model_x.dashcamOnly
