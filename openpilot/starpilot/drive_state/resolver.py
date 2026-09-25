"""Pipeline state selection; physical ignition remains separate."""

from enum import StrEnum
from collections.abc import Mapping


class Mode(StrEnum):
  AUTO = 'auto'
  OFFROAD = 'offroad'
  ONROAD = 'onroad'


def effective_onroad(mode: Mode, conditions: Mapping[str, bool]) -> bool:
  if mode == Mode.OFFROAD:
    return False
  if mode == Mode.ONROAD:
    if 'ignition' not in conditions:
      return False
    return all(value for key, value in conditions.items() if key != 'ignition')
  return all(conditions.values())


def should_start(mode: Mode, onroad: Mapping[str, bool], startup: Mapping[str, bool], *, already_started: bool) -> bool:
  ready = effective_onroad(mode, onroad)
  return ready if already_started else ready and all(startup.values())
