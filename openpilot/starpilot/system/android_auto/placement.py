"""Runs the car renderer on core 6 at the lowest priority.
Safeguards:
- SCHED_IDLE, so camerad and the comma UI on core 6 always preempt it.
- Core 6 again since 2026-10-14. On 2026-10-08 the comma UI took 65-75 % of it
  and the renderer moved to core 7, but there it waited for a core 47 % of the
  time behind modeld and dmonitoringmodeld (core 7 at 78 %). With the UI now
  at 8-14 %, core 6 runs 16-24 % busy, and core 7 is left to the models and
  Jetlink's frame loop.
- Every renderer thread is placed, including ones the graphics driver starts later.
- Parked, power saving turns cores 4-7 off. The pin is re-applied every
  PLACEMENT_CHECK_INTERVAL seconds once core 6 is back, like selfdrive/ui/ui.py.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

RENDER_CORE = 6
PLACEMENT_CHECK_INTERVAL = 1.0  # s
FALLBACK_NICE = 10  # if SCHED_IDLE is unavailable


def _thread_ids() -> list[int]:
  try:
    return [int(tid) for tid in os.listdir("/proc/self/task")]
  except OSError:
    return [0]


def _core_online(core: int) -> bool:
  if core == 0:
    return True
  try:
    with open(f"/sys/devices/system/cpu/cpu{core}/online") as f:
      return f.read().strip() == "1"
  except OSError:
    return False


class RendererPlacement:
  """Keeps every thread of this process on RENDER_CORE while that core is online:
  SCHED_IDLE for the renderer, or normal scheduling (idle=False) for
  android_autod, whose stream thread otherwise sticks on whichever isolated
  core it first woke on (core 7, waiting ~32 % of the time behind the models)."""

  def __init__(self, core: int = RENDER_CORE, report: Callable[[dict[str, Any]], None] | None = None,
               thread_ids: Callable[[], list[int]] = _thread_ids, core_online: Callable[[int], bool] = _core_online,
               idle: bool = True):
    self.core = core
    self.idle = idle
    self.report = report or (lambda _event: None)
    self.thread_ids = thread_ids
    self.core_online = core_online
    self.next_check = 0.0
    self.pinned = False

  def start(self) -> None:
    """Call first, before any thread exists, so later threads inherit the policy."""
    if not hasattr(os, "sched_setaffinity"):
      self.report({"event": "cpu_placement", "pinned": False, "reason": "no CPU affinity on this platform"})
      self.next_check = float("inf")
      return
    inherited = sorted(os.sched_getaffinity(0))
    policy = "idle" if self.idle else "normal"
    try:
      if self.idle:
        os.sched_setscheduler(0, os.SCHED_IDLE, os.sched_param(0))
    except (AttributeError, OSError):
      policy = f"nice{FALLBACK_NICE}"
      try:
        os.nice(FALLBACK_NICE)
      except OSError:
        policy = "default"
    self.report({"event": "cpu_placement", "policy": policy, "inherited_cores": inherited, "core": self.core})
    self.maintain(0.0)

  def maintain(self, now: float) -> None:
    if now < self.next_check:
      return
    self.next_check = now + PLACEMENT_CHECK_INTERVAL
    if not self.core_online(self.core):
      if self.pinned:
        self.report({"event": "cpu_placement", "pinned": False, "reason": f"core {self.core} offline"})
      self.pinned = False
      return

    target = {self.core}
    changed = False
    for tid in self.thread_ids():
      try:
        if os.sched_getaffinity(tid) != target:
          os.sched_setaffinity(tid, target)
          changed = True
      except OSError:
        pass  # the thread exited
    if changed or not self.pinned:
      self.report({"event": "cpu_placement", "pinned": True, "cores": sorted(os.sched_getaffinity(0))})
    self.pinned = True
