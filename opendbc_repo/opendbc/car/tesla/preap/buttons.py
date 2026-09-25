class CruiseButtons:
  IDLE = 0
  CANCEL = 1
  MAIN = 2
  RES_ACCEL_2ND = 4
  DECEL_2ND = 8
  SET_ACCEL = 16
  RES_ACCEL = 16
  DECEL_SET = 32

  @classmethod
  def is_accel(cls, btn: int) -> bool:
    return btn in (cls.RES_ACCEL, cls.RES_ACCEL_2ND)

  @classmethod
  def is_decel(cls, btn: int) -> bool:
    return btn in (cls.DECEL_SET, cls.DECEL_2ND)
