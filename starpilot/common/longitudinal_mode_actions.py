"""Shared explicit speed-control actions; never write individual mode flags here."""
import json
from threading import Lock, Thread
from time import monotonic
from urllib.request import ProxyHandler, Request, build_opener

PREFIX = "__starpilot_favorite_action__:longitudinal_"
MODE_ORDER = ("chill", "experimental", "conditional_experimental", "conditional_chill")
ACTION_TARGETS = {PREFIX + "cycle": None, **{PREFIX + mode: mode for mode in MODE_ORDER}}
ACTION_LABELS = {
  PREFIX + "cycle": "Cycle Speed Control Mode",
  PREFIX + "chill": "Speed Control: Chill",
  PREFIX + "experimental": "Speed Control: Experimental",
  PREFIX + "conditional_experimental": "Speed Control: CEM",
  PREFIX + "conditional_chill": "Speed Control: CCM",
}
LEGACY_MODE_ACTIONS = {
  "ExperimentalMode": PREFIX + "experimental",
  "ConditionalExperimental": PREFIX + "conditional_experimental",
  "ConditionalChill": PREFIX + "conditional_chill",
}
ACTION_OPTIONS = tuple({
  "key": key, "label": ACTION_LABELS[key], "section": "Longitudinal",
  "description": ("Cycles Chill → Experimental → Conditional Experimental (CEM) → Conditional Chill (CCM)."
                  if target is None else f"Selects {dict(zip(MODE_ORDER, ('Chill', 'Experimental', 'Conditional Experimental (CEM)', 'Conditional Chill (CCM)')))[target]} speed control."),
  "action": "longitudinalMode",
} for key, target in ACTION_TARGETS.items())


def resolve_action_target(key, current):
  if key not in ACTION_TARGETS or current not in MODE_ORDER:
    raise ValueError("Unknown speed control action or mode")
  return ACTION_TARGETS[key] or MODE_ORDER[(MODE_ORDER.index(current) + 1) % len(MODE_ORDER)]


_PENDING = Lock()


def _post_action(key, deadline, on_result=None):
  # Bounded, non-queued and no retry: an uncertain reply must not cycle again.
  opener = build_opener(ProxyHandler({}))
  with opener.open(Request("http://127.0.0.1:8082/api/longitudinal_mode", headers={"Cache-Control": "no-store"}), timeout=1.0) as response:
    state = json.load(response)
  if state.get("locked") is not False or state.get("mode") not in MODE_ORDER or monotonic() >= deadline:
    return False
  # Existing boolean assignments keep their toggle behavior and stored keys.
  # Route their writes through the same coherent transaction as new actions.
  if key in LEGACY_MODE_ACTIONS:
    values = state.get("values", {})
    if type(values.get(key)) is not bool:
      return False
    key = PREFIX + "chill" if values[key] else LEGACY_MODE_ACTIONS[key]
  body = {"key": key, "expires_at": deadline, "expected": state.get("values"), "acknowledged": True}
  request = Request("http://127.0.0.1:8082/api/favorites/action", data=json.dumps(body).encode(),
                    headers={"Content-Type": "application/json"}, method="POST")
  with opener.open(request, timeout=1.0) as response:
    result = json.load(response)
    confirmed = result.get("mode") in MODE_ORDER
    if confirmed and on_result is not None:
      on_result(result["mode"])
    return confirmed


def request_mode_action(key, *, on_result=None):
  """Queue at most one immediate request off the HID/native render thread.

  True means dispatched, not activated. Galaxy enforces current safety/capability
  and coherent writes; native mode indicators remain authoritative readback.
  """
  if (key not in ACTION_TARGETS and key not in LEGACY_MODE_ACTIONS) or not _PENDING.acquire(blocking=False):
    return False
  deadline = monotonic() + 1.0

  def send():
    try:
      if on_result is None:
        _post_action(key, deadline)
      elif not _post_action(key, deadline, on_result):
        on_result(None)
    except Exception:
      # No fallback Params writes and no retry after a failed/uncertain request.
      if on_result is not None:
        on_result(None)
    finally:
      _PENDING.release()

  try:
    Thread(target=send, name="speed-control-action", daemon=True).start()
  except Exception:
    _PENDING.release()
    return False
  return True
