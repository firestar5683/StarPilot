"""StarPilot's boundary to the pinned Jetlink public API."""
from __future__ import annotations

from functools import cached_property, lru_cache
import logging
import os
import time
import threading
import uuid
from pathlib import Path


ADAPTER_MODULE = "openpilot.starpilot.models.jetlink_adapter"
BASEDIR = Path(__file__).resolve().parents[3]
API_VERSION = 1


def supported_device(device_type=None):
  if device_type is None:
    from openpilot.common.hardware import HARDWARE
    device_type = HARDWARE.get_device_type()
  return device_type in ("tizi", "mici")


def params_directory() -> Path:
  # Match Path::params() and Params' prefix without loading native libraries.
  home = Path.home() / (".comma" + os.environ.get("OPENPILOT_PREFIX", ""))
  root = os.environ.get("PARAMS_ROOT", "/data/params" if Path("/AGNOS").is_file() else str(home / "params"))
  return Path(root) / os.environ.get("OPENPILOT_PREFIX", "d")


def keys():
  from jetlink.openpilot import Keys
  return Keys(link="JetlinkMode", offroad="IsOffroad", progress="JetlinkProgress", spec="JetlinkSpec",
              pointers="JetlinkPointers", big_model="JetlinkBigModel", catalog="JetlinkCatalog",
              charge_phone="JetlinkChargePhone")


def process_start_ticks(pid):
  try:
    return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19])
  except (OSError, ValueError, IndexError):
    return None


def runtime_snapshot(record, now_ns, boot_id, start_ticks):
  unavailable = {"state": "unavailable", "active": False}
  if not isinstance(record, dict) or type(record.get("version")) is not int or record["version"] != 1:
    return unavailable
  mono, output = record.get("mono_ns"), record.get("remote_output_mono_ns")
  session = record.get("session")
  if (not boot_id or record.get("boot_id") != boot_id or
      not isinstance(session, str) or len(session) != 32 or any(c not in "0123456789abcdef" for c in session) or
      type(record.get("pid")) is not int or record["pid"] <= 0 or type(start_ticks) is not int or start_ticks <= 0 or
      type(record.get("process_start_ticks")) is not int or
      record.get("process_start_ticks") != start_ticks or type(mono) is not int or
      not 0 < mono <= now_ns or now_ns - mono > 1_500_000_000 or type(output) is not int or
      not 0 <= output <= mono or record.get("state") not in
      ("none", "joining", "retrying", "ready", "running", "unavailable")):
    return unavailable
  digest = record.get("artifact_sha256")
  identity = (isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest))
  active = record["state"] == "running" and identity and output > 0 and mono - output <= 250_000_000
  snapshot = {"state": record["state"], "active": active}
  if active:
    snapshot["artifact_sha256"] = digest
    checkpoint = record.get("model_checkpoint")
    if isinstance(checkpoint, str) and len(checkpoint) <= 256:
      snapshot["model_checkpoint"] = checkpoint
  return snapshot


def runtime_status():
  op = adapter()
  record = op.get("JetlinkRuntime")
  try:
    boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
  except OSError:
    boot_id = None
  pid = record.get("pid") if isinstance(record, dict) else None
  start = process_start_ticks(pid) if type(pid) is int and pid > 0 else None
  return runtime_snapshot(record, time.monotonic_ns(), boot_id, start)


