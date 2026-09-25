"""Runs the car renderer on core 7 at the lowest priority.
Safeguards:
- SCHED_IDLE, so the realtime driving and driver-monitoring models on core 7
  always preempt it. Core 6 is no longer an option: since 2026-10-07
  (c01f815736) selfdrive/ui/ui.py runs the comma UI there next to camerad, which
  left a SCHED_IDLE renderer waiting ~70% of the time with the core 98% busy.
- Every renderer thread is placed, including ones the graphics driver starts later.
- Parked, power saving turns cores 4-7 off. The pin is re-applied every
  PLACEMENT_CHECK_INTERVAL seconds once core 7 is back, like selfdrive/ui/ui.py.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

RENDER_CORE = 7
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
  """Keeps every renderer thread SCHED_IDLE on RENDER_CORE while that core is online."""

  def __init__(self, core: int = RENDER_CORE, report: Callable[[dict[str, Any]], None] | None = None,
               thread_ids: Callable[[], list[int]] = _thread_ids, core_online: Callable[[int], bool] = _core_online):
    self.core = core
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
    policy = "idle"
    try:
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
