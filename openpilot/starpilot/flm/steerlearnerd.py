"""Sole optional learning publisher; native torqued never waits for this process.

Actual controller baseline and independent physical model adapters are selected
from received source-bound evidence, never another process's startup preference.
"""

from collections.abc import Callable
from typing import cast
from openpilot.starpilot.flm.runtime_adapter_registry import SourceState

import os
import uuid
import time
from functools import partial

from opendbc.car.structs import car
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.starpilot.flm.fullrate_collector import FullrateCollector, drain
from openpilot.starpilot.flm.learning_wire import read_control, read_applied, result_message, write_source_receipt
from openpilot.starpilot.flm.runtime_adapter_registry import SOURCE_LEASE_NS


MAX_OBJECTIVES = 12
MAX_CACHED_PROFILES = 14  # Six FF cells and four independently qualified centre speed bands.


def production_adapter_for_evidence(cp, evidence, key, *, source):
  """Adopt the qualified event contract only in the optional live producer.

  Legacy/reference callers retain version2. The live event producer explicitly
  selects the separate fixed-map version6 restore declaration, never FD shadow.
  """
  from openpilot.starpilot.flm.clipping_quality import ZERO_REFERENCE_QUALITY
  from openpilot.starpilot.flm.runtime_adapter_registry import SourceState, adapter_for_evidence

  if not isinstance(source, SourceState) or not source.enabled or source.manual:
    return None
  return adapter_for_evidence(cp, evidence, key, source=source,
    event_replay_version=3, event_clipping_quality=ZERO_REFERENCE_QUALITY, event_restore_version=6)


def _source_config_binding(source):
  return (source.cp_sha256, source.source_epoch, source.reset, source.calibration_generation,
          source.enabled, source.manual, source.persistent_source_epoch, tuple(source.manual_baseline))


def _source_config_known(source, now_ns):
  import math
  from openpilot.starpilot.flm.runtime_adapter_registry import SourceState
  return bool(isinstance(source, SourceState) and type(source.configuration_known) is bool and source.configuration_known and
    type(source.enabled) is bool and type(source.manual) is bool and
    type(source.observed_ns) is int and type(source.expires_ns) is int and
    0 < source.observed_ns <= now_ns <= source.expires_ns <= source.observed_ns + SOURCE_LEASE_NS and
    type(source.cp_sha256) is str and len(source.cp_sha256) == 64 and
    all(char in '0123456789abcdef' for char in source.cp_sha256) and
    type(source.reset) is str and 1 <= len(source.reset) <= 64 and
    all(char in '0123456789abcdef' for char in source.reset) and
    type(source.calibration_generation) is str and (not source.calibration_generation or
      len(source.calibration_generation) == 32 and all(char in '0123456789abcdef' for char in source.calibration_generation)) and
    type(source.persistent_source_epoch) is str and (not source.persistent_source_epoch or
      len(source.persistent_source_epoch) == 64 and all(char in '0123456789abcdef' for char in source.persistent_source_epoch)) and
    type(source.manual_baseline) is tuple and len(source.manual_baseline) in (0, 3) and
    all(type(value) in (int, float) and math.isfinite(value) for value in source.manual_baseline))