class StarPilotAdapter:
  basedir = BASEDIR
  catalog_selector = 0

  @property
  def keys(self):
    return keys()

  @cached_property
  def log(self):
    from openpilot.common.swaglog import cloudlog
    return cloudlog

  def params_dir(self) -> Path:
    return params_directory()

  @property
  def params(self):
    from openpilot.common.params import Params
    directory = self.params_dir()
    if getattr(self, "_params_directory", None) != directory:
      self._params = Params()
      self._params_directory = directory
    return self._params

  def get(self, key):
    try:
      return self.params.get(key)
    except Exception:
      return None

  def put(self, key, value, *, block=False):
    self.params.put(key, value, block=block)

  def remove(self, key):
    self.params.remove(key)

  def chestnut_present(self):
    from openpilot.common.hardware.usb import is_chestnut_usb_id, read_int, usb_devices
    return any(is_chestnut_usb_id(read_int(path / "idVendor", 16), read_int(path / "idProduct", 16), True)
               for path in usb_devices())

  def camera(self):
    from openpilot.common.hardware import HARDWARE
    camera = (1344, 760) if HARDWARE.get_device_type() == "mici" else (1928, 1208)
    return (*camera, 512, 256)

  def warp_path(self, cam_w, cam_h, model_w, model_h):
    return BASEDIR / "openpilot/selfdrive/modeld/models" / f"jetlink_warp_{cam_w}x{cam_h}_{model_w}x{model_h}.pkl"

  def model_root(self):
    from openpilot.starpilot.models.manager import ROOT
    return ROOT

  def model_face(self):
    from jetlink.openpilot import ModelFace
    from openpilot.selfdrive.modeld.constants import ModelConstants
    from openpilot.selfdrive.modeld.modeld import LAT_SMOOTH_SECONDS, LONG_SMOOTH_SECONDS, get_action_from_model
    from openpilot.system.camerad.cameras.nv12_info import get_nv12_info
    return ModelFace(remote_parser, lambda w, h: get_nv12_info(w, h)[3], ModelConstants.DESIRE_LEN, ModelConstants,
                     LAT_SMOOTH_SECONDS, LONG_SMOOTH_SECONDS, get_action_from_model)

  def engagement(self):
    from openpilot.cereal.messaging import SubMaster
    sm = SubMaster(["selfdriveState", "carControl"])

    def engaged(timeout_ms):
      sm.update(timeout_ms)
      return (not sm.all_checks() or sm["selfdriveState"].enabled or sm["selfdriveState"].active or
              sm["carControl"].latActive or sm["carControl"].longActive)
    return engaged

  def event(self, name, **fields):
    self.log.event(name, **fields)

  def make_warp(self, cam_w, cam_h, model_w, model_h):
    from openpilot.starpilot.models.jetlink_warp import make_warp
    return make_warp(cam_w, cam_h, model_w, model_h)


def remote_parser():
  import numpy as np
  from openpilot.selfdrive.modeld.parse_model_outputs import Parser

  class RemoteParser(Parser):
    def parse_outputs(self, outs):
      if not all(np.isfinite(value).all() for value in outs.values()):
        raise ValueError("non-finite Jetlink model output")
      parsed = super().parse_outputs(outs)
      if not all(np.isfinite(value).all() for value in parsed.values()):
        raise ValueError("non-finite parsed Jetlink model output")
      return parsed
  return RemoteParser()


@lru_cache(maxsize=1)
def adapter():
  return StarPilotAdapter()


def owner_config():
  from jetlink.openpilot import OwnerConfig
  from openpilot.common.hardware.usb import CHESTNUT_USB_IDS, CHESTNUT_ROM_USB_IDS
  return OwnerConfig(params_directory(), keys(), frozenset(CHESTNUT_USB_IDS + CHESTNUT_ROM_USB_IDS),
                     ADAPTER_MODULE, BASEDIR, {}, Path("/data/log/jetlink-owner.log"))


@lru_cache(maxsize=1)
def get_jetlink():
  try:
    from jetlink.openpilot import API, bind
    if API != API_VERSION:
      raise RuntimeError(f"unsupported Jetlink API {API}")
    return bind(adapter())
  except Exception:
    logging.getLogger(__name__).exception("Jetlink unavailable; retaining local model")
    return None


class SmallModelFace:
  """Expose catalog history to Jetlink without changing the catalog runner."""
  def __init__(self, model):
    self.model = model
    self.lat_delay = 0.0
    self.PLANPLUS_CONTROL = 1.0
    self.frame_drop_ratio = 0.0

  @property
  def prev_desire(self):
    return self.model.prev_desire

  @property
  def numpy_inputs(self):
    return self.model.npy

  def __getattr__(self, name):
    return getattr(self.model, name)


