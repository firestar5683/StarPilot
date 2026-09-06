"""Nonblocking native client of Galaxy's serialized, guarded mode adapter.

No Params writes here: the endpoint also publishes StarPilot toggles, verifies
writes and rejects stale snapshots. Never retry a PUT after an uncertain result.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from time import monotonic
from urllib.request import Request, build_opener, ProxyHandler

from openpilot.starpilot.system.the_galaxy.longitudinal_mode import MODE_KEYS, selected_mode

MODE_LABELS = {
  "chill": "Chill",
  "experimental": "Experimental",
  "conditional_experimental": "Conditional Experimental",
  "conditional_chill": "Conditional Chill",
}


def request_mode(body=None):
  request = Request("http://127.0.0.1:8082/api/longitudinal_mode",
                    data=None if body is None else json.dumps(body).encode(),
                    headers={"Content-Type": "application/json", "Cache-Control": "no-store"},
                    method="GET" if body is None else "PUT")
  # Never send local settings through an environment-configured HTTP proxy.
  with build_opener(ProxyHandler({})).open(request, timeout=2) as response:
    return json.load(response)


def validate_snapshot(data):
  if (not isinstance(data, dict) or data.get("mode") not in MODE_LABELS or
      type(data.get("locked")) is not bool or not isinstance(data.get("reason"), str) or
      type(data.get("experimental_confirmed")) is not bool or not isinstance(data.get("values"), dict) or
      any(type(data["values"].get(key)) is not bool for key in MODE_KEYS) or
      selected_mode(data["values"]) != data["mode"]):
    raise ValueError("Longitudinal mode state unavailable")
  return data


class LongitudinalModeClient:
  def __init__(self, transport=request_mode, executor=None, clock=monotonic):
    self._transport = transport
    self._executor = executor if executor is not None else ThreadPoolExecutor(max_workers=1, thread_name_prefix="longitudinal-mode")
    self._clock = clock
    self._future = None
    self._next_refresh = 0
    self.state = None
    self.error = ""
    self.pending = False

  @property
  def enabled(self):
    return self.state is not None and not self.state["locked"] and not self.pending and self._future is None

  @property
  def display_enabled(self):
    # A routine GET must not flash the tile's disabled artwork every second.
    # Click dispatch still uses enabled, including its in-flight request guard.
    return self.state is not None and not self.state["locked"] and not self.pending

  @property
  def label(self):
    return MODE_LABELS[self.state["mode"]] if self.state else "Unavailable"

  def _exchange(self, body):
    error = ""
    if body is not None:
      try:
        validate_snapshot(self._transport(body))
      except Exception as exc:
        error = str(exc)
    # Always read back, including partial writes and lost responses. No retry.
    return validate_snapshot(self._transport()), error

  def update(self):
    if self._future is not None and self._future.done():
      try:
        self.state, self.error = self._future.result()
      except Exception as exc:
        self.state, self.error = None, str(exc)
      self._future = None
      self.pending = False
      self._next_refresh = self._clock() + 1
    if self._future is None and self._clock() >= self._next_refresh:
      self._future = self._executor.submit(self._exchange, None)

  def cycle(self):
    if not self.enabled or self.state is None:
      return
    modes = tuple(MODE_LABELS)
    target = modes[(modes.index(self.state["mode"]) + 1) % len(modes)]
    self.select(target)

  def select(self, target):
    if not self.enabled or self.state is None or target not in MODE_LABELS:
      return
    body = {"mode": target, "expected": dict(self.state["values"]), "acknowledged": target == "experimental"}
    self.pending = True
    self._future = self._executor.submit(self._exchange, body)
