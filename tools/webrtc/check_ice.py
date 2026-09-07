#!/usr/bin/env python3
"""Check the installed WebRTC library's ICE role handling over real UDP sockets.

No cameras, device parameters, external servers, or live sessions are used.
Run this with the same Python environment as webrtcd when validating an image.
"""

import binascii
import hashlib
import hmac
import secrets
import socket
import struct
import time

from libdatachannel import Configuration, Description, PeerConnection


def attribute(kind: int, value: bytes) -> bytes:
  return struct.pack("!HH", kind, len(value)) + value + bytes(-len(value) % 4)


def binding_request(username: str, password: str, roles: list[tuple[int, int]]) -> tuple[bytes, bytes]:
  transaction = secrets.token_bytes(12)
  attrs = attribute(0x0006, username.encode())
  # Match Chromium's attribute ordering, including its optional network info.
  attrs += attribute(0xC057, bytes(4))
  for role, tiebreaker in roles:
    attrs += attribute(role, struct.pack("!Q", tiebreaker))
  attrs += attribute(0x0025, b"") + attribute(0x0024, struct.pack("!I", 1853824767))
  def header(size: int) -> bytes:
    return struct.pack("!HHI12s", 1, size, 0x2112A442, transaction)

  integrity = hmac.new(password.encode(), header(len(attrs) + 24) + attrs, hashlib.sha1).digest()
  attrs += attribute(0x0008, integrity)
  packet = header(len(attrs) + 8) + attrs
  packet += attribute(0x8028, struct.pack("!I", binascii.crc32(packet) ^ 0x5354554E))
  return packet, transaction


def sdp_value(sdp: str, name: str) -> str:
  prefix = f"a={name}:"
  return next(line[len(prefix):] for line in sdp.splitlines() if line.startswith(prefix))


def check_binding(roles: list[tuple[int, int]], *, invalid_password: bool = False) -> int | None:
  config = Configuration()
  config.bind_address = "127.0.0.1"
  config.disable_auto_negotiation = True
  offerer = PeerConnection(config)
  answerer = PeerConnection(config)
  channel = offerer.create_data_channel("data")
  try:
    offerer.set_local_description(Description.Type.Offer)
    offer = str(offerer.local_description())
    # Only our probe sends checks; do not start an independent connection.
    offer = "\r\n".join(line for line in offer.splitlines() if not line.startswith("a=candidate:")) + "\r\n"
    answerer.set_remote_description(Description(offer, Description.Type.Offer))
    answerer.set_local_description(Description.Type.Answer)
    deadline = time.monotonic() + 2
    while answerer.gathering_state() != PeerConnection.GatheringState.Complete:
      if time.monotonic() >= deadline:
        raise TimeoutError("Loopback candidate gathering timed out")
      time.sleep(0.01)
    answer = str(answerer.local_description())
    candidate = sdp_value(answer, "candidate").split()
    username = f"{sdp_value(answer, 'ice-ufrag')}:{sdp_value(offer, 'ice-ufrag')}"
    password = "invalid-test-password" if invalid_password else sdp_value(answer, "ice-pwd")
    packet, transaction = binding_request(username, password, roles)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
      sock.bind(("127.0.0.1", 0))
      sock.settimeout(1)
      sock.sendto(packet, (candidate[4], int(candidate[5])))
      deadline = time.monotonic() + 1
      while time.monotonic() < deadline:
        try:
          response = sock.recv(2048)
        except TimeoutError:
          return None
        if len(response) < 20 or response[8:20] != transaction:
          continue
        if response[:2] == b"\x01\x01":
          return 200
        offset = 20
        while offset + 4 <= len(response):
          kind, size = struct.unpack_from("!HH", response, offset)
          value = response[offset + 4:offset + 4 + size]
          if kind == 0x0009 and len(value) >= 4:
            return value[2] * 100 + value[3]
          offset += 4 + (size + 3) // 4 * 4
        raise AssertionError("Unexpected ICE response")
    return None
  finally:
    answerer.close()
    offerer.close()
    # Keep the wrapper alive until after its connection has closed.
    assert channel is not None


def main() -> None:
  cases = [
    ("nonzero controlling tiebreaker", [(0x802A, 123)], False, 200),
    ("zero controlling tiebreaker", [(0x802A, 0)], False, 200),
    ("missing role rejected", [], False, 400),
    ("both roles rejected", [(0x802A, 123), (0x8029, 456)], False, 400),
    ("invalid authentication rejected", [(0x802A, 0)], True, None),
  ]
  failed = False
  for name, roles, invalid_password, expected in cases:
    actual = check_binding(roles, invalid_password=invalid_password)
    passed = actual == expected
    print(f"{'PASS' if passed else 'FAIL'}: {name}: expected {expected}, got {actual}", flush=True)
    failed |= not passed
  raise SystemExit(int(failed))


if __name__ == "__main__":
  main()
