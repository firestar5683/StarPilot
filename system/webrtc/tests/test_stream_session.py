import asyncio
import json
import time

import capnp
import pytest

pytest.importorskip("libdatachannel", reason="the upstream WebRTC backend requires Python 3.12")

from cereal import messaging, log
from teleoprtc.tracks import VIDEO_CLOCK_RATE

from openpilot.system.webrtc.webrtcd import CerealOutgoingMessageProxy, CerealIncomingMessageProxy
from openpilot.system.webrtc.device.video import LiveStreamVideoStreamTrack


class TestStreamSession:
  def setup_method(self):
    self.loop = asyncio.new_event_loop()

  def teardown_method(self):
    self.loop.stop()
    self.loop.close()

  def test_outgoing_proxy(self, mocker):
    test_msg = log.Event.new_message()
    test_msg.logMonoTime = 123
    test_msg.valid = True
    test_msg.customReservedRawData0 = b"test"
    expected_dict = {"type": "customReservedRawData0", "logMonoTime": 123, "valid": True, "data": "test"}
    expected_json = json.dumps(expected_dict).encode()

    channel = mocker.Mock()
    channel.is_open.return_value = True
    proxy = CerealOutgoingMessageProxy(["customReservedRawData0"])

    def mocked_update(_):
      proxy.sm.update_msgs(0, [test_msg])

    mocker.patch.object(messaging.SubMaster, "update", side_effect=mocked_update)
    proxy.add_channel(channel)
    proxy.update()

    channel.send.assert_called_once_with(expected_json)

  def test_incoming_proxy(self, mocker):
    tested_msgs = [
      {"type": "customReservedRawData0", "data": "test"},
      {"type": "can", "data": [{"address": 0, "dat": "", "src": 0}]},
      {"type": "testJoystick", "data": {"axes": [0, 0], "buttons": [False]}},
    ]

    mocked_pubmaster = mocker.MagicMock(spec=messaging.PubMaster)
    proxy = CerealIncomingMessageProxy(mocked_pubmaster)

    for msg in tested_msgs:
      proxy.send(json.dumps(msg).encode())

      mocked_pubmaster.send.assert_called_once()
      msg_type, message = mocked_pubmaster.send.call_args.args
      assert msg_type == msg["type"]
      assert isinstance(message, capnp._DynamicStructBuilder)
      assert hasattr(message, msg_type)
      mocked_pubmaster.reset_mock()

  def test_livestream_track(self, mocker):
    fake_msg = messaging.new_message("livestreamDriverEncodeData")
    fake_msg.livestreamDriverEncodeData.idx.flags = 8

    config = {"receive.return_value": fake_msg.to_bytes()}
    mocker.patch("msgq.SubSocket", spec=True, **config)
    track = LiveStreamVideoStreamTrack("driver")

    assert track.id.startswith("driver")

    for i in range(5):
      packet = self.loop.run_until_complete(track.recv())
      if i == 0:
        start_ns = time.monotonic_ns()
        start_pts = packet.pts
      assert abs(i + packet.pts - (start_pts + (((time.monotonic_ns() - start_ns) * VIDEO_CLOCK_RATE) // 1_000_000_000))) < 450
      assert bytes(packet) == b""
