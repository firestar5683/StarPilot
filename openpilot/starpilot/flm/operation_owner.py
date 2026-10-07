"""One parked, read-only FLM operation with an isolated local-log worker."""

from collections.abc import Callable, Sequence
from contextlib import contextmanager
import json
import logging
import os
from pathlib import Path
import selectors
import subprocess
import sys
import threading
import time
import uuid

from openpilot.common.hardware.hw import Paths
from openpilot.starpilot.galaxy.drive_history import SEGMENT_NAME


MAX_REPORT_BYTES = 1024 * 1024
MAX_PIPE_BYTES = MAX_REPORT_BYTES + 4096
WALL_DEADLINE_SECONDS = 5 * 60
POLL_SECONDS = 0.05
ACTIVE_STATE = 'running'
ERROR_CODES = frozenset(('invalid_request', 'busy', 'not_parked', 'operation_changed', 'unavailable',
                         'canceled', 'process_failed', 'deadline', 'recording_unavailable', 'decode_failed', 'resource_limit'))


class FlmOperationError(RuntimeError):
  def __init__(self, code: str):
    self.code = code if code in ERROR_CODES else 'unavailable'
    super().__init__(self.code)


def _stop_child(child: subprocess.Popen) -> None:
  if child.poll() is not None:
    child.wait()
    return
  try:
    child.terminate()
  except ProcessLookupError:
    pass
  try:
    child.wait(timeout=0.5)
  except subprocess.TimeoutExpired:
    try:
      child.kill()
    except ProcessLookupError:
      pass
    try:
      child.wait(timeout=0.5)
    except subprocess.TimeoutExpired as error:
      raise FlmOperationError('unavailable') from error


