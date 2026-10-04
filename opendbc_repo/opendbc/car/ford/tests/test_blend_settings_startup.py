import gc
import time

import pytest

from opendbc.car import structs
from opendbc.car.ford.generic_canfd_lateral import GENERIC_CANFD_CARS
from opendbc.car.ford.tests.test_three_ports import params


@pytest.mark.parametrize("identity", sorted(GENERIC_CANFD_CARS))
def test_generic_actual_card_publication_reaches_blend_settings(identity, monkeypatch):
  alpha = release = disable = False
  from opendbc.car import car_helpers, gen_empty_fingerprint
  from opendbc.car.ford.generic_canfd_lateral import qualified as generic_qualified
  from openpilot.selfdrive.car import card as card_module
  from openpilot.cereal import messaging
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.selfdrive.car.card import Car, alpha_long_requested
  from openpilot.selfdrive.controls.controlsd import Controls
  from openpilot.starpilot.controller_extensions import ManualTurnInputs
  from openpilot.starpilot.lateral.tests.test_lane_runtime import feed

  monkeypatch.setenv('SIMULATION', '1')
  monkeypatch.setenv('REPLAY', '1')
  with OpenpilotPrefix():
    saved = Params()
    saved.put_bool('OpenpilotEnabledToggle', True, block=True)
    saved.put_bool('AlphaLongitudinalEnabled', alpha, block=True)
    saved.put_bool('IsReleaseBranch', release, block=True)
    saved.put_bool('DisableOpenpilotLongitudinal', disable, block=True)
    saved.put_bool('FordHumanTurnDetection', False, block=True)
    for key, value in (("FordCurvatureBlendLow", 0.25), ("FordCurvatureBlendHigh", 0.65), ("FordCurvatureLaneChangeFactor", 1.1)):
      saved.put(key, value, block=True)
    cp = params(identity, alpha_long_requested(saved, is_release=release), release)
    cp.carVin = '0' * 17
    cp.carFw = []
    expected = cp.to_dict()
    fingerprint = gen_empty_fingerprint()
    fingerprint[0][0x5A] = 8
    fingerprint[2][0x3D6] = 8
    fingerprint[2][0x186] = 8
    observed = (identity, fingerprint, cp.carVin, [], cp.fingerprintSource, True)
    subscriber = messaging.sub_sock('carParams', timeout=100, conflate=True)
    ci = card = controls = None
    try:
      with monkeypatch.context() as discovery:
        discovery.setattr(car_helpers, 'fingerprint', lambda *args: observed)
        discovery.setattr(card_module, 'can_comm_callbacks', lambda *args: (lambda *args: [], lambda frames: None))
        initial_can = messaging.new_message('can', 1)
        discovery.setattr(card_module.messaging, 'recv_one_retry', lambda socket: initial_can)
        card = Car()
      ci = card.CI
      assert card.CP.to_dict() == expected
      assert generic_qualified(card.CP)
      owner = ci.CC.classic_lateral
      assert owner is not None
      assert (owner.curvature_blend_low, owner.curvature_blend_high, owner.curvature_lane_change_factor) == (0.25, 0.65, 1.1)
      assert isinstance(ci.CC.manual_turn_inputs, ManualTurnInputs)
      assert not ci.CC.manual_turn_inputs.enabled
      assert not ci.CC.mache_extended_announced and not ci.CC.classic_extended_announced
      with structs.CarParams.from_bytes(saved.get('CarParams')) as published:
        assert published.to_dict() == expected
      event = None
      for _ in range(10):
        card.car_params_published = False
        card.state_publish(ci.update([]), None)
        event = messaging.recv_one(subscriber)
        if event is not None:
          break
        time.sleep(.01)
      assert event is not None and event.valid and event.carParams.to_dict() == expected
      controls = Controls()
      assert controls.CP.to_dict() == expected
      feed(controls, 1_000_000_000, 0, active=False, enabled=False, can_valid=False, can_timeout=True)
      command, lateral_log = controls.state_control()
      assert not command.enabled and not command.latActive and not command.longActive
      controls.publish(command, lateral_log)
      _, packets = ci.apply(command.as_reader(), 1_000_000_000)
      assert packets
      assert ci.CC.classic_extended_announced
      assert not owner.human_turn_enabled
      assert (owner.curvature_blend_low, owner.curvature_blend_high, owner.curvature_lane_change_factor) == (0.25, 0.65, 1.1)
    finally:
      del controls, card, ci, subscriber
      gc.collect()
