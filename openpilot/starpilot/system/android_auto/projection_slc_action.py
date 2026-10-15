"""Speed-limit taps from the car screen, handed to the native UI, which owns the action publisher."""
import json
import os
import socket

from openpilot.starpilot.ui.onroad_state import SlcActionKind, SlcUiRequest

DEFAULT_SOCKET = '/tmp/starpilot-projection-slc.sock'
MAX_DATAGRAM = 512


class SlcActionSender:
  def __init__(self, path=DEFAULT_SOCKET):
    self.path = str(path)
    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    self.sock.setblocking(False)

  def send(self, request: SlcUiRequest) -> bool:
    payload = json.dumps({'kind': request.kind.value, 'session': request.session_id, 'decision': request.decision_id,
                          'presentation': request.presentation_id, 'speed': request.candidate_speed_mps}).encode()
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

  def drain(self) -> list[SlcUiRequest]:
    """At most a few typed requests; malformed input is dropped. The caller still validates against live state."""
    requests = []
    for _ in range(4):
      try:
        raw = self.sock.recv(MAX_DATAGRAM)
      except BlockingIOError:
        break
      try:
        data = json.loads(raw)
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
