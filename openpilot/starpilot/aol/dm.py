def armed_lateral_current(cp, cs, intent, native, *, source_ns, now_ns, axis_session_id) -> bool:
  """Retain only a current deliberately armed native-permitted lateral owner."""
  from opendbc.car.structs import car
  from openpilot.starpilot.aol.vehicle import policy_for
  from openpilot.starpilot.aol.runtime import AXIS_MAX_AGE_NS, SAFETY_MAX_AGE_NS, native_inventory_matches_cp
  try:
    return bool(policy_for(cp).intent_supported and
      cs.canValid and not cs.canTimeout and not cs.accFaulted and not cs.doorOpen and
      not cs.steerFaultTemporary and not cs.steerFaultPermanent and cs.cruiseState.available and
      cs.gearShifter in (car.CarState.GearShifter.drive, car.CarState.GearShifter.low,
                        car.CarState.GearShifter.sport, car.CarState.GearShifter.brake) and
      intent is not None and intent.settingsQualified and intent.allowedLatch and intent.lateralArmed and
      intent.producerSessionId and intent.carStateLogMonoTime == source_ns and
      0 < source_ns <= intent.observedMonoTime <= now_ns <= intent.validUntilMonoTime and
      now_ns - source_ns <= AXIS_MAX_AGE_NS and
      intent.validUntilMonoTime - intent.observedMonoTime <= SAFETY_MAX_AGE_NS and
      native is not None and native.compatible and int(native.protocolVersion) == 1 and
      axis_session_id and native.axisSessionId == axis_session_id and
      native.requestedLateral and native.lateralAllowed and native.pandaInventory and
      native_inventory_matches_cp(native, cp) and
      0 < native.observedMonoTime <= now_ns <= native.validUntilMonoTime and
      native.validUntilMonoTime - native.observedMonoTime <= SAFETY_MAX_AGE_NS)
  except (AttributeError, KeyError, IndexError, TypeError, ValueError):
    return False
