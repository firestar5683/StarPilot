"""Speed-limit and experimental-mode taps from the car screen, handed to the native UI, which owns the action publishers."""
import json
import os
import socket

from openpilot.starpilot.ui.onroad_state import OnroadRequest, SlcActionKind, SlcUiRequest

DEFAULT_SOCKET = '/tmp/starpilot-projection-slc.sock'
MAX_DATAGRAM = 512
# The projection cannot see the native experimental binding's token, so a wheel
# tap carries only the state it asks for; the native UI checks it against live state.
SET_EXPERIMENTAL = 'set_experimental'


class SlcActionSender:
  def __init__(self, path=DEFAULT_SOCKET):
    self.path = str(path)
    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    self.sock.setblocking(False)

  def send(self, request: OnroadRequest | SlcUiRequest) -> bool:
    if isinstance(request, OnroadRequest):
      if request.kind != SET_EXPERIMENTAL or not isinstance(request.value, bool):
        return False
      payload = json.dumps({'kind': SET_EXPERIMENTAL, 'value': request.value}).encode()
      return self._send(payload)
    payload = json.dumps({'kind': request.kind.value, 'session': request.session_id, 'decision': request.decision_id,
                          'presentation': request.presentation_id, 'speed': request.candidate_speed_mps}).encode()
    return self._send(payload)

  def _send(self, payload: bytes) -> bool:
    try:
      self.sock.sendto(payload, self.path)
      return True
    except OSError:
      return False

  def close(self):
    self.sock.close()


class SlcActionReceiver:
  def __init__(self, path=DEFAULT_SOCKET):
    self.path = str(path)
    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
      try:
        os.unlink(self.path)
      except FileNotFoundError:
        pass
      self.sock.bind(self.path)
      os.chmod(self.path, 0o600)
      self.sock.setblocking(False)
    except BaseException:
      self.sock.close()
      raise

  def drain(self) -> list[OnroadRequest | SlcUiRequest]:
    """At most a few typed requests; malformed input is dropped. The caller still validates against live state."""
    requests = []
    for _ in range(4):
      try:
        raw = self.sock.recv(MAX_DATAGRAM)
      except BlockingIOError:
        break
      try:
        data = json.loads(raw)
        if data['kind'] == SET_EXPERIMENTAL:
          if not isinstance(data['value'], bool):
            continue
          requests.append(OnroadRequest(SET_EXPERIMENTAL, data['value']))
          continue
        requests.append(SlcUiRequest(SlcActionKind(data['kind']), str(data['session']), int(data['decision']),
                                     int(data['presentation']), float(data['speed'])))
      except (ValueError, KeyError, TypeError):
        continue
    return requests

  def close(self):
    self.sock.close()
    try:
      os.unlink(self.path)
    except FileNotFoundError:
      pass
