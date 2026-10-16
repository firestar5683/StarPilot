"""StarPilot's adapter to jetlink's openpilot layer, and the guard every Jetlink hook line calls.

The top level imports the standard library only: manager builds its process list from this module and the
gadget owner (jetlinkd) runs it.
"""
from __future__ import annotations

import functools
import os
import time

API = 3  # the jetlink.openpilot API this adapter is written to
UNSUPPORTED = "Jetlink requires a comma 3X or comma 4"
# AOL steers on its own axes, and a paused AOL is still armed: only its intent says so
AOL_SERVICES = ("aolIntentWire", "aolAxisState")
AOL_AXES = ("desiredLateral", "desiredLongitudinal", "lateralActive", "longitudinalActive")
# how long after AOL's reader is built an intent not yet heard counts as armed: its first polls run before the
# subscription connects, though card publishes the intent at 100 Hz
AOL_GRACE_S = 1.
# CatalogModelState's per-frame camera input, not history
FRAME_INPUTS = ("mapped_gpu_image",)


def supported_device(device_type=None) -> bool:
  if device_type is None:
    from openpilot.common.hardware import HARDWARE
    device_type = HARDWARE.get_device_type()
  return device_type in ("tizi", "mici")


def aol_in_control(intent, alive, axes, waiting=False) -> bool:
  """AOL armed (paused or not) or on its axes: the half of the swap's in-control rule that is not openpilot's,
  shared by engaged() and selfdrived. `intent` is aolIntentWire's message, None until heard; `alive` that it still
  is; `axes` the AOL_AXES flags, empty when unknown; `waiting` that its reader is younger than AOL_GRACE_S, when an
  intent not heard yet may be armed."""
  if intent is None:
    if waiting:
      return True
  elif not alive:
    return True
  else:
    from openpilot.starpilot.aol.wire import decode_intent
    decoded = decode_intent(intent)
    if decoded is None or decoded.allowedLatch or decoded.lateralArmed:
      return True
  return any(axes)


@functools.cache
def _adapter_class():
  from jetlink.openpilot.interface import Keys
  from jetlink.openpilot.stock import Stock

  class StarPilotAdapter(Stock):
    # No big-model slot or catalog: jetlink provisions its default model
    KEYS = Keys(link="JetlinkMode", offroad="IsOffroad", progress="JetlinkProgress", spec="JetlinkSpec",
                pointers="JetlinkPointers", charge_phone="JetlinkChargePhone")
    IN_CONTROL_SERVICES = ("carControl", "selfdriveState")
    _aol = None
    _aol_since = 0.

    def model_root(self):
      from openpilot.starpilot.models.manager import ROOT
      return ROOT

    def engaged(self, sm) -> bool:
      # openpilot, or aol_in_control(); Stock.in_control() answers True if this raises. AOL's reader is built and
      # polled on every call, openpilot engaged or not, so it has heard AOL by the time an offer or a fall asks,
      # rather than answering from its grace
      if self._aol is None:
        from openpilot.cereal import messaging
        self._aol, self._aol_since = messaging.SubMaster(list(AOL_SERVICES)), time.monotonic()
      aol = self._aol
      aol.update(0)
      if super().engaged(sm):
        return True
      heard = aol.seen["aolIntentWire"]
      axes = aol["aolAxisState"] if aol.seen["aolAxisState"] and aol.alive["aolAxisState"] else None
      return aol_in_control(aol["aolIntentWire"] if heard else None, aol.alive["aolIntentWire"],
                            () if axes is None else [getattr(axes, axis) for axis in AOL_AXES],
                            waiting=time.monotonic() - self._aol_since < AOL_GRACE_S)

    def small_reset(self, small):
      # CatalogModelState's history zeroed in place: GPU queues, numpy inputs (prev_feat, packed inputs) and
      # the desire edge. Never _reset_state(), which makes tensors the run JIT was not captured with
      from openpilot.starpilot.models.runner import CatalogModelState
      if not isinstance(small, CatalogModelState):
        return None
      from jetlink.openpilot.warp import reset_queues
      queues = [q for name, q in small.input_queues.items() if q.device != "NPY" and name not in FRAME_INPUTS]
      return reset_queues(queues, small.npy.values(), small.prev_desire)

  return StarPilotAdapter


def adapter():
  return _adapter_class()()


def owner_config():
  return _adapter_class().owner_config()


def main():
  _adapter_class().main()


def link_on() -> bool:
  """The Jetlink setting, read as a file, so it works with no jetlink at all."""
  prefix = os.environ.get("OPENPILOT_PREFIX", "")
  root = os.environ.get("PARAMS_ROOT") or ("/data/params" if os.path.isfile("/AGNOS") else
                                           os.path.expanduser(f"~/.comma{prefix}/params"))
  try:
    with open(os.path.join(root, os.environ.get("OPENPILOT_PREFIX", "d"), "JetlinkMode")) as f:
      return f.read().strip() in ("1", "2")
  except OSError:
    return False


def _cloudlog():
  from openpilot.common.swaglog import cloudlog
  return cloudlog


@functools.cache
def hooks():
  """What every hook line calls, one per process. Never raises."""
  try:
    from jetlink.openpilot.hooks import Hooks, Off
  except Exception as e:
    return _NoJetlink(f"jetlink is missing: {e}")
  try:
    if not supported_device():
      return Off(UNSUPPORTED, link_on=link_on)
    return Hooks(API, adapter, link_on=link_on, log=_cloudlog)
  except Exception as e:
    return Off(str(e), link_on=link_on)


class _NoJetlink:
  """The hooks with no usable jetlink checkout, each answering link off. Only these are reached: modeld stops at
  prepare()."""
  def __init__(self, why):
    self._why = why

  def should_run(self, started, params, CP):
    return False

  def status(self):
    return None

  def reason(self):
    return self._why if link_on() else None

  def prepare(self, chestnut):
    return False

  def shutdown_step(self, should_shutdown, reason=""):
    return should_shutdown

  def runtime(self):
    return None

  def swap_events(self, tick_s):
    return None
