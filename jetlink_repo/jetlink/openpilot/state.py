"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

The spec of the last model a server built (the pick, or a stand-in for it), and whether its engine is built, in one record.

Reading the shapes and output slices means parsing a 766 MB ONNX. The server
does that when it builds the engine and answers with the spec; provisioning
keeps the answer here, and modeld reads it and never touches the file. The
record also says whether the server has built the engine for the sha it names,
so the spec and the readiness can never name different models. It must
survive a reboot, or every ignition rebuilds a 160 s engine.

Stored as a param (Keys.spec), through the adapter's get and put.
"""
from __future__ import annotations


class SpecRecord:
  def __init__(self, op):
    self.op = op

  def _raw(self) -> dict | None:
    # get tolerates a params library older than the key
    value = self.op.get(self.op.keys.spec)
    return value if isinstance(value, dict) else None

  def load(self, d: dict | None = None):
    """The recorded ModelSpec, or None if there is not a usable one. `d` is
    the record, when the caller has read it already."""
    from jetlink.spec import ModelSpec
    try:
      d = self._raw() if d is None else d
      return ModelSpec.from_dict(d) if d else None
    except Exception:
      self.op.log.exception("jetlink: cached spec is unreadable")
      return None

  def store(self, spec) -> None:
    """The server has built the engine for this spec and answered with it."""
    self.op.put(self.op.keys.spec, {**spec.to_dict(), 'ready': True})

  def engine_ready_for(self, sha256: str | None) -> bool:
    """Has the server built the engine for this model? Params only."""
    return bool(sha256) and self.built_sha() == sha256

  def built_sha(self) -> str | None:
    """ready_spec()'s sha256, without making the spec of it."""
    d = self._raw()
    return d.get('sha256') if d is not None and d.get('ready') is True else None

  def ready_spec(self):
    """The last model whose engine the server built, whichever model is picked
    now: what drives while a new pick is still being fetched or built. None
    without one."""
    d = self._raw()
    return self.load(d) if d is not None and d.get('ready') is True else None

  def clear_ready(self, sha256: str | None = None) -> None:
    """The engine is no longer known to be built. The spec stays: it still
    sizes the warp, and the next provisioning run asks again. With `sha256`,
    only if the record is that model's: a new pick the server has nothing of
    says nothing about the last model it built, which still drives."""
    d = self._raw()
    if d is not None and d.get('ready') and (sha256 is None or d.get('sha256') == sha256):
      self.op.put(self.op.keys.spec, {**d, 'ready': False})
