"""Exact first-generation GV70 Electrified captured-ADRV startup."""
from opendbc.car.hyundai.captured_adrv_startup import CapturedADRVStartup, first_generation
from opendbc.car.hyundai.gv70_template import GV70Template
from opendbc.car.hyundai.ecu_startup import Outcome
from opendbc.car.hyundai.values import CAR


def eligible(cp):
  return cp.carFingerprint == CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN and first_generation(cp)


def required(cp):
  return eligible(cp) and cp.openpilotLongitudinalControl


class GV70Startup(CapturedADRVStartup):
  def __init__(self, cp, callbacks):
    super().__init__(cp, callbacks, label='GV70', template_type=GV70Template)

  def configure(self, ci):
    super().configure(ci)
    # This owner exists only for a requested exact-model takeover. The original
    # failed-disable controller avoided fighting stock cruise with Cancel.
    ci.CC.gv70_stock_fallback = self.outcome is not Outcome.SENT_UNCONFIRMED
