import math
import random

import pytest

from opendbc.can.dbc import DBC as DbcFile
from opendbc.can.parser import get_raw_value
from opendbc.car.can_definitions import CanData
from opendbc.car.honda.hondacan import CanBus
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.radar_interface import (
  BOSCH_A_AZIMUTH_SCALE_RAD,
  BOSCH_A_AUX_IDS,
  BOSCH_A_DBC_NAME,
  BOSCH_A_DIRECT_VREL_INVALID,
  BOSCH_A_DIRECT_VREL_MAX_RAW,
  BOSCH_A_DIRECT_VREL_MAX_UNCERTAINTY_RAW,
  BOSCH_A_FALLBACK_RANGE_RATE_MAX_MPS,
  BOSCH_A_FREQ_HZ,
  BOSCH_A_MAIN_IDS,
  BOSCH_A_NUM_SLOTS,
  BOSCH_A_RANGE_RATIO_INVALID,
  BOSCH_A_RANGE_SCALE_M,
  BOSCH_A_STALE_S,
  BOSCH_A_SWEEP_END_MSG,
  BOSCH_A_TRIGGER_MSG,
  _bosch_a_aux_id,
  _bosch_a_direct_vrel,
  _bosch_a_main_base,
  _bosch_a_range_ratio,
  _bosch_a_range_ratio_vrel,
)
from opendbc.car.honda.values import CAR
from openpilot.common.params import Params

# Tester toggle: CP is computed once at import time below (many helpers in this module close over
# it), which runs before any pytest fixture could -- so this has to be plain top-level code, not a
# fixture. teardown_module() restores it once every test in this file has run (mirrors
# gm/tests/test_gm.py's put_bool/finally pattern for params-gated _get_params behavior).
Params().put_bool("HondaBoschARadar", True)


def teardown_module(module):
  Params().remove("HondaBoschARadar")


CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC_BOSCH)
BUS = CanBus(CP).camera


# --- synthetic frame builders (inverse of the spec's raw-byte formulas) -----------------------------

def make_f0(frame_idx=0, status=0x7, range_raw=0, angle_raw=0, range_sigma_raw=1):
  # inverse of raw_angle = (B4 << 3) | (B5 >> 5): B4 carries the top 8 bits, B5's top 3 bits carry the
  # bottom 3 bits of the 11-bit angle (the decoder ignores B5's low 5 bits entirely).
  B0 = (range_sigma_raw & 0x7F) << 1
  B3 = (frame_idx & 0xF) | ((range_raw & 0xF) << 4)
  B2 = (range_raw >> 4) & 0xFF
  B1 = (status & 0xF) << 4
  B5 = (angle_raw & 0x7) << 5
  B4 = (angle_raw >> 3) & 0xFF
  return bytes([B0, B1, B2, B3, B4, B5, 0, 0])


def make_f1(frame_idx=0, existence_raw=126):
  return bytes([0, 0, 0, (frame_idx & 0xF) << 1, 0, existence_raw & 0x7F, 0, 0])


def make_f2(frame_idx=0, life=0):
  B1 = (frame_idx & 0xF) | ((life & 0xF) << 4)
  B0 = (life >> 4) & 0xFF
  return bytes([B0, B1, 0, 0, 0, 0, 0, 0])


def make_f3(frame_idx=0, edge_a_raw=0, edge_b_raw=0, sigma_a_raw=0, track_id=0xFF):
  B0 = (edge_a_raw >> 3) & 0xFF
  B1 = ((edge_a_raw & 0x7) << 5) | ((frame_idx & 0xF) << 1)
  B2 = (edge_b_raw >> 3) & 0xFF
  B3 = (edge_b_raw & 0x7) << 5
  B4 = (sigma_a_raw >> 2) & 0xFF
  B5 = (sigma_a_raw & 0x3) << 6
  return bytes([B0, B1, B2, B3, B4, B5, track_id & 0xFF, 0])


def make_aux(frame_idx=0, rawc9=0, rawca=0, direct_vrel_raw=BOSCH_A_DIRECT_VREL_INVALID,
             direct_vrel_uncertainty_raw=0x3FF):
  B0 = (direct_vrel_raw >> 3) & 0xFF
  B1 = ((direct_vrel_raw & 0x7) << 5) | ((frame_idx & 0xF) << 1)
  B2 = (direct_vrel_uncertainty_raw >> 2) & 0xFF
  B3 = (direct_vrel_uncertainty_raw & 0x3) << 6
  B5 = (rawc9 & 0x3) << 6
  B4 = (rawc9 >> 2) & 0xFF
  B7 = (rawca & 0x3) << 6
  B6 = (rawca >> 2) & 0xFF
  return bytes([B0, B1, B2, B3, B4, B5, B6, B7])


def make_main_frames(slot, frame_idx, status, range_raw, angle_raw, life, track_id=1,
                     range_sigma_raw=1, existence_raw=126):
  f0, f1, f2, f3 = BOSCH_A_MAIN_IDS[slot]
  return [
    CanData(f0, make_f0(frame_idx, status, range_raw, angle_raw, range_sigma_raw), BUS),
    CanData(f1, make_f1(frame_idx, existence_raw), BUS),
    CanData(f2, make_f2(frame_idx, life), BUS),
    CanData(f3, make_f3(frame_idx, track_id=track_id), BUS),
  ]


def make_radar_interface():
  return CarInterface.RadarInterface(CP)


def sweep(slot, frame_idx, status, range_raw, angle_raw, life, t_nanos, with_aux=False, aux_frame_idx=None,
          rawc9=0, rawca=BOSCH_A_RANGE_RATIO_INVALID, extra_slots=(), track_id=1, direct_vrel_raw=BOSCH_A_DIRECT_VREL_INVALID,
          direct_vrel_uncertainty_raw=0x3FF, range_sigma_raw=1, existence_raw=126):
  """Build one update() input: a full main-frame set for `slot` (+ optional aux), plus the trigger
  frame (slot 15's f3) so update() always processes the cycle unless the caller is testing slot 15
  itself or an incomplete-frame scenario via extra_slots."""
  f0, f1, f2, f3 = BOSCH_A_MAIN_IDS[slot]
  aux = BOSCH_A_AUX_IDS[slot]
  frames = make_main_frames(
    slot, frame_idx, status, range_raw, angle_raw, life, track_id,
    range_sigma_raw=range_sigma_raw, existence_raw=existence_raw,
  )
  if with_aux:
    frames.append(CanData(aux, make_aux(aux_frame_idx if aux_frame_idx is not None else frame_idx, rawc9, rawca,
                                        direct_vrel_raw, direct_vrel_uncertainty_raw), BUS))
  if slot != BOSCH_A_NUM_SLOTS - 1:
    _, _, _, trig_f3 = BOSCH_A_MAIN_IDS[BOSCH_A_NUM_SLOTS - 1]
    frames.append(CanData(trig_f3, make_f3(frame_idx), BUS))
  for extra in extra_slots:
    frames.append(extra)
  return [(t_nanos, frames)]


# --- 1. all 16 slot/frame ID mappings ---------------------------------------------------------------

def test_all_16_slot_main_ids():
  for slot in range(16):
    base = 0x280 + 4 * slot if slot < 4 else 0x2D0 + 4 * (slot - 4)
    assert _bosch_a_main_base(slot) == base
    assert BOSCH_A_MAIN_IDS[slot] == [base, base + 1, base + 2, base + 3]


