"""Mixed Palisade radar qualifies through the actual factory/parser/ownership transaction."""

import pytest
from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.radar_interface import RadarInterface, get_radar_can_parser, radar_dbc
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.values import CAR, DBC, HYUNDAI_GV70_RADAR_DBC
from opendbc.car.hyundai.blended_longitudinal import candidate_from_stock, BlendedLongitudinalOwner, Outcome, DISABLE, ENABLE


def params(bank=None, lka=True, bus=0):
  fp = gen_empty_fingerprint()
  if lka:
    fp[2][0x50] = 32
  if bank is not None:
    fp[bus].update(bank)
  return CarInterface.get_params(CAR.HYUNDAI_PALISADE_2023, fp, [], False, False, False)


def test_exact_full_bank_factory_availability_does_not_grant_long_control():
  full = dict.fromkeys(range(0x210, 0x220), 32)
  absent = params()
  stock = params(full)
  assert absent.radarUnavailable and not stock.radarUnavailable
  assert stock.flags == absent.flags
  assert [(r.safetyModel, r.safetyParam) for r in stock.safetyConfigs] == [(r.safetyModel, r.safetyParam) for r in absent.safetyConfigs]
  assert not stock.openpilotLongitudinalControl and not absent.openpilotLongitudinalControl
  assert stock.pcmCruise and absent.pcmCruise
  assert radar_dbc(stock) == HYUNDAI_GV70_RADAR_DBC
  assert Bus.radar not in DBC[CAR.HYUNDAI_PALISADE_2023]  # Static siblings/config untouched.
  for addr in full:
    missing = full.copy()
    missing.pop(addr)
    assert params(missing).radarUnavailable
    short = full.copy()
    short[addr] = 24
    assert params(short).radarUnavailable
  assert params(full, bus=1).radarUnavailable
  assert params(full, lka=False).radarUnavailable


def frames():
  packer = CANPacker(HYUNDAI_GV70_RADAR_DBC)
  result = []
  for ordinal, addr in enumerate(range(0x210, 0x220)):
    values = {}
    for slot in (1, 2):
      count = ordinal * 2 + slot
      values.update({f"{slot}_STATE": 3, f"{slot}_LONG_DIST": count, f"{slot}_LAT_DIST": -0.05 * count, f"{slot}_REL_SPEED": -0.01 * count})
    result.append(packer.make_can_msg(f"RADAR_TRACK_{addr:x}", 0, values))
  return result


def test_actual_parser_full_32_slots_exact_wire_and_fresh_source():
  stock = params(dict.fromkeys(range(0x210, 0x220), 32))
  radar = RadarInterface(stock)
  assert (radar.start_addr, radar.msg_count, radar.rcp.bus) == (0x210, 16, 0)
  packed = frames()
  assert all(len(data) == 32 and bus == 0 for _, data, bus in packed)
  result = radar.update((1_000_000_000, packed))
  assert result is not None and not result.errors.canError
  assert len(result.points) == len({p.trackId for p in result.points}) == 32
  for index, point in enumerate(result.points, 1):
    assert point.dRel == pytest.approx(index, abs=0.051)
    assert point.yRel == pytest.approx(-0.05 * index, abs=0.026)
    assert point.vRel == pytest.approx(-0.01 * index, abs=0.051)
  # One trigger-only frame cannot resurrect any missing older slot after50ms.
  result = radar.update((1_100_000_000, [packed[-1]]))
  assert all(point.dRel >= 31.0 for point in result.points)
  wrong_bus = [(addr, data, 1) for addr, data, _ in packed]
  fresh = RadarInterface(stock)
  assert fresh.update((1_000_000_000, wrong_bus)) is None
  short = [(addr, data[:-1], bus) for addr, data, bus in packed]
  fresh = RadarInterface(stock)
  assert fresh.update((1_000_000_000, short)) is None


def test_current_owner_requires_native_admission_and_ack_before_candidate_publication():
  stock = params(dict.fromkeys(range(0x210, 0x220), 32))
  assert candidate_from_stock(stock, alpha_requested=True, native_qualified=False) is None
  assert candidate_from_stock(stock, alpha_requested=False, native_qualified=True) is None
  candidate = candidate_from_stock(stock, alpha_requested=True, native_qualified=True)
  assert candidate is not None and not candidate.radarUnavailable
  assert candidate.openpilotLongitudinalControl and not candidate.pcmCruise
  calls = []

  def exchange(*args, **kwargs):
    calls.append(kwargs["com_cont_req"])
    return True

  def restore(*args, **kwargs):
    calls.append(ENABLE)
    return True

  owner = BlendedLongitudinalOwner(candidate, CanBus(candidate), exchange, restore_exchange=restore)
  with pytest.raises(RuntimeError):
    owner.begin(None, None, unpublished=False, admission=True)
  assert calls == []
  result = owner.begin(None, None, unpublished=True, admission=True)
  assert result.outcome == Outcome.OWNED and owner.active() and calls == [DISABLE]
  assert owner.restore(None, None)
  assert not owner.active() and calls == [DISABLE, ENABLE]


def test_missing_radar_remains_unavailable_in_admitted_candidate():
  candidate = candidate_from_stock(params(), alpha_requested=True, native_qualified=True)
  assert candidate is not None and candidate.radarUnavailable
  assert get_radar_can_parser(candidate) is not None
