"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

The onroad events of a big model that joins mid-drive, as flags. A native big
model loads before the first modelV2; this one joins onto a modelV2 the small
model already publishes, and can leave and come back. Each fork's selfdrived
calls SwapEvents.update once a tick and maps the flags onto its own events.

It swaps in only while nothing is in control, so the driver is told once when
it is ready (offer) and re-engages to use it. For a second after a swap nothing
engages (no_entry) while the big model builds its history and proves it keeps
up (the joining model hands back on a held frame in that second), and the chime
at the end of it says the driver can. When it leaves, the small model drives on
and the driver is told (link_lost); nothing disengages.

The fork's own chime on a rising modelV2.big, a native big model's, must not
fire for a joined one, or it says engage now at the start of the no-entry
second: gate it on the state being 'none', or at least drop it on no_entry
(zoompilot drops it on no_entry or chime, then adds it on chime).

Either way the switch costs modeld a frame or two, and a frame the camera
dropped is an invalid pose from the model and a localizer soft disable on the
next tick (TAKE CONTROL IMMEDIATELY). So a switch is `settling` for a second, which selfdrived must
treat as it does a native big model's load: hold the comm and localization
errors that frame raises.
"""
from __future__ import annotations

from typing import NamedTuple

# how long each lasts, in seconds; SwapEvents counts them in the caller's ticks.
# The link-lost warning covers about the time the small model takes to refill
# its history, the no-entry about 20 frames of the big model's. An enable inside
# that second is refused, and pressed again after the chime
OFFER_S = 3.
HANDBACK_S = 5.
SWITCHING_S = 1.


class Flags(NamedTuple):
  offer: bool       # ready while something is in control: re-engage to switch
  link_lost: bool   # it fell while in control; the small model drives on
  no_entry: bool    # the second after a swap: refuse an engagement
  chime: bool       # the end of that second: the big model drives, engage now
  settling: bool    # the second after a switch either way: forgive its dropped frame


def _tick(left: int) -> tuple[bool, int]:
  return left > 0, max(left - 1, 0)


class SwapEvents:
  def __init__(self, tick_s: float):
    # checked once here: update() runs in selfdrived's loop and never raises
    if not tick_s > 0 or round(SWITCHING_S / tick_s) < 1:
      raise ValueError(f"SwapEvents needs the loop period in seconds, short enough to count a {SWITCHING_S:g} s switch: {tick_s}")
    self.offer_ticks = round(OFFER_S / tick_s)
    self.handback_ticks = round(HANDBACK_S / tick_s)
    self.switching_ticks = round(SWITCHING_S / tick_s)
    self.offered = False
    self.running = False
    # the state as last seen fresh: a gap in the fork's status or message holds
    # it, never reads as the link going
    self._state = 'none'
    # ticks left of each event, and of the settling after a switch either way
    self._offer = self._handback = self._switching = self._settle = 0

  @property
  def settling(self) -> bool:
    return self._settle > 0

  def update(self, fresh: bool, big: bool, in_control: bool, state: str) -> Flags:
    """One tick of the caller's loop, in hooks.SwapTracker.update's order.

    `fresh`: modelV2 and the fork's state message are seen, alive and valid
    this tick. `big`: modelV2.big, from a modelV2 alive and valid this tick.
    `in_control`: the fork's meaning of something steering or able to
    (zoompilot: openpilot or MADS, MADS even paused), the same rule the swap
    waits on (the adapter's engaged()). `state`: the joining model's
    big_model_state, its STATES name (str() of a capnp enum, never its .raw
    number, which matches no state)."""
    # a stale state neither offers the switch nor rearms the offer
    if fresh:
      self._state = state
      if self._state != 'ready' or big:
        # ended by the swap as well as by the link going: an offer still on
        # screen after the switch reads as if it had not happened
        self.offered = False
        self._offer = 0
      elif in_control and not self.offered and self._handback == 0:
        # with nothing in control it swaps at once and the chime says so. Once
        # per readiness, not at every stop, and after the link-lost warning,
        # which would hide it
        self.offered = True
        self._offer = self.offer_ticks

    # a chestnut dropping modelV2.big is its own fork's failure event, not this
    running = bool(big) and self._state != 'none'
    if running != self.running:
      self._settle = self.switching_ticks + 1   # counted down below, this tick included
      self._switching = self.switching_ticks + 1 if running else 0   # the no-entry, then the chime
      if not running and in_control:
        self._handback = self.handback_ticks
    self.running = running
    self._settle = max(self._settle - 1, 0)
    if not in_control:
      self._handback = 0

    offer, self._offer = _tick(self._offer)
    link_lost, self._handback = _tick(self._handback)
    switching, self._switching = _tick(self._switching)
    return Flags(offer, link_lost, switching and self._switching > 0, switching and self._switching == 0, self.settling)
