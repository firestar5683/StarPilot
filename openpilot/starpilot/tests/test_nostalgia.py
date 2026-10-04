"""Left-paddle longitudinal pause preserves only separately qualified AOL steering."""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.car import gen_empty_fingerprint
from opendbc.car.hyundai.interface import CarInterface as HyundaiInterface
from opendbc.car.hyundai.ioniq6_handoff import build_ioniq6_hda2_long_candidate
from opendbc.car.hyundai.values import CAR as HyundaiCar
from opendbc.car.structs import car
from openpilot.cereal import log
from openpilot.common.params import Params
from openpilot.selfdrive.selfdrived.events import Events, EventName
from openpilot.selfdrive.selfdrived.state import StateMachine
from openpilot.starpilot.aol.intent import AolCardIntent, AolSettings
from openpilot.starpilot.aol.runtime import decide_axes
from openpilot.starpilot.feature_runtime import enabled as feature_enabled, requested as feature_requested
from openpilot.starpilot.nostalgia import aol_no_entry, paddle_cancel, saved_enabled


ButtonType = car.CarState.ButtonEvent.Type


class Files:
  def __init__(self, root: Path):
    self.root = root

  def get_param_path(self, key: str) -> str:
    return str(self.root / key)


def _car(*events):
  return SimpleNamespace(canValid=True, canTimeout=False, buttonEvents=events,
                         gearShifter=car.CarState.GearShifter.drive,
                         steerFaultPermanent=False, steerFaultTemporary=False,
                         brakePressed=False, vEgo=12.0, standstill=False, accFaulted=False,
                         cruiseState=SimpleNamespace(available=True))


def _button(kind, pressed):
  return car.CarState.ButtonEvent(type=kind, pressed=pressed)


def test_saved_preference_is_strict_and_absent_off():
  with TemporaryDirectory() as directory:
    params = Files(Path(directory))
    path = Path(params.get_param_path('NostalgiaMode'))
    assert not saved_enabled(params)
    for invalid in (b'01', b'true', b'1' * 20):
      path.write_bytes(invalid)
      assert not saved_enabled(params)
      assert path.read_bytes() == invalid
    path.write_bytes(b'1')
    assert saved_enabled(params)


def test_normal_aol_owner_needs_saved_request_and_exact_tagged_ioniq_cp():
  with TemporaryDirectory() as directory:
    params = Params(directory)
    fp = gen_empty_fingerprint()
    fp[2].update({0x50: 16, 0x2A4: 24})
    fp[1].update({0x1CF: 8, 0x1AA: 16, 0x35: 32, 0x175: 24, 0xA0: 24, 0xEA: 24,
                  0x1BA: 24, 0x1E5: 16, 0x36A: 16})
    fp[0][0x3A5] = 24
    stock = HyundaiInterface.get_params(HyundaiCar.HYUNDAI_IONIQ_6, fp, [], False, False, False)
    assert not feature_enabled(params, stock, 'aol', {})
    Path(params.get_param_path('AlwaysOnLateral')).write_bytes(b'1')
    assert feature_requested(params, 'aol')
    assert feature_enabled(params, stock, 'aol', {})
    tagged = build_ioniq6_hda2_long_candidate(stock, fp)
    assert tagged is not None
    assert not feature_enabled(params, tagged, 'aol', {})  # Card has not requested native AOL bit.
    tagged.safetyConfigs[0].safetyParam |= 0x800
    assert feature_enabled(params, tagged, 'aol', {})
    Path(params.get_param_path('AlwaysOnLateral')).write_bytes(b'01')
    assert not feature_requested(params, 'aol')
    assert not feature_enabled(params, tagged, 'aol', {})


