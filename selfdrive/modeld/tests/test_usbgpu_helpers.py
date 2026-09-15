import io
import struct
import threading
from types import MethodType
from types import SimpleNamespace

import numpy as np
import pytest

from openpilot.selfdrive.modeld import modeld
from openpilot.selfdrive.modeld.helpers import dump_oob, load_oob, tinygrad_dev_config
from scripts import model_compiler


def test_external_gpu_keeps_the_native_device_available():
  assert tinygrad_dev_config(True, tici=True) == "QCOM;USB+AMD:LLVM"
  assert tinygrad_dev_config(False, tici=True) == "QCOM"
  assert tinygrad_dev_config(True, tici=False) == "CPU:LLVM;USB+AMD:LLVM"


def test_external_gpu_selects_amd_without_probing_other_backends(monkeypatch, tmp_path):
  from openpilot.selfdrive.modeld import helpers

  monkeypatch.setattr(helpers, "TG_INPUT_DEVICES_PATH", tmp_path / "missing.json")
  monkeypatch.setattr(helpers, "_default_tinygrad_backend", lambda: "QCOM")
  monkeypatch.setattr(
    helpers.Device,
    "get_available_devices",
    lambda: (_ for _ in ()).throw(AssertionError("must not probe every tinygrad backend")),
  )

  assert helpers.get_tg_input_devices("selfdrive.modeld.modeld", usbgpu=True) == {
    "WARP_DEV": "QCOM",
    "QUEUE_DEV": "AMD",
  }


def test_external_gpu_uses_a_longer_load_watchdog():
  assert modeld.BIG_MODEL_LOAD_WAIT_TIMEOUT_MS == 30000
  assert modeld.BIG_MODEL_RUN_WAIT_TIMEOUT_MS == 3000


def test_external_gpu_voltage_uses_hardware_specific_source():
  panda_type = modeld.log.PandaState.PandaType
  panda_states = [SimpleNamespace(pandaType=panda_type.dos, voltage=230)]
  peripheral_state = SimpleNamespace(pandaType=panda_type.dos, voltage=13550)

  assert modeld._external_gpu_power_voltage("tici", panda_states, peripheral_state) == 13550

  panda_states = [SimpleNamespace(pandaType=panda_type.tres, voltage=14100)]
  peripheral_state = SimpleNamespace(pandaType=panda_type.tres, voltage=12800)
  assert modeld._external_gpu_power_voltage("tizi", panda_states, peripheral_state) == 14100

  panda_states = [SimpleNamespace(pandaType=panda_type.cuatro, voltage=13200)]
  peripheral_state = SimpleNamespace(pandaType=panda_type.cuatro, voltage=12800)
  assert modeld._external_gpu_power_voltage("mici", panda_states, peripheral_state) == 13200


def test_external_gpu_power_must_remain_stable():
  ready, stable_since = modeld._external_gpu_power_ready(9900, 10.0, None)
  assert not ready
  assert stable_since is None

  ready, stable_since = modeld._external_gpu_power_ready(14100, 11.0, stable_since)
  assert not ready
  assert stable_since == 11.0

  ready, stable_since = modeld._external_gpu_power_ready(14100, 13.9, stable_since)
  assert not ready
  ready, stable_since = modeld._external_gpu_power_ready(14100, 14.0, stable_since)
  assert ready

  ready, stable_since = modeld._external_gpu_power_ready(11900, 15.0, stable_since)
  assert ready
  assert stable_since == 11.0


def test_external_gpu_power_wait_times_out(monkeypatch):
  panda_type = modeld.log.PandaState.PandaType

  class FakeSubMaster:
    def __init__(self, _services):
      self.updated = {}
      self.data = {
        "pandaStates": [SimpleNamespace(pandaType=panda_type.cuatro, voltage=9000)],
        "peripheralState": SimpleNamespace(pandaType=panda_type.cuatro, voltage=9000),
      }

    def update(self, _timeout):
      pass

    def __getitem__(self, key):
      return self.data[key]

  times = iter((10.0, 70.0))
  monkeypatch.setattr(modeld.HARDWARE, "get_device_type", lambda: "mici")
  monkeypatch.setattr(modeld, "SubMaster", FakeSubMaster)
  monkeypatch.setattr(modeld, "time", SimpleNamespace(monotonic=lambda: next(times)))

  with pytest.raises(TimeoutError, match="after 60s"):
    modeld.wait_for_external_gpu_power_ready()


