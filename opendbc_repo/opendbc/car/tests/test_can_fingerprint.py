from types import SimpleNamespace

import pytest
import opendbc.car.car_helpers as car_helpers
from opendbc.car.can_definitions import CanData
from opendbc.car.car_helpers import FRAME_FINGERPRINT, _apply_starpilot_access_policy, _get_gm_stored_candidate_fallback, \
                                            can_fingerprint, fingerprint as fingerprint_car
from opendbc.car.fingerprints import _FINGERPRINTS as FINGERPRINTS
from opendbc.car.gm.values import CAR as GM


class TestCanFingerprint:
  @staticmethod
  def _fingerprint_from_can(fingerprint):
    can = [CanData(address=address, dat=b'\x00' * length, src=src)
           for address, length in fingerprint.items() for src in (0, 1)]
    fingerprint_iter = iter([can])
    return can_fingerprint(lambda **kwargs: [next(fingerprint_iter, [])])  # noqa: B023

  @pytest.mark.parametrize("car_model, fingerprints", FINGERPRINTS.items())
  def test_can_fingerprint(self, car_model, fingerprints):
    """Tests online fingerprinting function on offline fingerprints"""

    for fingerprint in fingerprints:  # can have multiple fingerprints for each platform
      can = [CanData(address=address, dat=b'\x00' * length, src=src)
             for address, length in fingerprint.items() for src in (0, 1)]

      fingerprint_iter = iter([can])
      car_fingerprint, finger = can_fingerprint(lambda **kwargs: [next(fingerprint_iter, [])])  # noqa: B023

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
    car_model = "CHEVROLET_BOLT_ACC_2022_2023"
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

  def test_fingerprint_can_disable_all_vin_and_firmware_queries(self, monkeypatch):
    monkeypatch.delenv("FINGERPRINT", raising=False)
    monkeypatch.delenv("SKIP_FW_QUERY", raising=False)
    monkeypatch.delenv("DISABLE_FW_CACHE", raising=False)
    monkeypatch.setattr(car_helpers, "get_vin",
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("VIN query must be vetoed")))
    monkeypatch.setattr(car_helpers, "get_present_ecus",
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("ECU query must be vetoed")))
    monkeypatch.setattr(car_helpers, "get_fw_versions_ordered",
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("FW query must be vetoed")))
    monkeypatch.setattr(car_helpers, "can_fingerprint", lambda _can_recv: (None, {0: {}, 1: {}, 2: {}, 3: {}}))

    set_obd_calls = []
    fingerprint_car(lambda **kwargs: [], lambda _msgs: None, set_obd_calls.append, 1, None, allow_fw_query=False)

    assert set_obd_calls == [False]

  def test_fingerprint_uses_valid_cache_while_wire_queries_are_disabled(self, monkeypatch):
    monkeypatch.delenv("FINGERPRINT", raising=False)
    monkeypatch.delenv("SKIP_FW_QUERY", raising=False)
    monkeypatch.delenv("DISABLE_FW_CACHE", raising=False)
    monkeypatch.setattr(car_helpers, "get_vin",
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("VIN query must be vetoed")))
    monkeypatch.setattr(car_helpers, "get_present_ecus",
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("ECU query must be vetoed")))
    monkeypatch.setattr(car_helpers, "get_fw_versions_ordered",
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("FW query must be vetoed")))
    monkeypatch.setattr(car_helpers, "match_fw_to_car", lambda _car_fw, _vin: (True, set()))
    monkeypatch.setattr(car_helpers, "can_fingerprint", lambda _can_recv: (None, {0: {}, 1: {}, 2: {}, 3: {}}))
    cached_fw = [SimpleNamespace(address=0x730)]
    cached_params = SimpleNamespace(brand="hyundai", carVin="KM8KNDAF0PU123456", carFw=cached_fw)

    set_obd_calls = []
    result = fingerprint_car(lambda **kwargs: [], lambda _msgs: None, set_obd_calls.append, 1, cached_params,
                             allow_fw_query=False)

    assert result[2] == cached_params.carVin
    assert result[3] == cached_fw
    assert set_obd_calls == [False]
