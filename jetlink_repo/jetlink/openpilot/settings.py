"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

The settings jetlink reads straight off openpilot's params files: the Jetlink
setting and whether the car is parked, which every process reads, and whether
the owner charges an iPhone.

The owner cannot construct openpilot's Params: it imports swaglog, which costs
28 MB and brings numpy, capnp and zmq with it. So the fork's adapter says where
the store is and what the keys are called (OwnerConfig), and this reads the
files. params.cc writes a value to a temporary file, fsyncs it and renames it
over the key, so a plain read gets the old value or the new one and never a
torn one. The byte format is params.cc's put: b"1" or b"0" for a BOOL,
decimal ASCII for an INT. The fork's tests write with the real Params and read
back through here, so a change on either side fails there.

Every other process reads these two the same way, so they agree with the owner;
JSON values go through the adapter's get and put, which are the real Params.

The standard library only: the owner imports this module.
"""
from __future__ import annotations

import os
from pathlib import Path

from jetlink.openpilot.interface import MODES, Keys


class FileParams:
  """openpilot's params store, read as files. Nothing here writes."""

  def __init__(self, directory: Path):
    self.directory = Path(directory)

  def path(self, key: str) -> Path:
    return self.directory / key

  def raw(self, key: str) -> bytes | None:
    """A param's bytes, or None if it is unset or unreadable."""
    try:
      return self.path(key).read_bytes()
    except OSError:
      return None

  def get_bool(self, key: str) -> bool | None:
    """A param openpilot stores with put_bool. None when it is unset."""
    value = self.raw(key)
    if value is None:
      return None
    return value.strip() in (b'1', b'true', b'True')

  def get_int(self, key: str) -> int | None:
    """An INT param. None when it is unset or not a number."""
    value = self.raw(key)
    try:
      return int(value)
    except (TypeError, ValueError):
      return None


class Settings:
  """What jetlink reads of openpilot's params without the Params library."""

  def __init__(self, params: FileParams, keys: Keys):
    self.params = params
    self.keys = keys
    # the pick and the built model's record: a change to either is a reason
    # for the owner to look again. A stat, not a read: the owner does not parse
    # the catalog or the spec, it only notices they moved. Paths once, since
    # the owner stats them twice a second
    watched = (keys.big_model, keys.spec)
    self._watched = {k: str(params.path(k)) for k in watched if k}

  def mode(self) -> str:
    """The Jetlink setting, one of MODES. Unset or unreadable is 'off'; manager
    writes the default before anything runs."""
    index = self.params.get_int(self.keys.link)
    return MODES[index] if index is not None and 0 <= index < len(MODES) else 'off'

  def offroad(self) -> bool:
    """Is the car parked? The owner runs onroad too, to keep hold of the gadget,
    and everything else jetlink does belongs to a parked car. A missing param
    is manager not having written one yet, which reads as parked."""
    value = self.params.get_bool(self.keys.offroad)
    return True if value is None else value

  def charge_phone(self) -> bool:
    """Is an iPhone on a direct cable asked to charge from the comma? Off when
    the param is unset or the fork declares none."""
    key = self.keys.charge_phone
    return bool(key) and self.params.get_bool(key) is True

  def marks(self) -> dict[str, int]:
    """When each watched param last changed, by key; 0 for one that is unset."""
    out = {}
    for key, path in self._watched.items():
      try:
        out[key] = os.stat(path).st_mtime_ns
      except OSError:
        out[key] = 0
    return out
