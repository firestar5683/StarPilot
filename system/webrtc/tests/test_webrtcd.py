import json

import pytest

pytest.importorskip("libdatachannel", reason="the upstream WebRTC backend requires Python 3.12")

from openpilot.system.webrtc.webrtcd import ServerState, handle_get_schema, handle_post_notify, on_shutdown


@pytest.mark.asyncio
async def test_get_schema():
  status, body, content_type = await handle_get_schema(ServerState(), "carState")

  assert status == 200
  assert content_type.startswith("application/json")
  assert "carState" in json.loads(body)


@pytest.mark.asyncio
async def test_get_schema_rejects_unknown_service():
  with pytest.raises(AssertionError, match="Invalid service name"):
    await handle_get_schema(ServerState(), "notARealService")


@pytest.mark.asyncio
async def test_notify_and_shutdown_active_stream(mocker):
  state = ServerState()
  session = mocker.MagicMock()
  session.stop = mocker.AsyncMock()
  state.streams["test"] = session

  status, body, content_type = await handle_post_notify(state, {"type": "ping"})

  assert (status, body) == (200, b"OK")
  assert content_type.startswith("text/plain")
  channel = session.stream.get_messaging_channel.return_value
  channel.send.assert_called_once_with(json.dumps({"type": "ping"}))

  await on_shutdown(state)

  session.stop.assert_awaited_once()
  assert state.streams == {}
