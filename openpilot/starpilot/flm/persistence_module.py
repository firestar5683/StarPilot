"""Separate learner-process persistence hooks; no fit/receipt restored from disk."""

from openpilot.starpilot.flm.learned_lifecycle import ProducerPersistence


class PersistenceModule:
  def __init__(self, params, current_sources):
    self.owner = ProducerPersistence(params)
    self.current_sources = current_sources

  def attach_prior(self, collector, *, identity, source_epoch, reset):
    adapter = collector.adapter
    current = tuple(adapter.parameters())
    schemas = tuple(adapter.prior_schemas()) if hasattr(adapter, 'prior_schemas') else (current,)
    if not 1 <= len(schemas) <= 3 or any(not 1 <= len(schema) <= 8 for schema in schemas):
      collector.restore_prior(None)
      return False
    for schema in schemas:
      parameters = tuple(schema)
      prior = self.owner.prior(identity=identity, parameters=parameters, reset=reset, current_sources=lambda: self.current_sources(identity, source_epoch))
      if prior is None:
        continue
      if parameters != current:
        if not hasattr(adapter, 'select_prior_schema') or not adapter.select_prior_schema(parameters):
          continue
      if tuple(adapter.parameters()) != parameters:
        collector.restore_prior(None)
        return False
      collector.restore_prior(prior)
      return True
    collector.restore_prior(None)
    return False

  def save_current(self, collector, *, now_ns, source_epoch, reset):
    if collector.result is None or collector.result.profile is None or collector.last_validation is None:
      return False
    profile = collector.result.profile
    return self.owner.update(
      profile, collector.last_validation, now_ns=now_ns, reset=reset, current_sources=lambda: self.current_sources(profile.identity, source_epoch)
    )
