from types import SimpleNamespace

import pytest
from opendbc.car.can_definitions import CanData
from opendbc.car.car_helpers import FRAME_FINGERPRINT, _apply_starpilot_access_policy, _get_gm_stored_candidate_fallback, can_fingerprint
from opendbc.car.fingerprints import _FINGERPRINTS as FINGERPRINTS
from opendbc.car.gm.values import CAR as GM
from opendbc.car.toyota.values import CAR as TOYOTA


class TestCanFingerprint:
  @staticmethod
  def _fingerprint_from_can(fingerprint):
    can = [CanData(address=address, dat=b'\x00' * length, src=src)
           for address, length in fingerprint.items() for src in (0, 1)]
    fingerprint_iter = iter([can])
    return can_fingerprint(lambda **kwargs: [next(fingerprint_iter, [])])

  @pytest.mark.parametrize("car_model, fingerprints", FINGERPRINTS.items())
  def test_can_fingerprint(self, car_model, fingerprints):
    """Tests online fingerprinting function on offline fingerprints"""

    for fingerprint in fingerprints:  # can have multiple fingerprints for each platform
      can = [CanData(address=address, dat=b'\x00' * length, src=src)
             for address, length in fingerprint.items() for src in (0, 1)]

      fingerprint_iter = iter([can])
      car_fingerprint, finger = can_fingerprint(lambda **kwargs: [next(fingerprint_iter, [])])  # noqa: B023

      if car_model == TOYOTA.TOYOTA_MATRIX_RETROFIT:
        assert fingerprint == {}
        assert car_fingerprint is None
      elif car_fingerprint is None and str(car_model).startswith(("BUICK_", "CADILLAC_", "CHEVROLET_", "GMC_", "HOLDEN_")):
        assert _get_gm_stored_candidate_fallback(finger, str(car_model), None) is not None
      else:
        assert car_fingerprint == car_model
      assert finger[0] == fingerprint
      assert finger[1] == fingerprint
      assert finger[2] == {}

  def test_gm_sascm_superset_fingerprint_matches_ascm_variant(self):
    car_fingerprint, finger = self._fingerprint_from_can(FINGERPRINTS[GM.CADILLAC_ESCALADE_ESV_2019_ASCM][0])

    assert car_fingerprint == GM.CADILLAC_ESCALADE_ESV_2019_ASCM
    assert finger[0][0x2FF] == 8

  def test_timing(self, subtests):
    # just pick any CAN fingerprinting car
    car_model = "COMMA_BODY"
    fingerprint = FINGERPRINTS[car_model][0]

    cases = []

    # case 1 - one match, make sure we keep going for 100 frames
    can = [CanData(address=address, dat=b'\x00' * length, src=src)
           for address, length in fingerprint.items() for src in (0, 1)]
    cases.append((FRAME_FINGERPRINT, car_model, can))

    # case 2 - no matches, make sure we keep going for 100 frames
    can = [CanData(address=1, dat=b'\x00' * 1, src=src) for src in (0, 1)]  # uncommon address
    cases.append((FRAME_FINGERPRINT, None, can))

    # case 3 - multiple matches, make sure we keep going for 200 frames to try to eliminate some
    can = [CanData(address=2016, dat=b'\x00' * 8, src=src) for src in (0, 1)]  # common address
    cases.append((FRAME_FINGERPRINT * 2, None, can))

    for expected_frames, car_model, can in cases:
      with subtests.test(expected_frames=expected_frames, car_model=car_model):
        frames = 0

        def can_recv(**kwargs):
          nonlocal frames
          frames += 1
          return [can]  # noqa: B023

        car_fingerprint, _ = can_fingerprint(can_recv)
        assert car_fingerprint == car_model
        assert frames == expected_frames + 2  # TODO: fix extra frames

  def test_gm_stored_candidate_fallback_prefers_persisted_model(self):
    fingerprints = {0: {190: 6, 201: 8, 209: 7, 211: 2, 241: 6}}

    candidate = _get_gm_stored_candidate_fallback(fingerprints, "CHEVROLET_VOLT_CC", None)

    assert candidate == "CHEVROLET_VOLT_CC"

  def test_gm_stored_candidate_fallback_uses_cached_model(self):
    fingerprints = {0: {190: 6, 201: 8, 209: 7, 211: 2, 241: 6}}

    candidate = _get_gm_stored_candidate_fallback(fingerprints, "MOCK", "CHEVROLET_VOLT_CC")

    assert candidate == "CHEVROLET_VOLT_CC"

  def test_gm_stored_candidate_fallback_demotes_volt_camera_without_live_camera_msg(self):
    fingerprints = {0: {190: 6, 201: 8, 209: 7, 211: 2, 241: 6}, 2: {}}

    candidate = _get_gm_stored_candidate_fallback(fingerprints, "CHEVROLET_VOLT_CAMERA", None)

    assert candidate == "CHEVROLET_VOLT"

  def test_gm_stored_candidate_fallback_promotes_volt_when_live_camera_msg_present(self):
    fingerprints = {0: {190: 6, 201: 8, 209: 7, 211: 2, 241: 6}, 2: {0x320: 3}}

    candidate = _get_gm_stored_candidate_fallback(fingerprints, "CHEVROLET_VOLT", None)

    assert candidate == "CHEVROLET_VOLT_CAMERA"

  def test_gm_stored_candidate_fallback_ignores_non_gm_fingerprint(self):
    fingerprints = {0: {1: 1, 2: 2, 3: 3, 4: 4}}

    candidate = _get_gm_stored_candidate_fallback(fingerprints, "CHEVROLET_VOLT_CC", "CHEVROLET_VOLT_CC")

    assert candidate is None

  def test_starpilot_access_policy_ignores_stale_block_user_toggle(self):
    candidate = _apply_starpilot_access_policy("CHEVROLET_VOLT_CC", SimpleNamespace(block_user=True))

    assert candidate == "CHEVROLET_VOLT_CC"
