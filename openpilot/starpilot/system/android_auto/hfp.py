"""Minimal Hands-Free Profile audio gateway: enough of a phone for the car to accept us.

Android Auto head units treat a device as a phone only once its HFP service
level connection is up, and some refuse to start wireless projection before
that (``WIRELESS_SETUP_FAILED_TO_START_NO_HFP_FROM_HU_PRESENCE`` on real phones).
This answers the SLC AT exchange and reports "no call, service available". It
never places or answers calls and never opens SCO audio.
"""

from __future__ import annotations

import select
import socket
import threading
from collections.abc import Callable

AG_FEATURES = 0  # no three-way calling, no codec negotiation, no voice recognition
INDICATORS = ",".join(('("call",(0,1))', '("callsetup",(0-3))', '("service",(0-1))', '("signal",(0-5))',
                       '("roam",(0,1))', '("battchg",(0-5))', '("callheld",(0-2))'))
INDICATOR_VALUES = "0,0,1,5,0,5,0"
OPERATOR = "StarPilot"
MAX_LINE = 512


def respond(command: str) -> list[str]:
  """Return the AG result lines for one HF command (without CR/LF framing)."""
  cmd = command.strip().upper()
  if cmd.startswith("AT+BRSF"):
    return [f"+BRSF: {AG_FEATURES}", "OK"]
  if cmd == "AT+CIND=?":
    return [f"+CIND: {INDICATORS}", "OK"]
  if cmd == "AT+CIND?":
    return [f"+CIND: {INDICATOR_VALUES}", "OK"]
  if cmd == "AT+CHLD=?":
    return ["+CHLD: (0,1,2,3)", "OK"]
  if cmd == "AT+COPS?":
    return [f'+COPS: 0,0,"{OPERATOR}"', "OK"]
  if cmd == "AT+BIND=?":
    return ["+BIND: (1,2)", "OK"]
  if cmd == "AT+BIND?":
    return ["+BIND: 1,0", "+BIND: 2,0", "OK"]
  if cmd.startswith(("ATD", "ATA", "AT+BLDN", "AT+BVRA", "AT+CHLD=")):
    return ["ERROR"]  # no telephony behind this gateway
  if cmd.startswith(("AT+CMER", "AT+CLIP", "AT+CCWA", "AT+NREC", "AT+VGS", "AT+VGM", "AT+CMEE", "AT+BIA", "AT+COPS=",
                     "AT+CLCC", "AT+CNUM", "AT+BTRH", "AT+BAC", "AT+BIND=", "AT+BIEV", "AT+XAPL", "AT+IPHONEACCEV",
                     "AT+CHUP", "AT+XEVENT", "AT+CSRSF", "AT+APLSIRI", "AT+BCS", "AT+BCC", "AT+NREC")):
    return ["OK"]
  return ["ERROR"]


def serve(sock: socket.socket, stop: threading.Event, log: Callable[..., None], peer: str = "") -> None:
  """Service one HFP RFCOMM connection until the car or ``stop`` closes it."""
  buffer = b""
  commands = 0
  try:
    sock.setblocking(True)
    while not stop.is_set():
      if not select.select([sock], [], [], 0.5)[0]:
        continue
      data = sock.recv(256)
      if not data:
        break
      buffer += data
      if len(buffer) > MAX_LINE:
        buffer = buffer[-MAX_LINE:]
      while b"\r" in buffer:
        line, buffer = buffer.split(b"\r", 1)
        command = line.strip(b"\n ").decode("ascii", "replace")
        if not command:
          continue
        commands += 1
        results = respond(command)
        if commands <= 16:
          log("hfp_command", peer=peer, command=command.split("=")[0], result=results[-1])
        sock.sendall(b"".join(b"\r\n" + line.encode() + b"\r\n" for line in results))
  except OSError as error:
    log("hfp_closed", peer=peer, error=str(error))
  finally:
    try:
      sock.close()
    except OSError:
      pass
