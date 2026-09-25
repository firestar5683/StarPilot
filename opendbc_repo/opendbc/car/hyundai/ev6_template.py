"""Exact EV6 compatibility descriptor; speed never changes its captured body."""
from dataclasses import dataclass
from opendbc.car.hyundai.captured_adrv import CapturedADRVTemplate


@dataclass(frozen=True)
class EV6Template(CapturedADRVTemplate):
  pass