def test_egmp_ready_uses_accelerator_ready_bit():
  bus = 1
  not_ready = SimpleNamespace(address=0x35, src=bus, dat=bytes([0, 0, 0, 0x00]))
  wrong_bus = SimpleNamespace(address=0x35, src=0, dat=bytes([0, 0, 0, 0x40]))
  ready = SimpleNamespace(address=0x35, src=bus, dat=bytes([0, 0, 0, 0x40]))

  assert not modeld._egmp_vehicle_ready([not_ready, wrong_bus], bus)
  assert modeld._egmp_vehicle_ready([not_ready, ready], bus)


def test_external_gpu_signal_wait_yields_between_usb_polls(monkeypatch):
  from tinygrad.runtime import ops_amd

  sleeps = []
  monkeypatch.setattr(ops_amd.time, "sleep", sleeps.append)
  signal = ops_amd.AMDSignal.__new__(ops_amd.AMDSignal)
  signal.should_return = False
  signal.owner = SimpleNamespace(is_usb=lambda: True, iface=SimpleNamespace(sleep=lambda _: None))

  signal._sleep(0)

  assert sleeps == [ops_amd.AMD_USB_POLL_US / 1e6]


def test_native_amd_signal_keeps_existing_short_wait_behavior():
  from tinygrad.runtime import ops_amd

  sleeps = []
  signal = ops_amd.AMDSignal.__new__(ops_amd.AMDSignal)
  signal.should_return = False
  signal.owner = SimpleNamespace(is_usb=lambda: False, iface=SimpleNamespace(sleep=sleeps.append))

  signal._sleep(199)

  assert sleeps == []

  signal._sleep(201)

  assert sleeps == [200]


def test_external_gpu_wait_timeout_updates_tinygrad_cache(monkeypatch):
  from tinygrad.helpers import getenv

  try:
    monkeypatch.setenv("HCQDEV_WAIT_TIMEOUT_MS", "30000")
    getenv.cache_clear()
    assert getenv("HCQDEV_WAIT_TIMEOUT_MS", 0) == 30000

    modeld._set_hcq_wait_timeout(3000)
    assert getenv("HCQDEV_WAIT_TIMEOUT_MS", 0) == 3000
  finally:
    getenv.cache_clear()


def test_chestnut_telemetry_is_bounded_when_amd_is_unavailable(monkeypatch):
  from cereal.services import SERVICE_LIST

  class FakePubMaster:
    def __init__(self):
      self.sent = []

    def send(self, service, message):
      self.sent.append((service, message))

  publisher = FakePubMaster()
  monkeypatch.setattr(modeld, "Device", SimpleNamespace(_opened_devices=set()))

  telemetry = modeld.ChestnutState(publisher, big=True)
  telemetry.send()

  assert SERVICE_LIST["chestnutState"].frequency == 10.0
  assert len(publisher.sent) == 1
  service, message = publisher.sent[0]
  assert service == "chestnutState"
  assert message.which() == "chestnutState"
  assert not message.valid


def test_chestnut_power_telemetry_works_before_amd_initializes(monkeypatch):
  class FakePubMaster:
    def __init__(self):
      self.sent = []

    def send(self, service, message):
      self.sent.append((service, message))

  class FakeHandle:
    def controlRead(self, *_args, **_kwargs):
      return struct.pack("<Hh?", 12100, 850, True)

    def close(self):
      pass

  class FakeContext:
    def openByVendorIDAndProductID(self, *_args, **_kwargs):
      return FakeHandle()

    def close(self):
      pass

  publisher = FakePubMaster()
  monkeypatch.setattr(modeld, "Device", SimpleNamespace(_opened_devices=set()))
  monkeypatch.setattr(modeld.usb1, "USBContext", FakeContext)

  telemetry = modeld.ChestnutState(publisher, big=False)
  telemetry.send()

  _, message = publisher.sent[0]
  assert message.valid
  assert message.chestnutState.supplyVoltage == 12100
  assert message.chestnutState.supplyCurrent == 850
  assert message.chestnutState.supplyFault


