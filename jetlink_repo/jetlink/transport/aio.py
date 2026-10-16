"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

Linux native AIO (io_submit), for the gadget's endpoint writes.

A synchronous FunctionFS write holds the endpoint's one usb_request, and
epfile->mutex with it, until the host has taken every byte, so a frame sent as
32 KB writes leaves the bus idle between them: 1.4 ms a frame at 13 writes,
2.8 ms at 25, against one 512 KB write. The AIO path in
ffs_epfile_io gives each iocb its own request, copies the iocb's bytes into it
and queues it before io_submit moves on, then lets go of the mutex. dwc3 puts
every queued request on its TRB ring, so the bus streams them back to back,
and the caller's buffers are free again the moment io_submit returns.

Only what FfsTransport needs: one context, PWRITEV iocbs, and reaping. Linux
only: the comma is aarch64, and CI's x86_64 runs the real thing too.
"""
from __future__ import annotations

import ctypes
import functools
import os
import platform
import time

import numpy as np

# io_setup, io_destroy, io_submit, io_getevents
_SYSCALLS = {'aarch64': (0, 1, 2, 4), 'x86_64': (206, 207, 209, 208)}
IOCB_CMD_PWRITEV = 8
# iovecs one iocb may gather. A request is cut from the message's parts and
# padding; the most it spans is the header, the inference header, the frame,
# the packed inputs and the padding.
IOVECS = 8


class _Iocb(ctypes.Structure):
  # struct iocb, little-endian (aio_key before aio_rw_flags)
  _fields_ = [('data', ctypes.c_uint64), ('key', ctypes.c_uint32), ('rw_flags', ctypes.c_uint32),
              ('opcode', ctypes.c_uint16), ('reqprio', ctypes.c_int16), ('fildes', ctypes.c_uint32),
              ('buf', ctypes.c_uint64), ('nbytes', ctypes.c_uint64), ('offset', ctypes.c_int64),
              ('reserved2', ctypes.c_uint64), ('flags', ctypes.c_uint32), ('resfd', ctypes.c_uint32)]


class _Event(ctypes.Structure):
  _fields_ = [('data', ctypes.c_uint64), ('obj', ctypes.c_uint64), ('res', ctypes.c_int64), ('res2', ctypes.c_int64)]


class _Iovec(ctypes.Structure):
  _fields_ = [('base', ctypes.c_void_p), ('len', ctypes.c_size_t)]


class _Timespec(ctypes.Structure):
  _fields_ = [('sec', ctypes.c_long), ('nsec', ctypes.c_long)]


class _PyBuffer(ctypes.Structure):
  # CPython's Py_buffer, stable since 3.3
  _fields_ = [('buf', ctypes.c_void_p), ('obj', ctypes.c_void_p), ('len', ctypes.c_ssize_t),
              ('itemsize', ctypes.c_ssize_t), ('readonly', ctypes.c_int), ('ndim', ctypes.c_int),
              ('format', ctypes.c_char_p), ('shape', ctypes.c_void_p), ('strides', ctypes.c_void_p),
              ('suboffsets', ctypes.c_void_p), ('internal', ctypes.c_void_p)]


_get_buffer = ctypes.pythonapi.PyObject_GetBuffer
_get_buffer.argtypes = [ctypes.py_object, ctypes.POINTER(_PyBuffer), ctypes.c_int]
_get_buffer.restype = ctypes.c_int
_release_buffer = ctypes.pythonapi.PyBuffer_Release
_release_buffer.argtypes = [ctypes.POINTER(_PyBuffer)]
_release_buffer.restype = None


def address(buf) -> tuple[int, int]:
  """Where a contiguous buffer's bytes start, and how many there are;
  read-only ones (bytes) included, which ctypes.c_char.from_buffer refuses.
  Valid while the caller holds `buf` and nothing resizes it."""
  view = _PyBuffer()
  _get_buffer(buf, ctypes.byref(view), 0)   # PyBUF_SIMPLE: contiguous bytes; raises otherwise
  try:
    return view.buf or 0, view.len
  finally:
    _release_buffer(ctypes.byref(view))


class Layout:
  """A message whose spans are `lengths` bytes long, cut into requests of
  `size` bytes: for each piece, the request it is in, its iovec within that
  request's IOVECS, the span it gathers from and where in it, and its length.
  Python loops over the pieces only here; a message of the same shape (every
  frame of a link) reuses it through layout()."""

  def __init__(self, lengths: tuple[int, ...], size: int):
    request, slot, span, offset, length, pieces = [], [], [], [], [], []
    r = filled = 0
    for j, n in enumerate(lengths):
      at = 0
      while n:
        take = min(n, size - filled)
        if len(pieces) == r:
          pieces.append(0)
        if pieces[r] == IOVECS:
          raise ValueError(f'a request gathers more than {IOVECS} buffers')
        request.append(r)
        slot.append(pieces[r])
        span.append(j)
        offset.append(at)
        length.append(take)
        pieces[r] += 1
        at, n, filled = at + take, n - take, filled + take
        if filled == size:
          r, filled = r + 1, 0
    self.count = len(pieces)
    # where each request's pieces start, and the iovec words they fill
    self.first = [0]
    for c in pieces:
      self.first.append(self.first[-1] + c)
    self.words = 2 * (IOVECS * np.array(request, dtype=np.int64) + np.array(slot, dtype=np.int64))
    self.span = np.array(span, dtype=np.int64)
    self.offset = np.array(offset, dtype=np.uint64)
    self.length = np.array(length, dtype=np.uint64)
    self.pieces = np.array(pieces, dtype=np.uint64)


@functools.lru_cache(maxsize=8)
def layout(lengths: tuple[int, ...], size: int) -> Layout:
  return Layout(lengths, size)


class Aio:
  """A kernel AIO context of `depth` iocbs writing to `fd`, used from one
  thread at a time.

  submit() queues requests of a Layout, gathered from the spans' addresses
  (`bases`), and returns how many the kernel queued; the kernel has copied
  those bytes, so the caller may reuse its buffers at once. reap() returns
  each finished request's result, bytes written or a negative errno, in no
  promised order. The iocb and iovec arrays are reused across submits: the
  kernel copies both before io_submit returns.
  """

  def __init__(self, fd: int, depth: int):
    self._setup, self._destroy, self._submit, self._getevents = _SYSCALLS[platform.machine()]
    self._libc = ctypes.CDLL(None, use_errno=True)
    self._syscall = self._libc.syscall
    self._syscall.restype = ctypes.c_long
    self.depth = depth
    self._ctx = ctypes.c_ulong(0)
    self._call(self._setup, ctypes.c_long(depth), ctypes.byref(self._ctx))
    self._iocbs = (_Iocb * depth)()
    self._ptrs = (ctypes.POINTER(_Iocb) * depth)(*(ctypes.pointer(c) for c in self._iocbs))
    self._iovecs = (_Iovec * (depth * IOVECS))()
    iovecs, size = ctypes.addressof(self._iovecs), ctypes.sizeof(_Iovec)
    for i, cb in enumerate(self._iocbs):
      # everything but the token, the iovec count and the iovecs is fixed
      cb.opcode, cb.fildes, cb.buf = IOCB_CMD_PWRITEV, fd, iovecs + i * IOVECS * size
    # The per-frame fields as 64-bit words, written with numpy: iocb word 4 is
    # the iovec count, an iovec is (address, length), and an event is (data,
    # iocb, result, result2).
    self._iocb_words = np.frombuffer(self._iocbs, dtype=np.uint64)
    self._counts = np.arange(depth) * 8 + 4
    self._iovec_words = np.frombuffer(self._iovecs, dtype=np.uint64)
    self._events = (_Event * depth)()
    self._event_words = memoryview(self._events).cast('B').cast('q')
    self._timeout = _Timespec()

  def _call(self, nr: int, *args) -> int:
    ret = self._syscall(ctypes.c_long(nr), *args)
    if ret < 0:
      err = ctypes.get_errno()
      raise OSError(err, os.strerror(err))
    return ret

  address = staticmethod(address)
  layout = staticmethod(layout)

  def submit(self, plan: Layout, bases: list[int], start: int, count: int) -> int:
    """Queue `count` of the plan's requests from `start`, in order, gathered
    from the spans at `bases`. Raises OSError only when the kernel took none
    of them; a short count means the next one failed, and nothing of it, or of
    any after it, was queued."""
    if count > self.depth:
      raise ValueError(f'{count} requests for a context of {self.depth}')
    bases = np.array(bases, dtype=np.uint64)
    lo, hi = plan.first[start], plan.first[start + count]
    words = plan.words[lo:hi] - 2 * IOVECS * start
    self._iovec_words[words] = bases[plan.span[lo:hi]] + plan.offset[lo:hi]
    self._iovec_words[words + 1] = plan.length[lo:hi]
    self._iocb_words[self._counts[:count]] = plan.pieces[start:start + count]   # nbytes counts iovecs for PWRITEV
    return self._call(self._submit, self._ctx, ctypes.c_long(count), self._ptrs)

  def reap(self, min_nr: int, timeout: float) -> list[int]:
    """Finished requests' results, waiting up to `timeout` s (0: not at all)
    for at least `min_nr`; `min_nr` must not exceed what is queued, or this
    waits out the whole timeout. The GIL is released while it waits (ctypes).

    A signal ends io_getevents with EINTR, and nothing retries a ctypes call
    (PEP 475 is os.* only), so this does: modeld's frame thread takes a
    SIGUSR2 from msgq ~160 times a second."""
    end = time.monotonic() + timeout
    while True:
      left = max(0.0, end - time.monotonic())
      self._timeout.sec = int(left)
      self._timeout.nsec = int((left - int(left)) * 1e9)
      try:
        n = self._call(self._getevents, self._ctx, ctypes.c_long(min_nr), ctypes.c_long(self.depth),
                       self._events, ctypes.byref(self._timeout))
      except InterruptedError:
        if time.monotonic() >= end:
          return []
        continue
      return self._event_words[2:4 * n:4].tolist()

  def close(self) -> None:
    """Destroy the context. The kernel cancels what is still queued and waits,
    uninterruptibly, for it to finish: only call this with nothing in flight,
    or after the endpoint has been disabled, which completes everything."""
    if self._ctx.value:
      ctx, self._ctx = self._ctx, ctypes.c_ulong(0)
      self._call(self._destroy, ctx)
