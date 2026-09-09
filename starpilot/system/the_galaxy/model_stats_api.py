"""Read-only Model Manager API. Failure leaves catalog/download controls usable."""
import copy
from pathlib import Path
import threading
import time

from openpilot.starpilot.assets.model_sizes import artifact_size
from openpilot.starpilot.common.model_stats import empty_stats
from openpilot.starpilot.common.model_stats_store import DEFAULT_PATH, read_stats


class ModelStatsAPI:
  def __init__(self, path=DEFAULT_PATH):
    self.path = path
    self.lock = threading.Lock()
    self.cached = None
    self.expires = 0
    self.sizes = {}

  def summary(self):
    with self.lock:
      if self.cached is None or time.monotonic() >= self.expires:
        self.cached = read_stats(self.path, history=False)
        self.expires = time.monotonic() + 2
      return copy.deepcopy(self.cached)

  def size(self, path, declared):
    # Short TTL avoids repeated directory scans on status polls, not stale sizes
    # across completed downloads. Bad metadata is treated as unknown by helper.
    key = (str(path), repr(declared))
    with self.lock:
      cached = self.sizes.get(key)
      if cached is None or time.monotonic() >= cached[0]:
        cached = (time.monotonic() + 2, artifact_size(path, declared))
        if len(self.sizes) > 1000:
          self.sizes.clear()
        self.sizes[key] = cached
      return dict(cached[1])

  def annotate(self, models, models_path, builtin_path, metadata, accelerator_filename):
    summary = self.summary()
    for model in models:
      key = model['value']
      entry = metadata.get(key, {})
      entry = entry if isinstance(entry, dict) else {}
      path = builtin_path if model['builtin'] else Path(models_path) / f'{key}_driving_tinygrad.pkl'
      model.update(self.size(path, entry.get('artifact_size')))
      stored = summary['models'].get(key)
      empty_status = 'ok' if summary['available'] else summary['status']
      if summary['trackingStatus'] == 'telemetry_unavailable':
        empty_status = 'telemetry_unavailable'
      model['stats'] = stored['stats'] if stored else empty_stats(empty_status)
      model['stats']['trackingStatus'] = summary['trackingStatus']
      model['stats']['recordedSince'] = summary['recordedSince']
      configurations = stored['configurations'] if stored else []
      model['stats']['revisionStatus'] = ('verified_loaded_content' if configurations and
                                         all(role.get('artifactVerified') for c in configurations for role in c['roles'])
                                         else 'unverified_loaded_runs')
      model['stats']['usedInPairs'] = any(key in pair['modelIds'] for pair in summary['pairs'])
      variants = entry.get('accelerator_artifacts', {})
      variant = variants.get('chestnut') if isinstance(variants, dict) else None
      if isinstance(variant, dict):
        model['modelLabFileSize'] = self.size(Path(models_path) / accelerator_filename(key), variant.get('artifact_size'))
    return models


def register_model_stats_api(app, path=DEFAULT_PATH):
  from flask import jsonify, request
  service = ModelStatsAPI(path)

  @app.route('/api/models/stats', methods=['GET'])
  def model_stats():
    try:
      if set(request.args) - {'model', 'mode', 'period', 'limit', 'offset'}:
        raise ValueError('Unsupported statistics filter')
      period = request.args.get('period', 'all')
      model = request.args.get('model')
      if model is not None and (not model or len(model) > 256):
        raise ValueError('Invalid model ID')
      payload = read_stats(service.path, model=model, mode=request.args.get('mode', 'all'), period=period,
                           limit=int(request.args.get('limit', '50')), offset=int(request.args.get('offset', '0')))
      return jsonify(payload)
    except ValueError as error:
      return jsonify({'error': str(error)}), 400

  return service
