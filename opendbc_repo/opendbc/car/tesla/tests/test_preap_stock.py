import pytest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.values import CAR
from opendbc.car.tesla.preap.aol import qualified
from opendbc.car.tesla.tests.preap_stream import PreAPStream


def params(alpha=False, release=False):
  return CarInterface.get_params(CAR.TESLA_MODEL_S_PREAP, gen_empty_fingerprint(), [], alpha, release, False)


@pytest.mark.parametrize("alpha", (False, True))
@pytest.mark.parametrize("release", (False, True))
def test_stock_factory_and_serialized_profile(alpha, release):
  cp = params(alpha, release)
  assert cp.pcmCruise and cp.radarUnavailable and not cp.openpilotLongitudinalControl
  assert not cp.alphaLongitudinalAvailable and qualified(cp)
  assert cp.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.teslaPreap
  assert cp.safetyConfigs[0].safetyParam == 0
  with structs.CarParams.from_bytes(cp.to_bytes()) as decoded:
    assert qualified(decoded)


@pytest.mark.parametrize("key", ("NAPPedalEnabled", "NAPRadarEnabled", "NAPRadarBehindNosecone"))
@pytest.mark.parametrize("raw", (b"1", b"invalid", b""))
def test_unsupported_hardware_configuration_never_falls_back_to_stock(key, raw, tmp_path):
  from openpilot.starpilot.car.tesla.preap_preferences import stock_configuration, prepare_stock

  class Saved:
    def get_param_path(self, name):
      return str(tmp_path / name)

  (tmp_path / key).write_bytes(raw)
  cp = params()
  assert not stock_configuration(Saved())
  prepare_stock(cp, False)
  assert cp.dashcamOnly and not qualified(cp)
  assert cp.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.noOutput


def test_wrong_model_35_cannot_be_preap_or_overwrite_byd():
  from openpilot.starpilot.car.tesla.preap_preferences import prepare_stock

  cp = params()
  cp.safetyConfigs[0].safetyModel = 35
  assert not qualified(cp)
  prepare_stock(cp, True)
  assert cp.dashcamOnly and cp.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.noOutput


@pytest.mark.parametrize("state, field", (({"brake": 2}, "brakePressed"), ({"brake": 0}, "brakePressed"),
  ({"belt": 0}, "seatbeltUnlatched"), ({"doors": 2}, "doorOpen"), ({"doors": 3}, "doorOpen"),
  ({"eps_error": 15}, "steerFaultPermanent"), ({"speed": 0.0}, "standstill")))
def test_actual_parser_reports_physical_or_unknown_restrictions(state, field):
  ci = CarInterface(params())
  stream = PreAPStream()
  ci.update([])
  for tick in range(1, 61):
    cs = ci.update([(1_000_000_000 + tick * 10_000_000, stream.frames(tick, **state))])
  assert cs.canValid and getattr(cs, field)


@pytest.mark.parametrize("brake_at_second_pull", (False, True))
def test_actual_stock_controller_withdraws_pending_set_when_real_brake_arrives(brake_at_second_pull):
  ci = CarInterface(params())
  stream = PreAPStream()
  ci.update([])
  command = structs.CarControl()
  command.latActive = command.longActive = False
  sent = []
  for tick in range(1, 121):
    lever = 2 if tick in (61, 71) else 0
    braking = tick >= (71 if brake_at_second_pull else 75)
    now = 1_000_000_000 + tick * 10_000_000
    ci.update([(now, stream.frames(tick, lever=lever, brake=2 if braking else 1))])
    _, tx = ci.apply(command.as_reader(), now)
    sent.extend((tick, address, data) for address, data, _ in tx)
    if braking:
      assert not any(address == 0x45 and data[0] & 0x3F == 16 for address, data, _ in tx)
  assert any(address == 0x488 for _, address, _ in sent)
  assert any(address == 0x214 for _, address, _ in sent)
  assert not ci.CS.preap_lateral_authorized


