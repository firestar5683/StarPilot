from openpilot.starpilot.favorites.actions import SET_SPEED, mapped_actions
from openpilot.starpilot.favorites.owner import FavoritesOwner
from openpilot.starpilot.galaxy.settings import SettingsGateway


class FavoritesGateway:
  def __init__(self, params, context=None):
    self.settings = SettingsGateway(params, context)
    self.owner = FavoritesOwner(params, self.actions, lambda: True)

  def close(self):
    self.settings.close()

  def actions(self):
    context = self.settings.context.sample()
    return mapped_actions(lambda page: self.settings._state(page, context), lambda _request: False,
                          lambda: self.settings._state("appearance", context), lambda _request: False)

  def snapshot(self):
    return project_snapshot(self.owner.snapshot())

  def save(self, payload, *, session_valid):
    if type(payload) is not dict or set(payload) != {"revision", "slots"}:
      raise ValueError("Invalid Quick Select request")
    return project_snapshot(self.owner.save(payload["slots"], payload["revision"], authorized=session_valid))


def project_snapshot(snapshot):
  return {
    "slots": [{"enabled": slot.enabled, "show_onroad": slot.show_onroad, "key": slot.key, "label": slot.label[:32],
               **({"value": slot.value} if slot.key == SET_SPEED else {})} for slot in snapshot.slots],
    "states": [{"index": slot.index, "kind": slot.kind, "stateLabel": slot.state_label,
                "available": slot.available, "reason": slot.reason} for slot in snapshot.slots],
    "options": [{"key": option.key, "label": option.label, "kind": option.kind, "section": option.section,
                 "stateLabel": option.state_label, "available": option.available, "reason": option.reason} for option in snapshot.options],
    "revision": snapshot.revision, "editable": snapshot.configurable, "valid": snapshot.valid,
  }
