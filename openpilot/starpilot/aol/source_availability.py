"""Classify ordinary host source loss without granting commands or engagement."""
from opendbc.car.structs import car
from openpilot.cereal import log
from openpilot.selfdrive.selfdrived.events import ET
from openpilot.starpilot.aol.intent_companion import MAX_COMPANIONS
from openpilot.starpilot.aol.runtime import INTENT_MAX_AGE_NS, SAFETY_MAX_AGE_NS, current_native
from openpilot.starpilot.aol.transport_pause import cp_identity, healthy_transport
from openpilot.starpilot.nostalgia import physical_cancel

EventName = log.OnroadEvent.EventName
AlertLevel = log.DriverMonitoringState.AlertLevel


def ordinary_source_availability(self, CS, now_ns, native=None, *, replay: bool, native_provider=current_native):
  """Classify lost host source; never renew a command or change engagement."""
  anchor = getattr(self, 'aol_ordinary_source_anchor', None)
  companion = getattr(self, 'aol_intent_companion', None)
  if (replay or not self.aol_replay or not self.axis_transport_required or anchor is None or
      not self.initialized or getattr(self, 'aol_availability_long_inhibit', False) or self.aol_authority_lost or
      getattr(self, 'aol_fault_reason', 'none') not in ('none', 'availabilityPause') or
      self.events.contains(ET.USER_DISABLE) or self.events.contains(ET.IMMEDIATE_DISABLE) or
      any(e.softDisable and e.name not in (EventName.commIssue, EventName.commIssueAvgFreq)
          for e in self.events.to_msg()) or self.events.contains(ET.ENABLE) or
      getattr(self, 'car_state_queue_invalid', False) or
      not getattr(self, 'aol_step_intent_drain_ok', True) or
      getattr(self, 'aol_step_intent_drain_count', 0) > MAX_COMPANIONS or companion is None or not companion.last_drain_ok or
      getattr(self, 'aol_selected_pair_future', False) or
      not self.sm.all_checks(['modelV2', 'extrinsicsCalibration', 'driverMonitoringState']) or
      self.sm['extrinsicsCalibration'].calStatus != log.ExtrinsicsCalibration.Status.calibrated or
      self.sm['driverMonitoringState'].alertLevel == AlertLevel.three or
      self.sm['driverMonitoringState'].lockout or self.sm['driverMonitoringState'].alwaysOnLockout):
    return False
  proof, prior_native, accepted, identity, accepted_state = anchor
  if accepted is None:
    return False
  source = self.aol_car_state_log_ns or getattr(self, 'car_state_retained_source_ns', 0)
  held_metadata = bool(not getattr(self, 'car_state_samples', ()) and CS is accepted_state and
                       getattr(self, 'aol_publication_retained_intent', None) is accepted)
  if not source and held_metadata:
    source = int(accepted.carStateLogMonoTime)
  if (proof[0] != self.aol_session_id or not proof[9] or accepted is None or source != int(accepted.carStateLogMonoTime) or
      not 0 < source <= now_ns or now_ns - source <= INTENT_MAX_AGE_NS or
      cp_identity(self.CP) != identity or companion.integrity_epoch != proof[5] or
      accepted is None or accepted.producerSessionId != proof[4] or
      prior_native is None or not prior_native.pandaInventory):
    return False
  samples = getattr(self, 'car_state_samples', ()) or ((CS,
    bool(getattr(self, 'car_state_retained_valid', False) or held_metadata)),)
  if any(not valid or not sample.canValid or sample.canTimeout or sample.steerFaultPermanent or
         sample.steerFaultTemporary or sample.accFaulted or sample.doorOpen or sample.seatbeltUnlatched or
         sample.brakePressed or sample.regenBraking or sample.gasPressed or physical_cancel(sample) or
         sample.gearShifter not in (car.CarState.GearShifter.drive, car.CarState.GearShifter.sport,
                                   car.CarState.GearShifter.low, car.CarState.GearShifter.brake)
         for sample, valid in samples):
    return False
  def valid_metadata(stamp, value):
    if (value is None or value.carStateLogMonoTime != stamp or
        value.producerSessionId != proof[4] or not value.settingsQualified or
        value.allowedLatch != accepted.allowedLatch or value.lateralArmed != accepted.lateralArmed or
        value.pauseLongitudinal or value.pauseLateral and (proof[8] or not accepted.pauseLateral)):
      return False
    # Only the exact originally accepted tuple is identity after expiry.
    # Every newer raw/SM tuple keeps its own original shape and 200ms lease;
    # none supplies an active command or a renewed source/output deadline.
    return bool(stamp == accepted.carStateLogMonoTime and value == accepted or
      0 < stamp <= value.observedMonoTime <= now_ns <= value.validUntilMonoTime and
      0 < value.validUntilMonoTime - value.observedMonoTime <= SAFETY_MAX_AGE_NS)

  # The raw-only cache retains every distinct tuple in a <=16-message step.
  # Its exact validated receipts remain metadata when current() legitimately
  # prunes the separate 30ms source-pair cache. Check every original restriction
  # directly, including one no longer present in the conflated SM/sample cache.
  accounted = 0
  for stamp, (value, epoch, producer) in companion.raw_projections.items():
    if stamp < accepted.carStateLogMonoTime:
      continue
    if epoch != proof[5] or producer != proof[4] or not valid_metadata(stamp, value):
      return False
    accounted += 1
  if accounted < getattr(self, 'aol_step_intent_drain_count', 0):
    return False
  # A newer conflated SM sample may add a restriction but cannot remove any
  # already checked raw restriction. Invalid/reordered bursts also retain the
  # existing integrity-epoch and cumulative-drain vetoes above.
  for stamp, valid, value in companion.samples.values():
    if stamp > accepted.carStateLogMonoTime and (not valid or not valid_metadata(stamp, value)):
      return False
  latest = companion.latest
  raw = latest[2] if latest is not None and latest[1] else None
  if (latest is None or not accepted.carStateLogMonoTime <= latest[0] <= now_ns or
      not valid_metadata(latest[0], raw)):
    return False
  native = native or native_provider(self.sm, self.CP, now_ns=now_ns, axis_session_id=self.aol_session_id)
  if (native is None or not healthy_transport(self.sm, self.CP, CS, self.aol_session_id, now_ns, native) or
      native.observedMonoTime < prior_native.observedMonoTime or
      native.pandaSerial != prior_native.pandaSerial or
      tuple(p.hardwareSerial for p in native.pandaInventory) != tuple(p.hardwareSerial for p in prior_native.pandaInventory)):
    return False
  self.aol_ordinary_source_native = native
  return True
