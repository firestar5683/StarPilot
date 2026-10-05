"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

The picked model's spec, and whether its engine is built, in one record.

Reading the shapes and output slices means parsing a 766 MB ONNX. The server
does that when it builds the engine and answers with the spec; provisioning
keeps the answer here, and modeld reads it and never touches the file. The
record also says whether the server has built the engine for the sha it names,
so the spec and the readiness can never name different models. It must
survive a reboot, or every ignition rebuilds a 160 s engine.

A param today (Keys.spec), through the adapter's get and put.
"""
from __future__ import annotations


class SpecRecord:
  def __init__(self, op):
    self.op = op

  def _raw(self) -> dict | None:
    # get tolerates a params library older than the key
    value = self.op.get(self.op.keys.spec)
    return value if isinstance(value, dict) else None

  def load(self):
    """The recorded ModelSpec, or None if there is not a usable one."""
    from jetlink.spec import ModelSpec
    try:
      d = self._raw()
      return ModelSpec.from_dict(d) if d else None
    except Exception:
      self.op.log.exception("jetlink: cached spec is unreadable")
      return None

  def store(self, spec) -> None:
    """The server has built the engine for this spec and answered with it."""
    self.op.put(self.op.keys.spec, {**spec.to_dict(), 'ready': True})

  def engine_ready_for(self, sha256: str | None) -> bool:
    """Has the server built the engine for this model? Params only."""
    d = self._raw()
    return bool(sha256) and d is not None and d.get('sha256') == sha256 and d.get('ready') is True

  def clear_ready(self) -> None:
    """The engine is no longer known to be built. The spec stays: it still
    sizes the warp, and the next provisioning run asks again."""
    d = self._raw()
    if d is not None and d.get('ready'):
      self.op.put(self.op.keys.spec, {**d, 'ready': False})
