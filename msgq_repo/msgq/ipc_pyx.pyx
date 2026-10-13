# distutils: language = c++
# cython: c_string_encoding=ascii, language_level=3

import time
from libcpp.string cimport string
from libcpp.vector cimport vector
from libcpp cimport bool
from libc cimport errno
from libc.string cimport strerror
from libc.stdint cimport uint64_t
from cython.operator import dereference


from .ipc cimport Context as cppContext
from .ipc cimport SubSocket as cppSubSocket
from .ipc cimport PubSocket as cppPubSocket
from .ipc cimport Poller as cppPoller
from .ipc cimport Message as cppMessage
from .ipc cimport Event as cppEvent, SocketEventHandle as cppSocketEventHandle


cdef extern from *:
  """
  #include <stdint.h>
  #include <time.h>
  static inline uint64_t msgq_receive_clock_ns() noexcept {
    struct timespec ts{};
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) return 0;
    return uint64_t(ts.tv_sec) * 1000000000ULL + uint64_t(ts.tv_nsec);
  }
  """
  uint64_t msgq_receive_clock_ns() noexcept nogil


class IpcError(Exception):
  def __init__(self, endpoint=None):
    suffix = f"with {endpoint.decode('utf-8')}" if endpoint else ""
    message = f"Messaging failure {suffix}: {strerror(errno.errno).decode('utf-8')}"
    super().__init__(message)


class MultiplePublishersError(IpcError):
  pass


def toggle_fake_events(bool enabled):
  cppSocketEventHandle.toggle_fake_events(enabled)


def set_fake_prefix(string prefix):
  cppSocketEventHandle.set_fake_prefix(prefix)


def get_fake_prefix():
  return cppSocketEventHandle.fake_prefix()


def delete_fake_prefix():
  cppSocketEventHandle.set_fake_prefix(b"")


def wait_for_one_event(list events, int timeout=-1):
  cdef vector[cppEvent] items
  for event in events:
    items.push_back(dereference(<cppEvent*><size_t>event.ptr))
  return cppEvent.wait_for_one(items, timeout)


cdef class Event:
  cdef cppEvent event;

  cdef setEvent(self, cppEvent event):
    self.event = event

  def set(self):
    self.event.set()

  def clear(self):
    return self.event.clear()

  def wait(self, int timeout=-1):
    self.event.wait(timeout)

  def peek(self):
    return self.event.peek()

  @property
  def fd(self):
    return self.event.fd()

  @property
  def ptr(self):
    return <size_t><void*>&self.event


cdef class SocketEventHandle:
  cdef cppSocketEventHandle * handle;

  def __cinit__(self, string endpoint, string identifier, bool override):
    self.handle = new cppSocketEventHandle(endpoint, identifier, override)

  def __dealloc__(self):
    del self.handle

  @property
  def enabled(self):
    return self.handle.is_enabled()

  @enabled.setter
  def enabled(self, bool value):
    self.handle.set_enabled(value)

  @property
  def recv_called_event(self):
    e = Event()
    e.setEvent(self.handle.recv_called())

    return e

  @property
  def recv_ready_event(self):
    e = Event()
    e.setEvent(self.handle.recv_ready())

    return e


cdef class Context:
  cdef cppContext * context

  def __cinit__(self):
    self.context = cppContext.create()

  def term(self):
    del self.context
    self.context = NULL

  def __dealloc__(self):
    pass
    # Deleting the context will hang if sockets are still active
    # TODO: Figure out a way to make sure the context is closed last
    # del self.context


cdef class Poller:
  cdef cppPoller * poller
  cdef list sub_sockets

  def __cinit__(self):
    self.sub_sockets = []
    self.poller = cppPoller.create()

  def __dealloc__(self):
    del self.poller

  def registerSocket(self, SubSocket socket):
    self.sub_sockets.append(socket)
    self.poller.registerSocket(socket.socket)

  def poll(self, timeout):
    sockets = []
    cdef int t = timeout

    with nogil:
      result = self.poller.poll(t)

    for s in result:
      socket = SubSocket()
      socket.setPtr(s)
      sockets.append(socket)

    return sockets