def test_all_16_slot_aux_ids():
  expected = {
    0: 0x2C8, 1: 0x2C9, 2: 0x2CA, 3: 0x2CB, 4: 0x2CC, 5: 0x2CD, 6: 0x2CE, 7: 0x2CF,
    8: 0x290, 9: 0x291, 10: 0x292, 11: 0x293, 12: 0x294, 13: 0x295, 14: 0x296, 15: 0x297,
  }
  for slot, addr in expected.items():
    assert _bosch_a_aux_id(slot) == addr
    assert BOSCH_A_AUX_IDS[slot] == addr


def test_no_duplicate_can_ids_across_80_messages():
  all_ids = [addr for ids in BOSCH_A_MAIN_IDS for addr in ids] + BOSCH_A_AUX_IDS
  assert len(all_ids) == 80
  assert len(set(all_ids)) == 80


# --- 2. DBC bit geometry matches the spec's raw-byte formulas exactly (section 16) -------------------

class TestDbcBitGeometry:
  dbc = DbcFile(BOSCH_A_DBC_NAME)

  def test_f0_fields(self):
    msg = self.dbc.msgs[0x280]
    rng = random.Random(0)
    for _ in range(500):
      b = [rng.randint(0, 255) for _ in range(8)]
      dat = bytes(b)
      assert get_raw_value(dat, msg.sigs['STATUS']) == (b[1] >> 4) & 0x0F
      assert get_raw_value(dat, msg.sigs['FRAME_IDX']) == b[3] & 0x0F
      assert get_raw_value(dat, msg.sigs['RANGE_RAW']) == (b[2] << 4) | (b[3] >> 4)
      assert get_raw_value(dat, msg.sigs['AZIMUTH_RAW']) == (b[4] << 3) | (b[5] >> 5)

  def test_f1_frame_idx(self):
    msg = self.dbc.msgs[0x281]
    rng = random.Random(1)
    for _ in range(500):
      b = [rng.randint(0, 255) for _ in range(8)]
      assert get_raw_value(bytes(b), msg.sigs['FRAME_IDX']) == (b[3] >> 1) & 0x0F

  def test_f2_fields(self):
    msg = self.dbc.msgs[0x282]
    rng = random.Random(2)
    for _ in range(500):
      b = [rng.randint(0, 255) for _ in range(8)]
      dat = bytes(b)
      assert get_raw_value(dat, msg.sigs['FRAME_IDX']) == b[1] & 0x0F
      assert get_raw_value(dat, msg.sigs['LIFECYCLE_RAW']) == (b[0] << 4) | (b[1] >> 4)

  def test_f3_fields(self):
    msg = self.dbc.msgs[0x283]
    rng = random.Random(3)
    for _ in range(500):
      b = [rng.randint(0, 255) for _ in range(8)]
      dat = bytes(b)
      assert get_raw_value(dat, msg.sigs['AZIMUTH_EDGE_A_RAW']) == (b[0] << 3) | (b[1] >> 5)
      assert get_raw_value(dat, msg.sigs['FRAME_IDX']) == (b[1] >> 1) & 0x0F
      assert get_raw_value(dat, msg.sigs['AZIMUTH_EDGE_B_RAW']) == (b[2] << 3) | (b[3] >> 5)
      assert get_raw_value(dat, msg.sigs['AZIMUTH_EDGE_SIGMA_A_RAW']) == (b[4] << 2) | (b[5] >> 6)

  def test_track_id_is_f3_byte6_and_does_not_overlap_existing_fields(self):
    def affected_bits(signal):
      bits = set()
      for byte in range(8):
        for bit in range(8):
          data = bytearray(8)
          data[byte] = 1 << bit
          if get_raw_value(bytes(data), signal) != 0:
            bits.add((byte, bit))
      return bits

    expected_bits = {(6, bit) for bit in range(8)}
    f3_ids = [BOSCH_A_MAIN_IDS[slot][3] for slot in range(BOSCH_A_NUM_SLOTS)]
    for message_id in f3_ids:
      msg = self.dbc.msgs[message_id]
      track_id = msg.sigs['TRACK_ID']
      assert track_id.start_bit == 55
      assert track_id.size == 8
      assert track_id.is_little_endian is False
      assert affected_bits(track_id) == expected_bits

      existing_bits = set()
      for name, signal in msg.sigs.items():
        if name != 'TRACK_ID':
          existing_bits |= affected_bits(signal)
      assert not existing_bits & expected_bits

    rng = random.Random(33)
    msg = self.dbc.msgs[BOSCH_A_MAIN_IDS[0][3]]
    for _ in range(500):
      data = bytes(rng.randint(0, 255) for _ in range(8))
      assert get_raw_value(data, msg.sigs['TRACK_ID']) == data[6]

  def test_aux_fields(self):
    msg = self.dbc.msgs[0x2C8]
    rng = random.Random(4)
    for _ in range(500):
      b = [rng.randint(0, 255) for _ in range(8)]
      dat = bytes(b)
      assert get_raw_value(dat, msg.sigs['FRAME_IDX']) == (b[1] >> 1) & 0x0F
      assert get_raw_value(dat, msg.sigs['REL_VELOCITY_RAW']) == (b[0] << 3) | (b[1] >> 5)
      assert get_raw_value(dat, msg.sigs['REL_VELOCITY_UNCERTAINTY_RAW']) == (b[2] << 2) | (b[3] >> 6)
      assert get_raw_value(dat, msg.sigs['FW_LID_00C9_RAW']) == (b[4] << 2) | (b[5] >> 6)
      assert get_raw_value(dat, msg.sigs['FW_LID_00CA_RAW']) == (b[6] << 2) | (b[7] >> 6)
      assert get_raw_value(dat, msg.sigs['AZIMUTH_EDGE_SIGMA_B_RAW']) == (b[4] << 2) | (b[5] >> 6)
      assert get_raw_value(dat, msg.sigs['RANGE_RATIO_RAW']) == (b[6] << 2) | (b[7] >> 6)

  def test_semantic_quality_aliases_exist_on_every_slot(self):
    for slot in range(BOSCH_A_NUM_SLOTS):
      f0, f1, f2, _ = BOSCH_A_MAIN_IDS[slot]
      aux = BOSCH_A_AUX_IDS[slot]
      assert self.dbc.msgs[f0].sigs['RANGE_SIGMA_RAW'].size == 7
      assert self.dbc.msgs[f1].sigs['OBJECT_EXISTENCE_PROBABILITY_RAW'].size == 7
      assert self.dbc.msgs[f1].sigs['ANGULAR_WIDTH_RAW'].size == 11
      assert self.dbc.msgs[f2].sigs['NORMALIZED_CLOSING_RAW'].size == 10
      assert self.dbc.msgs[f2].sigs['NORMALIZED_CLOSING_SIGMA_RAW'].size == 7
      assert self.dbc.msgs[aux].sigs['AZIMUTH_EDGE_SIGMA_B_RAW'].size == 10
      assert self.dbc.msgs[aux].sigs['RANGE_RATIO_RAW'].size == 10

  def test_descriptor_backed_raw_fields_cover_all_unmapped_main_bits(self):
    f0_ids = [
      ['25', '26', '28', '29'], ['34', '35', '37', '38'], ['43', '44', '46', '47'],
      ['52', '53', '55', '56'], ['61', '62', '64', '65'], ['70', '71', '73', '74'],
      ['7F', '80', '82', '83'], ['8E', '8F', '91', '92'], ['9D', '9E', 'A0', 'A1'],
      ['AC', 'AD', 'AF', 'B0'], ['BB', 'BC', 'BE', 'BF'], ['CA', 'CB', 'CD', 'CE'],
      ['D9', 'DA', 'DC', 'DD'], ['E8', 'E9', 'EB', 'EC'], ['F7', 'F8', 'FA', 'FB'],
      ['06', '07', '09', '0A'],
    ]
    f1_ids = [
      ['2B', '18', '2C', '19', '2D'], ['3A', '23', '3B', '24', '3C'], ['49', '2E', '4A', '2F', '4B'],
      ['58', '39', '59', '3A', '5A'], ['67', '44', '68', '45', '69'], ['76', '4F', '77', '50', '78'],
      ['85', '5A', '86', '5B', '87'], ['94', '65', '95', '66', '96'], ['A3', '70', 'A4', '71', 'A5'],
      ['B2', '7B', 'B3', '7C', 'B4'], ['C1', '86', 'C2', '87', 'C3'], ['D0', '91', 'D1', '92', 'D2'],
      ['DF', '9C', 'E0', '9D', 'E1'], ['EE', 'A7', 'EF', 'A8', 'F0'], ['FD', 'B2', 'FE', 'B3', 'FF'],
      ['0C', 'BD', '0D', 'BE', '0E'],
    ]
    f2_ids = [
      ['2F', '1A', '30', '1B', '1C'], ['3E', '25', '3F', '26', '27'], ['4D', '30', '4E', '31', '32'],
      ['5C', '3B', '5D', '3C', '3D'], ['6B', '46', '6C', '47', '48'], ['7A', '51', '7B', '52', '53'],
      ['89', '5C', '8A', '5D', '5E'], ['98', '67', '99', '68', '69'], ['A7', '72', 'A8', '73', '74'],
      ['B6', '7D', 'B7', '7E', '7F'], ['C5', '88', 'C6', '89', '8A'], ['D4', '93', 'D5', '94', '95'],
      ['E3', '9E', 'E4', '9F', 'A0'], ['F2', 'A9', 'F3', 'AA', 'AB'], ['01', 'B4', '02', 'B5', 'B6'],
      ['10', 'BF', '11', 'C0', 'C1'],
    ]
    positions = {
      'F0': [(44, 4), (11, 2), (7, 7), (55, 8)],
      'F1': [(46, 7), (23, 11), (15, 8), (39, 9), (7, 6)],
      'F2': [(29, 1), (23, 10), (46, 7), (39, 9), (55, 9)],
    }
    ids_by_frame = {'F0': f0_ids, 'F1': f1_ids, 'F2': f2_ids}
    for slot in range(BOSCH_A_NUM_SLOTS):
      for frame in ('F0', 'F1', 'F2'):
        msg = self.dbc.msgs[BOSCH_A_MAIN_IDS[slot][int(frame[-1])]]
        for logical_id, (start_bit, size) in zip(ids_by_frame[frame][slot], positions[frame], strict=True):
          signal = msg.sigs[f'FW_LID_{logical_id}_RAW']
          assert signal.start_bit == start_bit
          assert signal.size == size
          assert signal.is_little_endian is False

        def affected_bits(signal):
          bits = set()
          for byte in range(8):
            for bit in range(8):
              data = bytearray(8)
              data[byte] = 1 << bit
              if get_raw_value(bytes(data), signal) != 0:
                bits.add((byte, bit))
          return bits

        fields = [msg.sigs[f'FW_LID_{logical_id}_RAW'] for logical_id in ids_by_frame[frame][slot]]
        covered = set()
        for signal in fields:
          bits = affected_bits(signal)
          assert not covered & bits
          covered |= bits

        semantic_aliases = {
          'RANGE_SIGMA_RAW', 'OBJECT_EXISTENCE_PROBABILITY_RAW',
          'ANGULAR_WIDTH_RAW', 'ANGULAR_WIDTH_DEG',
          'NORMALIZED_CLOSING_RAW', 'NORMALIZED_CLOSING', 'NORMALIZED_CLOSING_SIGMA_RAW',
        }
        existing_bits = set()
        for name, signal in msg.sigs.items():
          if not name.startswith('FW_LID_') and name not in semantic_aliases:
            existing_bits |= affected_bits(signal)
        assert not existing_bits & covered


