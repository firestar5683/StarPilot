"""Exact first-generation EV6 startup compatibility wrapper."""
from opendbc.car.hyundai.captured_adrv_startup import CapturedADRVStartup, first_generation
from opendbc.car.hyundai.ev6_template import EV6Template
from opendbc.car.hyundai.values import CAR


def eligible(cp):
  return cp.carFingerprint == CAR.KIA_EV6 and first_generation(cp)


def required(cp):
  return eligible(cp) and cp.openpilotLongitudinalControl


class EV6Startup(CapturedADRVStartup):
  def __init__(self, cp, callbacks):
    super().__init__(cp, callbacks, label='EV6', template_type=EV6Template)