cdef class SubSocket:
  cdef cppSubSocket * socket
  cdef bool is_owner
  cdef bool receive_timing_enabled
  cdef uint64_t rt_calls[2]
  cdef uint64_t rt_messages
  cdef uint64_t rt_nulls
  cdef uint64_t rt_invalid
  cdef uint64_t rt_totals[7]
  cdef uint64_t rt_slowest[2][8]
  cdef uint64_t rt_max[2]

  def __cinit__(self):
    with nogil:
      self.socket = cppSubSocket.create()

    self.is_owner = True
    if self.socket == NULL:
      raise IpcError

  def __dealloc__(self):
    if self.is_owner:
      with nogil:
        del self.socket

  cdef setPtr(self, cppSubSocket * ptr):
    if self.is_owner:
      with nogil:
        del self.socket

    self.is_owner = False
    self.socket = ptr

  def connect(self, Context context, string endpoint, string address=b"127.0.0.1", bool conflate=False, size_t segment_size=0):
    cdef int r
    with nogil:
      r = self.socket.connect(context.context, endpoint, address, conflate, True, segment_size)

    if r != 0:
      if errno.errno == errno.EADDRINUSE:
        raise MultiplePublishersError(endpoint)
      else:
        raise IpcError(endpoint)

  def setTimeout(self, int timeout):
    with nogil:
      self.socket.setTimeout(timeout)

  cdef void _reset_receive_timing(self):
    cdef int i, j
    self.rt_messages = self.rt_nulls = self.rt_invalid = 0
    for i in range(7):
      self.rt_totals[i] = 0
    for i in range(2):
      self.rt_calls[i] = self.rt_max[i] = 0
      for j in range(8):
        self.rt_slowest[i][j] = 0

  def set_receive_timing(self, bool enabled):
    self.receive_timing_enabled = enabled
    self._reset_receive_timing()

  def take_receive_timing(self):
    cdef int i, j
    report = {
      'schema_version': 1, 'clock': 'MONOTONIC',
      'enabled': self.receive_timing_enabled,
      'blocking_calls': self.rt_calls[0], 'nonblocking_calls': self.rt_calls[1],
      'messages': self.rt_messages, 'nulls': self.rt_nulls,
      'invalid_clock_samples': self.rt_invalid,
      'totals_ns': dict(zip(('release', 'native', 'reacquire', 'copy', 'delete_release', 'delete_native', 'delete_reacquire'),
                           [self.rt_totals[i] for i in range(7)])),
      'boundary_names': ('before_release', 'native_entry', 'native_return', 'after_reacquire',
                         'before_delete_release', 'delete_entry', 'delete_return', 'after_delete_reacquire'),
      'slowest_blocking_ns': tuple(self.rt_slowest[0][j] for j in range(8)),
      'slowest_nonblocking_ns': tuple(self.rt_slowest[1][j] for j in range(8)),
    }
    self._reset_receive_timing()
    return report

  def receive(self, bool non_blocking=False):
    cdef cppMessage *msg
    cdef uint64_t points[8]
    cdef uint64_t elapsed
    cdef int i, kind = 1 if non_blocking else 0
    cdef bool valid = True
    cdef bool has_message
    # Disabled path retains the existing native call/copy/delete order.
    if not self.receive_timing_enabled:
      with nogil:
        msg = self.socket.receive(non_blocking)
      if msg == NULL:
        return None
      else:
        sz = msg.getSize()
        m = msg.getData()[:sz]
        with nogil:
          del msg
        return m

    points[0] = msgq_receive_clock_ns()
    with nogil:
      points[1] = msgq_receive_clock_ns()
      msg = self.socket.receive(non_blocking)
      points[2] = msgq_receive_clock_ns()
    points[3] = msgq_receive_clock_ns()
    has_message = msg != NULL
    if not has_message:
      self.rt_nulls += 1
      for i in range(4, 8):
        points[i] = 0
    else:
      self.rt_messages += 1
      sz = msg.getSize()
      m = msg.getData()[:sz]
      points[4] = msgq_receive_clock_ns()
      with nogil:
        points[5] = msgq_receive_clock_ns()
        del msg
        points[6] = msgq_receive_clock_ns()
      points[7] = msgq_receive_clock_ns()
    self.rt_calls[kind] += 1
    for i in range(8 if has_message else 4):
      if points[i] == 0 or (i > 0 and points[i] < points[i-1]):
        valid = False
    if not valid:
      self.rt_invalid += 1
    else:
      for i in range(7 if has_message else 3):
        self.rt_totals[i] += points[i+1] - points[i]
      elapsed = points[7 if has_message else 3] - points[0]
      if elapsed > self.rt_max[kind]:
        self.rt_max[kind] = elapsed
        for i in range(8):
          self.rt_slowest[kind][i] = points[i]
    if not has_message:
      return None
    return m


cdef class PubSocket:
  cdef cppPubSocket * socket

  def __cinit__(self):
    self.socket = cppPubSocket.create()
    if self.socket == NULL:
      raise IpcError

  def __dealloc__(self):
    del self.socket

  def connect(self, Context context, string endpoint, size_t segment_size=0):
    r = self.socket.connect(context.context, endpoint, True, segment_size)

    if r != 0:
      if errno.errno == errno.EADDRINUSE:
        raise MultiplePublishersError(endpoint)
      else:
        raise IpcError(endpoint)

  def send(self, bytes data):
    length = len(data)
    r = self.socket.send(<char*>data, length)

    if r != length:
      if errno.errno == errno.EADDRINUSE:
        raise MultiplePublishersError
      else:
        raise IpcError

  def all_readers_updated(self):
    return self.socket.all_readers_updated()

  def wait_for_readers(self, double timeout=1.0, double interval=0.001):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
      if self.all_readers_updated():
        return
      time.sleep(interval)
    raise TimeoutError("subscriber did not connect")
