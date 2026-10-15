"""Sole optional learning publisher; native torqued never waits for this process.

Actual controller baseline and independent physical model adapters are selected
from received source-bound evidence, never another process's startup preference.
"""

import os
import uuid
import time

from opendbc.car.structs import car
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.starpilot.flm.fullrate_collector import FullrateCollector, drain
from openpilot.starpilot.flm.learning_wire import read_control, read_applied, result_message, write_source_receipt


MAX_OBJECTIVES = 6
MAX_CACHED_PROFILES = 10  # Six FF cells and four independently qualified centre speed bands.


def run(
  CP,
  sm,
  control_socket,
  applied_socket,
  pm,
  adapter_for_evidence,
  physical_observer,
  source_reader,
  collection_keys,
  objective_key,
  decode_fit_result,
  persistence,
  fitter,
  adapter_for_ford,
  *,
  clock=time.monotonic_ns,
):
  from openpilot.starpilot.flm.native_health import current_native_health

  collector = None
  raw_context = active_key = pending_key = pending_token = None
  cached_reports = {}
  prior_attached = {}
  previous_publish = publication_sequence = 0
  unavailable_reason = 'no_current_controller_evidence'

  def clear(reason):
    nonlocal collector, raw_context, active_key, pending_key, pending_token, unavailable_reason
    unavailable_reason = reason
    if collector is not None:
      collector.split(reason, reset=True)
    collector = None
    cached_reports.clear()
    prior_attached.clear()
    raw_context = active_key = pending_key = pending_token = None
    fitter.cancel(reason)

  class Sink:
    def split(self, reason, **kwargs):
      if collector is not None:
        collector.split(reason, **kwargs)

    def overrun(self):
      if collector is not None:
        collector.overrun()

  sink = Sink()
  try:
    while True:
      # Parent handles bounded primitive ingest and live receipts. Physical
      # fitting, stage normalization and full replay run in ONE separate child.
      sm.update()
      now = clock()
      source = source_reader(now)
      if not source.enabled or source.manual or not source.observed_ns <= now <= source.expires_ns:
        clear('learning_disabled' if not source.enabled else 'manual_profile_override' if source.manual else 'settings_receipt_expired')
      elif collector is None:
        unavailable_reason = 'no_current_controller_evidence'

      def control(event, current, stamp, *, source=source, now=now):
        nonlocal collector, raw_context, active_key, unavailable_reason
        if event.which() == 'starpilotLateralState' and event.starpilotLateralState.learningEvidence.version == 0:
          if collector is not None:
            collector.split('no_current_learning_evidence')
          return
        evidence = read_control(event)
        if (
          not source.enabled
          or source.manual
          or evidence.source_epoch != source.source_epoch
          or not 0 < evidence.source_receipt_ns <= evidence.control_ns <= now <= source.expires_ns
        ):
          clear('learning_disabled' if not source.enabled else 'manual_profile_override' if source.manual else 'controller_source_receipt_mismatch')
          return
        incoming = (
          evidence.identity,
          evidence.generation,
          evidence.domain,
          evidence.stage_revision,
          evidence.response_revision,
          evidence.source_epoch,
          evidence.controller_mode,
          evidence.policy,
          evidence.baseline_revision,
          evidence.controller_revision,
          evidence.turn_assist,
        )
        if incoming != raw_context:
          clear('actual_controller_identity_changed')
          raw_context = incoming
        keys = tuple(collection_keys(evidence))
        if not 0 < len(keys) <= MAX_OBJECTIVES or len(set(keys)) != len(keys):
          clear('objective_registry_bound')
          return
        active_key = objective_key(evidence)
        if active_key not in keys:
          clear('current_objective_unavailable')
          return
        if collector is None:
          adapter = adapter_for_evidence(CP, evidence, active_key)
          if adapter is None:
            unavailable_reason = 'actual_adapter_unavailable'
            return
          collector = FullrateCollector(adapter)
        collector.adapter.select_objective(active_key)
        # This records primitive actual frames/checkpoints ONLY. No selected
        # controller update, baseline probes or numerical fitting at100Hz.
        prepared = collector.adapter.prepare_control(evidence)
        if prepared is None:
          collector.split('actual_stage_capture_unqualified')
        else:
          collector.control(prepared, stamp)

      def output(event, current, stamp, *, source=source):
        if collector is not None:
          if event.which() == 'starpilotCarState' and event.starpilotCarState.appliedEvidence.version == 0:
            collector.split('no_current_applied_evidence')
            return
          collector.output(read_applied(event), stamp)

      drain(control_socket, control, messaging.recv_one_or_none, sink, now)
      drain(applied_socket, output, messaging.recv_one_or_none, sink, now)
      current_native = False
      if collector is not None and collector.ready:
        current_native = current_native_health(sm, CP, collector.ready[-1][0], now)
        collector._learning_current_native_allowed = current_native
        physical = physical_observer(sm, CP, collector, now)
        if physical is None or not current_native:
          collector.split('physical_or_native_witness_unavailable')
        else:
          collector.physical(physical, now)

      token = (raw_context, pending_key, collector.physical_context) if collector is not None and collector.ready and current_native else None
      report = fitter.poll(token=token, now_ns=now)
      if report is not None:
        decoded = decode_fit_result(report)
        if decoded is not None and collector is not None and token == pending_token:
          if len(cached_reports) < MAX_CACHED_PROFILES or pending_key in cached_reports:
            cached_reports[pending_key] = (report, decoded)
        pending_key = pending_token = None
      if fitter.child is None:
        pending_key = pending_token = None
        if collector is not None and current_native and active_key is not None:
          collector.adapter.select_objective(active_key)
          if collector.context is not None:
            scope = (collector.context[0], active_key, source.reset)
            cached_prior = prior_attached.get(scope)
            if cached_prior is None or cached_prior[0] != tuple(collector.adapter.parameters()):
              persistence.attach_prior(collector, identity=collector.context[0], source_epoch=source.source_epoch, reset=source.reset)
              prior_attached[scope] = (tuple(collector.adapter.parameters()), collector.prior_coefficients)
            else:
              collector.restore_prior(cached_prior[1])
          snapshot = collector.job_snapshot(now)
          if snapshot is not None:
            token = (raw_context, active_key, collector.physical_context)
            if fitter.submit(snapshot, token=token, now_ns=now):
              collector.mark_job_submitted(now)
              pending_key, pending_token = active_key, token

      if now - previous_publish >= 250_000_000:
        previous_publish = now
        publication_sequence += 1
        if collector is not None:
          cached = cached_reports.get(active_key)
          collector.fit_result = collector.fit_validation = None
          if cached is not None and current_native:
            report, decoded = cached
            collector.adapter.select_objective(active_key)
            if collector.adapter.install_fit(report, *decoded, physical_context=collector.physical_context):
              collector.install_fit(*decoded)
          collector.live_profile_sequence = max(collector.live_profile_sequence, publication_sequence)
          collector.revalidate_fit(now)
          publication_sequence = max(publication_sequence, collector.live_profile_sequence)
          message = result_message(collector.result, collector.session, publication_sequence, now, replay_validation=collector.last_validation)
          persistence.save_current(collector, now_ns=now, source_epoch=source.source_epoch, reset=source.reset)
        else:
          message = messaging.new_message('autoSteeringLearning')
          value = message.autoSteeringLearning.learning
          value.version, value.status, value.reason, value.family = 1, 'unavailable', unavailable_reason, 'runtimeProfile'
          value.observedMonoTime, value.validUntilMonoTime = now, now + 500_000_000
          message.valid = True
        write_source_receipt(message, source)
        pm.send('autoSteeringLearning', message)
  finally:
    fitter.close('learner_parent_exit')


