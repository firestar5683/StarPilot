from opendbc.car.gm.values import AccState, CAR


def get_stock_cc_active_for_cancel(CP, CS):
  stock_cc_active = CS.out.cruiseState.enabled or CS.pcm_acc_status != AccState.OFF
  if CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL:
    return CS.out.cruiseState.enabled
  return stock_cc_active
