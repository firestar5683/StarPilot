import asyncio
import json

import pytest

from cereal import car
from openpilot.common.params import Params
from openpilot.system.athena import athenad
from openpilot.system.webrtc import helpers


@pytest.mark.parametrize("not_car", [False, True])
@pytest.mark.parametrize("enabled", [False, True])
def test_start_stream_request(mocker, not_car, enabled):
  params = Params()
  params.put("CarParamsPersistent", car.CarParams.new_message(notCar=not_car).to_bytes())
  params.put_bool("IsOffroad", True)
  wait = mocker.patch.object(helpers, "wait_for_webrtcd")
  post = mocker.patch.object(helpers.requests, "post")
  post.return_value.json.return_value = {"sdp": "answer", "type": "answer"}

  answer = athenad.dispatcher["startStream"](sdp="offer", enabled=enabled)

  assert params.get_bool("IsLiveStreaming")
  wait.assert_called_once_with()
  assert answer["sdp"] == "answer"
  body = post.call_args.kwargs["json"]
  assert body["sdp"] == "offer"
  assert body["cameras"] == ["wideRoad"]
  assert body["enabled"] is enabled
  assert body["bridge_services_in"] == (["testJoystick"] if not_car else [])
  assert body["bridge_services_out"] == ["carState", "deviceState"]


@pytest.mark.asyncio
async def test_connected_stream_preserves_telemetry_publishers(mocker):
  pytest.importorskip("libdatachannel")
  from cereal import messaging
  from openpilot.system.webrtc.webrtcd import DynamicPubMaster, StreamSession

  params = Params()
  params.put("CarParamsPersistent", car.CarParams.new_message(notCar=False).to_bytes())
  params.put_bool("IsOffroad", True)
  mocker.patch.object(helpers, "wait_for_webrtcd")
  post = mocker.patch.object(helpers, "post_stream_request")
  athenad.dispatcher["startStream"](sdp="offer", enabled=True)

  # The real device already has publishers for both services when Connect starts.
  publishers = messaging.PubMaster(["carState", "deviceState"])
  mocker.patch.object(StreamSession, "shared_pub_master", DynamicPubMaster([]))
  connected = asyncio.Event()
  disconnected = asyncio.Event()

  async def wait_for_disconnection():
    connected.set()
    await disconnected.wait()

  # Exercise the session after ICE connects, including real msgq ownership and
  # telemetry forwarding. Only the external WebRTC transport is mocked.
  builder = mocker.patch("teleoprtc.builder.WebRTCAnswerBuilder")
  stream = builder.return_value.stream.return_value
  stream.wait_for_connection = mocker.AsyncMock()
  stream.wait_for_disconnection.side_effect = wait_for_disconnection
  stream.stop = mocker.AsyncMock()
  session = StreamSession(post.call_args.args[0])
  session.start()
  try:
    await asyncio.wait_for(connected.wait(), timeout=2)
    messages = {service: messaging.new_message(service).to_bytes() for service in ["carState", "deviceState"]}

    async def publish_until_forwarded():
      while True:
        for service, message in messages.items():
          publishers.send(service, message)
        forwarded = [json.loads(call.args[0])["type"] for call in stream.get_messaging_channel.return_value.send.call_args_list]
        if {"carState", "deviceState"}.issubset(forwarded):
          return
        await asyncio.sleep(0.01)

    await asyncio.wait_for(publish_until_forwarded(), timeout=2)

    assert session.shared_pub_master.sock == {}
  finally:
    disconnected.set()
    await session.stop()
