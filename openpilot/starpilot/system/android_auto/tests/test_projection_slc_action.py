import tempfile
from pathlib import Path

from openpilot.starpilot.system.android_auto.projection_slc_action import SlcActionReceiver, SlcActionSender
from openpilot.starpilot.ui.onroad_state import SlcActionKind, SlcUiRequest


def test_request_round_trips_and_malformed_input_is_dropped():
  # AF_UNIX paths are short on macOS; pytest's tmp_path is not.
  path = Path(tempfile.mkdtemp(dir='/tmp')) / 's.sock'
  receiver, sender = SlcActionReceiver(path), SlcActionSender(path)
  try:
    request = SlcUiRequest(SlcActionKind.ADOPT, 'drive-1', 7, 9, 22.0)
    assert sender.send(request)
    sender.sock.sendto(b'not json', str(path))
    sender.sock.sendto(b'{"kind": "explode"}', str(path))
    assert receiver.drain() == [request]
    assert receiver.drain() == []
  finally:
    sender.close()
    receiver.close()
