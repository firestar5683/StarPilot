"""Compatibility API retaining the exact Ioniq 5 PE stock contract."""
from opendbc.car.hyundai import ccnc_ev_stock
from opendbc.car.hyundai.values import CAR

STOCK_SAFETY_PARAM = 0x5491


def qualified(cp):
  return cp.carFingerprint == CAR.HYUNDAI_IONIQ_5_PE and ccnc_ev_stock.qualified(cp)


def request_allowed(cp, state):
  return qualified(cp) and ccnc_ev_stock.request_allowed(cp, state)


def replacement_requested(cp, control, state):
  return qualified(cp) and ccnc_ev_stock.replacement_requested(cp, control, state)
