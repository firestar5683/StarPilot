"""Saved planner profiles follow the exact finalized GM longitudinal owner."""

from opendbc.car.gm.feature_capabilities import longitudinal_supported


def profiles_supported(cp) -> bool:
  return longitudinal_supported(cp)