# --- 3. range / azimuth extraction + invalid sentinels ------------------------------------------------

class TestRangeAzimuth:
  def test_range_scale_and_offset(self):
    ri = make_radar_interface()
    raw_range = 1000
    ri.update(sweep(0, 0, 0x7, raw_range, 1024, 1, 0))
    rr = ri.update(sweep(0, 1, 0x7, raw_range, 1024, 3, 50_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert rr.points[0].dRel == pytest.approx(0.05712 * raw_range - 3.0)

  def test_range_invalid_sentinel_0xfff(self):
    ri = make_radar_interface()
    rr = ri.update(sweep(0, 0, 0x7, 0xFFF, 1024, 1, 0))
    assert len(rr.points) == 0

  def test_azimuth_invalid_sentinel_0x7ff(self):
    ri = make_radar_interface()
    rr = ri.update(sweep(0, 0, 0x7, 1000, 0x7FF, 1, 0))
    assert len(rr.points) == 0

  def test_yrel_sign_right_of_center_is_negative(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024 - 100, 1, 0))
    rr = ri.update(sweep(0, 1, 0x7, 1000, 1024 - 100, 3, 50_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))  # raw_angle < center -> right of center
    d = 0.05712 * 1000 - 3.0
    expected_y = d * math.tan(-100.0 / 2048.0)
    assert rr.points[0].yRel == pytest.approx(expected_y)
    assert rr.points[0].yRel < 0

  def test_yrel_sign_left_of_center_is_positive(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024 + 100, 1, 0))
    rr = ri.update(sweep(0, 1, 0x7, 1000, 1024 + 100, 3, 50_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))  # raw_angle > center -> left of center
    assert rr.points[0].yRel > 0

  def test_yrel_zero_on_boresight(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
    rr = ri.update(sweep(0, 1, 0x7, 1000, 1024, 3, 50_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert rr.points[0].yRel == pytest.approx(0.0, abs=1e-9)


# --- 4. status / life invalid sentinels -> conservative object_valid ---------------------------------

class TestObjectValid:
  def test_status_invalid_0xf(self):
    ri = make_radar_interface()
    rr = ri.update(sweep(0, 0, 0xF, 1000, 1024, 1, 0))
    assert len(rr.points) == 0

  def test_life_invalid_0xfff(self):
    ri = make_radar_interface()
    rr = ri.update(sweep(0, 0, 0x7, 1000, 1024, 0xFFF, 0))
    assert len(rr.points) == 0

  def test_first_valid_sample_is_withheld(self):
    ri = make_radar_interface()
    rr = ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
    assert len(rr.points) == 0

  def test_invalid_observation_does_not_mature_or_preserve_birth_history(self):
    ri = make_radar_interface()
    rr = ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
    assert len(rr.points) == 0
    rr = ri.update(sweep(0, 1, 0xF, 1000, 1024, 3, 50_000_000))
    assert len(rr.points) == 0
    rr = ri.update(sweep(0, 2, 0x7, 1000, 1024, 1, 100_000_000))
    assert len(rr.points) == 0

  def test_incomplete_observation_does_not_mature_or_add_history(self):
    ri = make_radar_interface()
    rr = ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
    assert len(rr.points) == 0

    f0, f1, f2, f3 = BOSCH_A_MAIN_IDS[0]
    _, _, _, trig_f3 = BOSCH_A_MAIN_IDS[15]
    frames = [
      CanData(f0, make_f0(1, 0x7, 1010, 1024), BUS),
      CanData(f1, make_f1(1), BUS),
      CanData(f2, make_f2(1, 3), BUS),
      CanData(trig_f3, make_f3(1), BUS),
    ]
    rr = ri.update([(50_000_000, frames)])
    assert len(rr.points) == 0

    rr = ri.update(sweep(0, 2, 0x7, 1020, 1024, 5, 100_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert len(rr.points) == 1
    assert math.isfinite(rr.points[0].vRel)

  def test_second_same_incarnation_sample_without_u11_or_ratio_does_not_publish(self):
    # Neither native U11 nor the ratio field is available on either sample (no aux at all). The raw
    # one-sweep range derivative that would previously have matured into a measured=True point is now
    # never published: with no prior trusted velocity to coast, the point is withheld entirely.
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000))
    assert len(rr.points) == 0


# --- 5. lifecycle continuity ---------------------------------------------------------------------------

class TestLifecycle:
  def test_normal_plus_2_continuity_keeps_trackid(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    t0 = rr.points[0].trackId
    rr = ri.update(sweep(0, 2, 0x7, 1020, 1024, 5, 100_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert rr.points[0].trackId == t0

  def test_continuity_across_dropped_sweeps(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    t0 = rr.points[0].trackId
    # 3 sweeps missed: frame_idx jumps from 0 to 4, life must jump by 2*4=8 to stay the same incarnation
    rr = ri.update(sweep(0, 4, 0x7, 1040, 1024, 9, 200_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert rr.points[0].trackId == t0

  def test_frame_idx_wraps_mod_16(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 14, 0x7, 1000, 1024, 1, 0))
    rr = ri.update(sweep(0, 15, 0x7, 1005, 1024, 3, 50_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    t0 = rr.points[0].trackId
    # frame_idx wraps 14 -> 1 (delta = (1-14)&0xF = 3), life must advance by 6
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 7, 150_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert rr.points[0].trackId == t0

  def test_life_wraps_mod_4096_stays_same_incarnation(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 14, 0x7, 1000, 1024, 4094, 0))
    rr = ri.update(sweep(0, 15, 0x7, 1005, 1024, 0, 50_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    t0 = rr.points[0].trackId
    # frame_idx 14 -> 0 (delta=2), life 4094 -> 2 ((2-4094)&0xFFF == 4 == 2*2)
    rr = ri.update(sweep(0, 0, 0x7, 1010, 1024, 2, 100_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert rr.points[0].trackId == t0

  def test_in_place_replacement_no_invalid_gap_resets_history_but_keeps_can_id(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    t0 = rr.points[0].trackId
    # frame_idx advances normally (+1) but life jumps by an unrelated odd amount -> NOT +2*frame_delta
    rr = ri.update(sweep(0, 2, 0x7, 50, 1024, 7, 100_000_000))
    assert len(rr.points) == 0  # replacement birth sample is withheld
    rr = ri.update(sweep(0, 3, 0x7, 50, 1024, 9, 150_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert len(rr.points) == 1
    assert rr.points[0].trackId == t0

  def test_replacement_does_not_assume_life_restarts_at_1_3_5(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    t0 = rr.points[0].trackId
    # a "replacement" that happens to restart life at a big/even value must still be treated as a
    # replacement (not death) because it fails the frame/life identity, regardless of the new value's parity
    rr = ri.update(sweep(0, 2, 0x7, 50, 1024, 4000, 100_000_000))
    assert len(rr.points) == 0  # replacement birth sample is withheld
    rr = ri.update(sweep(0, 3, 0x7, 50, 1024, 4002, 150_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert rr.points[0].trackId == t0
    assert rr.points[0].vRel == 0.0
    assert len(rr.points) == 1

  def test_death_then_rebirth_reuses_can_id_with_clean_history(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    t0 = rr.points[0].trackId
    rr = ri.update(sweep(0, 1, 0xF, 1000, 1024, 3, 50_000_000))  # death
    assert len(rr.points) == 0
    rr = ri.update(sweep(0, 2, 0x7, 1000, 1024, 1, 100_000_000))  # rebirth, first sample withheld
    assert len(rr.points) == 0
    rr = ri.update(sweep(0, 3, 0x7, 1000, 1024, 3, 150_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert len(rr.points) == 1
    assert rr.points[0].trackId == t0


# --- 6. CAN track identity is the RadarPoint identity -----------------------------------------------

def test_trackid_comes_from_can_and_is_not_synthetic():
  ri = make_radar_interface()
  seen_ids = set()
  t = 0
  for i in range(10):
    frame_idx = (2 * i) % 16
    can_track_id = i + 1
    ri.update(sweep(0, frame_idx, 0x7, 1000, 1024, 1, t, track_id=can_track_id))
    t += 50_000_000
    rr = ri.update(sweep(0, (frame_idx + 1) % 16, 0x7, 1000, 1024, 3, t, track_id=can_track_id,
                         with_aux=True, direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    t += 50_000_000
    assert can_track_id in {point.trackId for point in rr.points}
    seen_ids.add(can_track_id)
  assert seen_ids == set(range(1, 11))


# --- 7. vRel derivative sign -------------------------------------------------------------------------

class TestVrel:
  def test_direct_aux_vrel_is_preferred_over_range_derivative(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True,
                    direct_vrel_raw=800, direct_vrel_uncertainty_raw=80))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=True,
                         direct_vrel_raw=800, direct_vrel_uncertainty_raw=80))
    assert rr.points[0].vRel == pytest.approx((800 - 864) / 64.0)

  def test_direct_aux_vrel_domain_and_sentinel(self):
    assert _bosch_a_direct_vrel(0) == pytest.approx(-13.5)
    assert _bosch_a_direct_vrel(BOSCH_A_DIRECT_VREL_MAX_RAW) == pytest.approx(13.5)
    assert _bosch_a_direct_vrel(1729) is None
    assert _bosch_a_direct_vrel(BOSCH_A_DIRECT_VREL_INVALID) is None
    assert _bosch_a_direct_vrel(0x7FF) is None
    assert _bosch_a_direct_vrel(None) is None
    assert _bosch_a_direct_vrel(0, BOSCH_A_DIRECT_VREL_MAX_UNCERTAINTY_RAW) == pytest.approx(-13.5)
    assert _bosch_a_direct_vrel(0, BOSCH_A_DIRECT_VREL_MAX_UNCERTAINTY_RAW + 1) is None
    assert _bosch_a_direct_vrel(864, 0x3FE) is None
    assert _bosch_a_direct_vrel(864, 0x3FF) is None

  def test_high_u10_live_vrel_without_trust_is_withheld(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=False))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=True,
                         direct_vrel_raw=0, direct_vrel_uncertainty_raw=1023))
    assert len(rr.points) == 0
    assert len(ri._tracks[1].samples) == 1

  def test_fast_clean_range_rate_without_u11_or_ratio_withholds_rather_than_synthesizes(self):
    # This range rate (~-46 m/s) is well outside native U11's representable domain ([-13.5, 13.5]
    # m/s), so it can only ever have come from the raw one-sweep derivative -- which is exactly the
    # synthesized-measurement hazard this fix closes. With no aux at all (no U11, no ratio) and no
    # prior trusted velocity to coast, the point is correctly withheld rather than published at a
    # fabricated, out-of-band rate.
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 2000, 1024, 1, 0, with_aux=False))
    ri.update(sweep(0, 1, 0x7, 1945, 1024, 3, 70_000_000, with_aux=False))
    rr = ri.update(sweep(0, 2, 0x7, 1889, 1024, 5, 140_000_000, with_aux=False))
    assert len(rr.points) == 0
    assert len(ri._tracks[1].samples) == 1  # only the birth sample; later cycles coast, not append

  def test_high_u10_live_vrel_coasts_recent_trusted_motion(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1724, 1024, 1, 0, with_aux=True,
                    direct_vrel_raw=696, direct_vrel_uncertainty_raw=84))
    rr = ri.update(sweep(0, 1, 0x7, 1724, 1024, 3, 50_000_000, with_aux=True,
                   direct_vrel_raw=696, direct_vrel_uncertainty_raw=84))
    assert rr.points[0].vRel == pytest.approx(-2.625)
    # R146/S21 ID50's 19-count / 68.962 ms high-U10 step would have synthesized about -15.74 m/s.
    rr = ri.update(sweep(0, 2, 0x7, 1705, 1024, 5, 118_962_000, with_aux=True,
                   direct_vrel_raw=585, direct_vrel_uncertainty_raw=744))
    assert len(rr.points) == 1
    assert rr.points[0].dRel == pytest.approx(1705 * BOSCH_A_RANGE_SCALE_M - 3.0)
    assert rr.points[0].vRel == pytest.approx(-2.625)
    assert not rr.points[0].measured
    assert len(ri._tracks[1].samples) == 2

  def test_qualified_u11_recovers_immediately_after_high_u10_coast(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True,
                    direct_vrel_raw=800, direct_vrel_uncertainty_raw=84))
    ri.update(sweep(0, 1, 0x7, 1000, 1024, 3, 50_000_000, with_aux=True,
              direct_vrel_raw=800, direct_vrel_uncertainty_raw=84))
    ri.update(sweep(0, 2, 0x7, 981, 1024, 5, 100_000_000, with_aux=True,
              direct_vrel_raw=585, direct_vrel_uncertainty_raw=744))
    rr = ri.update(sweep(0, 3, 0x7, 980, 1024, 7, 150_000_000, with_aux=True,
                   direct_vrel_raw=760, direct_vrel_uncertainty_raw=84))
    assert rr.points[0].vRel == pytest.approx((760 - 864) / 64.0)
    assert rr.points[0].measured
    assert ri._tracks[1].last_trusted_vrel == pytest.approx((760 - 864) / 64.0)

  def test_high_u10_coast_cannot_cross_lifecycle_incarnation(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True,
                    direct_vrel_raw=800, direct_vrel_uncertainty_raw=84))
    ri.update(sweep(0, 1, 0x7, 1000, 1024, 3, 50_000_000, with_aux=True,
              direct_vrel_raw=800, direct_vrel_uncertainty_raw=84))
    rr = ri.update(sweep(0, 2, 0x7, 981, 1024, 99, 100_000_000, with_aux=True,
                   direct_vrel_raw=585, direct_vrel_uncertainty_raw=744))
    assert len(rr.points) == 0
    assert ri._tracks[1].last_trusted_vrel is None

  def test_high_u10_coast_expires_with_trusted_motion_age(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True,
                    direct_vrel_raw=800, direct_vrel_uncertainty_raw=84))
    ri.update(sweep(0, 1, 0x7, 1000, 1024, 3, 50_000_000, with_aux=True,
              direct_vrel_raw=800, direct_vrel_uncertainty_raw=84))
    ri.update(sweep(0, 2, 0x7, 981, 1024, 5, 100_000_000, with_aux=True,
              direct_vrel_raw=585, direct_vrel_uncertainty_raw=744))
    rr = ri.update(sweep(0, 3, 0x7, 980, 1024, 7, 300_000_000, with_aux=True,
                   direct_vrel_raw=585, direct_vrel_uncertainty_raw=744))
    assert len(rr.points) == 0

  def test_range_ratio_conversion_and_sentinel(self):
    assert _bosch_a_range_ratio(500) == pytest.approx(1.0)
    assert _bosch_a_range_ratio(509) == pytest.approx(1.009)
    assert _bosch_a_range_ratio(BOSCH_A_RANGE_RATIO_INVALID) is None
    assert _bosch_a_range_ratio(None) is None
    assert _bosch_a_range_ratio_vrel(600, 10.0, 0.1) == pytest.approx(-10.0)

  @pytest.mark.parametrize(
    ('direct_raw', 'range_raw', 'rawca', 'expected'),
    [(0, 974, 528, -13.5), (BOSCH_A_DIRECT_VREL_MAX_RAW, 1027, 472, 13.5)],
  )
  def test_range_ratio_does_not_extend_direct_vrel_rails(self, direct_raw, range_raw, rawca, expected):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True,
                    direct_vrel_raw=direct_raw, direct_vrel_uncertainty_raw=80, rawca=500))
    rr = ri.update(sweep(0, 1, 0x7, range_raw, 1024, 3, 50_000_000, with_aux=True,
                         direct_vrel_raw=direct_raw, direct_vrel_uncertainty_raw=80, rawca=rawca))
    assert len(rr.points) == 1
    assert rr.points[0].vRel == pytest.approx(expected)

  def test_first_sighting_vrel_is_zero(self):
    ri = make_radar_interface()
    rr = ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
    assert len(rr.points) == 0

  def test_decreasing_range_gives_negative_vrel(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 2000, 1024, 1, 0))
    rr = ri.update(sweep(0, 1, 0x7, 1990, 1024, 3, 50_000_000, with_aux=True,
                        direct_vrel_raw=800, direct_vrel_uncertainty_raw=0))
    assert rr.points[0].vRel < 0

  def test_increasing_range_gives_positive_vrel(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=True,
                        direct_vrel_raw=928, direct_vrel_uncertainty_raw=0))
    assert rr.points[0].vRel > 0

  def test_vrel_reflects_native_u11_not_raw_range_derivative(self):
    # The raw one-sweep (dRel-previous_range)/dt derivative is no longer an authoritative vRel source
    # (see TestFallbackNeverPublishes below) -- confirm the published value tracks native U11 exactly,
    # not the range-implied rate, even when the two would clearly disagree.
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True,
                    direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=True,
                         direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    d1 = 0.05712 * 1000 - 3.0
    d2 = 0.05712 * 1010 - 3.0
    range_implied_vrel = (d2 - d1) / 0.05
    assert range_implied_vrel != pytest.approx(0.0)
    assert rr.points[0].vRel == pytest.approx(0.0)  # native U11 (864 -> 0 m/s), not the range rate

  def test_incarnation_does_not_carry_velocity_across_lifecycle_break(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 2000, 1024, 1, 0))
    rr = ri.update(sweep(0, 1, 0x7, 1990, 1024, 3, 50_000_000, with_aux=True,
                        direct_vrel_raw=800, direct_vrel_uncertainty_raw=0))
    assert rr.points[0].vRel < 0
    # replacement: life breaks identity -> fresh incarnation; its first sample is withheld.
    rr = ri.update(sweep(0, 2, 0x7, 500, 1024, 99, 100_000_000))
    assert len(rr.points) == 0
    rr = ri.update(sweep(0, 3, 0x7, 500, 1024, 101, 150_000_000, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert rr.points[0].vRel == 0.0

  def test_discontinuous_range_coasts_last_accepted_point_unmeasured(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True,
                    direct_vrel_raw=864, direct_vrel_uncertainty_raw=80, rawca=500))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=True,
                         direct_vrel_raw=864, direct_vrel_uncertainty_raw=80, rawca=500))
    assert len(rr.points) == 1
    accepted_drel = rr.points[0].dRel

    rr = ri.update(sweep(0, 2, 0x7, 100, 1024, 5, 100_000_000, with_aux=True,
                         direct_vrel_raw=864, direct_vrel_uncertainty_raw=80, rawca=509,
                         range_sigma_raw=4, existence_raw=0))
    assert len(rr.points) == 1
    assert rr.points[0].dRel == pytest.approx(accepted_drel)
    assert rr.points[0].measured is False
    assert len(ri._tracks[1].samples) == 2

  def test_exact_peter_reset_sequence_never_rebases_on_rejected_ranges(self):
    ri = make_radar_interface()
    rows = [
      # range_raw, U11, U10, range sigma, existence, 00CA
      (203, 713, 136, 2, 3, 512),
      (198, 740, 92, 2, 76, 510),
      (64, 463, 612, 4, 0, 509),
      (82, 554, 437, 4, 0, 508),
      (96, 727, 101, 2, 0, 508),
      (102, 795, 31, 1, 0, 508),
    ]
    times = [0, 70_696_000, 120_413_000, 200_552_000, 260_482_000, 331_286_000]

    rr = None
    for i, ((range_raw, u11, u10, sigma, existence, rawca), t_nanos) in enumerate(zip(rows, times, strict=True)):
      rr = ri.update(sweep(
        0, (11 + i) & 0xF, 0x9, range_raw, 1024, 5 + 2 * i, t_nanos,
        with_aux=True, direct_vrel_raw=u11, direct_vrel_uncertainty_raw=u10,
        rawca=rawca, range_sigma_raw=sigma, existence_raw=existence, track_id=23,
      ))

    assert rr is not None
    assert len(rr.points) == 0
    assert len(ri._tracks[23].samples) == 2
    assert ri._tracks[23].samples[-1][1] == pytest.approx(8.30976)


# --- 7b. residual vRel-authority fix: raw one-sweep fallback never becomes a published measurement ----
# (U11 genuinely unavailable -- sentinel/out-of-range -- is a different path than the high-u10-but-live
# case above; see radar_interface.py's u11_and_ratio_unavailable branch.)

class TestFallbackNeverPublishes:
  def test_invalid_u11_and_ratio_with_trusted_history_coasts_not_derivative(self):
    """TEST 1: invalid U11 + unusable ratio + a recent trusted velocity on record. A large range jump
    that would imply a big closing velocity via the raw derivative must not reach vRel/measured/KF --
    it should coast the trusted value instead."""
    ri = make_radar_interface()
    # Establish trust: two qualified-U11 samples at a steady range.
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True,
                    direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    rr = ri.update(sweep(0, 1, 0x7, 1000, 1024, 3, 50_000_000, with_aux=True,
                         direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert rr.points[0].measured is True
    assert rr.points[0].vRel == pytest.approx(0.0)

    # Third sweep: U11 sentinel (unavailable), ratio invalid, and a range jump that -- via the raw
    # (dRel-previous_range)/dt derivative -- would imply a closing velocity of about -17 m/s over 50ms.
    # Deliberately kept under the 50 m/s generic range-rejection ceiling so this exercises the new
    # u11_and_ratio_unavailable coast path specifically, not the pre-existing range_rejected path.
    rr = ri.update(sweep(0, 2, 0x7, 985, 1024, 5, 100_000_000, with_aux=True,
                         direct_vrel_raw=BOSCH_A_DIRECT_VREL_INVALID, direct_vrel_uncertainty_raw=0,
                         rawca=BOSCH_A_RANGE_RATIO_INVALID))
    implied_fallback_vrel = (985 - 1000) * BOSCH_A_RANGE_SCALE_M / 0.05
    assert implied_fallback_vrel == pytest.approx(-17.136)  # confirms the setup would poison, if reached
    assert abs(implied_fallback_vrel) < BOSCH_A_FALLBACK_RANGE_RATE_MAX_MPS  # and clears range_rejected
    assert len(rr.points) == 1
    assert rr.points[0].measured is False
    assert rr.points[0].vRel == pytest.approx(0.0)  # coasted trusted value, not the -17 m/s derivative
    # The KF-facing measurement update never happened: last_trusted_vrel/age is untouched by this cycle.
    assert ri._tracks[1].last_trusted_vrel == pytest.approx(0.0)
    assert ri._tracks[1].last_trusted_vrel_nanos == 50_000_000

  def test_invalid_u11_and_ratio_without_trusted_history_withholds_point(self):
    """TEST 2: invalid U11 + unusable ratio + no prior trusted velocity. No fabricated point."""
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True,
                    direct_vrel_raw=BOSCH_A_DIRECT_VREL_INVALID, direct_vrel_uncertainty_raw=0))
    rr = ri.update(sweep(0, 1, 0x7, 985, 1024, 3, 50_000_000, with_aux=True,
                         direct_vrel_raw=BOSCH_A_DIRECT_VREL_INVALID, direct_vrel_uncertainty_raw=0,
                         rawca=BOSCH_A_RANGE_RATIO_INVALID))
    assert len(rr.points) == 0

  def test_invalid_u11_with_valid_ratio_still_publishes_via_ratio(self):
    """TEST 3: invalid U11 + a valid ratio field. Untouched by this fix -- still publishes via
    ratio_vrel, exactly as before. rawca=520 is chosen so the ratio-implied residual (~1.08m) clears
    innovation checking, so this exercises the ratio_vrel publish path and not range_rejected."""
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True,
                    direct_vrel_raw=BOSCH_A_DIRECT_VREL_INVALID, direct_vrel_uncertainty_raw=0,
                    rawca=500))
    rr = ri.update(sweep(0, 1, 0x7, 1000, 1024, 3, 50_000_000, with_aux=True,
                         direct_vrel_raw=BOSCH_A_DIRECT_VREL_INVALID, direct_vrel_uncertainty_raw=0,
                         rawca=520))
    d = 0.05712 * 1000 - 3.0
    ratio = 0.5 + 0.001 * 520
    residual = abs(d - d * ratio)
    assert residual < 2.0  # clears innovation checking regardless of degraded status
    assert len(rr.points) == 1
    assert rr.points[0].measured is True
    expected = d * (1.0 - ratio) / 0.05
    assert rr.points[0].vRel == pytest.approx(expected)


# --- 8. auxiliary tag join: enrichment only, never gates validity -------------------------------------

class TestAuxiliary:
  def test_aux_matching_cycle_is_attached(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True, aux_frame_idx=0, rawc9=123, rawca=456))
    st = ri._slots[0]
    assert st.logical_00c9_raw == 123
    assert st.logical_00ca_raw == 456

  def test_aux_mismatched_cycle_not_attached_and_point_withheld_without_vrel_source(self):
    # A mismatched aux frame_idx means the AUX payload (U11, ratio, and the c9/ca enrichment fields)
    # is never attached for that cycle -- it's as if aux were absent. With no vRel source and no prior
    # trusted velocity, the point is correctly withheld rather than synthesized from the range alone.
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True, aux_frame_idx=5, rawc9=123, rawca=456))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=True, aux_frame_idx=5, rawc9=123, rawca=456))
    assert len(rr.points) == 0
    st = ri._slots[0]
    assert math.isnan(st.logical_00c9_raw) and math.isnan(st.logical_00ca_raw)  # never attached

  def test_aux_absent_without_trust_withholds_point(self):
    # Aux absence alone no longer implies "fall back to the raw range derivative" -- with no U11, no
    # ratio, and no prior trusted velocity to coast, the point is withheld rather than fabricated.
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=False))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=False))
    assert len(rr.points) == 0

  def test_aux_absent_does_not_suppress_point_once_trust_is_established(self):
    # A subsequent aux-absent sweep does NOT suppress a point once a recent trusted velocity exists --
    # it coasts that trusted value (measured=False) rather than withholding the point outright.
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True,
                    direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    ri.update(sweep(0, 1, 0x7, 1000, 1024, 3, 50_000_000, with_aux=True,
              direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    rr = ri.update(sweep(0, 2, 0x7, 1000, 1024, 5, 100_000_000, with_aux=False))
    assert len(rr.points) == 1
    assert rr.points[0].vRel == pytest.approx(0.0)
    assert rr.points[0].measured is False

  def test_aux_param_invalid_sentinel(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True, aux_frame_idx=0, rawc9=1, rawca=0x3FF))
    st = ri._slots[0]
    assert st.logical_00c9_raw == 1
    assert math.isnan(st.logical_00ca_raw)

  def test_sigma_does_not_share_aux_param_invalid_sentinel(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, with_aux=True,
                    aux_frame_idx=0, rawc9=0x3FF, rawca=500))
    st = ri._slots[0]
    assert st.logical_00c9_raw == 0x3FF
    assert st.logical_00ca_raw == 500


