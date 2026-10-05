"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

Holds the USB gadget, and nothing else.

The comma is the USB device: the link exists only while some process holds ep0
with the UDC bound. This is that process, for as long as the link is enabled,
onroad and offroad alike, and no other process ever holds ep0. Whoever wants
to move bytes borrows the endpoint files over a unix socket (lending.py) and
the gadget never leaves the bus.

The Jetlink setting names the host. For USB (a Jetson or a Mac) the
gadget is FunctionFS alone and the endpoint files are lent at once. For iOS
the gadget is composite: the phone is on its network interface and dials this
process (lending.CableListener), and the loan carries its socket; the endpoint
files are never lent, and the gadget is never released, settled or bounced,
since every unbind drops the phone's network interface with it.

It is deliberately small. Everything heavy jetlink does is episodic, so none of
it lives here: a download, an upload and a TensorRT build all belong to the
provisioning run (jetlink.openpilot.provision), which this spawns when there is
something to do and which exits when there is not. That keeps a parked car and
a drive alike at one resident jetlink process of about 13 MB rather than
47.5 MB, and it is why nothing in this module may import swaglog, Params,
numpy, capnp or zmq; see gadget.py and tests/test_comma_gadget.py. The caller
names the worker and hands over the settings: jetlink.openpilot.owner makes
and runs the Owner from what the fork's adapter says (OwnerConfig), so nothing
here knows an openpilot module or a param name.

What it knows, it writes down whole every step in its status record
(gadget.STATUS): the gadget, the host, presence with its hold, the errors. The
UI and hardwared read that one file rather than the gadget's own files one by
one, and its timestamp is the heartbeat that tells them the owner is gone.

