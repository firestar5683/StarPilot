"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

What jetlink needs from openpilot, as one interface the fork implements.

jetlink never imports openpilot. The fork has one adapter module that holds
every openpilot import jetlink needs; it implements `Openpilot` below and
hands the object in, and jetlink.openpilot reaches openpilot through it and
nothing else. So jetlink is tested against a fake, and an openpilot sync that
moves something jetlink relies on fails the adapter's tests in the fork, where
the fix belongs.

The interface is split by process. The resident gadget owner gets data only
(OwnerConfig), no callbacks, so it stays at the standard library and about
10 MB. The heavy processes get the adapter object and each uses its side:
StatusSide in manager, the UI, hardwared and the model manager, WorkerSide in
the provisioning run, ModelSide in modeld, BuildSide in the warp build.

The standard library only: the owner imports this module.
"""
from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

# the Jetlink setting: off; a Jetson, a Linux PC or a Mac on USB; an
# iPhone on the cable. The INT param holds the index
MODES = ('off', 'usb', 'ios')
# what a joining model reports as big_model_state, by the names of the fork's
# modelDataV2SP.acceleratorState enum
STATES = ('none', 'joining', 'retrying', 'ready', 'running', 'unavailable')


@dataclass(frozen=True)
class Keys:
  """The params the fork declares for jetlink, by name: jetlink itself knows no param name."""
  link: str                      # INT, an index into MODES: the Jetlink setting
  offroad: str                   # BOOL: is the car parked (manager's IsOffroad)
  progress: str                  # JSON {stage, frac, msg, drops}: provisioning and join progress
  spec: str                      # JSON: the built model's spec and whether its engine is built
  pointers: str                  # JSON: catalog ref -> {oid, size}
  # sunnypilot's model manager: the big-model pick, JSON {ref, displayName},
  # and the big-model catalog, JSON {bundles}. Without one both are None, and
  # jetlink runs its own default big model
  big_model: str | None = None
  catalog: str | None = None
  # BOOL: an iPhone on a direct cable is asked to charge from the comma
  # (comma.port). Off when unset, and without the key
  charge_phone: str | None = None


@dataclass(frozen=True)
class OwnerConfig:
  """What the resident gadget owner needs, built without importing anything heavy."""
  params_dir: Path                           # the params store's directory, by params.cc's rule
  keys: Keys                                 # the settings it reads and the pick it watches
  chestnut_ids: frozenset[tuple[int, int]]   # (vid, pid) of comma's chestnut, running or in its ROM: never held as a host
  adapter: str                               # the adapter module, which the provisioning run is started with
  cwd: Path                                  # where the run starts: the checkout
  env: Mapping[str, str]                     # over the owner's environment, for the run
  log_file: Path                             # the owner's rotating log


@dataclass(frozen=True)
class ModelFace:
  """What openpilot's modeld reads off a ModelState, supplied for comma's large model."""
  parser: Callable[[], Any]                  # a new Parser: .parse_outputs(dict[str, ndarray]) -> dict
  frame_size: Callable[[int, int], int]      # a camera frame buffer's size for (w, h): get_nv12_info(w, h)[3]
  desire_len: int                            # ModelConstants.DESIRE_LEN
  constants: Any                             # modeld_v2's ModelConstants, which modeld_tinygrad reads off the model
  lat_smooth_seconds: float                  # modeld's LAT_SMOOTH_SECONDS
  long_smooth_seconds: float                 # modeld's LONG_SMOOTH_SECONDS
  get_action_from_model: Callable[..., Any]  # modeld's action function


# The sides are typing Protocols so a type checker can hold the adapter to
# them; conformance() is the check both repos run. A parameter jetlink passes
# by keyword is keyword-only here, and only those names must match.

class StatusSide(Protocol):
  """Every reader: manager, the UI, hardwared, the model manager."""
  keys: Keys
  log: Any                  # logging.Logger-like (cloudlog): debug, info, warning, error, exception
  catalog_selector: int     # the model manager's REQUIRED_JSON_VERSION; 0 without a model manager

  def params_dir(self) -> Path:
    """The params store's directory, by params.cc's rule, worked out on every
    call so it follows OPENPILOT_PREFIX as Params does. jetlink reads the link
    setting and IsOffroad there as files, for every setting a heavy process
    reads (manager's should_run among them), so it is cheap and never raises."""

  def get(self, key: str) -> Any:
    """A param's decoded value. None when unset or unknown to this build; never raises."""

  def chestnut_present(self) -> bool:
    """Is comma's chestnut fitted? A USB walk; jetlink caches the answer."""

  def camera(self) -> tuple[int, int, int, int]:
    """This device's (cam_w, cam_h, model_w, model_h): the warp modeld asks for."""

  def warp_path(self, cam_w: int, cam_h: int, model_w: int, model_h: int) -> Path:
    """Where the build puts the warp for this geometry."""


class WorkerSide(StatusSide, Protocol):
  """The provisioning run: writes, files, the network."""
  basedir: Path             # the checkout, whose .lfsconfig names the nearest LFS server

  def put(self, key: str, value: Any, *, block: bool = False) -> None:
    """Write a param. May raise, as Params does for a key this build does not declare."""

  def remove(self, key: str) -> None:
    """Clear a param."""

  def model_root(self) -> Path:
    """The model manager's model root (openpilot's Paths.model_root()). jetlink
    keeps its downloads in a directory of its own under it, `jetlink/`: the
    model manager's cache clear deletes every file in the root it does not
    recognise, a downloaded 1.75 GB ONNX included, and leaves directories alone."""


class ModelSide(WorkerSide, Protocol):
  """modeld: comma's model face, the engagement a swap waits out, and the
  structured log line the link's telemetry goes to."""

  def model_face(self) -> ModelFace:
    """What a ModelState for comma's large model has to carry."""

  def engagement(self) -> Callable[[int], bool]:
    """A poller, made on the thread that calls it: (timeout_ms) -> engaged. Waits
    up to timeout_ms for news and answers True when controls are engaged, or when
    that is not known."""

  def event(self, name: str, **fields: Any) -> None:
    """A structured log line (cloudlog.event)."""


class BuildSide(Protocol):
  """scons: comma's warp graph."""

  def make_warp(self, cam_w: int, cam_h: int, model_w: int, model_h: int) -> tuple[Callable[..., Any], int]:
    """The warp graph for this geometry, and the size of the NV12 frame it
    reads. Imports comma's graph module before anything of tinygrad's."""


class Openpilot(ModelSide, BuildSide, Protocol):
  """The whole adapter: one object implements every side."""


def load_adapter(module: str) -> Openpilot:
  """The adapter an adapter module makes. An adapter module is the fork's
  module that holds every openpilot import jetlink needs: its top level
  imports only the standard library, and it has adapter() -> Openpilot and
  owner_config() -> OwnerConfig. The entry points that run as their own
  process (the provisioning run, the warp build) are told its name."""
  return importlib.import_module(module).adapter()


def members(protocol: type) -> dict[str, inspect.Signature | None]:
  """Every member of `protocol`, inherited ones included: a method's signature
  without self, or None for a data member."""
  found: dict[str, inspect.Signature | None] = {}
  for cls in reversed(protocol.__mro__):
    if cls is object or cls.__module__ == 'typing':
      continue
    for name in inspect.get_annotations(cls):
      if not name.startswith('_'):
        found[name] = None
    for name, value in vars(cls).items():
      if not name.startswith('_') and inspect.isfunction(value):
        sig = inspect.signature(value)
        found[name] = sig.replace(parameters=list(sig.parameters.values())[1:])
  return found


def _shape(sig: inspect.Signature) -> list[tuple[str | None, Any, bool]]:
  """What a caller depends on: each parameter's kind and whether it has a
  default, and the name of one jetlink passes by keyword (keyword-only). The
  other names are the adapter's to choose."""
  return [(p.name if p.kind is p.KEYWORD_ONLY else None, p.kind, p.default is not p.empty)
          for p in sig.parameters.values()]


def _plain(sig: inspect.Signature) -> str:
  """The parameters alone, as a caller writes them: '(key, value, block=False)'."""
  return str(sig.replace(parameters=[p.replace(annotation=p.empty) for p in sig.parameters.values()],
                         return_annotation=sig.empty))


def conformance(obj: object, protocol: type) -> list[str]:
  """Each member of `protocol` that `obj` lacks, or has with parameters a
  caller would trip on (another count, kind or default, or another name for
  one passed by keyword); [] when it conforms. One checker for both repos:
  jetlink pins the interface with it, and the fork's tests run it against the
  real adapter."""
  problems = []
  for name, expected in members(protocol).items():
    if not hasattr(obj, name):
      problems.append(f"{name}: missing")
      continue
    if expected is None:
      continue
    value = getattr(obj, name)
    if not callable(value):
      problems.append(f"{name}: not callable")
      continue
    try:
      actual = inspect.signature(value)
    except (TypeError, ValueError):
      problems.append(f"{name}: no signature to check")
      continue
    if _shape(actual) != _shape(expected):
      problems.append(f"{name}{_plain(actual)}: expected {name}{_plain(expected)}")
  return problems
