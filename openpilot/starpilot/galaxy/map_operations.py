"""Authenticated HTTP projection of the single parked map-operation owner.

This adapter owns no processes or map files. Download authority and lifecycle
stay in the manager child, shared by native UI and Galaxy.
"""

import re


class MapOperationError(Exception):
  def __init__(self, status: int, code: str):
    super().__init__(code)
    self.status = status
    self.code = code


def validate_action(operation: str, payload: object) -> dict:
  if type(payload) is not dict:
    raise ValueError('Invalid map operation')
  if any(type(key) is not str for key in payload):
    raise ValueError('Invalid map operation')
  fields = {key: value for key, value in payload.items() if type(key) is str}
  if operation == 'start':
    region = fields.get('regionToken')
    generation = fields.get('expectedCurrentGeneration')
    transfer = fields.get('maxTransferBytes')
    disk = fields.get('maxNewDiskBytes')
    if (set(fields) != {'regionToken', 'maxTransferBytes', 'maxNewDiskBytes', 'expectedCurrentGeneration'} or
        type(region) is not str or not 1 <= len(region) <= 128 or
        type(generation) is not str or re.fullmatch(r'(?:[0-9a-f]{64})?', generation) is None or
        type(transfer) is not int or not 0 < transfer <= 8 << 30 or
        type(disk) is not int or not 0 < disk <= 16 << 30):
      raise ValueError('Invalid map start')
  elif operation == 'cancel':
    operation_id = fields.get('operationId')
    if (set(fields) != {'operationId'} or type(operation_id) is not str or
        re.fullmatch(r'[a-zA-Z0-9_:-]{1,80}', operation_id) is None):
      raise ValueError('Invalid map cancellation')
  else:
    raise ValueError('Invalid map action')
  return {'version': 1, 'op': operation, **fields}


class MapOperations:
  def __init__(self, request=None):
    self._request = request

  def request(self, operation: str, payload: dict | None = None) -> dict:
    if operation in ('catalog', 'status', 'setup') and payload is None:
      command = {'version': 1, 'op': operation}
    else:
      command = validate_action(operation, payload)
    try:
      if self._request is None:
        from openpilot.starpilot.maps.operation_owner import request_operation
        self._request = request_operation
      response = self._request(command)
      if (type(response) is not dict or type(response.get('version')) is not int or response['version'] != 1 or
          type(response.get('ok')) is not bool):
        raise ValueError('Invalid owner response')
      if response['ok']:
        if set(response) != {'version', 'ok', 'result'} or type(response['result']) is not dict:
          raise ValueError('Invalid owner result')
        return response['result']
      owner_error = response.get('error')
      if (set(response) != {'version', 'ok', 'error'} or type(owner_error) is not dict or
          type(owner_error.get('code')) is not str or re.fullmatch(r'[a-z_]{1,64}', owner_error['code']) is None):
        raise ValueError('Invalid owner error')
    except (OSError, RuntimeError, ValueError) as error:
      raise MapOperationError(503, 'owner_unavailable') from error
    code = owner_error['code']
    status = 400 if code in ('invalid_request', 'invalid_region', 'invalid_budget') else (
      409 if code in ('busy', 'selection_changed', 'not_parked', 'operation_changed') else 503)
    raise MapOperationError(status, code)