def test_tinygrad_disk_cache_connection_is_closed_between_models(monkeypatch):
  import tinygrad.helpers as tinygrad_helpers

  class FakeConnection:
    def __init__(self):
      self.closed = False

    def close(self):
      self.closed = True

  connection = FakeConnection()
  monkeypatch.setattr(tinygrad_helpers, "_db_connection", connection)

  modeld._close_tinygrad_disk_cache_connection()

  assert connection.closed
  assert tinygrad_helpers._db_connection is None


def test_tinygrad_thread_local_cache_holder_survives_cleanup(monkeypatch):
  import threading
  import tinygrad.helpers as tinygrad_helpers

  class FakeConnection:
    def __init__(self):
      self.closed = False

    def close(self):
      self.closed = True

  holder = threading.local()
  connection = FakeConnection()
  holder.conn = connection
  monkeypatch.setattr(tinygrad_helpers, "_db_connection", holder)

  modeld._close_tinygrad_disk_cache_connection()

  assert connection.closed
  assert tinygrad_helpers._db_connection is holder
  assert not hasattr(holder, "conn")


def test_tinygrad_empty_thread_local_cache_holder_is_safe(monkeypatch):
  import threading
  import tinygrad.helpers as tinygrad_helpers

  holder = threading.local()
  monkeypatch.setattr(tinygrad_helpers, "_db_connection", holder)

  modeld._close_tinygrad_disk_cache_connection()

  assert tinygrad_helpers._db_connection is holder


def _stub_big_model_loader(monkeypatch, calls, *, uses_external_gpu=True, model_error=None):
  class FakeModelState:
    def __init__(self, cam_w, cam_h, external_gpu_active, model_id_override, write_model_version,
                 model_version_override):
      calls.append(("model", cam_w, cam_h, external_gpu_active, model_id_override,
                    write_model_version, model_version_override))
      if model_error is not None:
        raise model_error
      self.uses_external_gpu = uses_external_gpu

    def warmup(self):
      calls.append("warmup")

  monkeypatch.setattr(modeld, "set_core_affinity", lambda cores: calls.append(("affinity", tuple(cores))))
  monkeypatch.setattr(modeld, "wait_usbgpu_link", lambda: calls.append("link"))
  monkeypatch.setattr(modeld, "wait_for_external_gpu_power_ready",
                      lambda CP, cancel=None: calls.append(("power", CP)))
  monkeypatch.setattr(modeld, "_close_tinygrad_disk_cache_connection", lambda: calls.append("close_cache"))
  monkeypatch.setattr(modeld, "ModelState", FakeModelState)
  return FakeModelState


def test_background_big_model_load_leaves_the_running_model_untouched(monkeypatch):
  calls = []
  fake_model_state = _stub_big_model_loader(monkeypatch, calls)
  # The small model is already driving on these process-global settings, so the background
  # load must not touch tinygrad's DEV, its HCQ watchdog, or its shared buffer UOp cache.
  for name, detail in (
    ("tinygrad_dev_config", "runtime must not change tinygrad's process-global DEV"),
    ("_set_hcq_wait_timeout", "the background load must not move the running model's HCQ watchdog"),
    ("_isolate_next_model_artifact_load", "the background load must not evict the running model's buffers"),
  ):
    monkeypatch.setattr(modeld, name, lambda *_args, _d=detail: (_ for _ in ()).throw(AssertionError(_d)))

  loader = modeld.BigModelLoader(1928, 1208, "car-params")
  assert loader.start("big-model", "v15")
  loader._thread.join(timeout=10)

  loaded, error = loader.take()
  assert isinstance(loaded, fake_model_state)
  assert error == ""
  assert calls == [
    ("affinity", tuple(sorted(modeld.BIG_MODEL_LOADER_CORES))),
    ("power", "car-params"),
    "link",
    ("model", 1928, 1208, True, "big-model", False, "v15"),
    "warmup",
    "close_cache",
  ]