manager stops this on shutdown with SIGINT and SIGKILLs it 5 s later, so every
long wait polls `stop`: a FunctionFS owner killed mid-transfer leaves the
gadget in a state only a reboot clears.
"""
from __future__ import annotations

import errno
import fcntl
import json
import logging
import os
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

from jetlink.comma import gadget, lending, port, root

POLL = 0.5
# how long the gadget is held after the last thing that wanted it. The server
# sleeps 120 s after the gadget goes; a stop inside the hold rejoins at once,
# one outside it costs the ~8 s wake. It also covers a jetson that is still
# enumerating when the run that woke it has already finished
DORMANT_HOLD = 60.0
# how long settle() waits for its own re-enumeration before carrying on
SETTLE_TIMEOUT = 10.0
# after a borrower lets go. The server has just lost its client and is closing
# the gadget and reopening it, two seconds at a time
LEASE_SETTLE = 4.0
RECONNECT_BACKOFF = 5.0
GADGET_SETUP_BACKOFF = 60.0
# a build refused because another gadget holds the controller: the host turns
# that one off itself (openpilot's ADB toggle with the link on), within seconds
GADGET_HELD_RETRY = 2.0
# between attempts to bring the gadget's network interface up after a bind
NET_BACKOFF = 5.0
# between attempts to listen for borrowers after one failed
LENDER_BACKOFF = 30.0
# between runs of the worker that found nothing to do. It costs a couple of
# seconds of imports, so it is spawned on a change and not on a timer
WORKER_BACKOFF = 300.0
SHUTDOWN_RETRY = 2.0      # a shutdown run that exited with the request still there
WORKER_GRACE = 10.0
# between opens of an ep0 that answered EBUSY: a borrower from before this
# owner started still has the endpoint files, and the open succeeds the moment
# it lets go. A refused open changes nothing in the kernel, so it is safe to
# repeat; only a read of an endpoint no host has enabled is not (_ensure_epfiles)
EP0_BUSY_RETRY = 1.0

# A crash loop re-enumerates the Jetson at every start, since the gadget goes
# with the owner that held it. Each start is written down and a clean stop
# takes its own back out, so what is left is owners that died or were killed.
# With CRASH_FREE of those inside CRASH_WINDOW the next start waits, holding
# nothing, CRASH_BACKOFF doubling up to CRASH_BACKOFF_MAX
CRASH_WINDOW = 600.0
CRASH_FREE = 3
CRASH_BACKOFF = 10.0
CRASH_BACKOFF_MAX = 300.0

# the log is rotated: the loop below logs a traceback per cycle if something stays broken
LOG_BYTES = 1 << 20


def logger(path: Path) -> logging.Logger:
  """The owner's log, to stderr and `path`: swaglog costs 28 MB, so the owner
  keeps its own. The worker's lines go to the drive; these are for a bench
  session, which wants them after the drive."""
  log = logging.getLogger('jetlink.owner')
  log.setLevel(logging.INFO)
  handlers: list[logging.Handler] = [logging.StreamHandler()]
  try:
    from logging.handlers import RotatingFileHandler
    handlers.append(RotatingFileHandler(path, maxBytes=LOG_BYTES, backupCount=1))
  except OSError:
    pass   # a read-only or missing /data/log; stderr is enough
  for handler in handlers:
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-7s %(message)s'))
    log.addHandler(handler)
  return log


def server_sleeps(server: dict | None) -> bool:
  """Does the far end suspend when the gadget goes, by its hello's
  sleep_after? No hello yet, or a server too old to say, is a yes: letting go
  of one that stays up only costs a rebind, and holding on to one that sleeps
  keeps it awake all night."""
  try:
    return float((server or {}).get('sleep_after', 1.0)) > 0
  except (TypeError, ValueError):
    return True


def _starts() -> list[float]:
  try:
    starts = json.loads(gadget.STARTS.read_text())
  except (OSError, ValueError):
    return []
  return [t for t in starts if isinstance(t, (int, float))] if isinstance(starts, list) else []


def _write_starts(starts: list[float]) -> None:
  try:
    gadget.write_record(gadget.STARTS, starts)
  except OSError:
    gadget.log.exception("jetlink: could not record the owner's starts")


def note_start(now: float) -> tuple[float, int]:
  """Write this start down. How long it should wait before taking the
  gadget, and how many owners inside CRASH_WINDOW never stopped cleanly."""
  starts = [t for t in _starts() if 0.0 <= now - t < CRASH_WINDOW]
  _write_starts([*starts, now])
  died = len(starts)
  if died < CRASH_FREE:
    return 0.0, died
  return min(CRASH_BACKOFF_MAX, CRASH_BACKOFF * 2 ** (died - CRASH_FREE)), died


def forget_start(started: float) -> None:
  """A clean stop: this start no longer counts against the next one."""
  _write_starts([t for t in _starts() if t != started])


class Owner:
  def __init__(self, worker: Sequence[str], cwd: str | None = None, env: Mapping[str, str] | None = None, *,
               settings, chestnut_ids):
    # the provisioning run: its argv, its working directory, and what it gets
    # over this process's environment
    self.worker_argv = list(worker)
    self.worker_cwd = cwd
    self.worker_env = dict(env or {})
    # mode(), offroad() and marks(): the link setting, whether the car is
    # parked, and when the pick and the built model last changed
    self.settings = settings
    self.transport = None
    self.stop = False
    self.dormant = False
    # the link mode the root tuning was applied for, None while stock
    self.tuned: str | None = None
    # when there was last something to do. The hold runs from here, not from
    # process start: this daemon is not restarted at ignition any more, so a
    # hold measured from its birth expires once and never applies again, and
    # every wake released the gadget a second later with the jetson still
    # coming up
    self.idle_since = time.monotonic()
    self.next_attempt = 0.0
    self.next_gadget_attempt = 0.0
    self.failed_ios: bool | None = None  # the mode whose last build failed, until one works
    self.next_worker = 0.0
    self.shutting_down = False          # the run in flight is the one asking the jetson to power off
    self.next_shutdown_run = 0.0
    self.lease_settled = 0.0
    self.attached = False
    self.configured = False             # attached, as of the last step: for the edges
    self.dialed = False                 # a phone dialed in since the last run
    self.built_ios: bool | None = None  # what the gadget was built for; None until looked at
    self._peer: str | None = None       # the phone published as dialed in
    self.net_ready = False              # usb0 configured for this bind
    self.next_net_attempt = 0.0
    self.lender_failed = False          # said once, until it listens again
    self.next_lender = 0.0
    self.worker: subprocess.Popen | None = None
    self.seen: dict[str, int] = {}      # watched param -> mtime when last looked
    self.had_host = False
    # the status record every other process reads (gadget.STATUS): the setting
    # the last step acted on, when a host last had us configured (presence's
    # hold), when the record was last written, and a failure writing it, said once
    self.mode: str | None = None
    self.last_configured = 0.0
    self.published = 0.0
    self.status_error: str | None = None
    # what this process never speaks the protocol to learn: the fields of the
    # server's last hello, which every borrower passes on over its loan
    # (lending.SERVER_FIELDS), and whether the last run left work undone, from
    # its exit status
    self.server: dict | None = None
    self.unfinished = False
    self.ep0_busy = False               # said once, until an open works
    self.switch_waiting = False         # a rebuild held off by a borrower of a dead owner, said once
    # why a crash loop's backoff holds this start back, for the status record
    self.backing_off: str | None = None
    self.lock_fd: int | None = None      # gadget.OWNER_LOCK, held for the life of run()
    # this owner's entry in gadget.STARTS, until a stop that was asked for takes it back
    self.born: float | None = None
    self.port = port.Port(chestnut_ids)
    self.cable = lending.CableListener()
    self.lender = lending.Lender(self.lendable, self.bounce_gadget, cable=self.cable_mode, vacate=self.cable.vacate,
                                 server=self.note_server)

  # -- the gadget -----------------------------------------------------------

  def close_link(self) -> None:
    """Always go through this: a FunctionFS owner that exits without closing
    can wedge the driver until a reboot."""
    transport, self.transport = self.transport, None
    # the phone's network interface goes with the gadget, and its dial with it
    self.cable.close()
    self.net_ready = False
    self.publish()
    if transport is not None:
      try:
        transport.close()
      except Exception:
        gadget.log.exception("jetlink: error closing the link")

  def lendable(self) -> bool:
    """Is the gadget in a state a borrower can take the endpoints over from?"""
    return self.transport is not None and self.transport.lendable

  def cable_mode(self) -> bool:
    """Is the link a phone's dial rather than the endpoint files? On a gadget
    built for iOS, always: the host is a phone, which never reads them, so a
    borrower listens for its dial instead (lending.Loan.accept). The build,
    not the setting: a setting moved while somebody borrowed waits for them."""
    return bool(self.built_ios)

  def publish(self, peer: str | None = None) -> None:
    """What the gadget is, for every other process's link_kind, and on the
    cable which phone dialed in."""
    self._peer = peer
    if self.built_ios is None:
      gadget.clear_link()
    else:
      gadget.note_link('cable' if self.built_ios else 'usb', peer)

  def bounce_gadget(self) -> bool:
    """One unplug and replug, for a borrower whose write has no reader.

    Unbinding is the only thing that makes FunctionFS dequeue a write the host
    is not draining, and the unbind belongs to whoever holds ep0. See
    FfsTransport._abort_write. Only a borrower on FunctionFS asks: for iOS
    nothing is ever lent the endpoint files.
    """
    if self.transport is None:
      return False
    try:
      return bool(self.transport.rebind())
    except Exception:
      gadget.log.exception("jetlink: could not bounce the gadget for the borrower")
      return False
    finally:
      # the unbind took usb0 with it; the rebind made a bare one
      self.net_ready = False
      self.next_net_attempt = 0.0

  def open_link(self) -> bool:
    """Present the gadget so a Jetson can enumerate whenever it powers on.

    The transport, not a client: this end never speaks the protocol, and
    jetlink.client would bring numpy with it.
    """
    if self.transport is not None:
      return True
    try:
      from jetlink.transport.ffs import FfsTransport
      self.transport = FfsTransport(str(gadget.FFS_MOUNT), gadget=str(gadget.GADGET_PATH))
      gadget.log.warning("jetlink: gadget presented, waiting for a jetson")
      self.net_ready = False
      self.next_net_attempt = 0.0
      self.ep0_busy = False
      return True
    except OSError as e:
      if e.errno == errno.EBUSY and os.path.basename(os.fsdecode(e.filename or '')) == 'ep0':
        # an owner started after one that died: its borrower (modeld mid-drive,
        # or the dead owner's own run) still has ep1 and ep2, and FunctionFS
        # refuses ep0 until they are closed. Nothing was opened, and the UDC
        # was never touched, so the borrower's link carries on meanwhile
        if not self.ep0_busy:
          gadget.log.warning("jetlink: ep0 is busy, something still has the gadget's endpoint files open "
                             "(most likely a borrower from before this owner); presenting it once they are closed")
          self.ep0_busy = True
        self.next_attempt = time.monotonic() + EP0_BUSY_RETRY
        return False
      return self._open_failed()
    except Exception:
      return self._open_failed()

  def _open_failed(self) -> bool:
    gadget.log.exception("jetlink: could not present the gadget")
    self.next_attempt = time.monotonic() + RECONNECT_BACKOFF
    return False

  def ensure_gadget(self, ios: bool) -> bool:
    """Is there a gadget to present? Create it, for iOS or USB, if there is
    none: nothing sets it up at boot, so the owner's first step does, parked
    or onroad, and a link turned on later gets one at once."""
    if gadget.link_configured():
      return True
    return self.build(ios)

  def build(self, ios: bool) -> bool:
    """Set the gadget up for USB or iOS. A failure backs off, since the script
    is sudo, configfs and for iOS the network; a success does not, or a switch
    just after a build would wait out the backoff. The backoff is the failed
    mode's: a half-built iOS gadget never delays the way back to USB, and a
    controller another gadget holds is tried again in seconds."""
    now = time.monotonic()
    if now < self.next_gadget_attempt and ios == self.failed_ios:
      return False
    if not gadget.setup_gadget(ios):
      self.failed_ios = ios
      held = gadget.other_gadget() is not None
      self.next_gadget_attempt = now + (GADGET_HELD_RETRY if held else GADGET_SETUP_BACKOFF)
      return False
    self.failed_ios = None
    self.built_ios = ios
    self.publish()
    return True

  def ensure_net(self) -> None:
    """usb0 exists only once the UDC is bound, so the network comes up here,
    after open_link, once per bind and again after a bounce. Retried on a
    backoff: the script is sudo, nmcli and dnsmasq, not twice a second."""
    if self.transport is None or self.net_ready:
      return
    now = time.monotonic()
    if now < self.next_net_attempt:
      return
    self.next_net_attempt = now + NET_BACKOFF
    self.net_ready = gadget.net_up()

  def settle(self) -> None:
    """Put the gadget back to bound with nothing open on it.

    ep0 and the descriptors stay here throughout; only the endpoint files go.
    See FfsTransport.release_endpoints. Not over the cable: nothing of ours
    is open on the endpoints, and the re-enumeration it may cost would drop
    the phone's network interface.
    """
    if self.transport is None or self.lendable() or self.built_ios:
      return
    gadget.log.warning("jetlink: putting the endpoints down, keeping the gadget bound")
    if not self.transport.release_endpoints():
      return
    gadget.wait_for_host(SETTLE_TIMEOUT, bounce=self.bounce_gadget, should_stop=self.waiting)

  def hold(self, ios: bool) -> None:
    """Everything this process does once the car is moving, or once somebody
    has the endpoints.

    Keep the gadget on the bus and stay off it. One sysfs read a cycle: a
    process that wakes up to do work on modeld's core is a dropped frame.
    """
    self.wake()
    if self.transport is not None:
      return self.settle()
    # a failed open waits its backoff here too: a busy ep0 is asked once a
    # second, not every step, and a broken one is not a traceback a step
    if time.monotonic() >= self.next_attempt and self.ensure_gadget(ios):
      self.open_link()

  # -- the parked car -------------------------------------------------------

  def go_dormant(self) -> None:
    """Release the gadget so the Jetson can sleep. The marker goes first so
    present() never blinks. Never on the cable: see step()."""
    gadget.log.warning("jetlink: nothing left to do, releasing the gadget so the jetson can sleep")
    gadget.set_dormant(True)
    self.close_link()
    self.dormant = True
    self.had_host = False

  def wake(self) -> None:
    """Present the gadget again. If the Jetson is asleep, the bind wakes it."""
    if not self.dormant:
      return
    gadget.log.warning("jetlink: presenting the gadget again")
    gadget.set_dormant(False)
    self.dormant = False
    self.idle_since = time.monotonic()

  def note_server(self, borrower: str, fields: dict) -> None:
    """What a borrower passed on of the server's hello (lending.Loan.note_server),
    on the lender's thread. Said when it changes, which is how a server moved
    to --sleep-after 0 or back shows in this log, and kept in gadget.SERVER,
    which outlives this owner: a run with nothing to do never says hello, so
    the next owner would otherwise take an always-on Jetson for one that
    sleeps and let the gadget go until the next drive."""
    known, self.server = self.server or {}, dict(fields)
    if any(known.get(k) != fields.get(k) for k in ('device', 'sleep_after')) or not known:
      gadget.log.warning("jetlink: %s says the server on %s %s when the gadget goes (sleep_after %s)", borrower,
                         fields.get('device') or 'the far end', 'sleeps' if server_sleeps(fields) else 'stays up',
                         fields.get('sleep_after'))
    if fields != known:
      try:
        gadget.write_record(gadget.SERVER, self.server)
      except OSError as e:
        gadget.log.warning("jetlink: could not keep what the server said (%s)", e)

  def far_end_sleeps(self) -> bool:
    """Does the far end suspend when the gadget goes, as its last hello said?"""
    return server_sleeps(self.server)

  # -- the worker -----------------------------------------------------------

  def worker_running(self) -> bool:
    if self.worker is None:
      return False
    if self.worker.poll() is None:
      return True
    gadget.log.warning("jetlink: the provisioning run finished (%s)", self.worker.returncode)
    # 0 is a run with nothing left to do; anything else, a crash included, is
    # tried again once WORKER_BACKOFF has passed
    self.unfinished = self.worker.returncode != 0
    self.worker = None
    self.shutting_down = False
    # the far end may still be waking; give it the hold before letting go
    self.idle_since = time.monotonic()
    # after the run, not before it: a run writes JetlinkSpec itself, so a mark
    # taken at spawn always differs by the time it exits and every successful
    # provision started a second one
    self.note_marks()
    return False

  def note_marks(self) -> None:
    self.seen = self.settings.marks()
    self.had_host = gadget.host_attached()

  def wanted(self) -> str | None:
    """Why the worker should run, or None. Everything that decides whether
    there is work needs the catalog, the spec and the Jetson, so the worker
    decides; this only notices the things that could have changed the answer."""
    if not self.seen:
      return 'nothing has been checked since boot'
    changed = [k for k, v in self.settings.marks().items() if self.seen.get(k) != v]
    if changed:
      return f"{', '.join(changed)} changed"
    if self.dialed:
      return 'a phone dialed in'
    if self.attached and not self.had_host:
      return 'a jetson turned up'
    if time.monotonic() >= self.next_worker and self.unfinished:
      return 'the last run left something to do'
    return None

  def spawn_worker(self, why: str) -> None:
    gadget.log.warning("jetlink: starting a provisioning run: %s", why)
    self.dialed = False
    self.note_marks()
    self.next_worker = time.monotonic() + WORKER_BACKOFF
    try:
      self.worker = subprocess.Popen(self.worker_argv, cwd=self.worker_cwd,
                                     env={**os.environ, **self.worker_env})
    except Exception:
      gadget.log.exception("jetlink: could not start the provisioning run")
      self.worker = None

  def stop_worker(self) -> None:
    if self.worker is None:
      return
    self.worker.terminate()
    deadline = time.monotonic() + WORKER_GRACE
    while True:
      try:
        # a run that finished its round on the way out says so like any other
        self.unfinished = self.worker.wait(POLL) != 0
        break
      except subprocess.TimeoutExpired:
        if time.monotonic() >= deadline:
          self.worker.kill()
          self.unfinished = True
          break
        self.beat()   # a run inside a hello can take the whole grace
    self.worker = None
    self.shutting_down = False

  # -- the status record ------------------------------------------------------

  def status_record(self) -> dict:
    """What every other process reads instead of the gadget's files one by one
    (jetlink.openpilot.status), presence and its hold worked out once, here."""
    now = time.monotonic()
    state = gadget.udc_state()
    configured = state == 'configured'
    if configured:
      self.last_configured = now
    if self.dormant:
      # no enumeration during suspend; the CC line still tells a sleeping host from an unplugged one
      present = gadget.port_has_host()
    else:
      present = configured or now - self.last_configured < gadget.PRESENCE_HOLD
    return {
      'pid': os.getpid(),
      'at': now,
      'mode': self.mode,
      'link': None if self.built_ios is None else ('cable' if self.built_ios else 'usb'),
      'peer': self._peer,
      # root's jetlink-gadget and the lender's error, as gadget_error() puts
      # them together, or why a crash loop's backoff is holding this start
      'error': self.backing_off or gadget.gadget_error(),
      'net': gadget.net_status(),
      'dormant': self.dormant,
      'udc': state,
      'speed': gadget.usb_speed() if configured else None,
      'present': present,
      'server': self.server,
      'worker': self.worker is not None and self.worker.poll() is None,
      'unfinished': self.unfinished,
      # asked to stop: a record a SIGKILL during the teardown leaves behind is
      # an owner that was stopped, not one that died, and readers take it for none
      'stopping': self.stop,
    }

  def publish_status(self) -> None:
    """Rewrite the status record, which is the heartbeat as well. Never
    raises; a failure is logged once, until a write works again."""
    self.stopping_cleanly()
    try:
      gadget.write_record(gadget.STATUS, self.status_record())
    except Exception as e:
      # the last record would go stale under a live owner and read as
      # "service stopped"; without one the readers go back to
      # the gadget's files, which are still right
      self.forget_status()
      error = f"{type(e).__name__}: {e}"
      if error != self.status_error:
        self.status_error = error
        gadget.log.error("jetlink: could not write the status record (%s); readers read the gadget's files", error)
      return
    self.status_error = None
    self.published = time.monotonic()

  def beat(self) -> None:
    """Renew the record from inside a wait that can outlast the readers'
    HEARTBEAT_TIMEOUT, at most once a POLL."""
    if time.monotonic() - self.published >= POLL:
      self.publish_status()

  def waiting(self) -> bool:
    """should_stop for a wait inside a step: keeps the heartbeat going."""
    self.beat()
    return self.stop

  def forget_status(self) -> None:
    """A clean stop leaves no record, so only an owner that died leaves a
    heartbeat behind to go stale; the readers go back to the files."""
    try:
      gadget.STATUS.unlink(missing_ok=True)
    except OSError:
      pass

  # -- the loop -------------------------------------------------------------

  def request_stop(self, *_) -> None:
    self.stop = True

  def stopping_cleanly(self) -> None:
    """A stop that was asked for is clean however long its teardown takes:
    manager SIGKILLs an owner still in stop_worker's 10 s grace 5 s after its
    SIGINT, and a start left in gadget.STARTS would count as a death, three of
    them a crash loop. So the start is taken back as soon as the main thread
    sees the request, at the next record (within 0.5 s), not in the finally
    a SIGKILL never reaches. Not in the signal handler: it can land inside
    a write of the same file."""
    if self.stop and self.born is not None:
      forget_start(self.born)
      self.born = None

  def step(self) -> None:
    # each read is a file; take them once and pass them down
    mode = self.mode = self.settings.mode()
    if mode == 'off':
      if self.transport is not None:
        gadget.log.warning("jetlink: disabled, releasing the link")
        self.close_link()
      self.stop_worker()
      self.wake()
      if self.tuned:
        root.run('vm', 'restore')
        root.run('udc', 'restore')
        if self.tuned == 'ios':
          root.run('draw', 'on', timeout=root.PORT_TIMEOUT)
        self.tuned = None
      self.port.off()
      return
    self.link_step(mode == 'ios')
    if self.tuned != mode:
      # jetlink-root.sh vm: the recording VM tuning the gadget's reads need;
      # udc: the USB device side kept on for a host that powers the port
      # (port.py); draw, iOS only: no current drawn from the port, which an
      # iPhone cannot supply. While the link is on. After the step, so the
      # first gadget does not wait on them. Put back only when the link is
      # turned off or leaves iOS, never on exit: manager stops this at
      # ignition, just as the contention starts, and a phone plugged in before
      # it is back should still come up. A start assumes the draw stock, so a
      # cut a dead iOS owner left lasts until the reboot that clears it
      if self.tuned is None:
        root.run('vm', 'apply')
        root.run('udc', 'apply')
      if mode == 'ios':
        if root.run('draw', 'off', timeout=root.PORT_TIMEOUT):
          gadget.log.info("jetlink: drawing no current from the USB-C port, for an iPhone")
      elif self.tuned == 'ios':
        root.run('draw', 'on', timeout=root.PORT_TIMEOUT)
      self.tuned = mode

  def ensure_lender(self) -> None:
    """Listen for borrowers, or say why not and try again later.

    Only this process ever holds ep0, so without the lender nothing can use
    the link: the gadget stays held all the same, since letting it go would
    be an unplug that helps nobody, and the reason goes where
    gadget.gadget_error() reads it, which the panels show.
    """
    if self.lender.listening:
      return
    now = time.monotonic()
    if now < self.next_lender:
      return
    if self.lender.start():
      if self.lender_failed:
        gadget.log.warning("jetlink: listening for borrowers again")
      self.lender_failed = False
      gadget.note_lender_error(None)
      return
    self.next_lender = now + LENDER_BACKOFF
    if not self.lender_failed:
      gadget.log.error("jetlink: nothing can borrow the gadget, the lender could not listen on %s (%s); "
                       "trying again every %.0f s", self.lender.path, self.lender.error, LENDER_BACKOFF)
      self.lender_failed = True
    gadget.note_lender_error(self.lender.error)

  def link_step(self, ios: bool) -> None:
    """A step with the link on, for an iPhone or not."""
    self.ensure_lender()
    # before anything is presented: a C-to-C host has to find a device here.
    # The charging param is read every step; turned off, a phone already
    # charging keeps charging until the next plug
    self.port.update(configured=self.configured, charge=ios and self.settings.charge_phone())

    offroad = self.settings.offroad()
    if self.switch_mode(offroad, ios):
      return
    self.attached = gadget.host_attached()
    self.watch_the_port()

    # before the worker gate: hardwared waits 25 s for this and a build in
    # flight takes minutes, so a shutdown request cannot queue behind one
    reason = gadget.pending_shutdown()
    if reason is not None and not self.lender.lent:
      if self.worker_running():
        if self.shutting_down:
          # the run asking the jetson. Stopping it here restarted it every
          # step, half a second, less than it takes to start: on the bench
          # nothing ever asked, and hardwared gave up after its 25 s
          return
        self.stop_worker()
      if time.monotonic() < self.next_shutdown_run:
        return
      self.wake()
      if self.open_link():
        self.next_shutdown_run = time.monotonic() + SHUTDOWN_RETRY
        self.spawn_worker(f'the jetson has to be shut down: {reason}')
        self.shutting_down = True
      return

    if not offroad:
      # the drive has started and the endpoints belong to modeld. A run of ours
      # holding the lease would keep it out for the whole drive; the server's
      # build carries on and modeld picks the engine up over its loan
      self.stop_worker()

    if self.lender.lent or not offroad:
      if self.lender.lent:
        # the window starts when the last borrower lets go. Its own deadline,
        # because a host arriving clears the worker backoff and a borrower
        # letting go looks like one arriving
        self.lease_settled = time.monotonic() + LEASE_SETTLE
        self.idle_since = time.monotonic()
      return self.hold(ios)

    if self.worker_running():
      return self.hold(ios)

    if time.monotonic() < max(self.next_attempt, self.lease_settled):
      return

    why = self.wanted()
    if why is not None:
      if not self.ensure_gadget(ios):
        return
      self.wake()
      if not self.open_link():
        return
      return self.spawn_worker(why)

    # a phone never sleeps, and letting go takes the network interface it
    # dials over: for iOS the gadget stays up whatever the record says
    sleeps = self.far_end_sleeps() and not self.built_ios
    if self.transport is None:
      # nothing to do and nothing presented: only worth a bind if the far end
      # stays awake for it
      if not sleeps and self.ensure_gadget(ios):
        self.open_link()
      return
    if sleeps and time.monotonic() - self.idle_since >= DORMANT_HOLD:
      self.go_dormant()
    else:
      self.settle()

  def watch_the_port(self) -> None:
    """The edges of the USB link, and for iOS the phone's dial.

    For iOS the gadget's network comes up after each bind and the owner
    listens for the phone while nobody holds the loan; a borrower listens
    for it itself, and the owner listens again once the loan ends. The host
    going away takes the dial with it, so the next one is looked at afresh.
    """
    if self.attached and not self.configured:
      gadget.log.warning("jetlink: a host configured us at %s", gadget.usb_speed() or 'an unknown speed')
    elif self.configured and not self.attached and self.cable.held:
      gadget.log.warning("jetlink: the host went away, the cable link with it")
      self.cable.release()
      self.dialed = False
      self.publish()
    self.configured = self.attached
    if not self.built_ios:
      return
    self.ensure_net()
    if self.lender.lent:
      return   # the borrower listens for the phone; the port is its
    if self.transport is not None and self.net_ready and not self.cable.listening:
      self.cable.open()   # not before: the bind to 192.168.60.1 fails without usb0
    peer = self.cable.poll()
    if peer is not None:
      self.publish(peer)
      gadget.log.warning("jetlink: cable link from %s", peer)
      self.had_host = True
      self.idle_since = time.monotonic()
      # a reason for a run, unless it is the phone coming back after we hung
      # up on it, or a run is already going and its borrow will take this dial
      running = self.worker is not None and self.worker.poll() is None
      if self.cable.news and not running:
        self.dialed = True
    elif not self.cable.held and self._peer is not None:
      self.publish()   # the phone hung up, or its borrower finished

  def switch_mode(self, offroad: bool, ios: bool) -> bool:
    """Rebuild the gadget when the setting moved between USB and iOS: they are
    different devices, and the rebuild is an unplug. True when this step went
    on it.

    A switch waits for the car to park: the panels lock the setting while
    driving, and one written some other way waits too. Building the mode that
    is set is never held back, onroad included. Parked, leaving iOS is not held
    back either: an iOS gadget lends nobody the endpoint files (cable_mode), so
    nothing of a borrower's is under the rebuild, and a borrower waiting for a
    phone that never dials, or a run stuck with a silent one, kept the comma on
    iOS until a power cycle. Entering iOS unplugs a USB host whose endpoint
    files may be lent, so it waits for nobody to be on the link, except a run
    of ours, which is stopped.

    What is built is learned once, onroad too: an iOS gadget taken for USB
    would lend a phone the endpoint files."""
    if self.built_ios is None:
      self.built_ios = gadget.built_for_ios() if gadget.link_configured() else ios
      self.publish()
    # a failed build of the other mode left the gadget half built: build the
    # set mode again. A failure of the set mode itself is build()'s to retry
    half_built = self.failed_ios is not None and self.failed_ios != ios
    if ios == self.built_ios and not half_built:
      return False
    if ios != self.built_ios:
      # the way out of iOS whose USB build failed is retried onroad too: held
      # for the drive, the comma would sit on iOS waiting for a phone
      if not offroad and not (not ios and self.failed_ios is False):
        return False
      if ios:
        if self.worker_running():
          if self.shutting_down:
            return False   # the run asking the jetson to power off finishes first
          self.stop_worker()   # its loan ends as it exits
          return True
        if self.lender.lent:
          return False
        if self.transport is None and gadget.bound_udc():
          # bound, and not by us: the borrower of an owner that died (its run)
          # is still on the endpoints. The rebuild's unbind would pull the
          # gadget from under it, so it waits for the borrower to let go, when
          # the kernel unbinds
          if not self.switch_waiting:
            gadget.log.warning("jetlink: the setting is now iOS; the gadget is still bound for a borrower "
                               "from before this owner, rebuilding it once that lets go")
            self.switch_waiting = True
          return False
    self.switch_waiting = False
    if time.monotonic() < self.next_gadget_attempt and ios == self.failed_ios:
      return True   # this mode's last build failed; build() says when to try again
    self.stop_worker()   # bounded: WORKER_GRACE, then SIGKILL
    gadget.log.warning("jetlink: the setting is now %s, rebuilding the gadget", 'iOS' if ios else 'USB')
    self.close_link()
    self.dialed = False
    self.build(ios)
    return True

  def adopt(self) -> None:
    """Start from whatever an owner before this one left, dead or alive.

    The configfs gadget is used as it is: ensure_gadget and switch_mode look
    at it before building anything, and the first bind presents it again.
    What the last owner heard of the server still holds (gadget.SERVER, which
    a clean stop leaves); without it an owner started again while parked took
    an always-on Jetson for one that sleeps, and let the gadget go until the
    next drive's hello. The last owner's own
    records do not hold: the link it published, its dormant marker and its
    lender's error. The lender clears the socket it left once a connect
    proves it dead, and the port's first update lets go of its hold.
    """
    gadget.clear_link()
    gadget.set_dormant(False)
    gadget.note_lender_error(None)
    gadget.clear_leftovers(gadget.STATUS.parent)
    if self.server is None:
      try:
        heard = json.loads(gadget.SERVER.read_text())
      except (OSError, ValueError):
        heard = None
      self.server = heard if isinstance(heard, dict) else None

  def sit_out(self, until: float, died: int) -> None:
    """A crash loop's backoff: hold nothing, not the gadget, the lender or
    the port, until `until` or a stop. The status record says why, and that
    is the offroad alert while the link is on.

    A power-off request ends it: hardwared waits 25 s for the owner to take
    one, and the Jetson on its own supply stays on otherwise."""
    self.backing_off = (f"the service keeps stopping ({died} times in {CRASH_WINDOW / 60:.0f} min), "
                        f"waiting {until - time.monotonic():.0f} s before starting it again")
    gadget.log.warning("jetlink: %s", self.backing_off)
    self.publish_status()
    try:
      while not self.stop and time.monotonic() < until:
        if gadget.SHUTDOWN_REQUEST.exists():
          gadget.log.warning("jetlink: a power-off request ends the wait")
          break
        time.sleep(min(POLL, max(0.0, until - time.monotonic())))
        self.beat()
    finally:
      self.backing_off = None

  def take_lock(self) -> bool:
    """One owner at a time. A second owner beside a live one (a manager that
    was SIGKILLed without its cleanup starts jetlinkd again while the orphan
    still holds the gadget) would clear that owner's records, overwrite its
    status record and release its port hold. The kernel lets an flock go with
    the process however it dies, and the fd is not inherited by a run.
    Without a /dev/shm to lock in, the owner runs as it did before."""
    try:
      gadget.OWNER_LOCK.parent.mkdir(parents=True, exist_ok=True)
      fd = os.open(gadget.OWNER_LOCK, os.O_RDWR | os.O_CREAT, 0o644)
    except OSError as e:
      gadget.log.error("jetlink: could not open the owner's lock (%s), running without it", e)
      return True
    try:
      fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
      try:
        holder = os.pread(fd, 32, 0).decode(errors='replace').strip() or 'unknown'
      except OSError:
        holder = 'unknown'
      os.close(fd)
      gadget.log.error("jetlink: another owner (pid %s) holds the gadget, exiting", holder)
      return False
    os.ftruncate(fd, 0)
    os.pwrite(fd, str(os.getpid()).encode(), 0)
    self.lock_fd = fd
    return True

  def run(self) -> None:
    """Hold the gadget until stopped. Returns at once, touching nothing, when
    another owner is alive."""
    if not self.take_lock():
      return
    try:
      self.hold_the_gadget()
    finally:
      fd, self.lock_fd = self.lock_fd, None
      if fd is not None:
        os.close(fd)

  def hold_the_gadget(self) -> None:
    born = self.born = time.monotonic()
    wait, died = note_start(born)
    self.adopt()
    # the heartbeat from the start: the first step builds the gadget
    self.publish_status()
    try:
      if wait:
        self.sit_out(born + wait, died)
      while not self.stop:
        started = time.monotonic()
        try:
          self.step()
        except Exception:
          # nothing may escape: restarting in a loop is worse than sitting out a cycle
          gadget.log.exception("jetlink: unhandled error")
          self.close_link()
          self.next_attempt = time.monotonic() + RECONNECT_BACKOFF
        self.publish_status()
        time.sleep(max(0.0, POLL - (time.monotonic() - started)))
    finally:
      # first, inside manager's 5 s: it stops this when a chestnut turns up,
      # and the comma has to host that. The sysctls stay: a stop here is where
      # a drive begins
      self.port.off()
      self.lender.stop()
      # about this process's lender; with no owner there is nothing to borrow
      # anyway, and a chestnut may be why it stopped
      gadget.note_lender_error(None)
      self.stop_worker()
      self.close_link()
      gadget.set_dormant(False)
      self.forget_status()
      # an owner killed before it got this far without being asked to stop
      # counts as one that died; one that was asked took it back already
      if self.born is not None:
        forget_start(born)
        self.born = None
    gadget.log.warning("jetlink: stopped")

