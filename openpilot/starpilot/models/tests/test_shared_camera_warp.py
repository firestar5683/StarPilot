from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
from tinygrad import Context, dtypes

from openpilot.starpilot.models.runner import CatalogModelState
from openpilot.starpilot.models.tests.test_runner import artifact_fixture


def fake_warp(shape=(2, 6, 2, 2), dtype=dtypes.uint8, device="CPU"):
  return SimpleNamespace(shape=shape, dtype=dtype, device=device)


def make_runner(artifact=None, camera=(8, 8)):
  artifact = artifact_fixture() if artifact is None else artifact
  artifact[camera] = Mock(return_value=fake_warp())
  with Context(DEV="CPU:LLVM"), patch("openpilot.starpilot.models.runner.load_oob", return_value=artifact):
    runner = CatalogModelState(camera[0], camera[1], Path("verified.pkl"), "v15", False)
  return runner


def frame_inputs(runner):
  frames = {name: np.zeros(runner.frame_buf_size, dtype=np.uint8) for name in runner.vision_input_names}
  transforms = {name: np.eye(3, dtype=np.float32) for name in runner.vision_input_names}
  inputs = {"desire_pulse": np.array([0, 1, 0, 0, 0, 0, 0, 0], dtype=np.float32),
            "prev_action": np.array([2, 3], dtype=np.float32)}
  return frames, transforms, inputs