def test_big_model_load_gives_up_instead_of_loading_forever(monkeypatch):
  # A load stuck inside tinygrad cannot be interrupted, so the timeout is what stops modeld
  # reporting "loading" for the rest of the drive while the small model quietly drives.
  release = threading.Event()
  calls = []

  class HangingModelState:
    uses_external_gpu = True

    def __init__(self, *_a, **_k):
      release.wait(timeout=10)

    def warmup(self):
      pass

  monkeypatch.setattr(modeld, "set_core_affinity", lambda cores: None)
  monkeypatch.setattr(modeld, "wait_usbgpu_link", lambda: None)
  monkeypatch.setattr(modeld, "wait_for_external_gpu_power_ready", lambda CP, cancel=None: None)
  monkeypatch.setattr(modeld, "_close_tinygrad_disk_cache_connection", lambda: calls.append("close"))
  monkeypatch.setattr(modeld, "ModelState", HangingModelState)

  loader = modeld.BigModelLoader(1928, 1208, "car-params")
  loader.start("big-model", "v15")
  try:
    assert loader.in_progress
    assert not loader.timed_out

    # Pretend the load has been running well past its budget.
    loader.started_t -= modeld.BIG_MODEL_LOAD_TIMEOUT_SECONDS + 1
    assert loader.timed_out
    # take() must not hand over a model from a load we already gave up on.
    assert loader.take() == (None, "")
  finally:
    release.set()
    loader._thread.join(timeout=10)


def test_big_model_load_timeout_leaves_room_for_a_normal_load():
  # A healthy load measured ~26 s on device; the budget must not cut those off.
  assert modeld.BIG_MODEL_LOAD_TIMEOUT_SECONDS > 60


def test_chestnut_telemetry_is_suppressed_while_a_background_load_runs():
  """Telemetry shares Chestnut's USB device with the model weight transfer.

  ChestnutState._read_ina() issues USB control reads on the same device tinygrad streams
  weights over. The old code loaded before the publish loop existed so the two never
  overlapped; loading in the background makes them concurrent, which stalls the transfer
  until it times out. Captured on four drives: the load never completed while telemetry
  was polling at 10 Hz, and chestnutState first appeared only after the load on the one
  drive that succeeded.
  """
  import ast
  from pathlib import Path

  source = (Path(modeld.__file__).with_name("modeld.py")).read_text(encoding="utf-8")
  main_fn = next(n for n in ast.parse(source).body
                 if isinstance(n, ast.FunctionDef) and n.name == "main")
  assign = next(
    node for node in ast.walk(main_fn)
    if isinstance(node, ast.Assign)
    and any(isinstance(t, ast.Name) and t.id == "send_chestnut" for t in node.targets)
  )
  guard = ast.dump(assign.value)
  assert "big_loader" in guard and "in_progress" in guard, \
    "chestnutState polling must be gated on the background loader being idle"


def test_background_big_model_loader_avoids_the_realtime_cores():
  """The loader must not share a core with modeld or the camera pipeline.

  modeld is SCHED_FIFO on core 7 and threads inherit its affinity, so a loader left there is
  starved behind the 20 Hz publish loop. Putting it on camerad's core instead stalls frame
  delivery: measured p95 on roadCameraState went 50.8 ms -> 108.9 ms for the whole load.
  """
  assert modeld.BIG_MODEL_LOADER_CORES

  reserved = {
    7: "modeld (config_realtime_process(7, 54)) and dmonitoringmodeld",
    6: "camerad (system/camerad/main.cc set_core_affinity({6}))",
    5: "plannerd, radard, selfdrived, starpilot_process",
    4: "card and controlsd",
  }
  for core, owner in reserved.items():
    assert core not in modeld.BIG_MODEL_LOADER_CORES, f"core {core} belongs to {owner}"

  # camerad pins itself in C++, which is easy to miss when auditing Python callers.
  import re
  from pathlib import Path

  camerad_main = Path(modeld.__file__).parents[2] / "system" / "camerad" / "main.cc"
  pinned = re.search(r"set_core_affinity\(\{([0-9,\s]+)\}\)", camerad_main.read_text(encoding="utf-8"))
  assert pinned, "could not find camerad's core affinity"
  camerad_cores = {int(c) for c in pinned.group(1).split(",") if c.strip()}
  assert not (camerad_cores & modeld.BIG_MODEL_LOADER_CORES), \
    f"the loader must not share camerad's cores {sorted(camerad_cores)}"


