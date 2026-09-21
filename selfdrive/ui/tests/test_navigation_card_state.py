from types import SimpleNamespace

from openpilot.selfdrive.ui.onroad.starpilot import navigation_card


def test_navigation_card_expires_with_its_control_hint(monkeypatch):
  now = [100.0]
  monkeypatch.setattr("time.monotonic", lambda: now[0])
  state = {"valid": True, "updatedAtMonotonic": 100.0, "maneuverDistance": 10.0, "maneuverPrimaryText": "Turn right"}
  params = SimpleNamespace(get_bool=lambda key: True, get=lambda key: "destination")
  memory = SimpleNamespace(get=lambda key: state)
  monkeypatch.setattr(navigation_card, "ui_state", SimpleNamespace(ui_params=params, params_memory=memory, is_metric=True))
  card = navigation_card.NavigationCardRenderer.__new__(navigation_card.NavigationCardRenderer)
  card._collapsed_param_supported = False
  card._collapsed_fallback = False

  card._update_state()
  assert card._valid
  now[0] = 103.0
  card._update_state()
  assert not card._valid
  state["updatedAtMonotonic"] = now[0]
  card._update_state()
  assert card._valid
  state["maneuverDistance"] = float("nan")
  card._update_state()
  assert not card._valid
