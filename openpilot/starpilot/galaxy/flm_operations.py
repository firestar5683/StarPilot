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
  if operation == 'start':
    names = fields.get('segments')
    if set(fields) != {'segments'} or type(names) is not list:
      raise ValueError('Invalid segment selection')
    if (not 1 <= len(names) <= 5 or any(type(name) is not str or len(name) > 180 or
                                     SEGMENT_NAME.fullmatch(name) is None for name in names) or
        len(set(names)) != len(names)):
      raise ValueError('Select one to five distinct closed segments')
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
    self.owner = owner if owner is not None else FlmAnalysisOwner(root=root, parked=context.parked)

  def request(self, operation: str, payload: dict | None = None) -> dict:
    if operation == 'status' and payload is None:
      return self.owner.snapshot()
    selected = validate_action(operation, payload)
    if operation == 'start':
      return self.owner.start(tuple(selected['segments']))
    if operation == 'cancel':
      return self.owner.cancel(selected['operationId'])
    return self.owner.report(selected['operationId'])

  def close(self) -> None:
    try:
      self.owner.close()
    finally:
      self.context.close()


def error_status(error: FlmOperationError) -> int:
  return 400 if error.code == 'invalid_request' else (409 if error.code in (
    'busy', 'not_parked', 'operation_changed', 'canceled') else 503)