class FlmAnalysisOwner:
  """Parent alone owns fresh parked authority, operation identity and report visibility."""

  def __init__(self, *, parked: Callable[[], bool], root: Path | None = None,
               worker_argv: Sequence[str] | None = None, completed: Callable[[dict], bool] | None = None):
    self.root = Path(Paths.log_root()) if root is None else root
    self._parked = parked
    self._completed = completed
    self._worker_argv = tuple(worker_argv) if worker_argv is not None else (
      sys.executable, '-m', 'openpilot.starpilot.flm.operation_worker')
    self._lock = threading.RLock()
    self._session = uuid.uuid4().hex
    self._sequence = 0
    self._closed = False
    self._cancel = threading.Event()
    self._child: subprocess.Popen | None = None
    self._monitor_thread: threading.Thread | None = None
    self._report: dict | None = None
    self._status = self._fresh_status('idle', None, 0)

  @staticmethod
  def _fresh_status(state: str, operation_id: str | None, selected: int, processed: int = 0,
                    error_code: str | None = None) -> dict:
    return {'version': 1, 'operationId': operation_id, 'state': state, 'selected': selected,
            'processed': processed, 'errorCode': error_code}

  def _allowed(self) -> bool:
    try:
      return self._parked() is True
    except Exception:
      return False

  def _revoke_if_unparked(self) -> None:
    if self._allowed():
      return
    with self._lock:
      if self._status['state'] != 'idle':
        self._status = self._fresh_status('unavailable', self._status['operationId'],
                                          self._status['selected'], self._status['processed'], 'not_parked')
        self._report = None
        self._cancel.set()

  def snapshot(self) -> dict:
    self._revoke_if_unparked()
    with self._lock:
      return dict(self._status)

  def start(self, segment_names: Sequence[str], *, gm_context: dict | None = None) -> dict:
    if (type(segment_names) not in (tuple, list) or not 1 <= len(segment_names) <= 5 or
        any(type(name) is not str or len(name) > 180 or SEGMENT_NAME.fullmatch(name) is None
            for name in segment_names) or len(set(segment_names)) != len(segment_names)):
      raise FlmOperationError('invalid_request')
    if gm_context is not None:
      from openpilot.starpilot.flm.gm_recommend import validate_context
      gm_context = json.loads(json.dumps(validate_context(gm_context), allow_nan=False))
    if not self._allowed():
      raise FlmOperationError('not_parked')
    with self._lock:
      if self._closed:
        raise FlmOperationError('unavailable')
      if self._status['state'] == ACTIVE_STATE or self._child is not None or \
         (self._monitor_thread is not None and self._monitor_thread.is_alive()):
        raise FlmOperationError('busy')
      self._sequence += 1
      token = f'{self._session}:{self._sequence}'
      self._cancel = threading.Event()
      self._report = None
      self._status = self._fresh_status(ACTIVE_STATE, token, len(segment_names))
      request_value = {'root': str(self.root), 'segments': list(segment_names), 'parentPid': os.getpid()}
      if gm_context is not None:
        request_value['gmContext'] = gm_context
      request = json.dumps(request_value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()
      if len(request) > (32768 if gm_context is not None else 2048):
        self._status = self._fresh_status('failed', token, len(segment_names), error_code='invalid_request')
        raise FlmOperationError('invalid_request')
      # The monitor must create the child: Linux PR_SET_PDEATHSIG follows the
      # creating thread, and an HTTP request thread ends after this response.
      self._monitor_thread = threading.Thread(target=self._monitor, args=(token, self._cancel,
                                                                           tuple(segment_names), request, gm_context), daemon=True)
      try:
        self._monitor_thread.start()
      except RuntimeError as error:
        self._monitor_thread = None
        self._status = self._fresh_status('failed', token, len(segment_names), error_code='unavailable')
        raise FlmOperationError('unavailable') from error
    self._revoke_if_unparked()
    return self.snapshot()

  def _monitor(self, token: str, canceled: threading.Event, names: tuple[str, ...], request: bytes,
               gm_context: dict | None = None) -> None:
    result: dict | None = None
    error: str | None = 'process_failed'
    child: subprocess.Popen | None = None
    reaped = False
    try:
      if canceled.is_set():
        error = 'canceled'
        return
      if not self._allowed():
        error = 'not_parked'
        return
      child = subprocess.Popen(self._worker_argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, bufsize=0, close_fds=True)
      with self._lock:
        if self._status['operationId'] == token:
          self._child = child
      if child.stdin is None:
        raise OSError('worker input unavailable')
      child.stdin.write(request)
      child.stdin.close()
      result, error = self._read_worker(token, child, canceled, names)
      if error is None:
        if result is None:
          raise ValueError('missing report')
        sources = result['segments']
        if (result.get('schemaVersion') != 1 or
            result.get('purpose') != ('offline_tracking_diagnostics' if gm_context is None else 'gm_flm_evidence_profiles') or
            result.get('tuneRecommendation', 1) is not None or result.get('vehicleQualification') is not False or
            type(sources) is not list or [row['source']['segmentName'] for row in sources] != list(names)):
          raise ValueError('report shape')
        if gm_context is not None:
          from openpilot.starpilot.flm.gm_recommend import validate_context
          evidence = result.get('gmEvidence')
          if (type(evidence) is not dict or validate_context(evidence['context']) != gm_context or
              evidence.get('fit') is not False or evidence.get('vehicleQualification') is not False):
            raise ValueError('GM report source')
        result = {**result, 'operationId': token}
        if len(json.dumps(result, allow_nan=False).encode()) > MAX_REPORT_BYTES:
          raise ValueError('report limit')
    except Exception:
      logging.exception('FLM operation failed')
      error = 'process_failed'
    finally:
      if child is not None:
        try:
          _stop_child(child)
          reaped = True
        except (OSError, FlmOperationError):
          error = 'unavailable'
        for pipe in (child.stdin, child.stdout):
          if pipe is None:
            continue
          try:
            pipe.close()
          except OSError:
            error = 'unavailable'
      else:
        reaped = True
      if not self._allowed():
        error = 'not_parked'
      # Completion effects acquire the HTTP effect guard before this owner's
      # lock. Never invoke a callback while holding the owner lock.
      if error is None and not canceled.is_set() and reaped and gm_context is not None and self._completed is not None:
        try:
          result['gmEvidence']['progressRecorded'] = self._completed(result) is True
        except Exception:
          logging.exception('FLM cleanup progress was not recorded')
          result['gmEvidence']['progressRecorded'] = False
      with self._lock:
        if self._status['operationId'] == token:
          if self._closed or self._status['state'] == 'unavailable' or not self._allowed():
            error = 'not_parked' if not self._closed else 'unavailable'
          if error is None and not canceled.is_set() and reaped:
            self._report = result
            self._status = self._fresh_status('completed', token, len(names), len(names))
          else:
            code = 'unavailable' if self._closed else \
                   'canceled' if canceled.is_set() and error != 'not_parked' else error or 'canceled'
            unavailable = code in ('not_parked', 'unavailable', 'recording_unavailable', 'decode_failed', 'resource_limit')
            state = 'canceled' if code == 'canceled' else 'unavailable' if unavailable else 'failed'
            self._status = self._fresh_status(state, token, len(names), self._status['processed'], code)
            self._report = None
        if child is not None and self._child is child and reaped:
          self._child = None

  def _read_worker(self, token: str, child: subprocess.Popen, canceled: threading.Event,
                   names: tuple[str, ...]) -> tuple[dict | None, str | None]:
    if child.stdout is None:
      return None, 'process_failed'
    deadline = time.monotonic() + WALL_DEADLINE_SECONDS
    buffer = bytearray()
    consumed = 0
    result = None
    error = None
    with selectors.DefaultSelector() as selector:
      selector.register(child.stdout, selectors.EVENT_READ)
      while error is None:
        if canceled.is_set():
          return None, 'canceled'
        if not self._allowed():
          return None, 'not_parked'
        if time.monotonic() >= deadline:
          return None, 'deadline'
        if not selector.select(POLL_SECONDS):
          continue
        chunk = os.read(child.stdout.fileno(), 64 * 1024)
        if not chunk:
          break  # Pipe EOF; wait only a bounded time for the child to exit.
        consumed += len(chunk)
        if consumed > MAX_PIPE_BYTES:
          return None, 'process_failed'
        buffer.extend(chunk)
        while b'\n' in buffer:
          line, _, remainder = buffer.partition(b'\n')
          buffer = bytearray(remainder)
          message = json.loads(line)
          if type(message) is not dict:
            return None, 'process_failed'
          if message.get('kind') == 'progress' and type(message.get('processed')) is int and \
             0 < message['processed'] <= len(names):
            with self._lock:
              if self._status['operationId'] == token and self._status['state'] == ACTIVE_STATE:
                self._status['processed'] = max(self._status['processed'], message['processed'])
          elif message.get('kind') == 'result' and type(message.get('report')) is dict:
            result = message['report']
          elif message.get('kind') == 'error' and message.get('code') in (
            'unavailable', 'process_failed', 'recording_unavailable', 'decode_failed', 'resource_limit',
          ):
            error = message['code']
          else:
            return None, 'process_failed'
          if error is not None:
            break
    if error is not None:
      return None, error
    if buffer or child.wait(timeout=0.5) != 0 or result is None:
      return None, 'process_failed'
    return result, None

  def report(self, operation_id: str) -> dict:
    self._revoke_if_unparked()
    with self._lock:
      if self._closed:
        raise FlmOperationError('unavailable')
      if self._status['operationId'] != operation_id:
        raise FlmOperationError('operation_changed')
      if self._status['state'] != 'completed' or self._report is None:
        raise FlmOperationError(self._status['errorCode'] or 'unavailable')
      return json.loads(json.dumps(self._report, allow_nan=False))

  @contextmanager
  def completion_guard(self, operation_id: str):
    # Called only after the shared HTTP effect guard, and retained through the
    # optional metadata commit so cancel/close cannot retire this operation
    # between its final authority check and document replacement.
    with self._lock:
      yield (self._status['operationId'] == operation_id and self._status['state'] == ACTIVE_STATE and
             not self._closed and not self._cancel.is_set() and self._allowed())

  def cancel(self, operation_id: str) -> dict:
    self._revoke_if_unparked()
    with self._lock:
      if self._status['operationId'] != operation_id:
        raise FlmOperationError('operation_changed')
      if self._status['state'] != ACTIVE_STATE:
        return dict(self._status)
      self._cancel.set()
      thread = self._monitor_thread
    if thread is not None:
      thread.join(timeout=1.5)
      if thread.is_alive():
        with self._lock:
          child = self._child
        if child is not None:
          _stop_child(child)
        thread.join(timeout=0.5)
    return self.snapshot()

  def close(self) -> None:
    with self._lock:
      self._closed = True
      self._cancel.set()
      thread = self._monitor_thread
    if thread is not None:
      thread.join(timeout=1.5)
    with self._lock:
      child = self._child
    if child is not None:
      _stop_child(child)
    with self._lock:
      self._report = None
      if self._status['state'] != 'idle':
        self._status = self._fresh_status('unavailable', self._status['operationId'],
                                          self._status['selected'], self._status['processed'], 'unavailable')

class FlmTrialOwner:
  """Existing FLM namespace's parked exact-source atomic surface editor."""
  def __init__(self, params, context):
    self.params, self.context = params, context

  def _sources(self):
    import hashlib
    from openpilot.starpilot.flm.live import gm_capability
    from openpilot.starpilot.lateral.controller_selection import DOCUMENT_KEY as SELECTION_KEY, selection_from_bytes
    from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY, MAX_DOCUMENT_BYTES, parse_document
    from openpilot.starpilot.saved_source import read_saved
    ctx = self.context.sample()
    raw, readable = read_saved(self.params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    selection_raw, selection_readable = read_saved(self.params, SELECTION_KEY, 4096)
    selection = None if ctx.cp is None or not selection_readable else selection_from_bytes(ctx.cp, selection_raw)
    cap = (None if selection is None or selection.source == 'invalid' else gm_capability(ctx.cp, selection.mode))
    if not readable or cap is None or ctx.cp_raw is None:
      raise FlmOperationError('unavailable')
    try:
      profiles = {} if raw is None else parse_document(raw)
    except (ValueError, TypeError, UnicodeError, OverflowError):
      raise FlmOperationError('unavailable') from None
    guards = []
    for key, limit in (('AdvancedLateralTune', 64), ('ForceAutoTuneOff', 1)):
      value, valid = read_saved(self.params, key, limit)
      guards.append((key, valid, None if value is None else value.hex()))
    token = hashlib.sha256(
      json.dumps(cap,sort_keys=True).encode()+b'\0'+ctx.cp_raw+b'\0'+(raw or b'')+
      b'\0'+(selection_raw or b'')+b'\0'+json.dumps(guards).encode()).hexdigest()
    return ctx, raw, selection_raw, cap, profiles, token

  def snapshot(self):
    from opendbc.car.lateral import FRICTION_THRESHOLD
    from openpilot.starpilot.flm.live import binding_matches
    from openpilot.starpilot.flm.torque_surface import GmFlmBinding, GmSurface, _GM_BOUNDS, _GM_RICH_BOUNDS
    try:
      ctx, _, _, cap, profiles, token = self._sources()
    except FlmOperationError:
      return {'version': 1, 'available': False, 'editable': False}
    profile = profiles.get(cap['fingerprint'])
    state = GmFlmBinding(cap['controller'],cap['policy'],cap['basis']) if profile is None or profile.flm is None else profile.flm
    matched = profile is None or (profile.basis == cap['basis'] and
                                  (profile.flm is None or binding_matches(profile,cap)))
    from openpilot.starpilot.flm.manual_trial import manual_snapshot, manual_profile, manual_preconditions
    from openpilot.starpilot.lateral.torque_settings import PlatformProfile, FieldChoice
    current = profile or PlatformProfile(cap['basis'], FieldChoice(), FieldChoice())
    current_manual = manual_snapshot(current, cap['fingerprint'])
    manual_conflict = state.applied_manual is not None and current_manual != state.applied_manual
    preconditions = {}
    for key, raw in state.manual:
      try:
        preconditions[key] = manual_preconditions(self.params, ctx.cp, cap['controller'],
                                                  manual_profile(raw, cap['fingerprint'], cap['basis']))
      except ValueError:
        preconditions[key] = ['The saved manual controller or geometry basis changed. Review those choices in settings and save again.']
    limits = dict(_GM_BOUNDS)
    limits.update(_GM_RICH_BOUNDS if cap['profile'] == 'gm_bolt_2022_2023' else {'ff_gain_left':(-.4,.6),'ff_gain_right':(-.4,.6)})
    return {'version': 1, 'available': matched, 'editable': bool(ctx.parked and matched),
            'reason': None if matched else ('The selected controller or vehicle basis changed. Reset this surface binding to retain ' +
              'manual choices and edit the current controller.'),
            'manualConflict': manual_conflict, 'manual': current_manual, 'preconditions': preconditions,
            'resettable': bool(ctx.parked and profile is not None and profile.flm is not None), 'token': token,
            'vehicle': cap['fingerprint'], 'controller': cap['controller'], 'profile': cap['profile'],
            'curveDefaults': [FRICTION_THRESHOLD if cap['controller'] == 'standard' else GmSurface(cap['profile'],{}).base_threshold(speed)
                              for speed in (0.,5.,10.,15.,25.)],
            'inactiveKnobs': {'low_speed_angle_assist_max_torque': ('The selected custom Bolt output law excludes universal angle assist. STANDARD consumes ' +
              'this choice.')}
                             if cap['controller'] == 'starpilot' and cap['policy'] == 'bolt' else {},
            'state': state.document(), 'defaults': GmSurface(cap['profile'],{}).document(),
            'knobs': {key:{'min':low,'max':high} for key,(low,high) in limits.items()}}

  def action(self, payload, *, session_valid=lambda: True, generated_manual=None):
    from dataclasses import replace
    import re
    import secrets
    from openpilot.starpilot.flm.live import binding_matches
    from openpilot.starpilot.flm.torque_surface import GmFlmBinding, GmSurface
    from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY, MAX_DOCUMENT_BYTES, PlatformProfile, FieldChoice, serialize_document
    from openpilot.starpilot.saved_document import commit_exact
    if type(payload) is not dict or payload.get('action') not in ('save','delete','trial','apply','restore','accept','disable','reset','record-progress'):
      raise ValueError('Invalid GM FLM action')
    action=payload['action']
    if generated_manual is not None and action != 'save':
      raise ValueError('Wrong generated manual action')
    expected_fields={'action','token'} | (
      {'id','label','surface'} if action=='save' else {'id'} if action in ('delete','trial','apply')
      else {'trial'} if action in ('restore','accept') else set())
    if set(payload)!=expected_fields or type(payload['token']) is not str or re.fullmatch(r'[a-f0-9]{64}',payload['token']) is None:
      raise ValueError('Invalid GM FLM source')
    ctx, raw, selection_raw, cap, profiles, token = self._sources()
    if not ctx.parked or not session_valid():
      raise FlmOperationError('not_parked')
    if payload['token']!=token:
      raise FlmOperationError('operation_changed')
    profile=profiles.get(cap['fingerprint'],PlatformProfile(cap['basis'],FieldChoice(),FieldChoice()))
    if action != 'reset' and (profile.basis != cap['basis'] or
                              profile.flm is not None and not binding_matches(profile,cap)):
      raise FlmOperationError('operation_changed')
    state=profile.flm or GmFlmBinding(cap['controller'],cap['policy'],cap['basis'])
    saved={key:(label,surface) for key,label,surface in state.saved}
    manual = dict(state.manual)
    from openpilot.starpilot.flm.manual_trial import manual_snapshot, manual_profile, manual_preconditions
    current_manual = manual_snapshot(profile, cap['fingerprint'])
    key=payload.get('id')
    if action in ('save','delete','trial','apply') and (type(key) is not str or re.fullmatch(r'[a-zA-Z0-9_-]{1,48}',key) is None):
      raise ValueError('Invalid saved surface identity')
    if action=='save':
      if state.trial is not None and key in (state.active,state.baseline_active):
        raise FlmOperationError('busy')
      surface=GmSurface.from_document(payload['surface'])
      if surface.profile!=cap['profile']:
        raise ValueError('Surface does not match selected controller')
      saved[key]=(payload['label'],surface)
      captured = current_manual if generated_manual is None else generated_manual
      manual_profile(captured, cap['fingerprint'], cap['basis'])
      manual[key] = captured
      state=replace(state,saved=tuple((name,label,surface) for name,(label,surface) in saved.items()), manual=tuple(manual.items()))
    elif action=='delete':
      if key in (state.active,state.baseline_active):
        raise FlmOperationError('busy')
      if key not in saved:
        raise ValueError('Unknown saved surface')
      del saved[key]
      manual.pop(key, None)
      state=replace(state,saved=tuple((name,label,surface) for name,(label,surface) in saved.items()), manual=tuple(manual.items()))
    elif action in ('trial','apply'):
      if key not in saved:
        raise ValueError('Unknown saved surface')
      if state.applied_manual is not None and current_manual != state.applied_manual:
        raise FlmOperationError('operation_changed')
      target_manual = manual.get(key, state.baseline_manual or current_manual)
      target = manual_profile(target_manual, cap['fingerprint'], cap['basis'])
      if manual_preconditions(self.params, ctx.cp, cap['controller'], target):
        raise FlmOperationError('unavailable')
      # Every switch starts from the original owned manual baseline; the saved
      # full canonical snapshot explicitly includes source/default choices.
      baseline_manual = state.baseline_manual if state.trial else current_manual
      old_flm = profile.flm
      profile = replace(target, flm=old_flm)
      state=replace(state,active=key,applied=True,trial=state.trial or secrets.token_hex(16),
                    baseline_active=state.baseline_active if state.trial else state.active,
                    baseline_applied=state.baseline_applied if state.trial else state.applied,
                    baseline_manual=baseline_manual, applied_manual=manual_snapshot(profile,cap['fingerprint']))
    elif action in ('restore','accept'):
      if state.trial is None or payload['trial']!=state.trial:
        raise FlmOperationError('operation_changed')
      if action == 'restore' and state.baseline_manual is not None:
        if current_manual != state.applied_manual:
          # A later explicit manual edit is never silently overwritten. Keep
          # as baseline resolves this conflict without rewriting preferences.
          raise FlmOperationError('operation_changed')
        profile = replace(manual_profile(state.baseline_manual, cap['fingerprint'], cap['basis']), flm=profile.flm)
      state=replace(state,active=state.baseline_active if action=='restore' else state.active,
                    applied=state.baseline_applied if action=='restore' else state.applied,
                    trial=None,baseline_active=None,baseline_applied=False,baseline_manual=None,applied_manual=None)
    elif action=='record-progress':
      state=replace(state, cleanup_progress=True)
    elif action=='disable':
      state=replace(state,active=None,applied=False,trial=None,baseline_active=None,baseline_applied=False,baseline_manual=None,applied_manual=None)
    # One atomic canonical document commit owns only this selected vehicle
    # manual+surface trial; other vehicle preferences are retained unchanged.
    profiles[cap['fingerprint']]=replace(profile,flm=None if action=='reset' else state)
    encoded=serialize_document(profiles)
    def authorized():
      try:
        fresh, fresh_raw, fresh_selection, fresh_cap, _, fresh_token=self._sources()
        return (session_valid() and fresh.parked and fresh.cp_raw==ctx.cp_raw and fresh_raw==raw and
                fresh_selection==selection_raw and fresh_cap==cap and fresh_token==token)
      except FlmOperationError:
        return False
    result=commit_exact(self.params,key=DOCUMENT_KEY,max_bytes=MAX_DOCUMENT_BYTES,raw=encoded,expected=raw,
                        authorized=authorized,temp_prefix='.flm-')
    if not result.committed or not result.verified:
      raise FlmOperationError('operation_changed')
    return self.snapshot()


  def training_context(self, token):
    from openpilot.starpilot.flm.gm_recommend import source_context
    from openpilot.starpilot.lateral.torque_settings import PlatformProfile, FieldChoice
    ctx, _, _, cap, profiles, current = self._sources()
    if not ctx.parked:
      raise FlmOperationError('not_parked')
    if token != current:
      raise FlmOperationError('operation_changed')
    profile = profiles.get(cap['fingerprint'], PlatformProfile(cap['basis'], FieldChoice(), FieldChoice()))
    return source_context(ctx.cp, cap['controller'], self.params, current, profile)

  def save_generated(self, report, generated_id, key, label, token, *, session_valid=lambda: True):
    context = self.training_context(token)
    from openpilot.starpilot.flm.gm_recommend import same_numerical_context
    if not same_numerical_context(context, report['context']):
      raise FlmOperationError('operation_changed')
    matches = [profile for path in report['paths'] for profile in path['profiles'] if profile['id'] == generated_id]
    if len(matches) != 1 or matches[0].get('canonical') is None:
      raise ValueError('Unavailable generated trial')
    selected = matches[0]['canonical']
    return self.action({'action': 'save', 'token': token, 'id': key, 'label': label, 'surface': selected['surface']},
                       generated_manual=selected['manual'], session_valid=session_valid)


  def record_cleanup(self, report, *, session_valid=lambda: False):
    evidence = report.get('gmEvidence')
    if evidence is None or evidence['decision']['primaryPathKey'] != 'cleanup_pass' or evidence['stats']['sampleCount'] <= 0:
      return False
    try:
      source = evidence['context']
      # This callback belongs only to an explicit Generate GM Trials operation.
      # It records original cleanup progression, never applies a tune or writes
      # any global flag. Changed source/unparked authority simply declines it.
      if self.training_context(source['sourceToken']) != source:
        return False
      self.action({'action': 'record-progress', 'token': source['sourceToken']}, session_valid=session_valid)
      return True
    except (ValueError, FlmOperationError):
      return False