class JetlinkModel:
  """Keep the current catalog's action contract while the remote model shadows."""
  def __init__(self, joined, small):
    self.joined = joined
    self.small = small
    self._session = uuid.uuid4().hex
    self._process_start_ticks = process_start_ticks(os.getpid())
    try:
      self._boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
      self._boot_id = None
    self._published_ns = 0
    self._published_state = None
    self._output = None
    self._output_ns = 0
    self._runtime_pending = None
    self._runtime_closed = False
    self._runtime_condition = threading.Condition()
    self._runtime_thread = threading.Thread(target=self._write_runtime, name="jetlink-runtime", daemon=True)
    self._runtime_thread.start()

  def __getattr__(self, name):
    return getattr(self.joined, name)

  def run(self, bufs, transforms, inputs, after_enqueue=None):
    outputs = self.joined.run(bufs, transforms, inputs, after_enqueue)
    client = self.joined.client
    if self.chestnut and outputs is not None and client is not None and client.last_output is not self._output:
      self._output = client.last_output
      self._output_ns = time.monotonic_ns()
    self.publish_runtime()
    return outputs

  def action(self, outputs, previous, lat_action_t, long_action_t, v_ego):
    from openpilot.selfdrive.modeld.modeld import LAT_SMOOTH_SECONDS, LONG_SMOOTH_SECONDS, get_action_from_model
    from openpilot.starpilot.models.runner import action_from_outputs
    if self.chestnut:
      return get_action_from_model(outputs, previous, lat_action_t, long_action_t, v_ego)
    return action_from_outputs(outputs, self.small.behavior_version, previous, lat_action_t, long_action_t, v_ego,
                               LAT_SMOOTH_SECONDS, LONG_SMOOTH_SECONDS)

  def observe_frame(self, lat_delay, drop_ratio):
    self.joined.lat_delay = lat_delay
    self.joined.frame_drop_ratio = drop_ratio

  def publish_runtime(self, *, closed=False):
    now = time.monotonic_ns()
    state = "unavailable" if closed else self.big_model_state
    if state == self._published_state and now - self._published_ns < 1_000_000_000:
      return
    self._published_ns, self._published_state = now, state
    record = {"version": 1, "boot_id": self._boot_id, "session": self._session, "pid": os.getpid(),
              "process_start_ticks": self._process_start_ticks,
              "mono_ns": now, "state": state, "handovers": self.handovers,
              "remote_output_mono_ns": self._output_ns if self.chestnut and not closed else 0}
    if self.chestnut and not closed:
      spec = self.joined.spec
      record["artifact_sha256"] = spec.sha256
      record["artifact_nbytes"] = spec.nbytes
      if isinstance(spec.checkpoint, str):
        record["model_checkpoint"] = spec.checkpoint[:256]
    with self._runtime_condition:
      self._runtime_pending = record
      self._runtime_condition.notify()

  def _write_runtime(self):
    while True:
      with self._runtime_condition:
        self._runtime_condition.wait_for(lambda: self._runtime_pending is not None or self._runtime_closed)
        if self._runtime_pending is None:
          return
        record, self._runtime_pending = self._runtime_pending, None
        closed = self._runtime_closed
      try:
        adapter().put("JetlinkRuntime", record, block=True)
      except Exception:
        adapter().log.exception("Jetlink runtime status unavailable")
      if closed:
        return

  def close(self):
    if self._runtime_closed:
      return
    self.joined.close()
    self.publish_runtime(closed=True)
    with self._runtime_condition:
      self._runtime_closed = True
      self._runtime_condition.notify()


def attach(small, cam_w, cam_h, *, chestnut=False, recovery=False):
  if chestnut or recovery or not supported_device():
    return small
  link = get_jetlink()
  if link is None:
    return small
  try:
    if not link.prepare():
      return small
    face = SmallModelFace(small)
    joined = link.attach(face, cam_w, cam_h)
    if joined is None or joined is face:
      return small
    model = JetlinkModel(joined, small)
    import atexit
    atexit.register(model.close)
    return model
  except Exception:
    adapter().log.exception("Jetlink startup failed; retaining local model")
    return small