# --- 9. missing CAN frame within a cycle does not kill an existing point -------------------------------

def test_incomplete_main_frame_set_leaves_existing_point_untouched():
  ri = make_radar_interface()
  ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
  rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=True,
                       direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
  assert len(rr.points) == 1
  t0 = rr.points[0].trackId

  # Next cycle: only f0/f1/f2 arrive for slot 0 (f3 missing) -- still send the trigger so update() runs.
  f0, f1, f2, f3 = BOSCH_A_MAIN_IDS[0]
  _, _, _, trig_f3 = BOSCH_A_MAIN_IDS[15]
  frames = [
    CanData(f0, make_f0(1, 0x7, 1000, 1024), BUS),
    CanData(f1, make_f1(1), BUS),
    CanData(f2, make_f2(1, 3), BUS),
    CanData(trig_f3, make_f3(1), BUS),
  ]
  rr = ri.update([(50_000_000, frames)])
  assert len(rr.points) == 1  # untouched, not dropped
  assert rr.points[0].trackId == t0


def test_incoherent_frame_index_across_main_frames_is_skipped():
  ri = make_radar_interface()
  ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
  rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=True,
                       direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
  t0 = rr.points[0].trackId

  f0, f1, f2, f3 = BOSCH_A_MAIN_IDS[0]
  _, _, _, trig_f3 = BOSCH_A_MAIN_IDS[15]
  frames = [
    CanData(f0, make_f0(1, 0x7, 1000, 1024), BUS),
    CanData(f1, make_f1(1), BUS),
    CanData(f2, make_f2(2, 3), BUS),  # frame idx mismatch vs f0/f1
    CanData(f3, make_f3(1), BUS),
    CanData(trig_f3, make_f3(1), BUS),
  ]
  rr = ri.update([(50_000_000, frames)])
  assert len(rr.points) == 1  # unchanged from before, not re-derived, not dropped
  assert rr.points[0].trackId == t0


