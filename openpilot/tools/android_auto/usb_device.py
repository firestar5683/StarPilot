#!/usr/bin/env python3
"""Wired Android Auto test: project to the car over USB instead of Wi-Fi.

Runs on the comma with the car's USB port connected to the comma's USB-C
device port. It runs one attempt of the supervisor's own wired session
(``Supervisor._attempt_usb``): an accessory-only USB gadget (comma's ADB gadget
steps aside if bound), the car's accessory handshake -- or, when it never comes,
presenting as Google's accessory directly -- then the real streaming path over
the USB link, printing every event. The ADB gadget is rebound on exit.

  cd /data/openpilot
  PYTHONPATH=/data/openpilot /usr/local/venv/bin/python tools/android_auto/usb_device.py [--mode direct]

Stop wireless Android Auto in settings first. Start this, then plug the cable
into the car (or unplug and replug it: the car sends the handshake on connect).
"""

import argparse
import json
import signal
import threading

from openpilot.starpilot.system.android_auto import identity as identity_store
from openpilot.starpilot.system.android_auto.supervisor import Cancelled, Supervisor


class EchoLog:
  """The supervisor's session log, also printed as it is written."""

  def __init__(self, log):
    self._log = log

  def __call__(self, name: str, **values) -> None:
    self._log(name, **values)
    print(json.dumps({"event": name, **values}, default=str), flush=True)

  def __getattr__(self, name):
    return getattr(self._log, name)


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("--view", choices=("car", "mirror"), help="default: the configured view")
  parser.add_argument("--encoder", choices=("auto", "hardware", "software"), help="default: the configured encoder")
  parser.add_argument("--mode", choices=("auto", "handshake", "direct"),
                      help="default: the configured usb_mode (auto: handshake, then direct if the car sends none)")
  parser.add_argument("--wait", type=float, default=600.0, help="seconds to wait for the car before giving up")
  args = parser.parse_args()

  supervisor = Supervisor()
  supervisor.config["connection"] = "wired"
  for key, config_key in (("view", "view"), ("encoder", "encoder"), ("mode", "usb_mode")):
    if getattr(args, key) is not None:
      supervisor.config[config_key] = getattr(args, key)
  ident = identity_store.load_identity()
  print(f"identity ok, expires {ident.expires} ({ident.days_left} days)", flush=True)
  supervisor.log = EchoLog(supervisor.log)

  def stop(*_):
    supervisor._stop.set()
    supervisor._close_sockets()
  signal.signal(signal.SIGINT, stop)
  signal.signal(signal.SIGTERM, stop)

  timed_out = threading.Event()

  def give_up():
    if supervisor.status()["state"] == "waiting_for_usb":
      print("the car never started Android Auto over USB", flush=True)
      timed_out.set()
      stop()
  timer = threading.Timer(args.wait, give_up)
  timer.daemon = True
  timer.start()

  def report():
    while not supervisor._stop.wait(5.0):
      status = supervisor.status()
      print(json.dumps({key: status[key] for key in ("state", "view", "encoder", "target_fps", "mode", "stats")}), flush=True)
  threading.Thread(target=report, daemon=True).start()

  supervisor.log.open()
  supervisor.log("session_start", receiver="usb", generation=0, trigger="usb_device")
  result = 0
  try:
    print("plug in (or replug) the USB cable", flush=True)
    supervisor._attempt_usb()
    print("session ended", flush=True)
  except Cancelled:
    print("stopped", flush=True)
  except Exception as error:
    if not supervisor._stop.is_set():
      print(json.dumps({"result": "fail", "error": f"{type(error).__name__}: {error}",
                        "recent": list(supervisor.log.recent)[-8:]}, default=str))
      result = 1
  finally:
    timer.cancel()
    supervisor._stop.set()
    supervisor._close_sockets()
    supervisor.log("session_stop")
    supervisor.log.close()
    print(f"log: {identity_store.LOG_DIR}", flush=True)
  return 1 if timed_out.is_set() else result


if __name__ == "__main__":
  raise SystemExit(main())
