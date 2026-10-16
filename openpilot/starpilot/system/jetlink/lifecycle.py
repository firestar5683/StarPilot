"""Manager's opt-in Jetlink owner and bounded remote power-off handoff."""
from __future__ import annotations

import time

# jetlink's SHUTDOWN_TIMEOUT (25 s) plus 5 s, written out so it holds without jetlink: a jetlink regression
# must never keep a comma from powering off and drain the car's battery
SHUTDOWN_CAP_S = 30.


def enabled(params) -> bool:
  # with the link off, should_run() binds nothing: jetlink's light hooks module alone loads
  from openpilot.starpilot.models.jetlink_adapter import hooks
  return hooks().should_run(False, params, None)


def shutdown(params, *, clock=time.monotonic, sleep=time.sleep) -> None:
  # A power-off only: the Jetson is on an always-on supply and wakes only on a USB edge, so one powered off at
  # a comma reboot would not come back. The resident owner must still be alive to run it.
  from openpilot.starpilot.models.jetlink_adapter import hooks, link_on
  if not params.get_bool('DoShutdown') or not link_on():
    return
  link = hooks()
  deadline = clock() + SHUTDOWN_CAP_S
  while not link.shutdown_step(True, 'DoShutdown') and clock() < deadline:
    sleep(0.1)
