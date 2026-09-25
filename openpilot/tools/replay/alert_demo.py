"""Synthetic visual alert for a private desktop replay session only."""

import argparse
import os
import signal
import time

from openpilot.tools.replay.onroad import PREFIX_RE, _ipc_root


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(description="Preview a synthetic critical visual alert during private replay")
  parser.add_argument("--delay", type=float, default=20.0)
  parser.add_argument("--hold", type=float, default=5.0)
  args = parser.parse_args(argv)
  prefix = os.environ.get("OPENPILOT_PREFIX", "")
  ipc = _ipc_root(prefix)
  if (os.environ.get("SP_HOST_RUNTIME") != "1" or PREFIX_RE.fullmatch(prefix) is None or
      ipc.is_symlink() or not ipc.is_dir() or ipc.stat().st_uid != os.getuid()):
    parser.error("alert preview requires an isolated host replay session")
  if not (0 <= args.delay <= 120 and 0 < args.hold <= 30):
    parser.error("invalid alert preview timing")

  from openpilot.cereal import log, messaging
  from openpilot.common.realtime import Ratekeeper

  running = True
  def stop(_signum, _frame) -> None:
    nonlocal running
    running = False

  previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
  try:
    publisher = messaging.PubMaster(["selfdriveState"])
    rate = Ratekeeper(100, print_delay_threshold=None)
    def send(active: bool) -> None:
      message = messaging.new_message("selfdriveState")
      message.valid = True
      state = message.selfdriveState
      state.alertSize = log.SelfdriveState.AlertSize.full if active else log.SelfdriveState.AlertSize.none
      state.alertStatus = log.SelfdriveState.AlertStatus.critical if active else log.SelfdriveState.AlertStatus.normal
      state.alertText1 = "TAKE CONTROL IMMEDIATELY" if active else ""
      state.alertText2 = "Developer visual alert preview" if active else ""
      state.alertType = "developerVisualPreview" if active else ""
      publisher.send("selfdriveState", message)

    start = time.monotonic()
    while running:
      now = time.monotonic() - start
      send(args.delay <= now < args.delay + args.hold)
      rate.keep_time()
    return 0
  finally:
    for sig, handler in previous.items():
      signal.signal(sig, handler)


if __name__ == "__main__":
  raise SystemExit(main())
