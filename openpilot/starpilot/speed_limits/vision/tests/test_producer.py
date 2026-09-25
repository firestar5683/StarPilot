"""Exercise the producer loop against the current camera API and typed wire."""

from collections import deque
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from openpilot.cereal import messaging
from openpilot.cereal.visionipc import VisionStreamType
from openpilot.starpilot.speed_limits.vision import producer
from openpilot.starpilot.speed_limits.vision.model import Detection, VisionModelCore


class EndProducer(BaseException):
  pass


class TestVisionProducer(unittest.TestCase):
  def run_frame(self, streams, *, completion_age_ns=10_000_000):
    core = Mock()
    core.observe.return_value = (55, 0.9, 2, 1)
    client = Mock()
    client.is_connected.return_value = True
    camera = Mock(return_value=client)
    camera.available_streams.side_effect = [streams, EndProducer()]
    messages = []

    def send(service, event):
      self.assertEqual(service, 'slcVisionObservation')
      messages.append(messaging.log_from_bytes(event.to_bytes()).slcVisionObservation.vision)

    clocks = [(1_000_000_000, 5_000_000_000),
              (1_000_000_000 + completion_age_ns, 5_000_000_000 + completion_age_ns)]
    with patch('msgq.visionipc.VisionIpcClient', camera), \
         patch('openpilot.common.params.Params', return_value=SimpleNamespace(get_bool=lambda _: False)), \
         patch.object(messaging, 'PubMaster', return_value=SimpleNamespace(send=send)), \
         patch.object(producer, 'VisionModelCore', return_value=core), \
         patch.object(producer, '_camera_frame', return_value=(np.zeros((2, 2, 3)), 5_000_000_000, 12)), \
         patch.object(producer, 'clock_pair_ns', side_effect=clocks), \
         patch.object(producer.time, 'sleep'), \
         self.assertRaises(EndProducer):
      producer.main()
    return camera, core, messages

  def test_actual_narrow_camera_api_and_compatible_road_wire_tag(self):
    for streams in ({VisionStreamType.VISION_STREAM_NARROW_ROAD},
                    {VisionStreamType.VISION_STREAM_NARROW_ROAD, VisionStreamType.VISION_STREAM_WIDE_ROAD}):
      with self.subTest(streams=streams):
        camera, core, messages = self.run_frame(streams)
        camera.assert_called_once_with('camerad', VisionStreamType.VISION_STREAM_NARROW_ROAD, True)
        core.observe.assert_called_once()
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0].status), 'valid')
        self.assertEqual(str(messages[0].stream), 'road')
        self.assertEqual(messages[0].frameId, 12)
        self.assertEqual(messages[0].cameraFrameEofBootTime, 5_000_000_000)

  def test_actual_wide_camera_fallback_and_no_camera_unavailability(self):
    camera, _, messages = self.run_frame({VisionStreamType.VISION_STREAM_WIDE_ROAD})
    camera.assert_called_once_with('camerad', VisionStreamType.VISION_STREAM_WIDE_ROAD, True)
    self.assertEqual(str(messages[0].status), 'valid')
    self.assertEqual(str(messages[0].stream), 'wideRoad')
    camera, core, messages = self.run_frame({VisionStreamType.VISION_STREAM_CABIN})
    camera.assert_not_called()
    core.observe.assert_not_called()
    self.assertEqual(str(messages[0].status), 'unavailable')
    self.assertEqual(str(messages[0].stream), 'unknown')

  def test_slow_inference_remains_stale_after_camera_api_fix(self):
    _, core, messages = self.run_frame({VisionStreamType.VISION_STREAM_NARROW_ROAD},
                                     completion_age_ns=270_000_000)
    core.observe.assert_called_once()
    self.assertEqual(len(messages), 1)
    self.assertEqual(str(messages[0].status), 'stale')
    self.assertEqual(messages[0].validUntilMonoTime, 0)
    self.assertEqual(messages[0].speedMps, 0)

  def test_same_client_reconnect_starts_new_consensus_and_session(self):
    # Use the real temporal state machine without loading ONNX assets. A sign
    # seen once before a reconnect cannot confirm a single post-reconnect read.
    core = VisionModelCore.__new__(VisionModelCore)
    core.history = deque()
    core.reset()
    core.is_metric = False
    client = Mock()
    client.is_connected.side_effect = [True, False, True, True]
    camera = Mock(return_value=client)
    road = {VisionStreamType.VISION_STREAM_NARROW_ROAD}
    camera.available_streams.side_effect = [road, road, road, EndProducer()]
    frames = [(np.zeros((2, 2, 3)), 5_000_000_000, 12),
              (np.zeros((2, 2, 3)), 5_300_000_000, 1),
              (np.zeros((2, 2, 3)), 5_600_000_000, 2)]
    clocks = [(1_000_000_000, 5_000_000_000), (1_010_000_000, 5_010_000_000),
              (1_300_000_000, 5_300_000_000), (1_310_000_000, 5_310_000_000),
              (1_600_000_000, 5_600_000_000), (1_610_000_000, 5_610_000_000)]
    messages = []

    def send(service, event):
      self.assertEqual(service, 'slcVisionObservation')
      messages.append(messaging.log_from_bytes(event.to_bytes()).slcVisionObservation.vision)

    with patch('msgq.visionipc.VisionIpcClient', camera), \
         patch('openpilot.common.params.Params', return_value=SimpleNamespace(get_bool=lambda _: False)), \
         patch.object(messaging, 'PubMaster', return_value=SimpleNamespace(send=send)), \
         patch.object(producer, 'VisionModelCore', return_value=core), \
         patch.object(producer, '_camera_frame', side_effect=frames), \
         patch.object(producer, 'clock_pair_ns', side_effect=clocks), \
         patch.object(producer.time, 'sleep'), \
         patch.object(core, 'infer', side_effect=[Detection(55, 0.60)] * 3), \
         self.assertRaises(EndProducer):
      producer.main()

    camera.assert_called_once_with('camerad', VisionStreamType.VISION_STREAM_NARROW_ROAD, True)
    client.connect.assert_called_once_with(False)
    self.assertEqual([str(message.status) for message in messages], ['unknown', 'unknown', 'valid'])
    self.assertEqual([message.frameId for message in messages], [12, 1, 2])
    self.assertNotEqual(messages[0].producerSessionId, messages[1].producerSessionId)
    self.assertEqual(messages[1].producerSessionId, messages[2].producerSessionId)
    self.assertEqual(messages[2].supportCount, 2)


if __name__ == '__main__':
  unittest.main()