@pytest.mark.parametrize("failure", [
  dict(model_error=RuntimeError("artifact is corrupt")),
  dict(uses_external_gpu=False),
])
def test_background_big_model_load_reports_failure_without_a_model(monkeypatch, failure):
  calls = []
  _stub_big_model_loader(monkeypatch, calls, **failure)

  loader = modeld.BigModelLoader(1928, 1208, "car-params")
  loader.start("big-model", "v15")
  loader._thread.join(timeout=10)

  loaded, error = loader.take()
  assert loaded is None
  assert error
  assert not loader.in_progress
  # Even a failed load must release the loader thread's own tinygrad cache handle.
  assert "close_cache" in calls


def test_background_big_model_load_is_handed_over_exactly_once(monkeypatch):
  calls = []
  fake_model_state = _stub_big_model_loader(monkeypatch, calls)

  loader = modeld.BigModelLoader(1928, 1208, "car-params")
  loader.start("big-model", "v15")
  loader._thread.join(timeout=10)

  assert isinstance(loader.take()[0], fake_model_state)
  # A second take must not promote the same model again.
  assert loader.take() == (None, "")


def test_cancelled_big_model_load_never_builds_a_model(monkeypatch):
  calls = []

  def cancelling_power_wait(CP, cancel=None):
    calls.append(("power", CP))
    cancel.set()
    raise modeld.BigModelLoadCancelled("cancelled while waiting for external GPU power")

  _stub_big_model_loader(monkeypatch, calls)
  monkeypatch.setattr(modeld, "wait_for_external_gpu_power_ready", cancelling_power_wait)

  loader = modeld.BigModelLoader(1928, 1208, "car-params")
  loader.start("big-model", "v15")
  loader._thread.join(timeout=10)

  loaded, error = loader.take()
  assert loaded is None
  assert error
  assert not any(call[0] == "model" for call in calls if isinstance(call, tuple))


def test_external_gpu_power_wait_aborts_when_the_loader_is_cancelled(monkeypatch):
  cancel = threading.Event()
  cancel.set()
  monkeypatch.setattr(modeld, "SubMaster",
                      lambda *_a, **_k: pytest.fail("a cancelled load must not start waiting on power"))

  with pytest.raises(modeld.BigModelLoadCancelled):
    modeld.wait_for_external_gpu_power_ready("car-params", cancel=cancel)