# --- 10. staleness gate -----------------------------------------------------------------------------

def test_stale_bus_clears_points_and_flags_temporary_unavailable():
  ri = make_radar_interface()
  ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
  rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, with_aux=True,
                       direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
  assert len(rr.points) == 1

  # Advance the parser clock well past BOSCH_A_STALE_S with no trigger frame at all.
  f0, f1, f2, f3 = BOSCH_A_MAIN_IDS[0]
  frames = [CanData(f0, make_f0(1, 0x7, 1000, 1024), BUS)]  # not a full/coherent set, and no trigger
  rr = ri.update([(300_000_000, frames)])  # +300ms, no trigger msg present
  assert rr is not None
  assert len(rr.points) == 0
  assert rr.errors.radarUnavailableTemporary is True


def test_stale_bus_clears_pending_birth_history_before_maturity():
  ri = make_radar_interface()
  rr = ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0))
  assert len(rr.points) == 0
  assert len(ri._tracks[1].samples) == 1

  # The birth has started, but no RadarPoint exists yet. A silent bus must still clear the pending
  # lifecycle/history state rather than allowing it to survive indefinitely.
  f0, _, _, _ = BOSCH_A_MAIN_IDS[0]
  rr = ri.update([(300_000_000, [CanData(f0, make_f0(1, 0x7, 1000, 1024), BUS)])])
  assert rr is not None
  assert len(rr.points) == 0
  assert rr.errors.radarUnavailableTemporary is True
  assert not ri._tracks