def main():
  # Imports belong only to the separate optional process. No workerthread/GIL
  # shared with realtime controller processes, no independent selection read.
  from openpilot.starpilot.flm.runtime_adapter_registry import (
    adapter_for_evidence,
    physical_observer,
    read_source,
    car_params_digest,
    collection_keys,
    objective_key,
    adapter_for_ford,
  )
  from openpilot.starpilot.flm.learner_factory import decode_fit_result
  from openpilot.starpilot.flm.persistence_module import PersistenceModule
  from openpilot.starpilot.flm.fit_process import FitProcess

  try:
    if hasattr(os, 'sched_setscheduler'):
      os.sched_setscheduler(0, os.SCHED_OTHER, os.sched_param(0))
    os.nice(10)
  except OSError:
    # An optional estimator must not inherit realtime scheduling on failure.
    return
  params = Params()
  CP = messaging.log_from_bytes(params.get('CarParams', block=True), car.CarParams)
  from opendbc.car.vin import is_valid_vin, VIN_UNKNOWN

  persistent_unit = is_valid_vin(str(CP.carVin)) and str(CP.carVin) != VIN_UNKNOWN
  services = [
    'deviceMotion',
    'extrinsicsCalibration',
    'carState',
    'carControl',
    'pandaStates',
    'lateralDelay',
    'vehicleParameters',
    'driverMonitoringState',
    'onroadEvents',
    'aolSafetyWire',
  ]
  sm = messaging.SubMaster(services, poll='deviceMotion', ignore_alive=['aolSafetyWire'], ignore_valid=['aolSafetyWire'], ignore_avg_freq=['aolSafetyWire'])
  control_socket = messaging.sub_sock('starpilotLateralState', conflate=False)
  applied_socket = messaging.sub_sock('starpilotCarState', conflate=False)
  pm = messaging.PubMaster(['autoSteeringLearning'])
  cp_sha256 = car_params_digest(CP)
  source_cache = [None]
  vehicle_session = uuid.uuid4().hex

  def calibration_basis():
    calibration = sm["extrinsicsCalibration"]
    if not (
      sm.seen["extrinsicsCalibration"]
      and sm.valid["extrinsicsCalibration"]
      and sm.alive["extrinsicsCalibration"]
      and str(calibration.calStatus) == "calibrated"
    ):
      return ()
    return tuple(float(value) for value in calibration.rpyCalib)

  def source_reader(now):
    # Read once each4Hz receipt renewal, outside all controller/torqued processes.
    if source_cache[0] is None or now - source_cache[0].observed_ns >= 250_000_000:
      source_cache[0] = read_source(CP, params, now_ns=now, cp_sha256=cp_sha256, calibration=calibration_basis(), vehicle_session=vehicle_session)
    return source_cache[0]

  def current_sources(identity, epoch):
    current = read_source(CP, params, now_ns=time.monotonic_ns(), cp_sha256=cp_sha256, calibration=calibration_basis(), vehicle_session=vehicle_session)
    return (identity if persistent_unit and epoch == current.source_epoch else '', current.enabled, current.manual, current.reset)

  persistence = PersistenceModule(params, current_sources)
  run(
    CP,
    sm,
    control_socket,
    applied_socket,
    pm,
    adapter_for_evidence,
    physical_observer,
    source_reader,
    collection_keys,
    objective_key,
    decode_fit_result,
    persistence,
    FitProcess(),
    adapter_for_ford,
  )


if __name__ == '__main__':
  main()