def _pause_historical_collector(collector, reason):
  # Preserve only bounded, originally admitted historical storage/replay. The
  # partial packet/current joins and every current fit/physical lease are gone.
  collector.raw_points.clear()
  if hasattr(collector, '_pending_storage'):
    collector._pending_storage = ()
    collector._pending_storage_lineage = None
  collector.split(reason)
  collector.fit_result = collector.fit_validation = collector.result = collector.last_validation = None
  collector.last_qualified_response = 0
  collector.adapter.fit_profile = None
  collector.adapter.current_physical_valid = False
  collector.adapter.last_physical_ns = 0
  collector._physical_pose_queue = ()
  collector._physical_pose_context = None
  replay = getattr(collector.adapter, 'replay', None)
  if replay is not None:
    # Only a genuine next checkpoint may restart frame recording after a pause.
    replay.failed = True
    replay.cached_validation = replay.cached_key = None


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
  reporter=None,
  publication_source_reader: Callable[[int], SourceState | None] | None = None,
):
  from openpilot.starpilot.flm.native_health import current_native_health

  collector = None
  source = None
  last_accepted_source = None
  source_rejected = False
  source_cp_sha256 = None
  raw_context = active_key = pending_key = pending_token = None
  cached_reports = {}
  prior_attached = {}
  previous_publish = publication_sequence = 0
  unavailable_reason = 'no_current_controller_evidence'
  retained_event = pending_event = None

  def clear(reason):
    nonlocal collector, raw_context, active_key, pending_key, pending_token, unavailable_reason, retained_event, pending_event
    unavailable_reason = reason
    retained_event = pending_event = None
    if collector is not None:
      if reporter is not None:
        reporter.reset(reason)
      collector.split(reason, reset=True)
    collector = None
    cached_reports.clear()
    prior_attached.clear()
    raw_context = active_key = pending_key = pending_token = None
    fitter.cancel(reason)

  def uncertain(reason):
    nonlocal unavailable_reason, retained_event, active_key, pending_key, pending_token, pending_event
    unavailable_reason, retained_event, pending_event = reason, None, None
    if collector is not None:
      _pause_historical_collector(collector, reason)
    cached_reports.clear()
    active_key = pending_key = pending_token = None
    fitter.cancel(reason)

  def source_current(*, read=False, publication=False):
    nonlocal source, source_rejected, source_cp_sha256, last_accepted_source
    now = clock()
    if source_rejected and not read:
      return False, now
    if read or source is None or not source.observed_ns <= now <= source.expires_ns:
      if not read:
        sm.update(0)
        now = clock()
      if publication:
        sm.update(0)
        now = clock()
      reader = publication_source_reader if publication else source_reader
      source = cast(Callable[[int], SourceState | None], reader)(now)
      now = clock()
    known = _source_config_known(source, now)
    if known and (not source.enabled or source.manual):
      source_rejected = True
      clear('manual_profile_override' if source.manual else 'learning_disabled')
      last_accepted_source = None
      return False, now
    valid = bool(known and source.enabled and not source.manual and
      type(source.source_epoch) is str and len(source.source_epoch) == 64 and
      all(char in '0123456789abcdef' for char in source.source_epoch) and
      (source_cp_sha256 is None or source.cp_sha256 == source_cp_sha256))
    if not valid:
      source_rejected = True
      if known and source_cp_sha256 is not None and source.cp_sha256 != source_cp_sha256:
        clear('actual_source_identity_changed')
      else:
        uncertain('settings_receipt_expired' if source is not None and type(source.expires_ns) is int and source.expires_ns < now
                  else 'source_configuration_uncertain')
      return False, now
    previous = last_accepted_source
    if previous is not None and _source_config_binding(previous) != _source_config_binding(source):
      clear('actual_source_identity_changed')
      source_rejected = True
      if previous.source_epoch != source.source_epoch:
        last_accepted_source = source
      return False, now
    last_accepted_source = source
    source_cp_sha256 = source.cp_sha256
    source_rejected = False
    return True, now

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
      source_rejected = False
      now = clock()
      source_valid, now = source_current(read=True)
      if source_valid and collector is None:
        unavailable_reason = 'no_current_controller_evidence'

      def control(event, current, stamp):
        nonlocal collector, raw_context, active_key, unavailable_reason
        valid_source, received_now = source_current()
        if not valid_source:
          return
        if event.which() == 'starpilotLateralState' and event.starpilotLateralState.learningEvidence.version == 0:
          if collector is not None:
            collector.split('no_current_learning_evidence')
          return
        evidence = read_control(event)
        if (
          not source.enabled
          or source.manual
          or evidence.source_epoch != source.source_epoch
          or not 0 < evidence.source_receipt_ns <= evidence.control_ns <= received_now <= source.expires_ns
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
        if reporter is not None:
          reporter.control = (event, evidence)
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
          if getattr(adapter, 'event_collection', False):
            from openpilot.starpilot.flm.event_collector import EventFullrateCollector
            collector = EventFullrateCollector(adapter)
          else:
            collector = FullrateCollector(adapter)
        if hasattr(collector.adapter, 'bind_source'):
          collector.adapter.bind_source(source)
        collector._calibration_generation = source.calibration_generation
        collector.adapter.select_objective(active_key)
        # This records primitive actual frames/checkpoints ONLY. No selected
        # controller update, baseline probes or numerical fitting at100Hz.
        prepared = collector.adapter.prepare_control(evidence)
        if prepared is None:
          collector.split('actual_stage_capture_unqualified')
        else:
          collector.control(prepared, received_now)

      def output(event, current, stamp):
        valid_source, received_now = source_current()
        if not valid_source:
          return
        if collector is not None:
          if event.which() == 'starpilotCarState' and event.starpilotCarState.appliedEvidence.version == 0:
            collector.split('no_current_applied_evidence')
            return
          collector.output(read_applied(event), received_now)

      drain(control_socket, control, messaging.recv_one_or_none, sink, now)
      drain(applied_socket, output, messaging.recv_one_or_none, sink, now)
      source_valid, now = source_current()
      current_native = False
      if source_valid and collector is not None and collector.ready:
        current_native = current_native_health(sm, CP, collector.ready[-1][0], now)
        collector._learning_current_native_allowed = current_native
        physical = physical_observer(sm, CP, collector, now)
        from openpilot.starpilot.flm.physical_observation import PendingPhysical
        if not current_native or physical is None:
          collector.split('physical_or_native_witness_unavailable')
        elif type(physical) is PendingPhysical:
          if not physical.fresh(now):
            collector.split('physical_or_native_witness_unavailable')
          elif physical.context_changed:
            # Discard prior current admission on a lineage/transform boundary;
            # waiting for new-context data must not restart its own queue.
            collector.last_qualified_response = 0
            collector.adapter.current_physical_valid = False
            collector.adapter.last_physical_ns = 0
          # Pending data is not physical evidence: no timestamp, model,
          # last_qualified_response or current admission is renewed here.
        else:
          collector.physical(physical, now)

      source_valid, now = source_current()
      current_native = bool(source_valid and collector is not None and collector.ready and
                            current_native_health(sm, CP, collector.ready[-1][0], now))
      token = ((raw_context, pending_key, collector.physical_context, collector.adapter.envelope.prior_full_profile_sha256)
               if getattr(collector.adapter, 'event_collection', False) else (raw_context, pending_key, collector.physical_context)) \
              if collector is not None and collector.ready and current_native else None
      report = fitter.poll(token=token, now_ns=now)
      if report is not None:
        decoded = decode_fit_result(report)
        if source_valid and token is not None and decoded is not None and collector is not None and token == pending_token:
          if reporter is not None:
            reporter.fitted(decoded[0], pending_key)
          if len(cached_reports) < MAX_CACHED_PROFILES or pending_key in cached_reports:
            cached_reports[pending_key] = (report, decoded, token)
            if getattr(collector.adapter, 'event_collection', False) and decoded[0].profile is not None:
              # A completed proposal owns its fitting objective independently
              # from the rotating capture selector. This is not live admission.
              pending_event = (cached_reports[pending_key], pending_key)
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
            token = ((raw_context, active_key, collector.physical_context, collector.adapter.envelope.prior_full_profile_sha256)
                     if getattr(collector.adapter, 'event_collection', False) else (raw_context, active_key, collector.physical_context))
            valid_source, now = source_current()
            current_native = bool(valid_source and collector is not None and collector.ready and
                                  current_native_health(sm, CP, collector.ready[-1][0], now))
            if valid_source and current_native and collector is not None and fitter.submit(snapshot, token=token, now_ns=now):
              if reporter is not None:
                reporter.fit_attempts += 1
              collector.mark_job_submitted(now)
              pending_key, pending_token = active_key, token

      source_valid, now = source_current()
      current_native = bool(source_valid and collector is not None and collector.ready and
                            current_native_health(sm, CP, collector.ready[-1][0], now))
      if now - previous_publish >= 250_000_000:
        previous_publish = now
        publication_sequence += 1
        if publication_source_reader is not None:
          source_valid, now = source_current(read=True, publication=True)
        if source_valid and collector is not None and active_key is not None and raw_context is not None:
          cached = cached_reports.get(active_key)
          collector.fit_result = collector.fit_validation = None
          if getattr(collector.adapter, 'event_collection', False):
            if pending_event is not None:
              candidate, candidate_key = pending_event
              expected = (raw_context, candidate_key, collector.physical_context,
                          collector.adapter.envelope.prior_full_profile_sha256)
              if candidate[2] != expected:
                pending_event = None
            selected_event = pending_event if pending_event is not None else retained_event
            if selected_event is not None and current_native:
              selected, selected_key = selected_event
              collector.adapter.select_objective(selected_key)
              installed = (collector.adapter.install_fit(selected[0], *selected[1], physical_context=collector.physical_context)
                           and collector.install_fit(*selected[1]))
              if not installed and selected_event is pending_event:
                pending_event = None
            collector.live_profile_sequence = max(collector.live_profile_sequence, publication_sequence)
            collector.revalidate_fit(now)
            if (selected_event is not None and collector.result is not None and
                collector.result.profile is not None):
              retained_event = selected_event
              if selected_event is pending_event:
                pending_event = None
            # While a structurally valid proposal awaits fresh physical proof,
            # do not alternate its model with the retained model each publish.
            # Same-model installation keeps the adapter's original current flags.
            # Restore only the fitting selector, not an owner or permission.
            collector.adapter.select_objective(active_key)
          else:
            if cached is not None and current_native:
              report, decoded, _ = cached
              collector.adapter.select_objective(active_key)
              if collector.adapter.install_fit(report, *decoded, physical_context=collector.physical_context):
                collector.install_fit(*decoded)
            collector.live_profile_sequence = max(collector.live_profile_sequence, publication_sequence)
            collector.revalidate_fit(now)
          publication_sequence = max(publication_sequence, collector.live_profile_sequence)
          publication_result = collector.result
          if (
            publication_result is None and cached is not None and current_native and cached[1][0].profile is None
            and cached[2] == ((raw_context, active_key, collector.physical_context,
                               collector.adapter.envelope.prior_full_profile_sha256)
                              if getattr(collector.adapter, 'event_collection', False)
                              else (raw_context, active_key, collector.physical_context))
          ):
            publication_result = cached[1][0]
          message = result_message(publication_result, collector.session, publication_sequence, now, replay_validation=collector.last_validation)
          persistence.save_current(collector, now_ns=now, source_epoch=source.source_epoch, reset=source.reset)
        else:
          message = messaging.new_message('autoSteeringLearning')
          value = message.autoSteeringLearning.learning
          value.version, value.status, value.reason, value.family = 1, 'unavailable', unavailable_reason, 'runtimeProfile'
          value.observedMonoTime, value.validUntilMonoTime = now, now + 500_000_000
          message.valid = True
        if publication_source_reader is not None:
          valid_publication_source, publication_now = source_current()
          if not valid_publication_source:
            # A reset/manual/vehicle/calibration transition must discard the
            # already prepared admission, never attach it to a new receipt.
            message = result_message(None, 'unavailable', publication_sequence, publication_now)
            message.autoSteeringLearning.learning.status = 'unavailable'
            message.autoSteeringLearning.learning.reason = 'publication_source_changed_or_unavailable'
          message.logMonoTime = publication_now
        write_source_receipt(message, source)
        pm.send('autoSteeringLearning', message)
        if reporter is not None:
          cached = cached_reports.get(active_key)
          reporter.publish(now_ns=now, message=message, collector=collector, source=source, objective=active_key,
            pending=fitter.child is not None, native_current=current_native,
            fit_result=None if cached is None else cached[1][0])
  finally:
    fitter.close('learner_parent_exit')


def main():
  # Imports belong only to the separate optional process. No workerthread/GIL
  # shared with realtime controller processes, no independent selection read.
  from openpilot.starpilot.flm.runtime_adapter_registry import (
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
  from openpilot.starpilot.flm.calibration_lifecycle import ProducerCalibrationLifecycle
  calibration_lifecycle = ProducerCalibrationLifecycle()

  def calibration_frame(now):
    stamp = int(sm.logMonoTime['extrinsicsCalibration'])
    receipt = int(sm.recv_time['extrinsicsCalibration'] * 1e9)
    current = bool(sm.all_checks(['extrinsicsCalibration']) and
      0 < stamp <= now <= stamp + 500_000_000 and
      0 < receipt <= now <= receipt + 500_000_000)
    return calibration_lifecycle.observe(sm['extrinsicsCalibration'], current=current)

  def current_source(now, frame):
    return read_source(CP, params, now_ns=now, cp_sha256=cp_sha256,
      calibration=() if frame is None else frame[1], vehicle_session=vehicle_session,
      calibration_generation='' if frame is None else frame[0])

  def source_reader(now):
    # Observe resets on every loop, but keep settings reads at receipt-renewal rate.
    frame = calibration_frame(now)
    generation = '' if frame is None else frame[0]
    if (source_cache[0] is None or generation != source_cache[0].calibration_generation or
        now - source_cache[0].observed_ns >= 250_000_000):
      source_cache[0] = current_source(now, frame)
    return source_cache[0]

  def publication_source_reader(now):
    # The regular 250ms read cache and independent 250ms publication cadence
    # can publish a receipt already330ms old; a normal next interval then
    # crosses its original500ms deadline. Read the actual snapshot here after
    # fitting/persistence work instead of extending that old observation.
    source_cache[0] = current_source(now, calibration_frame(now))
    return source_cache[0]

  def current_sources(identity, epoch):
    now = time.monotonic_ns()
    current = current_source(now, calibration_frame(now))
    return (identity if persistent_unit and epoch == current.source_epoch else '', current.enabled, current.manual, current.reset)

  from openpilot.starpilot.flm.training_report import TrainingReporter

  try:
    reporter = TrainingReporter(CP.carFingerprint)
  except (OSError, ValueError):
    reporter = None

  def current_adapter(cp, evidence, key):
    return production_adapter_for_evidence(cp, evidence, key, source=source_reader(time.monotonic_ns()))

  persistence = PersistenceModule(params, current_sources)
  run(
    CP,
    sm,
    control_socket,
    applied_socket,
    pm,
    current_adapter,
    partial(physical_observer, distinguish_pending=True),
    source_reader,
    collection_keys,
    objective_key,
    decode_fit_result,
    persistence,
    FitProcess(),
    adapter_for_ford,
    reporter=reporter,
    publication_source_reader=publication_source_reader,
  )


if __name__ == '__main__':
  main()
