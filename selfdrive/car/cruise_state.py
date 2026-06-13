from opendbc.car import structs


def hyundai_openpilot_longitudinal_acc_req_feedback(CP: structs.CarParams) -> bool:
  return CP.brand == 'hyundai' and CP.openpilotLongitudinalControl and not CP.pcmCruise


def should_cancel_stock_cruise(CP: structs.CarParams, cruise_enabled: bool, controls_enabled: bool) -> bool:
  if not cruise_enabled:
    return False
  if not controls_enabled:
    return True
  return not CP.pcmCruise and not hyundai_openpilot_longitudinal_acc_req_feedback(CP)


def should_flag_cruise_mismatch(CP: structs.CarParams, cruise_enabled: bool, controls_enabled: bool,
                                effective_pcm_cruise: bool) -> bool:
  if not cruise_enabled:
    return False
  if not controls_enabled:
    return True
  return not effective_pcm_cruise and not hyundai_openpilot_longitudinal_acc_req_feedback(CP)
