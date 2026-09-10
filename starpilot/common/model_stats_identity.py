"""Loaded-content identity only: no selected Params or inference-loop hashing.

Without a loaded-content digest the revision is deliberately isolated
by load UUID. All-time UI totals aggregate model IDs; raw configurations retain
this uncertainty and never pretend that a filename identifies immutable weights.
"""
import hashlib
import json
import uuid


class LoadedDigest:
  """Hash bytes consumed by pickle/OOB loading, never reopen a mutable filename.

  Only the load path uses this wrapper; there is no hashing during inference.
  Instrumentation errors disable provenance rather than aborting model loading.
  """
  def __init__(self, source):
    self.source = source
    self.digest = hashlib.sha256()

  def _record(self, data):
    try:
      if self.digest is not None:
        self.digest.update(data)
    except Exception:
      self.digest = None

  def read(self, size=-1):
    data = self.source.read(size)
    self._record(data)
    return data

  def readline(self, size=-1):
    data = self.source.readline(size)
    self._record(data)
    return data

  def readinto(self, buffer):
    size = self.source.readinto(buffer)
    if size:
      self._record(memoryview(buffer)[:size])
    return size

  def apply(self, identity):
    try:
      if self.digest is not None and identity is not None:
        identity.update(artifact='loaded-sha256:' + self.digest.hexdigest(), artifactVerified=True)
    except Exception:
      pass


def loaded_identity(model_id, external):
  return {'modelId': model_id, 'backend': 'chestnut' if external else 'comma',
          'artifact': 'unverified-load:' + uuid.uuid4().hex, 'artifactVerified': False}


def output_identity(model, longitudinal=None):
  roles = [model.stats_identity]
  if longitudinal is not None:
    roles.append(longitudinal.stats_identity)
  return json.dumps({'version': 1, 'roles': roles}, sort_keys=True, separators=(',', ':'))


def publish_identity(message, model_message, model, longitudinal=None):
  # Statistics must never prevent model/control publication, even with an old
  # schema or instrumentation failure. The observer treats empty provenance as a gap.
  try:
    message.starpilotModelV2.runtimeIdentity = output_identity(model, longitudinal)
    message.starpilotModelV2.modelMonoTime = model_message.logMonoTime
    message.valid = model_message.valid
  except Exception:
    pass
