"""Host-only regression: real controller, explicit synthetic Params/messages.

Run separately from following tests (their native import stubs are incompatible).
The oracle is the unmodified Dom controller at 249b03a3f5, not a reimplementation.
"""
from pathlib import Path

import pytest

from test_personality_longitudinal_profiles import (
  StarPilotAcceleration, _document, _planner, _sm, _toggles,
)


def _upstream():
  path = Path(__file__).parent / "fixtures/dom_249b03a3_starpilot_acceleration.py.txt"
  namespace = {"__name__": "dom_249b03a3_acceleration"}
  exec(compile(path.read_text(), str(path), "exec"), namespace)
  return namespace["StarPilotAcceleration"]


@pytest.mark.parametrize("preset,profile_id", [("eco", 1), ("standard", 0), ("sport", 2)])
@pytest.mark.parametrize("personality", [0, 1, 2])
@pytest.mark.parametrize("speed", [0.0, 5.0, 19.999, 20.0, 20.049999, 20.05, 20.050001, 25.0, 40.0])
@pytest.mark.parametrize("hazard", ["none", "lead", "force_decel"])
def test_named_braking_is_stock_dom_not_custom_overspeed_gate(preset, profile_id, personality, speed, hazard):
  document = _document()
  profile = ("aggressive", "standard", "relaxed")[personality]
  document["profiles"][profile]["braking"] = {"preset": preset, "curve": []}
  toggles = _toggles(document)
  sm = _sm(personality=personality, lead=hazard == "lead", force_decel=hazard == "force_decel")
  actual = StarPilotAcceleration(_planner())
  actual.update(speed, sm, toggles)
  toggles.custom_personalities = False
  toggles.deceleration_profile = profile_id
  expected = _upstream()(_planner())
  expected.update(speed, sm, toggles)
  assert actual.min_accel == expected.min_accel


def test_named_eco_has_no_added_threshold_cap_step():
  document = _document()
  document["profiles"]["standard"]["braking"] = {"preset": "eco", "curve": []}
  controller = StarPilotAcceleration(_planner())
  outputs = []
  for speed in (20.049999, 20.050001, 20.049999):
    controller.update(speed, _sm(), _toggles(document))
    outputs.append(controller.min_accel)
  assert outputs == [-0.5, -0.5, -0.5]
