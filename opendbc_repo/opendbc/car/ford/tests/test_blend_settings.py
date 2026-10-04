from pathlib import Path
from types import SimpleNamespace

import pytest

from opendbc.car.ford.lateral_strategy import FordLateralController
from opendbc.car.ford.values import CAR


@pytest.mark.parametrize("values,expected", ((None, (0.4, 0.4, 0.85)),
                                           ((0.25, 0.65, 1.1), (0.25, 0.65, 1.1)),
                                           ((-1.0, 2.0, 4.0), (0.0, 1.0, 1.25)),
                                           ((2.0, -1.0, -4.0), (1.0, 0.0, 0.5))))
def test_typed_saved_blends_reach_owner_without_model(values, expected, monkeypatch):
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.starpilot import controller_extensions

  model = SimpleNamespace(meta=SimpleNamespace(laneChangeState=0))
  sm = SimpleNamespace(update=lambda timeout: None, alive={"modelV2": False}, valid={"modelV2": False})

  class Transport:
    alive = sm.alive
    valid = sm.valid

    def update(self, timeout):
      return None

    def __getitem__(self, key):
      return model
  monkeypatch.setattr(controller_extensions.messaging, "SubMaster", lambda names: Transport())
  with OpenpilotPrefix():
    saved = Params()
    keys = ("FordCurvatureBlendLow", "FordCurvatureBlendHigh", "FordCurvatureLaneChangeFactor")
    if values is not None:
      for key, value in zip(keys, values, strict=True):
        saved.put(key, value, block=True)
    inputs = controller_extensions.ManualTurnInputs(saved)
    owner = FordLateralController(SimpleNamespace(carFingerprint=CAR.FORD_RANGER_MK2))
    calls = []
    setter = owner.set_blend_settings

    def counted_setter(*values):
      calls.append(values)
      setter(*values)
    monkeypatch.setattr(owner, "set_blend_settings", counted_setter)
    controller = SimpleNamespace(classic_lateral=owner)
    inputs.apply_blend_settings(controller)
    assert (owner.curvature_blend_low, owner.curvature_blend_high, owner.curvature_lane_change_factor) == expected
    inputs.update()
    inputs.apply_blend_settings(controller)
    assert inputs.blend_settings == expected
    assert len(calls) == 1
    for key, raw in zip(keys, (b"nan", b"not-a-float", b"inf"), strict=True):
      Path(saved.get_param_path(key)).write_bytes(raw)
    for _ in range(99):
      inputs.update()
    assert inputs.blend_settings == expected
    inputs.update()
    inputs.apply_blend_settings(controller)
    assert inputs.blend_settings == (0.4, 0.4, 0.85)
    assert len(calls) == (1 if expected == (0.4, 0.4, 0.85) else 2)
    assert (owner.curvature_blend_low, owner.curvature_blend_high, owner.curvature_lane_change_factor) == (0.4, 0.4, 0.85)


@pytest.mark.parametrize("desired,predicted,direction", ((-0.0005, -0.002, 1), (0.0005, 0.002, 2),
                                                       (-0.001, -0.003, 2), (0.001, 0.003, 1)))
def test_saved_blends_preserve_source_units_and_lane_direction(desired, predicted, direction):
  owner = FordLateralController(SimpleNamespace(carFingerprint=CAR.FORD_RANGER_MK2))
  owner.set_blend_settings(0.25, 0.65, 1.1)
  owner.model = SimpleNamespace(meta=SimpleNamespace(laneChangeState=2, laneChangeDirection=direction))
  blend = 0.25 + min(abs(desired) / 0.001, 1.0) * 0.4
  expected = predicted * blend + desired * (1.0 - blend)
  precision = 1
  if (direction == 1 and expected < 0.0) or (direction == 2 and expected > 0.0):
    expected *= 0.95 + (20.0 - 4.4) / (40.23 - 4.4) * 0.15
    precision = 0
  result, actual_precision = owner._blend_and_scale(desired, predicted, v_ego=20.0, current=0.0)
  assert result == pytest.approx(expected)
  assert actual_precision == precision