def test_full_literal_fingerprint_is_unique_in_production_candidate_inventory():
  from types import SimpleNamespace
  from opendbc.car.fingerprints import all_legacy_fingerprint_cars, eliminate_incompatible_cars
  from opendbc.car.tesla.fingerprints import FINGERPRINTS

  candidates = all_legacy_fingerprint_cars()
  assert len(FINGERPRINTS[CAR.TESLA_MODEL_S_PREAP]) == 1
  for address, length in FINGERPRINTS[CAR.TESLA_MODEL_S_PREAP][0].items():
    candidates = eliminate_incompatible_cars(SimpleNamespace(address=address, dat=bytes(length)), candidates)
  assert candidates == [CAR.TESLA_MODEL_S_PREAP]


def test_controller_attempted_cancel_echo_requires_fresh_native_reconciliation():
  from opendbc.car.tesla.preap.aol import native_observation
  from openpilot.starpilot.aol.intent import AolSettings
  from openpilot.starpilot.aol.wire import SafetyState
  from openpilot.starpilot.car.tesla.stock_intent import TeslaPreapCardIntent

  cp = params()
  cp.alternativeExperience = 32
  ci = CarInterface(cp)
  stream = PreAPStream()
  intent = TeslaPreapCardIntent(cp, AolSettings(False, 0., 0, 0, (0, 0, 0), (0, 0, 0)))
  emitted = None
  for tick in range(1, 80):
    now = 1_000_000_000 + tick * 10_000_000
    cs = ci.update([(now, stream.frames(tick, lever=2 if tick == 40 else 0))])
    intent.update(cs, now_ns=now, fault_active=False)
    _, tx = ci.apply(structs.CarControl().as_reader(), now)
    emitted = next((data for address, data, bus in tx if address == 0x45 and bus == 0), None)
    if emitted is not None and intent.allowed_latch:
      break
  assert emitted is not None and intent.allowed_latch
  assert emitted[0] & 63 == 1
  previous_physical_stamp = ci.CS.preap.physical_stw_stamp_ns
  now += 10_000_000
  frames = [(address, emitted if address == 0x45 else data, bus)
            for address, data, bus in stream.frames(tick + 1)]
  cs = ci.update([(now, frames)])
  assert ci.CS.preap.cancel_echo_stamp_ns == now
  assert ci.CS.preap.physical_stw_stamp_ns == previous_physical_stamp
  assert not any(event.type == structs.CarState.ButtonEvent.Type.cancel and event.pressed for event in cs.buttonEvents)
  denied = SafetyState(1, True, now, now + 30_000_000, 39, 0, False, False, False, False, 'native', 'session')
  _, lost, reset = native_observation(denied, latched=intent.allowed_latch, panda_ready=True,
    restricted=False, now_ns=now, pending_since_ns=0, pending_cancel_ns=now)
  assert not lost and reset
  intent.update(cs, now_ns=now, fault_active=False, native_rejection_ns=now)
  assert not intent.allowed_latch


@pytest.mark.parametrize('latched,observed,allowed,restricted,expected', (
  (True, 100, False, False, True),
  (True, 100, False, True, True),
  (True, 99, False, True, False),
  (True, 100, True, True, False),
  (False, 100, False, False, False),
))
def test_cancel_reconciliation_waits_for_current_native_and_preserves_cold_bootstrap(latched, observed, allowed, restricted, expected):
  from opendbc.car.tesla.preap.aol import native_observation
  from openpilot.starpilot.aol.wire import SafetyState

  native = SafetyState(1, True, observed, 200, 39, 0, allowed, False, allowed, False, 'native', 'session')
  _, lost, reset = native_observation(native, latched=latched, panda_ready=True, restricted=restricted,
    now_ns=100, pending_since_ns=0, pending_cancel_ns=100)
  assert not lost and reset is expected


def test_ordinary_temporary_restriction_without_matched_cancel_retains_arm():
  from opendbc.car.tesla.preap.aol import native_observation
  from openpilot.starpilot.aol.wire import SafetyState

  native = SafetyState(1, True, 100, 200, 39, 0, False, False, False, False, 'native', 'session')
  assert native_observation(native, latched=True, panda_ready=True, restricted=True,
    now_ns=100, pending_since_ns=1, pending_cancel_ns=0) == (0, False, False)
  assert native_observation(None, latched=True, panda_ready=True, restricted=True,
    now_ns=100, pending_since_ns=1, pending_cancel_ns=0) == (0, True, False)