# --- 11. persistent CAN identity is separate from wire-slot assembly -------------------------------

class TestPersistentCanIdentity:
  def test_same_slot_same_can_identity_is_stable(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, track_id=42))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, track_id=42, with_aux=True,
                         direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert len(rr.points) == 1
    assert rr.points[0].trackId == 42
    assert set(ri._tracks) == {42}

  def test_slot_migration_preserves_identity_and_ols_history(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, track_id=23))
    rr = ri.update(sweep(1, 1, 0x7, 1010, 1024, 3, 50_000_000, track_id=23, with_aux=True,
                         direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert len(rr.points) == 1
    assert rr.points[0].trackId == 23
    assert len(ri._tracks[23].samples) == 2
    assert ri._tracks[23].wire_slot == 1

  def test_slot_zero_one_zero_keeps_one_logical_track(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, track_id=17))
    ri.update(sweep(1, 1, 0x7, 1010, 1024, 3, 50_000_000, track_id=17, with_aux=True,
                    direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    rr = ri.update(sweep(0, 2, 0x7, 1020, 1024, 5, 100_000_000, track_id=17, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert len(rr.points) == 1
    assert [point.trackId for point in rr.points] == [17]
    assert len(ri._tracks) == 1
    assert len(ri._tracks[17].samples) == 3
    assert ri._tracks[17].wire_slot == 0

  def test_same_slot_replacement_preserves_returning_identity_history(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, track_id=2))
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000, track_id=2, with_aux=True,
                         direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert [point.trackId for point in rr.points] == [2]
    assert len(ri._tracks[2].samples) == 2

    # Bosch can put a different persistent object in the same wire slot while the slot's lifecycle
    # counter continues. The old logical track is not dead: retain its state until its own staleness
    # deadline so it can resume without a synthetic birth or an OLS reset.
    rr = ri.update(sweep(0, 2, 0x7, 1500, 1024, 5, 100_000_000, track_id=63))
    assert set(ri._tracks) == {2, 63}
    assert len(ri._tracks[2].samples) == 2
    assert len(rr.points) == 0
    assert 2 not in ri.pts

    rr = ri.update(sweep(0, 3, 0x7, 1020, 1024, 7, 150_000_000, track_id=2, with_aux=True,
                         direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert [point.trackId for point in rr.points] == [2]
    assert len(ri._tracks[2].samples) == 3
    assert math.isfinite(rr.points[0].vRel)

  def test_two_wire_slots_with_different_ids_publish_two_points(self):
    ri = make_radar_interface()
    first_extra = make_main_frames(1, 0, 0x7, 1400, 1024, 11, track_id=22)
    ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, extra_slots=first_extra, track_id=11))
    second_extra = make_main_frames(1, 1, 0x7, 1410, 1024, 13, track_id=22) + [
      CanData(BOSCH_A_AUX_IDS[1], make_aux(1, direct_vrel_raw=864, direct_vrel_uncertainty_raw=0), BUS),
    ]
    rr = ri.update(sweep(0, 1, 0x7, 1010, 1024, 3, 50_000_000,
                         extra_slots=second_extra, track_id=11, with_aux=True,
                         direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert {point.trackId for point in rr.points} == {11, 22}
    assert len(rr.points) == 2

  @pytest.mark.parametrize('track_id', [0, 0xFF, 0x40, 0xA5])
  def test_invalid_can_identity_never_creates_logical_track(self, track_id):
    ri = make_radar_interface()
    rr = ri.update(sweep(0, 0, 0x7, 1000, 1024, 1, 0, track_id=track_id))
    assert len(rr.points) == 0
    assert not ri._tracks

  def test_track_id_reuse_after_death_starts_with_clean_history(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 2000, 1024, 1, 0, track_id=9))
    rr = ri.update(sweep(0, 1, 0x7, 1990, 1024, 3, 50_000_000, track_id=9, with_aux=True,
                        direct_vrel_raw=800, direct_vrel_uncertainty_raw=0))
    assert rr.points[0].trackId == 9
    rr = ri.update(sweep(0, 2, 0xF, 1900, 1024, 5, 100_000_000, track_id=9))
    assert len(rr.points) == 0
    rr = ri.update(sweep(0, 3, 0x7, 1000, 1024, 1, 150_000_000, track_id=9))
    assert len(rr.points) == 0
    rr = ri.update(sweep(0, 4, 0x7, 1000, 1024, 3, 200_000_000, track_id=9, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert len(rr.points) == 1
    assert rr.points[0].trackId == 9
    assert rr.points[0].vRel == 0.0

  def test_lifecycle_discontinuity_keeps_can_id_but_clears_derivative(self):
    ri = make_radar_interface()
    ri.update(sweep(0, 0, 0x7, 2000, 1024, 1, 0, track_id=31))
    rr = ri.update(sweep(0, 1, 0x7, 1990, 1024, 3, 50_000_000, track_id=31, with_aux=True,
                        direct_vrel_raw=800, direct_vrel_uncertainty_raw=0))
    assert rr.points[0].vRel < 0
    rr = ri.update(sweep(0, 2, 0x7, 500, 1024, 99, 100_000_000, track_id=31))
    assert len(rr.points) == 0
    rr = ri.update(sweep(0, 3, 0x7, 500, 1024, 101, 150_000_000, track_id=31, with_aux=True,
                        direct_vrel_raw=864, direct_vrel_uncertainty_raw=0))
    assert len(rr.points) == 1
    assert rr.points[0].trackId == 31
    assert rr.points[0].vRel == 0.0


def test_no_can_data_returns_none_without_crash():
  ri = make_radar_interface()
  assert ri.update([]) is None


def test_bosch_a_azimuth_scale_is_exact_firmware_scale():
  assert BOSCH_A_AZIMUTH_SCALE_RAD == pytest.approx(1.0 / 2048.0)


def test_bosch_a_observed_sweep_end_and_publish_trigger_are_distinct():
  # 0x297 is the observed final object-family frame, but 0x2FF intentionally
  # remains the publish trigger while companion data is optional.
  assert BOSCH_A_TRIGGER_MSG == 0x2FF
  assert BOSCH_A_SWEEP_END_MSG == 0x297


def test_bosch_a_timing_contract():
  assert BOSCH_A_FREQ_HZ == 15
  assert BOSCH_A_STALE_S == pytest.approx(0.20)


# --- misc integration: DBC wiring -------------------------------------------------------------------

def test_civic_bosch_radar_dbc_wired_and_available():
  assert CP.radarUnavailable is False
  ri = make_radar_interface()
  assert ri.bosch_a_radar is True
  assert ri.rcp is not None


def test_civic_bosch_object_feed_uses_camera_side_acc_can():
  ri = make_radar_interface()
  can = CanBus(CP)

  assert ri.rcp.bus == can.camera
  assert ri.rcp.bus != can.radar


# Computed once at collection time, like CP above -- the openpilot_function_fixture in the root
# conftest.py gives every test function its own fresh, isolated OpenpilotPrefix(), so a
# get_non_essential_params() call made from *inside* a test body runs in an environment where the
# HondaBoschARadar=True set at module import time (before any fixture exists) was never written.
# Computing these at module scope, in the same environment CP uses, sidesteps that entirely.
_OPEN_BOSCH_A_CARS = [CAR.HONDA_CRV_5G, CAR.HONDA_CRV_HYBRID, CAR.HONDA_ACCORD, CAR.HONDA_INSIGHT, CAR.ACURA_RDX_3G]
_OPEN_BOSCH_A_CPS = {car: CarInterface.get_non_essential_params(car) for car in _OPEN_BOSCH_A_CARS}

# radarless and CANFD Bosch platforms respectively -- same HONDA_BOSCH family as Civic Bosch, but
# excluded from HONDA_BOSCH_A, so the gate must stay closed regardless of the tester toggle.
_CLOSED_BOSCH_A_CARS = [CAR.HONDA_CIVIC_2022, CAR.HONDA_ACCORD_11G]
_CLOSED_BOSCH_A_CPS = {car: CarInterface.get_non_essential_params(car) for car in _CLOSED_BOSCH_A_CARS}


@pytest.mark.parametrize("car", _OPEN_BOSCH_A_CARS)
def test_bosch_a_gate_open_to_other_bosch_a_platforms(car):
  cp = _OPEN_BOSCH_A_CPS[car]
  assert cp.radarUnavailable is False
  from opendbc.car.honda.radar_interface import RadarInterface
  ri = RadarInterface(cp)
  assert ri.bosch_a_radar is True
  assert ri.rcp is not None


@pytest.mark.parametrize("car", _CLOSED_BOSCH_A_CARS)
def test_bosch_a_gate_stays_closed_for_non_bosch_a_platforms(car):
  cp = _CLOSED_BOSCH_A_CPS[car]
  assert cp.radarUnavailable is True
