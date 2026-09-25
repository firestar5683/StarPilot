"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

This process's jetlink, inside: the fork's adapter and what jetlink.openpilot
keeps over it. The fork holds a Jetlink (the API) and never sees these; the
modules here pass them to each other.

One per process, from bind(). Each part is made on first use, so a reader
such as manager's should_run loads no more than the settings, and none of it
is on the resident owner's path.
"""
from __future__ import annotations

import time
from functools import cached_property
from pathlib import Path

from jetlink.comma import gadget
from jetlink.openpilot.settings import FileParams, Settings

# the chestnut runs the big model natively and the link stays off beside it,
# whatever the setting says. Cached: the UI asks five times a second and the
# answer is a walk of the USB bus
CHESTNUT_TTL = 2.0


def for_this_process(op) -> Parts:
  """The parts over the fork's adapter, with jetlink.comma's log pointed at
  op.log: a heavy process's lines belong in the drive's log, while the owner's
  go to its own file."""
  gadget.set_logger(op.log)
  return Parts(op)


class Parts:
  def __init__(self, op):
    self.op = op
    self._settings: Settings | None = None
    self._chestnut: tuple[float, bool] | None = None

  @property
  def log(self):
    return self.op.log

  @property
  def settings(self) -> Settings:
    """The link setting and whether the car is parked, off the params files,
    as the owner reads them. Follows the directory the adapter names, which
    moves with OPENPILOT_PREFIX as Params does."""
    directory = Path(self.op.params_dir())
    if self._settings is None or self._settings.params.directory != directory:
      self._settings = Settings(FileParams(directory), self.op.keys)
    return self._settings

  @cached_property
  def models(self):
    from jetlink.openpilot.models import Models
    return Models(self.op)

  @cached_property
  def spec(self):
    from jetlink.openpilot.state import SpecRecord
    return SpecRecord(self.op)

  @cached_property
  def progress(self):
    from jetlink.openpilot.status import Progress
    return Progress(self.op, size=lambda: (self.models.selected_model() or {}).get('size'))

  @cached_property
  def presence(self):
    from jetlink.openpilot.status import Presence
    return Presence()

  @cached_property
  def warps(self):
    from jetlink.openpilot.warp import Warps
    return Warps(self.op)

  def chestnut_fitted(self) -> bool:
    now = time.monotonic()
    if self._chestnut is None or now - self._chestnut[0] > CHESTNUT_TTL:
      self._chestnut = (now, bool(self.op.chestnut_present()))
    return self._chestnut[1]

  def enabled(self, mode: str | None = None) -> bool:
    """The link setting is on and no chestnut is fitted; `mode` is the setting
    when the caller has read it already."""
    mode = self.settings.mode() if mode is None else mode
    return mode != 'off' and not self.chestnut_fitted()