def test_big_model_promotion_waits_for_the_driver_to_disengage(monkeypatch):
  """Drive the real collect-and-promote blocks lifted out of main()'s loop."""
  import ast
  from pathlib import Path

  source = (Path(modeld.__file__).with_name("modeld.py")).read_text(encoding="utf-8")
  main_fn = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "main")
  def names(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}

  collect_block = next(n for n in ast.walk(main_fn)
                       if isinstance(n, ast.If) and "big_loader" in names(n.test)
                       and "in_progress" in ast.dump(n.test))
  promote_block = next(n for n in ast.walk(main_fn)
                       if isinstance(n, ast.If) and "_big_model_swap_allowed" in names(n.test))
  promote = compile(ast.Module(body=[collect_block, promote_block], type_ignores=[]),
                    "<promotion>", "exec")

  class FakeModel:
    model_id = "big-model"
    policy_generation = "v15"

    def __init__(self):
      self.reset = 0

    def _reset_state(self):
      self.reset += 1

  class FakeLoader:
    def __init__(self, model):
      self.in_progress = True
      self._model = model

    def take(self):
      return self._model, ""

  written = {}
  big = FakeModel()
  loader = FakeLoader(big)
  small = FakeModel()
  small.model_id = "small-model"
  scope = {
    "big_loader": loader, "big_model": None, "model": small, "small_model": small,
    "params": SimpleNamespace(put_bool=lambda k, v: written.__setitem__(k, v),
                              put=lambda k, v: written.__setitem__(k, v)),
    "cloudlog": SimpleNamespace(warning=lambda *_a: None, error=lambda *_a: None),
    "vipc_dropped_frames": 0, "live_calib_seen": True, "external_gpu_active": False,
    "run_count": 99, "frame_dropped_filter": SimpleNamespace(x=5.0),
    "PublishState": lambda: "fresh", "publish_state": "stale",
    "prev_action": "stale", "log": modeld.log, "chestnut_state": SimpleNamespace(big=False),
    "set_runtime_model_params": lambda *_a: None,
    "_big_model_swap_allowed": modeld._big_model_swap_allowed,
  }
  scope["sm"] = type("SM", (), {
    "__getitem__": lambda _s, k: SimpleNamespace(enabled=scope["_engaged"]),
    "alive": {"carControl": True, "carState": True},
  })()

  # Still loading: nothing is collected and the small model keeps driving.
  scope["_engaged"] = True
  exec(promote, scope)  # noqa: S102
  assert scope["model"] is small and scope["big_model"] is None

  # Load finishes while engaged: the model is collected but must NOT be promoted.
  loader.in_progress = False
  exec(promote, scope)  # noqa: S102
  assert scope["big_model"] is big
  assert scope["model"] is small, "must not swap models while the driver is engaged"
  assert written["UsbGpuPending"] is True
  assert written["UsbGpuLoading"] is False
  assert big.reset == 0

  # The driver disengages: now the big model takes over.
  scope["_engaged"] = False
  exec(promote, scope)  # noqa: S102
  assert scope["model"] is big
  assert big.reset == 1, "temporal queues must be reset before the big model drives"
  assert scope["run_count"] == 0 and scope["frame_dropped_filter"].x == 0.
  assert scope["publish_state"] == "fresh" and scope["prev_action"] != "stale"
  assert written["UsbGpuActive"] is True and written["UsbGpuPending"] is False
  assert scope["chestnut_state"].big is True


@pytest.mark.parametrize("kwargs,expected", [
  (dict(), True),
  (dict(engaged=True), False),
  (dict(carcontrol_alive=False), False),
  (dict(carstate_alive=False), False),
  (dict(vipc_dropped_frames=1), False),
  (dict(live_calib_seen=False), False),
])
def test_big_model_swap_only_while_disengaged_with_fresh_state(kwargs, expected):
  defaults = dict(engaged=False, carcontrol_alive=True, carstate_alive=True,
                  vipc_dropped_frames=0, live_calib_seen=True)
  assert modeld._big_model_swap_allowed(**(defaults | kwargs)) is expected