def test_only_factual_ioniq_press_cancels_longitudinal():
  press = _car(_button(ButtonType.altButton2, True))
  held = _car()
  release = _car(_button(ButtonType.altButton2, False))
  with patch('openpilot.starpilot.nostalgia.ioniq6_long_eligible', side_effect=lambda cp: cp == 'tagged'):
    assert paddle_cancel('tagged', press, enabled=True, saved=True)
    for car_state in (held, release):
      assert not paddle_cancel('tagged', car_state, enabled=True, saved=True)
    assert not paddle_cancel('stock', press, enabled=True, saved=True)
    assert not paddle_cancel('tagged', press, enabled=False, saved=True)
    assert not paddle_cancel('tagged', press, enabled=True, saved=False)
    press.canTimeout = True
    assert not paddle_cancel('tagged', press, enabled=True, saved=True)


def test_paddle_user_disable_keeps_only_independently_permitted_lateral():
  events = Events()
  events.add(EventName.buttonCancel)
  state = StateMachine()
  state.state = log.SelfdriveState.OpenpilotState.enabled
  enabled, active = state.update(events)
  assert not enabled and not active  # ordinary longitudinal state machine sees Cancel

  paddle = _car(_button(ButtonType.altButton2, True))
  assert not aol_no_entry(events.names, paddle, paddle_only_cancel=True)
  native = SimpleNamespace(requestedLateral=True, requestedLongitudinal=False,
                           lateralAllowed=True, longitudinalAllowed=True)
  intent = SimpleNamespace(allowedLatch=True, pauseLateral=False, pauseLongitudinal=False)
  decision = decide_axes(standard_lateral=active, standard_longitudinal=enabled,
                         intent=intent, native=native, car_state=paddle,
                         initialized=True, model_ready=True, no_entry=False,
                         immediate_disable=False, dm_lockout=False, pause_brake_mps=0)
  assert decision.lateral_active and not decision.longitudinal_active

  # With AOL off, or without its saved latch, both axes stay off after the press.
  assert not active and not enabled
  intent.allowedLatch = False
  decision = decide_axes(standard_lateral=active, standard_longitudinal=enabled,
                         intent=intent, native=native, car_state=paddle,
                         initialized=True, model_ready=True, no_entry=False,
                         immediate_disable=False, dm_lockout=False, pause_brake_mps=0)
  assert not decision.lateral_active and not decision.longitudinal_active

  # A real Cancel on the same frame retains the normal all-axis veto.
  paddle.buttonEvents = (*paddle.buttonEvents, _button(ButtonType.cancel, True))
  assert aol_no_entry(events.names, paddle, paddle_only_cancel=True)
  assert aol_no_entry(events.names, _car(), paddle_only_cancel=False)


def test_latch_survives_press_and_next_frame_then_real_cancel_requires_rearm():
  intent = AolCardIntent(AolSettings(True, 0.0, 0, 0, (0, 0, 0), (0, 0, 0)), explicit_latch=True)
  neutral = _car()
  intent.update(neutral)
  arm = _car(_button(ButtonType.lkas, True))
  intent.update(arm)
  assert intent.output(arm)[0]
  intent.update(_car(_button(ButtonType.lkas, False)))

  state = StateMachine()
  state.state = log.SelfdriveState.OpenpilotState.enabled
  press = _car(_button(ButtonType.altButton2, True))
  intent.update(press)
  events = Events()
  events.add(EventName.buttonCancel)
  enabled, active = state.update(events)
  assert not enabled and not active and intent.output(press)[0]
  assert not aol_no_entry(events.names, press, paddle_only_cancel=True)

  next_frame = _car()
  intent.update(next_frame)
  enabled, active = state.update(Events())
  assert not enabled and not active and intent.output(next_frame)[0]

  cancel = _car(_button(ButtonType.cancel, True))
  intent.update(cancel)
  assert not intent.output(cancel)[0]
  assert aol_no_entry(events.names, cancel, paddle_only_cancel=True)
  intent.update(_car(_button(ButtonType.cancel, False)))
  assert not intent.output(neutral)[0]
  intent.update(_car(_button(ButtonType.lkas, True)))
  assert intent.output(neutral)[0]  # A new deliberate host gesture rearms steering.
