"""Galaxy's read-only FLM owner and fresh parked authority lifetime."""

from pathlib import Path
import re

from openpilot.starpilot.flm.operation_owner import FlmAnalysisOwner, FlmOperationError
from openpilot.starpilot.galaxy.drive_history import SEGMENT_NAME


def validate_action(operation: str, payload: object) -> dict:
  if type(payload) is not dict:
    raise ValueError('Invalid FLM operation')
  if any(type(key) is not str for key in payload):
    raise ValueError('Invalid FLM operation')
  fields = {key: value for key, value in payload.items() if type(key) is str}
  if operation == 'live-action':
    if fields.get('action') not in ('save','delete','trial','apply','restore','accept','disable','reset') or type(fields.get('token')) is not str:
      raise ValueError('Invalid live FLM action')
  elif operation in ('start', 'train'):
    names = fields.get('segments')
    if set(fields) != ({'segments'} if operation == 'start' else {'segments', 'token'}) or type(names) is not list:
      raise ValueError('Invalid segment selection')
    if (not 1 <= len(names) <= 5 or any(type(name) is not str or len(name) > 180 or
                                     SEGMENT_NAME.fullmatch(name) is None for name in names) or
        len(set(names)) != len(names)):
      raise ValueError('Select one to five distinct closed segments')
    if operation == 'train' and (type(fields['token']) is not str or re.fullmatch(r'[a-f0-9]{64}', fields['token']) is None):
      raise ValueError('Invalid training source')
  elif operation in ('recommend', 'save-report'):
    required = {'operationId', 'feedback'} | ({'token', 'generatedId', 'id', 'label'} if operation == 'save-report' else set())
    if set(fields) != required or type(fields.get('feedback')) is not dict:
      raise ValueError('Invalid report profile request')
    if (set(fields['feedback']) - {'acceptedDimensions', 'ignoredDimensions'} or
        any(type(values) is not list or len(values) > 128 or any(type(key) is not str or len(key) > 128 for key in values)
            for values in fields['feedback'].values())):
      raise ValueError('Invalid evidence feedback')
    validate_action('report', {'operationId': fields.get('operationId')})
    if operation == 'save-report':
      if (type(fields['generatedId']) is not str or len(fields['generatedId']) > 128 or
          type(fields['id']) is not str or re.fullmatch(r'[a-zA-Z0-9_-]{1,48}', fields['id']) is None or
          type(fields['label']) is not str or not fields['label'].strip() or len(fields['label']) > 80 or
          type(fields['token']) is not str or re.fullmatch(r'[a-f0-9]{64}', fields['token']) is None):
        raise ValueError('Invalid generated profile identity')
  elif operation in ('cancel', 'report'):
    operation_id = fields.get('operationId')
    if (set(fields) != {'operationId'} or type(operation_id) is not str or
        re.fullmatch(r'[0-9a-f]{32}:[1-9][0-9]{0,15}', operation_id) is None):
      raise ValueError('Invalid operation identity')
  else:
    raise ValueError('Invalid FLM operation')
  return fields


class FlmOperations:
  def __init__(self, root: Path, *, context=None, owner=None):
    if context is None:
      from openpilot.common.params import Params
      from openpilot.starpilot.galaxy.settings import LiveContextSource
      context = LiveContextSource(Params())
    self.context = context
    self.live = None
    self._training_session = None
    self.owner = owner if owner is not None else FlmAnalysisOwner(root=root, parked=context.parked, completed=self._record_progress)

  def request(self, operation: str, payload: dict | None = None, *, session_valid=lambda: True, session_guard=None) -> dict:
    if operation in ("live", "live-action"):
      if self.live is None:
        from openpilot.common.params import Params
        from openpilot.starpilot.flm.operation_owner import FlmTrialOwner
        self.live = FlmTrialOwner(self.context.params if hasattr(self.context, "params") else Params(), self.context)
      if operation == "live" and payload is None:
        return self.live.snapshot()
      validate_action(operation,payload)
      return self.live.action(payload,session_valid=session_valid)
    if operation in ('train', 'recommend', 'save-report'):
      selected = validate_action(operation, payload)
      if self.live is None:
        self.request('live')
      if not session_valid():
        raise FlmOperationError('not_parked')
      if operation == 'train':
        context = self.live.training_context(selected['token'])
        previous = self._training_session
        self._training_session = (context['sourceToken'], session_valid, session_guard)
        try:
          return self.owner.start(tuple(selected['segments']), gm_context=context)
        except Exception:
          self._training_session = previous
          raise
      evidence = self.owner.report(selected['operationId']).get('gmEvidence')
      if evidence is None:
        raise ValueError('This report has no GM trial profiles')
      from openpilot.starpilot.flm.gm_recommend import build_report
      regenerated = build_report(evidence['context'], evidence['summaries'], evidence['stats'], feedback=selected['feedback'])
      if operation == 'recommend':
        return {'version': 1, 'operationId': selected['operationId'], 'recommendation': regenerated}
      return self.live.save_generated(regenerated, selected['generatedId'], selected['id'], selected['label'],
                                      selected['token'], session_valid=session_valid)
    if operation == 'status' and payload is None:
      return self.owner.snapshot()
    selected = validate_action(operation, payload)
    if operation == 'start':
      return self.owner.start(tuple(selected['segments']))
    if operation == 'cancel':
      return self.owner.cancel(selected['operationId'])
    return self.owner.report(selected['operationId'])

  def _record_progress(self, report):
    session = self._training_session
    if (self.live is None or session is None or session[2] is None or
        report['gmEvidence']['context']['sourceToken'] != session[0]):
      return False
    # HTTP cancel joins the monitor while holding this same guard. Optional
    # progress metadata must decline a busy guard, never wait behind cancel.
    guard = session[2]
    if not guard.acquire(blocking=False):
      return False
    try:
      with self.owner.completion_guard(report['operationId']) as current:
        return current and session[1]() and self.live.record_cleanup(report, session_valid=session[1])
    finally:
      guard.release()

  def close(self) -> None:
    try:
      self.owner.close()
    finally:
      self.context.close()


def error_status(error: FlmOperationError) -> int:
  return 400 if error.code == 'invalid_request' else (409 if error.code in (
    'busy', 'not_parked', 'operation_changed', 'canceled') else 503)
