import io
import struct
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
  assert not ready
  assert stable_since is None


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


def test_external_gpu_load_finishes_before_native_model_can_start(monkeypatch):
  calls = []

  class FakeModelState:
    uses_external_gpu = True

    def __init__(self, cam_w, cam_h, external_gpu_active, model_id_override, write_model_version):
      calls.append(("model", cam_w, cam_h, external_gpu_active, model_id_override, write_model_version))

    def warmup(self):
      calls.append("warmup")

  monkeypatch.setattr(modeld, "wait_usbgpu_link", lambda: calls.append("link"))
  monkeypatch.setattr(modeld, "wait_for_external_gpu_power_ready", lambda CP: calls.append(("power", CP)))
  monkeypatch.setattr(modeld, "_set_hcq_wait_timeout", lambda timeout: calls.append(("timeout", timeout)))
  monkeypatch.setattr(modeld, "_close_tinygrad_disk_cache_connection", lambda: calls.append("close_cache"))
  monkeypatch.setattr(modeld, "ModelState", FakeModelState)
  monkeypatch.setattr(
    modeld,
    "tinygrad_dev_config",
    lambda *_args: (_ for _ in ()).throw(AssertionError("runtime must not change tinygrad's process-global DEV")),
  )

  loaded = modeld._load_external_gpu_model(1928, 1208, "big-model", "car-params")

  assert isinstance(loaded, FakeModelState)
  assert calls == [
    ("power", "car-params"),
    ("timeout", modeld.BIG_MODEL_LOAD_WAIT_TIMEOUT_MS),
    "link",
    ("model", 1928, 1208, True, "big-model", False),
    "warmup",
    "close_cache",
    ("timeout", modeld.BIG_MODEL_RUN_WAIT_TIMEOUT_MS),
  ]


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
