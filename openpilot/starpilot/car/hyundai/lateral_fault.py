from opendbc.car.hyundai.values import CAR


class LateralFaultLatch:
  def __init__(self, fingerprint):
    self.enabled = fingerprint == CAR.HYUNDAI_ELANTRA_HEV_2024
    self.faulted = False
    self.previous_cruise_enabled = False

  def update(self, *, requested: bool | None, temporary_fault: bool, cruise_enabled: bool) -> bool:
    if not self.enabled:
      return False
    cruise_reenabled = cruise_enabled and not self.previous_cruise_enabled
    if requested is False or requested is True and cruise_reenabled:
      self.faulted = False
    else:
      self.faulted |= temporary_fault
    self.previous_cruise_enabled = cruise_enabled
    return self.faulted
