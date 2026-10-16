"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

USB gadget side of the link: a FunctionFS vendor-specific bulk function.

On a comma this is the comma end. The roles look backwards and are not: AGNOS
has CONFIG_USB_F_FS built in, while a host needs no kernel driver at all, which
an L4T rootfs stripped of the gadget modules does not have. See
docs/transport.md.

Bring-up (jetlink/comma/jetlink-root.sh gadget does all of this):
    configfs gadget -> functions/ffs.jetlink -> mount -t functionfs
    write descriptors + strings to ep0 -> ep1 (OUT) and ep2 (IN) appear
    echo <udc> > UDC
"""
from __future__ import annotations

import errno
import logging
import os
import signal
import struct
import threading
import time
from collections import deque

from jetlink import protocol as P
from jetlink.transport.base import UDC_SYSFS, LinkError, LinkTimeout, StreamTransport, udc_speed, usb_link_info
from jetlink.transport.priority import background_thread, widen_affinity

# --- FunctionFS ABI -------------------------------------------------------

FUNCTIONFS_DESCRIPTORS_MAGIC_V2 = 3
FUNCTIONFS_STRINGS_MAGIC = 2

FLAG_HAS_FS = 1 << 0
FLAG_HAS_HS = 1 << 1
FLAG_HAS_SS = 1 << 2

USB_DT_INTERFACE = 0x04
USB_DT_ENDPOINT = 0x05
USB_DT_SS_ENDPOINT_COMP = 0x30

USB_ENDPOINT_XFER_BULK = 0x02
EP_OUT = 0x01  # host -> device
EP_IN = 0x82   # device -> host

# FunctionFS kmallocs a contiguous buffer per read and frees it on return. 16 KB
# is an order-2 page allocation, which this kernel retries without bound under
# memory pressure; vm.extra_free_kbytes (jetlink-root.sh) keeps that from
# stalling: no reclaim in 3,396 reads while recording. 8 KB would come from
# the slab like the writes, but a reply is 8,356 bytes, so it would take a
# second read: +0.3 ms a frame at p50.
READ_CHUNK = 16 * P.USB_MAX_PACKET
# How much the reader may queue before it stops. Only bounds memory if the
# consumer stalls: inference never needs more than one response.
MAX_QUEUED = 512 << 10
# Read buffers kept for reuse. Steady state has one or two in flight, so this is
# only a ceiling for a transient backlog. 8 * 16 KB = 128 KB.
FREE_BUFS = 8
# Just below modeld's frame loop (54), so the loop wins a contended core and the
# reader still preempts everything else. See _raise_reader_priority.
READER_RT_PRIORITY = 51

log = logging.getLogger('jetlink')

# Enumerated is not ready: the host still has to open the device and claim the
# interface, and until then the endpoints return EIO. Its sysfs poll makes that
# a second or two, so wait rather than fail the first frame after connect.
EP_READY_TIMEOUT = 10.0
# How long opening the endpoint files waits for a host to configure the gadget;
# EP_READY_TIMEOUT covers the claim that follows.
EP_OPEN_TIMEOUT = 10.0

# FunctionFS writes cannot time out: a request sits queued until the host
# drains it, measured at 90 s while a Jetson booted and three minutes on a
# drive. Only unbinding the UDC completes it (ESHUTDOWN). A send waiting for
# the host to take earlier writes waits this long by default.
WRITE_TIMEOUT = 15.0
# Bytes the IN endpoint may hold that the host has not taken. A whole frame is
# 459 KB, so a frame may go out behind one the host has not finished, and a
# third may not (try_send refuses it). The one behind covers a completion the
# kernel has not posted yet as well: FunctionFS posts each from a SCHED_OTHER
# kworker. Uploads stream through it in windows.
QUEUED_LIMIT = 1 << 20
# How long closing waits for queued writes to reach the host (a LEAVE) before
# it drops the gadget to complete them, and how long it then waits for that.
# An endpoint file whose request is still queued stays open in the kernel, and
# the next open of it answers EBUSY.
CLOSE_FLUSH = 0.5
ABORT_DRAIN = 2.0
# where the comma's gadget lives: jetlink-root.sh gadget builds it there and
# mounts its FunctionFS instance here
GADGET = '/sys/kernel/config/usb_gadget/jetlink'
MOUNT = '/dev/ffs-jetlink'
# How long close() waits for the reader thread after unbinding, which is what
# wakes it. A read the kernel will not complete is left to die with the process.
READER_JOIN_TIMEOUT = 1.0
# How long a rebind leaves the gadget off the bus. Long enough that the host
# sees a disconnect and not a glitch; a dwc3 pull-down is immediate.
REBIND_SETTLE = 0.5
_NOT_READY = (errno.EIO, errno.ESHUTDOWN, errno.ENODEV)

# A signal inside a synchronous FunctionFS transfer is not a retry:
# ffs_epfile_io dequeues the request and returns EINTR whatever part of it the
# host already took, os.readv/os.writev re-issue the whole call, and the stream
# has lost or repeated bytes. modeld's msgq raises SIGUSR2 ~160 times a second,
# enough to fail a synchronous-write link about once per 30 s of driving.
# The reader masks every signal for its life. Writes are AIO, which never
# waits inside a transfer, so the frame thread needs no mask.
_IO_SIGNALS = signal.valid_signals()


def _interface_desc(n_endpoints: int = 2, i_interface: int = 1) -> bytes:
  return struct.pack('<BBBBBBBBB', 9, USB_DT_INTERFACE, 0, 0, n_endpoints,
                     *P.USB_VENDOR_CLASS, i_interface)


def _endpoint_desc(addr: int, max_packet: int) -> bytes:
  return struct.pack('<BBBBHB', 7, USB_DT_ENDPOINT, addr, USB_ENDPOINT_XFER_BULK, max_packet, 0)


def _ss_companion(max_burst: int = 15) -> bytes:
  """SuperSpeed endpoint companion.

  bMaxBurst counts *additional* packets, so 15 is a 16 KB burst. Without
  bursting a 459 KB request takes 167 ms, over the whole frame budget.
  """
  return struct.pack('<BBBBH', 6, USB_DT_SS_ENDPOINT_COMP, max_burst, 0, 0)


def build_descriptors() -> bytes:
  fs = _interface_desc() + _endpoint_desc(EP_OUT, 64) + _endpoint_desc(EP_IN, 64)
  hs = _interface_desc() + _endpoint_desc(EP_OUT, 512) + _endpoint_desc(EP_IN, 512)
  ss = (_interface_desc()
        + _endpoint_desc(EP_OUT, P.USB_MAX_PACKET) + _ss_companion()
        + _endpoint_desc(EP_IN, P.USB_MAX_PACKET) + _ss_companion())

  # struct usb_functionfs_descs_head_v2: magic, length, flags, then ALL the
  # per-speed counts together (one __le32 per flag set, in flag order), and only
  # then the descriptor blocks. Interleaving count/block per speed gets EINVAL.
  body = struct.pack('<III', 3, 3, 5) + fs + hs + ss
  flags = FLAG_HAS_FS | FLAG_HAS_HS | FLAG_HAS_SS
  return struct.pack('<III', FUNCTIONFS_DESCRIPTORS_MAGIC_V2, 12 + len(body), flags) + body


def build_strings(name: str = 'jetlink') -> bytes:
  s = name.encode() + b'\0'
  return (struct.pack('<IIII', FUNCTIONFS_STRINGS_MAGIC, 16 + 2 + len(s), 1, 1)
          + struct.pack('<H', 0x0409) + s)


class FfsTransport(StreamTransport):
  """The gadget transport. Reads run on their own thread; writes are AIO.

  FunctionFS ignores O_NONBLOCK once the host has enabled the endpoint, so a
  read on the caller's thread cannot honour a deadline: a 0.5 s timeout was
  measured returning after 14 s. The reader hands whole chunks over a condition
  variable the caller can wait on.

  A message goes out as AIO requests of write_chunk bytes, all submitted in
  one io_submit on the caller's thread (see aio.py): the kernel has copied the
  bytes when it returns, the bus streams the requests back to back, and the
  caller never waits inside a transfer. What it can wait on is room
  (QUEUED_LIMIT): a host that is not taking data fills it, which a frame
  answers by holding (try_send) and anything else by waiting, then dropping
  the gadget, under its deadline.
  """
  # FunctionFS kmallocs one contiguous buffer per request, and AIO holds a
  # frame's worth at once. A whole frame in one needs order-7 pages, which
  # recording rollover leaves none of; 57 x 32 KB needs 15 order-3 blocks at
  # once, and an aged comma can have as few as 3 free: io_submit then stalls
  # ~94 ms in compaction. 8 KB is the largest size
  # SLUB serves from a slab cache (kmalloc-8192), which never compacts: it
  # falls back to order-1 slabs. A whole number of 1 KB packets, so no request
  # ends on a short packet.
  write_chunk = P.GADGET_TX_ALIGN // 2
  tx_align = P.GADGET_TX_ALIGN

  def __init__(self, mount: str = MOUNT, gadget: str | None = None,
               udc: str | None = None):
    self._prepare(mount, gadget)
    try:
      self.ep0 = os.open(os.path.join(mount, 'ep0'), os.O_RDWR)
      os.write(self.ep0, build_descriptors())
      os.write(self.ep0, build_strings())
      if gadget is not None:
        # Bind last: a FunctionFS gadget cannot attach until its descriptors
        # are written, which is why jetlink-root.sh leaves UDC empty.
        self.bind(udc)
      # ep1/ep2 exist now, but opening one before a host enables it costs the
      # gadget until the next reboot; see _ensure_epfiles.
    except BaseException:
      self.close()   # otherwise a failed bring-up leaks the descriptors it did open
      raise

  def link_info(self) -> dict:
    return usb_link_info('usb', udc_speed(self.bound_udc))

  @classmethod
  def borrowed(cls, mount: str, udc: str, bounce=None, owner_gadget: str | None = None) -> FfsTransport:
    """A transport over a gadget another process owns.

    That process holds ep0 and the UDC bind for its whole life, so the gadget
    does not leave the bus when the link changes hands: this end only opens the
    endpoint files and moves bytes, and nothing here writes descriptors, binds
    or unbinds. The endpoint files open again once nothing is reading them (a
    read a dead link left queued keeps them busy: see _open_after_bounce); ep0
    never does, which is why the owner keeps it.

    The ep0 rule still holds and `udc` is what keeps it: the endpoints are
    still opened only once that controller reads configured. `bounce` is how a
    write with no reader is freed, since the unbind that frees it belongs to
    the owner. `owner_gadget` is the last resort for when the owner does not
    answer at all; see _abort_write.
    """
    if not udc:
      # _configured() would answer "no controller of ours to ask, assume
      # ready" and _ensure_epfiles would open an endpoint no host has enabled,
      # which costs the gadget until the comma is rebooted.
      raise LinkError('a borrowed gadget must name its controller')
    t = cls.__new__(cls)
    t._prepare(mount, gadget=None)
    t.bound_udc = udc
    t._bounce = bounce
    t._owner_gadget = owner_gadget
    return t

  def _prepare(self, mount: str, gadget: str | None) -> None:
    # This end only receives replies: an INFER_RESP is 8 KB, or 74 KB when
    # WANT_HIDDEN asks for the whole output, and the upload goes the other way.
    # 128 KB leaves margin the memory-tight comma can spare, and RxBuffer grows
    # past it on demand.
    super().__init__(rx_size=128 << 10)
    self.mount = mount
    self.gadget = gadget
    self.bound_udc: str | None = None
    self._bounce = None
    self._owner_gadget: str | None = None
    self.ep0 = self.ep_out = self.ep_in = -1
    self._state_fd = -1   # held-open UDC 'state' fd; see _udc_state
    self._ready_deadline: float | None = None
    self._cv = threading.Condition()
    self._chunks: deque[tuple[memoryview, float, float, float]] = deque()
    self._free: deque[bytearray] = deque()   # read buffers the consumer handed back; see _read_loop
    self.last_receive = {'prepare': 0.0, 'read_wait': 0.0, 'handoff': 0.0}
    self._queued = 0
    self._reader_error: str | None = None
    self._closing = False
    self._had_host = False
    self._open_lock = threading.Lock()
    self.last_send: dict = {}
    self.send_totals: dict = {}
    self._reader: threading.Thread | None = None
    # the AIO writes: the context once ep2 is open, holding QUEUED_LIMIT in
    # requests; requests submitted and reaped over its life, each write_chunk
    # bytes (_requests), and when each submit's last one went in; and the
    # first failure, which ends the link (see _queue)
    self._tx_lock = threading.Lock()
    self._aio = None
    self._submitted = self._reaped = 0
    self._batches: deque[tuple[int, float]] = deque()
    self._tx_error: str | None = None

  def _udc_state(self) -> str | None:
    """The controller's gadget state, off a held-open fd.

    The reader checks this before every readv and cannot skip it (see
    _read_loop). Opening the sysfs file each time allocates, and under memory
    pressure that reclaim stalled a frame 25 ms; a pread at offset 0 still
    re-runs the attribute's show(), so the value is current. pread, not lseek
    and read: the reader and the frame thread both ask during the claim
    window, and two lseek+read pairs interleaved on one fd hand one of them
    an empty read, which _host_gone would take for a host that left. The fd
    is dropped on unbind and reopened lazily in case the controller differs.
    """
    if self.bound_udc is None:
      return None
    if self._state_fd < 0:
      try:
        self._state_fd = os.open(os.path.join(UDC_SYSFS, self.bound_udc, 'state'), os.O_RDONLY)
      except OSError:
        return None
    try:
      state = os.pread(self._state_fd, 64, 0).decode().strip()
    except OSError:
      _close_quietly(self._state_fd)
      self._state_fd = -1
      return None
    return state or None

  def _configured(self) -> bool:
    """Has a host set our configuration? Only then are the endpoints enabled."""
    if self.bound_udc is None:
      return self.gadget is None   # no controller of ours to ask; assume ready
    return self._udc_state() == 'configured'

  def _udc_note(self) -> str:
    """The controller's state, for a failure message.

    The same ENODEV comes from a cable falling out ("not attached"), from a
    host resetting or re-enumerating us ("default", "addressed") and from a
    bus the host suspended ("suspended"). A drive's worth of failures read
    the same without it; with it the log says which layer let go.
    """
    state = self._udc_state()
    return f" (udc: {state})" if state else ''

  def _ensure_epfiles(self) -> None:
    """Open ep1/ep2 and start the reader, once a host has enabled them.

    Never touch an endpoint file before that. ffs_epfile_io sleeps in
    wait_event_interruptible until epfile->ep is set, and unbind does not wake
    it; the sleeping syscall holds the struct file, so ffs_epfile_release never
    runs and every ep0 open after it answers EBUSY, to this process and the next
    one, until the comma is rebooted. The UDC reading configured is the same
    edge that sets epfile->ep.
    """
    if self.ep_out >= 0:
      return
    with self._open_lock:
      if self.ep_out >= 0:
        return
      deadline = time.monotonic() + EP_OPEN_TIMEOUT
      self._wait_configured(deadline)
      try:
        self.ep_out = os.open(os.path.join(self.mount, 'ep1'), os.O_RDWR)
      except OSError as e:
        if e.errno != errno.EBUSY or self._bounce is None:
          raise
        self.ep_out = self._open_after_bounce(deadline)
      self.ep_in = os.open(os.path.join(self.mount, 'ep2'), os.O_RDWR)
      try:
        self._aio = _open_aio(self.ep_in, QUEUED_LIMIT // self.write_chunk)
      except OSError as e:
        self._close_fds(('ep_in', 'ep_out'), None)
        raise LinkError(f"no AIO context for the gadget's writes: {e}") from e
      self._had_host = True
      self._reader = threading.Thread(target=self._read_loop, name='jetlink-ffs-read', daemon=True)
      self._reader.start()

  def _wait_configured(self, deadline: float) -> None:
    while not self._configured():
      if self._closing:
        raise LinkError("gadget closing")
      if time.monotonic() >= deadline:
        raise LinkTimeout(f"no host configured the gadget within {EP_OPEN_TIMEOUT:.0f}s")
      time.sleep(0.02)

  def _open_after_bounce(self, deadline: float) -> int:
    """ep1 answered EBUSY: a transport this process closed after its link died
    left a read queued on it, and FunctionFS keeps that read, and the endpoint
    with it, until an unbind completes it, as when a Jetson's server
    restarts mid-drive. The unbind is the owner's, so a borrower asks for one, then opens once the
    host has the gadget back and the stale read has let go."""
    log.warning("jetlink: ep1 is held by a read the last link left queued, asking the owner to bounce the gadget")
    if not self._bounce():
      raise LinkError("ep1 is busy and the owner would not bounce the gadget")
    while True:
      self._wait_configured(deadline)
      try:
        return os.open(os.path.join(self.mount, 'ep1'), os.O_RDWR)
      except OSError as e:
        if e.errno != errno.EBUSY or time.monotonic() >= deadline:
          raise
      time.sleep(0.05)

  def release_endpoints(self) -> bool:
    """Put the endpoint files down, keeping ep0 and the descriptors.

    An exchange leaves a read queued on the endpoint, and FunctionFS keeps it
    queued until something completes it: nobody else may read that endpoint
    until it does, and the only thing that dequeues it is the unbind. So the
    owner gives the endpoints up like this and binds straight back (one
    re-enumeration) without ever letting go of ep0, which is the whole point,
    since the gadget exists only while somebody holds it.

    False when there is nothing to give up. Afterwards this transport is bare
    and bound, and using it again reopens the endpoints as any first use does.
    """
    if self.gadget is None or self._closing or self.ep_out < 0:
      return False
    udc, self._had_host = self.bound_udc, False
    self._settle_writes()
    self.unbind()          # completes the queued read with ESHUTDOWN
    reader, self._reader = self._reader, None
    if reader is not None and reader is not threading.current_thread():
      reader.join(READER_JOIN_TIMEOUT)
    self._close_fds(('ep_in', 'ep_out'), reader)
    # Whatever the last exchange left behind goes with the endpoints: half a
    # message would frame the next one's first reply as garbage.
    with self._cv:
      self._chunks.clear()
      self._free.clear()
      self._queued = 0
      self._reader_error = None
      self._cv.notify_all()
    self.rx.start = self.rx.end = 0
    self._ready_deadline = None
    self._tx_error = None
    time.sleep(REBIND_SETTLE)
    self.bind(udc)
    return True

  def bind(self, udc: str | None = None) -> None:
    if self.gadget is None:
      raise LinkError("no gadget path given")
    if udc is None:
      udcs = sorted(os.listdir(UDC_SYSFS))
      if not udcs:
        raise LinkError("no USB device controller found")
      udc = udcs[0]
    with open(os.path.join(self.gadget, 'UDC'), 'w') as f:
      f.write(udc + '\n')
    self.bound_udc = udc

  @property
  def lendable(self) -> bool:
    """Bound to a controller, with no endpoint file open on this end.

    The state another process can take the endpoints over from. FunctionFS
    keeps a queued read queued until something completes it, so a reader here
    would sit in front of the borrower and take its reply; and without a bound
    controller there is nothing to take over.
    """
    return bool(self.gadget is not None and self.bound_udc and self.ep_out < 0
                and not self._closing)

  def rebind(self) -> bool:
    """One unplug and replug, as the host sees it.

    For a host that answered our bind with a bus reset and then stopped: the
    UDC sits in `default` or `addressed` and only another edge moves it. A
    Jetson whose hubs are not armed for remote wakeup does exactly that.

    Refused while this end has the endpoint files open. Unbinding then
    completes the reader's request with ESHUTDOWN and the transport is done;
    the caller wants a working link, not a freshly bound dead one.
    """
    if self._closing or self.ep_out >= 0:
      return False
    if self._bounce is not None:
      return bool(self._bounce())   # a borrowed gadget: the bind is the owner's
    if not self.lendable:
      return False
    udc = self.bound_udc
    self.unbind()
    time.sleep(REBIND_SETTLE)
    self.bind(udc)
    return True

  def unbind(self, gadget: str | None = None) -> None:
    """Take the gadget off the bus. `gadget` overrides our own path, which is
    how a borrower reaches an owner that has stopped answering."""
    gadget = gadget or self.gadget
    if gadget is None or self.bound_udc is None:
      return
    try:
      with open(os.path.join(gadget, 'UDC'), 'w') as f:
        f.write('\n')
    except OSError:
      pass
    self.bound_udc = None
    if self._state_fd >= 0:   # reopens lazily against whatever udc we bind next
      _close_quietly(self._state_fd)
      self._state_fd = -1

  def _abort_write(self, why: str = 'USB send exceeded its deadline') -> None:
    """Drop the gadget so the writes the host is not taking complete, with
    ESHUTDOWN, and the link with them. Nothing else completes a queued
    FunctionFS request (see WRITE_TIMEOUT), and one left queued holds its
    endpoint file open in the kernel under the next user of the gadget.
    """
    self._set_error(f'{why}; link abandoned')
    self.last_send['aborted'] = True
    self.send_totals['aborts'] = self.send_totals.get('aborts', 0) + 1
    log.warning("jetlink: %s, dropping the gadget to free the queued writes", why)
    if self._bounce is None:
      return self.unbind()
    # A borrowed gadget: the unbind belongs to whoever owns ep0, so ask. If
    # nobody answers (the owner died, or is wedged itself), take the gadget
    # down from here anyway: a re-enumeration costs one rejoin, where requests
    # nothing completes cost the endpoint until the comma reboots.
    if self._bounce():
      return
    log.error("jetlink: the gadget's owner did not answer; dropping the link from here")
    self.unbind(self._owner_gadget)

  # -- writes: AIO ---------------------------------------------------------

  def try_send(self, msg_type: int, seq: int, parts=(), timeout: float | None = None) -> bool:
    """Queue one message unless that means waiting for the host: False, and
    nothing sent, while writes it has not taken leave no room for this one
    (QUEUED_LIMIT). A frame waits for nothing here, `timeout` included; the
    caller holds instead (JetlinkModelState)."""
    bufs = self._frame(msg_type, seq, parts, 0)
    self._ensure_epfiles()
    return self._queue(bufs, None, wait=False)

  def send(self, msg_type: int, seq: int, parts=(), flags: int = 0, timeout: float | None = None) -> None:
    bufs = self._frame(msg_type, seq, parts, flags)
    self._ensure_epfiles()
    self._queue(bufs, None if timeout is None else time.monotonic() + timeout, wait=True)

  def _queue(self, bufs: list[memoryview], deadline: float | None, wait: bool) -> bool:
    """Put one framed message on the IN endpoint as requests of write_chunk
    bytes. Returns once the kernel holds every byte, not once the host has
    taken them; a failure among earlier requests is this send's LinkError.
    `wait` waits for room until `deadline` (WRITE_TIMEOUT from now by
    default), then drops the gadget; without it there is no waiting, and
    False says the message was not sent."""
    started = time.monotonic()
    deadline = started + WRITE_TIMEOUT if deadline is None else deadline
    total = sum(b.nbytes for b in bufs)
    stats = self.last_send = {'bytes': total, 'requests': 0, 'submit_ms': 0.0, 'wait_ms': 0.0,
                              'backlog_kb': 0, 'backlog_ms': 0.0, 'chunk': self.write_chunk,
                              'refused': False, 'aborted': False, 'errno': None}
    try:
      with self._tx_lock:
        if self._closing or self._aio is None:
          raise LinkError('gadget closing')
        self._collect()
        if self._tx_error is not None:
          raise LinkError(self._tx_error)
        if queued := self._submitted - self._reaped:
          # what the host had not taken when this message came: the measure
          # of a host falling behind, which nothing else on this end can see
          stats['backlog_kb'] = queued * self.write_chunk >> 10
          stats['backlog_ms'] = (started - self._batches[0][1]) * 1e3
          if not wait and (queued + total // self.write_chunk) > self._aio.depth:
            stats['refused'] = True
            return False
        # the views in `bufs` keep these addresses valid until io_submit returns
        spans = [self._aio.address(b) for b in bufs if b.nbytes]
        plan = self._aio.layout(tuple(n for _, n in spans), self.write_chunk)
        self._submit_message(plan, [a for a, _ in spans], deadline, stats)
        return True
    finally:
      self._count(stats)

  def _submit_message(self, plan, bases: list[int], deadline: float, stats: dict) -> None:
    """io_submit the message's requests (an aio.Layout over the spans at
    `bases`) as room allows: all at once for a frame, in windows for an upload
    chunk larger than the context."""
    done = 0
    while done < plan.count:
      room = self._aio.depth - (self._submitted - self._reaped)
      if room <= 0:
        self._wait_for_room(deadline, stats)
        continue
      done += self._submit(plan, bases, done, min(room, plan.count - done), stats)

  def _submit(self, plan, bases: list[int], start: int, count: int, stats: dict) -> int:
    """io_submit `count` of the message's requests from `start`; how many the
    kernel queued. FunctionFS reports a failed write as its completion
    (_collect): io_submit itself fails only on a bad context or iocb."""
    t0 = time.monotonic()
    try:
      n = self._aio.submit(plan, bases, start, count)
    except OSError as e:
      stats['errno'] = e.errno
      why = f"gadget write failed: {e}{self._udc_note()}"
      self._set_error(why)
      raise LinkError(why) from e
    now = time.monotonic()
    stats['submit_ms'] += (now - t0) * 1e3
    stats['requests'] += n
    self._submitted += n
    self._batches.append((self._submitted, now))
    return n

  def _wait_for_room(self, deadline: float, stats: dict) -> None:
    """Wait for the host to take queued writes, until `deadline`."""
    now = time.monotonic()
    if now >= deadline:
      self._abort_write(f'the host took no USB data for {now - self._batches[0][1]:.2f} s')
      raise LinkError(self._tx_error)
    self._collect(1, deadline - now)
    stats['wait_ms'] += (time.monotonic() - now) * 1e3
    if self._tx_error is not None:
      raise LinkError(self._tx_error)

  def _set_error(self, why: str) -> None:
    """The link's first write failure, which every send after it raises."""
    if self._tx_error is None:
      self._tx_error = why

  def _collect(self, min_nr: int = 0, timeout: float = 0.0) -> None:
    """Reap finished writes, waiting up to `timeout` for `min_nr` of them. The
    first that did not write all of its bytes is the link's failure."""
    queued = self._submitted - self._reaped
    if not queued:
      return
    results = self._aio.reap(min(min_nr, queued), timeout)
    self._reaped += len(results)
    while self._batches and self._batches[0][0] <= self._reaped:
      self._batches.popleft()   # what is left starts with the oldest still queued
    chunk = self.write_chunk
    if results.count(chunk) != len(results):
      bad = next(r for r in results if r != chunk)
      self._set_error(f"gadget write failed: {os.strerror(-bad) if bad < 0 else f'{bad} of {chunk} bytes'}"
                      f"{self._udc_note()}")

  def _count(self, stats: dict) -> None:
    """Session totals, which keep a slow send between the 1 Hz log samples."""
    totals = self.send_totals
    totals['messages'] = totals.get('messages', 0) + 1
    for key in ('bytes', 'requests', 'refused'):
      totals[key] = totals.get(key, 0) + stats[key]
    for key, top in (('submit_ms', 'max_submit_ms'), ('wait_ms', 'max_wait_ms'), ('backlog_ms', 'max_backlog_ms')):
      totals[top] = max(totals.get(top, 0.0), stats[key])

  def _settle_writes(self) -> None:
    """Before the endpoint files go: give queued writes CLOSE_FLUSH to reach
    the host (a LEAVE), drop the gadget to complete the rest, and destroy the
    AIO context once nothing is left in it. io_destroy waits, uninterruptibly,
    for what it cancels, and FunctionFS cannot cancel a request while the bus
    is suspended (dwc3 refuses in LPM), so it is only called on an empty
    context; otherwise the context is left to the process."""
    if self._aio is None:
      return
    if not self._tx_lock.acquire(timeout=CLOSE_FLUSH):
      # a send is waiting for room the host is not making; this frees it
      self._abort_write('closing a link whose host stopped taking USB data')
      if not self._tx_lock.acquire(timeout=ABORT_DRAIN):
        log.error("jetlink: a send still holds the gadget's writes; leaving their AIO context to the process")
        return
    try:
      self._drain(CLOSE_FLUSH)
      if self._submitted > self._reaped:
        self._abort_write(f'{self._submitted - self._reaped} USB writes still queued at close')
        self._drain(ABORT_DRAIN)
      if self._submitted > self._reaped:
        log.error("jetlink: %d USB writes never completed; leaving their AIO context to the process",
                  self._submitted - self._reaped)
      else:
        self._aio.close()
      self._aio = None
      self._submitted = self._reaped = 0
      self._batches.clear()
    finally:
      self._tx_lock.release()

  def _drain(self, seconds: float) -> None:
    end = time.monotonic() + seconds
    while self._submitted > self._reaped and (left := end - time.monotonic()) > 0:
      self._collect(1, left)

  # -- the reader thread ---------------------------------------------------

  def _widen_affinity(self) -> None:
    """Move the reader off the core modeld pinned its frame loop to.

    A thread created under config_realtime_process(7, 54) inherits SCHED_FIFO 54
    and the single-core pin, and sharing that core serialises the reader with
    the frame loop. Usually a no-op: the creator is normally a background thread
    already. See priority.widen_affinity.
    """
    widen_affinity()

  def _raise_reader_priority(self) -> None:
    """Realtime priority, so a completed read leaves the endpoint at once.

    The creator has dropped to SCHED_OTHER, and under recording plus onroad load
    the wait to be scheduled after a transfer measures 17 ms mean, 23 ms max,
    over budget on read_wait alone. The reader copies a chunk and blocks again, so it
    never holds a core. Best effort, and open-coded because jetlink must not
    import openpilot.
    """
    try:
      os.sched_setscheduler(0, os.SCHED_FIFO, os.sched_param(READER_RT_PRIORITY))
    except (OSError, AttributeError, ValueError):
      pass

  def _read_loop(self) -> None:
    # See _IO_SIGNALS.
    signal.pthread_sigmask(signal.SIG_BLOCK, _IO_SIGNALS)
    self._widen_affinity()
    self._raise_reader_priority()
    # Fill the pool up front: recycling alone leaves a gap while a reply's
    # chunks arrive and the consumer is a scheduling beat behind, and an
    # allocation there reclaims under memory pressure (24 ms, over budget).
    self._free.extend(bytearray(READ_CHUNK) for _ in range(FREE_BUFS))
    while not self._closing:
      with self._cv:
        while self._queued >= MAX_QUEUED and not self._closing:
          self._cv.wait(0.1)
      if self._closing:
        return
      prepare_started = time.monotonic()
      if not self._configured():
        # Same trap as _ensure_epfiles: the host can drop the configuration
        # between two reads, and the readv after that sleeps forever. Treat it
        # as the endpoint error it would have been.
        if self._wait_for_host_ready():
          continue
        self._fail(f"host dropped the gadget configuration{self._udc_note()}")
        return
      # Reuse a buffer the consumer handed back: a fresh bytearray here was
      # measured stalling 20+ ms mid-frame under memory pressure, and the read
      # cannot start until it returns. Only this thread pops the free list.
      buf = self._free.popleft() if self._free else bytearray(READ_CHUNK)
      read_started = time.monotonic()
      try:
        # A multiple of the packet size: the OUT endpoint rejects anything else.
        got = os.readv(self.ep_out, [buf])
      except OSError as e:
        if self._closing:
          return
        if e.errno in _NOT_READY and self._wait_for_host_ready():
          continue
        self._fail(f"gadget read failed: {e}{self._udc_note()}")
        return
      if got == 0:
        self._fail(f"gadget read returned EOF (host disconnected){self._udc_note()}")
        return
      read_finished = time.monotonic()
      self._ready_deadline = None
      self._had_host = True
      with self._cv:
        self._chunks.append((memoryview(buf)[:got], read_finished,
                             read_started - prepare_started, read_finished - read_started))
        self._queued += got
        self._cv.notify_all()

  def _fail(self, why: str) -> None:
    with self._cv:
      self._reader_error = why
      self._cv.notify_all()

  def recv(self, timeout: float | None = None):
    # Per-message maxima, in seconds. read_wait covers the peer and kernel IO,
    # handoff the consumer's wake; neither is a pure scheduler measurement.
    self.last_receive = {'prepare': 0.0, 'read_wait': 0.0, 'handoff': 0.0}
    return super().recv(timeout)

  def _read_into(self, dest: memoryview, timeout: float | None) -> int:
    self._ensure_epfiles()
    with self._cv:
      if not self._chunks and self._reader_error is None:
        self._cv.wait(timeout)
      if self._chunks:
        chunk, arrived, prepare, read_wait = self._chunks[0]
        self.last_receive['prepare'] = max(self.last_receive['prepare'], prepare)
        self.last_receive['read_wait'] = max(self.last_receive['read_wait'], read_wait)
        self.last_receive['handoff'] = max(self.last_receive['handoff'], time.monotonic() - arrived)
        n = min(chunk.nbytes, dest.nbytes)
        dest[:n] = chunk[:n]
        if n < chunk.nbytes:
          self._chunks[0] = (chunk[n:], arrived, prepare, read_wait)
        else:
          self._chunks.popleft()
          # Copied out, so return the buffer to the pool. chunk.obj survives a
          # reslice; skip anything not from this pool, such as a test's bytes.
          buf = chunk.obj
          if type(buf) is bytearray and len(buf) == READ_CHUNK and len(self._free) < FREE_BUFS:
            self._free.append(buf)
        self._queued -= n
        self._cv.notify_all()
        return n
      if self._reader_error is not None:
        raise LinkError(self._reader_error)
      return 0   # timed out with nothing new; _fill owns the deadline

  def _wait_for_host_ready(self) -> bool:
    """True while still inside the grace period for the host to claim the link.

    The endpoints return EIO until the host claims the interface. The clock
    starts on the first such error, not at open, so it covers a re-enumeration.
    """
    if self._host_gone():
      return False
    now = time.monotonic()
    if self._ready_deadline is None:
      self._ready_deadline = now + EP_READY_TIMEOUT
    if now < self._ready_deadline:
      time.sleep(0.005)
      return True
    return False

  def _host_gone(self) -> bool:
    """A host had the gadget configured and no longer does.

    The endpoints answer ENODEV both before a host configures the gadget and
    after it disconnects, and only the first deserves the grace period; giving
    it to the second costs a mid-drive disconnect 10 s, about 200 frames. The UDC
    state separates them, and it is set in the interrupt that disabled the
    endpoint, so it is current when the failed call returns.
    """
    if not self._had_host or self.bound_udc is None:
      return False
    state = self._udc_state()
    return state is not None and state != 'configured'

  def close(self) -> None:
    self._closing = True
    self._settle_writes()
    # Unbinding disables the endpoints, which completes the reader's pending
    # request with ESHUTDOWN and lets the thread exit before its fd goes away.
    self.unbind()
    reader, self._reader = self._reader, None
    if reader is not None and reader is not threading.current_thread():
      reader.join(READER_JOIN_TIMEOUT)
    with self._cv:
      self._cv.notify_all()
    self._close_fds(('_state_fd', 'ep_in', 'ep_out', 'ep0'), reader)

  def _close_fds(self, names, reader: threading.Thread | None) -> None:
    """Close these descriptors, clearing each as it goes.

    Clearing matters because a second close() would otherwise shut whatever
    those descriptor numbers had been recycled into. ep_out is closed on its
    own thread while a read is still outstanding: the read never came back
    (nothing to unbind, or a kernel that will not complete it), and close()
    returns regardless on Linux but the caller must not be risked on that.
    """
    for name in names:
      fd = getattr(self, name, -1)
      setattr(self, name, -1)
      if fd is None or fd < 0:
        continue
      if name == 'ep_out' and reader is not None and reader.is_alive():
        threading.Thread(target=_close_quietly, args=(fd,), daemon=True).start()
        continue
      _close_quietly(fd)


def _open_aio(fd: int, depth: int):
  """The AIO context for ep2's writes (aio.Aio). Imported on first use: the
  resident gadget owner imports this module and never writes, and ctypes is
  not free."""
  from jetlink.transport.aio import Aio
  return Aio(fd, depth)


def _close_quietly(fd: int) -> None:
  # Runs on its own thread when a read never came back; that thread inherits
  # the creator's scheduling, which in modeld is the frame loop's.
  background_thread()
  try:
    os.close(fd)
  except OSError:
    pass