def test_external_gpu_nonfinite_outputs_trigger_fallback(monkeypatch):
  class FakeTensor:
    @staticmethod
    def from_blob(*_args, **_kwargs):
      return FakeTensor()

  class FakeOutput:
    def numpy(self):
      return np.array([np.nan], dtype=np.float32)

  state = modeld.ModelState.__new__(modeld.ModelState)
  state.uses_external_gpu = True
  state.frame_buf_size = 4
  state.vision_input_names = ["img", "big_img"]
  state.road_key = "img"
  state.wide_key = "big_img"
  state._blob_cache = {}
  state._warp_dev = "CPU"
  state._queue_dev = "CPU"
  state.desire_key = "desire_pulse"
  state.prev_desired_curv_key = None
  state.numpy_inputs = {"desire_pulse": np.zeros(8, dtype=np.float32)}
  state.npy = {
    "desire": np.zeros(8, dtype=np.float32),
    "tfm": np.zeros((3, 3), dtype=np.float32),
    "big_tfm": np.zeros((3, 3), dtype=np.float32),
  }
  state.prev_desire = np.zeros(8, dtype=np.float32)
  state.warp_input_keys = ()
  state.policy_input_keys = ()
  state.input_queues = {}
  state.image_history_pipeline = modeld.IMAGE_HISTORY_IN_POLICY
  state.warp_enqueue = lambda **_kwargs: object()
  state.run_policy = lambda **_kwargs: (FakeOutput(),)
  monkeypatch.setattr(modeld, "Tensor", FakeTensor)
  buffers = {
    "img": SimpleNamespace(data=bytearray(4)),
    "big_img": SimpleNamespace(data=bytearray(4)),
  }
  transforms = {
    "img": np.eye(3, dtype=np.float32),
    "big_img": np.eye(3, dtype=np.float32),
  }
  inputs = {"desire_pulse": np.zeros(8, dtype=np.float32)}

  callbacks = []
  with pytest.raises(RuntimeError, match="external GPU model output not finite"):
    state.run(buffers, transforms, inputs, False, lambda: callbacks.append("sent"))
  assert callbacks == ["sent"]


def test_out_of_band_artifact_round_trip():
  artifact = {"weights": np.arange(32, dtype=np.float32), "metadata": {"version": 1}}
  stream = io.BytesIO()
  dump_oob(artifact, stream)
  stream.seek(0)

  restored = load_oob(stream)
  assert restored["metadata"] == artifact["metadata"]
  np.testing.assert_array_equal(restored["weights"], artifact["weights"])


def test_external_gpu_probe_matches_upstream_retry_loop(monkeypatch):
  from openpilot.system.hardware.chestnut import flash

  calls = []
  results = iter((False, False, True))
  monkeypatch.setattr(flash, "link_up", lambda: calls.append("probe") or next(results))
  monkeypatch.setattr(model_compiler.time, "sleep", lambda seconds: calls.append(("sleep", seconds)))

  model_compiler.wait_for_external_gpu()

  assert calls == ["probe", ("sleep", 1), "probe", ("sleep", 1), "probe"]


def test_external_gpu_warmup_runs_a_complete_frame_and_resets(monkeypatch):
  class FakeTensor:
    @staticmethod
    def zeros(shape, **kwargs):
      calls.append(("tensor", shape, kwargs))
      return FakeTensor()

    def realize(self):
      return self

  calls = []
  state = modeld.ModelState.__new__(modeld.ModelState)
  state.frame_buf_size = 32
  state.vision_input_names = ["img", "big_img"]
  state._blob_cache = {}
  state._warp_dev = "QCOM"
  state.desire_key = "desire"
  state.prev_desired_curv_key = "prev_desired_curv"
  state.numpy_inputs = {
    "desire": np.zeros((1, 8), dtype=np.float32),
    "traffic_convention": np.zeros((1, 2), dtype=np.float32),
    "action_t": np.zeros((1, 2), dtype=np.float32),
    "prev_desired_curv": np.zeros((1, 5, 1), dtype=np.float32),
  }

  def fake_run(self, bufs, transforms, inputs, prepare_only):
    calls.append((
      "run",
      {key: value.shape for key, value in bufs.items()},
      {key: value.shape for key, value in transforms.items()},
      {key: value.shape for key, value in inputs.items()},
      prepare_only,
    ))
    return {}

  state.run = MethodType(fake_run, state)
  state._reset_state = MethodType(lambda self: calls.append(("reset",)), state)
  monkeypatch.setattr(modeld, "Tensor", FakeTensor)

  state.warmup()

  assert calls == [
    ("tensor", (32,), {"dtype": "uint8", "device": "QCOM"}),
    ("tensor", (32,), {"dtype": "uint8", "device": "QCOM"}),
    (
      "run",
      {"img": (32,), "big_img": (32,)},
      {"img": (3, 3), "big_img": (3, 3)},
      {"desire": (8,), "traffic_convention": (2,), "action_t": (2,)},
      False,
    ),
    ("reset",),
  ]
