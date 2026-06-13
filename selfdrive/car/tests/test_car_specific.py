from cereal import car

from openpilot.selfdrive.car.cruise_state import should_cancel_stock_cruise, should_flag_cruise_mismatch


def make_cp(brand="hyundai", op_long=True, pcm_cruise=False):
  cp = car.CarParams.new_message()
  cp.brand = brand
  cp.openpilotLongitudinalControl = op_long
  cp.pcmCruise = pcm_cruise
  return cp


def test_hyundai_openpilot_long_does_not_cancel_active_acc_req_feedback():
  cp = make_cp()

  assert not should_cancel_stock_cruise(cp, cruise_enabled=True, controls_enabled=True)
  assert not should_flag_cruise_mismatch(cp, cruise_enabled=True, controls_enabled=True, effective_pcm_cruise=False)


def test_hyundai_openpilot_long_still_flags_cruise_when_controls_disabled():
  cp = make_cp()

  assert should_cancel_stock_cruise(cp, cruise_enabled=True, controls_enabled=False)
  assert should_flag_cruise_mismatch(cp, cruise_enabled=True, controls_enabled=False, effective_pcm_cruise=False)


def test_non_hyundai_openpilot_long_behavior_is_unchanged():
  cp = make_cp(brand="toyota")

  assert should_cancel_stock_cruise(cp, cruise_enabled=True, controls_enabled=True)
  assert should_flag_cruise_mismatch(cp, cruise_enabled=True, controls_enabled=True, effective_pcm_cruise=False)


def test_pcm_cruise_behavior_is_unchanged():
  cp = make_cp(op_long=False, pcm_cruise=True)

  assert not should_cancel_stock_cruise(cp, cruise_enabled=True, controls_enabled=True)
  assert should_cancel_stock_cruise(cp, cruise_enabled=True, controls_enabled=False)
  assert not should_flag_cruise_mismatch(cp, cruise_enabled=True, controls_enabled=True, effective_pcm_cruise=True)
  assert should_flag_cruise_mismatch(cp, cruise_enabled=True, controls_enabled=False, effective_pcm_cruise=True)