class TestSharedCameraWarp(unittest.TestCase):
  def test_shared_frame_runs_one_warp_and_two_independent_policies(self):
    lateral, longitudinal, ordinary = (make_runner() for _ in range(3))
    frames, transforms, inputs = frame_inputs(lateral)
    lat_output = lateral.run(frames, transforms, inputs)
    packet = lateral.last_warp
    callback = Mock()
    long_output = longitudinal.run(frames, transforms, inputs, callback, shared_warp=packet)
    normal_output = ordinary.run(frames, transforms, inputs)
    lateral.warp_enqueue.assert_called_once()
    longitudinal.warp_enqueue.assert_not_called()
    ordinary.warp_enqueue.assert_called_once()
    callback.assert_called_once_with()
    self.assertIs(longitudinal.run_policy.call_args.kwargs["warped"], packet.tensor)
    self.assertIs(longitudinal.last_warp, packet)
    for key in lat_output:
      np.testing.assert_array_equal(long_output[key], normal_output[key])
    for key in lateral.input_queues:
      self.assertIsNot(lateral.input_queues[key], longitudinal.input_queues[key])
    for key in lateral.npy:
      self.assertFalse(np.shares_memory(lateral.npy[key], longitudinal.npy[key]))
    longitudinal.run(frames, transforms, {**inputs, "desire_pulse": np.zeros(8)})
    np.testing.assert_array_equal(lateral.prev_desire, inputs["desire_pulse"])
    np.testing.assert_array_equal(longitudinal.prev_desire, np.zeros(8))
    self.assertIs(lateral.last_warp, packet)

  def test_history_length_and_sampling_remain_private(self):
    artifact = artifact_fixture()
    artifact["metadata"]["model"]["input_shapes"]["img"] = (1, 6, 2, 2)
    artifact["metadata"]["model"]["input_shapes"]["big_img"] = (1, 6, 2, 2)
    artifact["frame_skip"] = 1
    lateral, longitudinal = make_runner(), make_runner(artifact)
    self.assertEqual(lateral.camera_warp_descriptor, longitudinal.camera_warp_descriptor)
    self.assertNotEqual(lateral.input_queues["img_q"].shape, longitudinal.input_queues["img_q"].shape)
    args = frame_inputs(lateral)
    lateral.run(*args)
    longitudinal.run(*args, shared_warp=lateral.last_warp)
    longitudinal.warp_enqueue.assert_not_called()

  def test_descriptor_and_actual_tensor_mismatches_rejected_before_state_update(self):
    lateral, longitudinal = make_runner(), make_runner()
    args = frame_inputs(lateral)
    lateral.run(*args)
    packet = lateral.last_warp
    descriptor = packet.descriptor
    mismatches = [replace(packet, descriptor=replace(descriptor, camera_size=(16, 8))),
                  replace(packet, descriptor=replace(descriptor, nv12_layout=(1, 2, 3, 4))),
                  replace(packet, descriptor=replace(descriptor, image_layouts=((4, 4), (4, 4)))),
                  replace(packet, descriptor=replace(descriptor, device="AMD")),
                  replace(packet, tensor=fake_warp(shape=(2, 6, 4, 4))),
                  replace(packet, tensor=fake_warp(dtype=dtypes.float32)),
                  replace(packet, tensor=fake_warp(device="AMD"))]
    for mismatch in mismatches:
      with self.subTest(packet=mismatch), self.assertRaises(ValueError):
        longitudinal.run(*args, shared_warp=mismatch)
    longitudinal.run_policy.assert_not_called()
    np.testing.assert_array_equal(longitudinal.prev_desire, np.zeros(8))

  def test_new_buffers_or_transforms_cannot_reuse_camera_warp(self):
    lateral, longitudinal = make_runner(), make_runner()
    frames, transforms, inputs = frame_inputs(lateral)
    lateral.run(frames, transforms, inputs)
    packet = lateral.last_warp
    other_frames = {key: value.copy() for key, value in frames.items()}
    with self.assertRaisesRegex(ValueError, "frame/transforms"):
      longitudinal.run(other_frames, transforms, inputs, shared_warp=packet)
    changed = {key: value.copy() for key, value in transforms.items()}
    changed["big_img"][0, 2] = 1
    with self.assertRaisesRegex(ValueError, "frame/transforms"):
      longitudinal.run(frames, changed, inputs, shared_warp=packet)
    longitudinal.run_policy.assert_not_called()

  def test_old_packet_and_repeat_consumption_rejected(self):
    lateral, longitudinal = make_runner(), make_runner()
    args = frame_inputs(lateral)
    lateral.run(*args)
    packet = lateral.last_warp
    longitudinal.run(*args, shared_warp=packet)
    with self.assertRaisesRegex(ValueError, "already consumed"):
      longitudinal.run(*args, shared_warp=packet)
    lateral.run(*args)
    with self.assertRaisesRegex(ValueError, "stale"):
      make_runner().run(*args, shared_warp=packet)

  def test_failed_output_and_warmup_invalidate_exposed_packet(self):
    producer = make_runner()
    args = frame_inputs(producer)
    producer.run(*args)
    packet = producer.last_warp
    producer.run_policy.return_value = (Mock(numpy=lambda: np.array([np.nan])),)
    with self.assertRaisesRegex(ValueError, "not finite"):
      producer.run(*args)
    self.assertIsNone(producer.last_warp)
    with self.assertRaisesRegex(ValueError, "stale"):
      make_runner().run(*args, shared_warp=packet)
    producer = make_runner()
    producer.run(*frame_inputs(producer))
    producer.warmup()
    self.assertIsNone(producer.last_warp)
    self.assertIsNone(producer._last_shared_warp)

  def test_borrowed_packet_relay_keeps_original_producer_lifetime(self):
    for invalidate in ("advance", "reset"):
      producer, relay, consumer = (make_runner() for _ in range(3))
      args = frame_inputs(producer)
      producer.run(*args)
      packet = producer.last_warp
      relay.run(*args, shared_warp=packet)
      self.assertIs(relay.last_warp, packet)
      self.assertIs(relay.last_warp.producer(), producer)
      if invalidate == "advance":
        producer.run(*args)
      else:
        producer._reset_state()
      with self.subTest(invalidate=invalidate), self.assertRaisesRegex(ValueError, "stale"):
        consumer.run(*args, shared_warp=relay.last_warp)
      consumer.run_policy.assert_not_called()
      consumer.warp_enqueue.assert_not_called()

  def test_history_in_warp_cannot_share_but_default_path_is_preserved(self):
    artifact = artifact_fixture()
    artifact["image_history_pipeline"] = "warp"
    consumer = make_runner(artifact)
    producer = make_runner()
    args = frame_inputs(producer)
    producer.run(*args)
    with self.assertRaisesRegex(ValueError, "history"):
      consumer.run(*args, shared_warp=producer.last_warp)
    consumer.warp_enqueue.return_value = ("road-history", "wide-history")
    consumer.run(*args)
    consumer.warp_enqueue.assert_called_once()
    self.assertEqual(consumer.run_policy.call_args.kwargs["img"], "road-history")
    self.assertEqual(consumer.run_policy.call_args.kwargs["big_img"], "wide-history")
    self.assertIsNone(consumer.last_warp)
