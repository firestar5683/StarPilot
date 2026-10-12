# distutils: language = c++
# cython: c_string_encoding=ascii, language_level=3

import time
from libcpp.string cimport string
from libcpp.vector cimport vector
from libcpp cimport bool
from libc cimport errno
from libc.string cimport strerror
from libc.stdint cimport int64_t, uint64_t
from cython.operator import dereference


cdef extern from "Python.h":
  unsigned long PyThread_get_thread_ident() noexcept


cdef extern from *:
  """
  #include <errno.h>
  #include <stdint.h>
  #include <time.h>

  // Diagnostics must neither raise nor disturb the backend's errno.
  static inline void msgq_receive_clock_pair(int64_t *wall, int64_t *cpu) {
    const int saved_errno = errno;
    struct timespec ts;
    *wall = clock_gettime(CLOCK_MONOTONIC, &ts) == 0
      ? (int64_t)ts.tv_sec * 1000000000LL + ts.tv_nsec : -1;
    *cpu = clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts) == 0
      ? (int64_t)ts.tv_sec * 1000000000LL + ts.tv_nsec : -1;
    errno = saved_errno;
  }
  """
  void msgq_receive_clock_pair(int64_t *wall, int64_t *cpu) noexcept nogil


cdef struct ReceiveTiming:
  uint64_t sequence
  bool non_blocking
  bool returned_message
  size_t byte_length
  int64_t before_wall
  int64_t before_cpu
  int64_t backend_return_wall
  int64_t backend_return_cpu
  int64_t gil_reacquired_wall
  int64_t gil_reacquired_cpu
  int64_t python_return_wall
  int64_t python_return_cpu


from .ipc cimport Context as cppContext
from .ipc cimport SubSocket as cppSubSocket
from .ipc cimport PubSocket as cppPubSocket
from .ipc cimport Poller as cppPoller
from .ipc cimport Message as cppMessage
from .ipc cimport Event as cppEvent, SocketEventHandle as cppSocketEventHandle


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
  cdef unsigned long receive_timing_owner
  cdef ReceiveTiming receive_timing_ring[64]
  cdef unsigned int receive_timing_next
  cdef unsigned int receive_timing_count
  cdef uint64_t receive_timing_sequence
  cdef uint64_t receive_timing_omitted
  cdef uint64_t receive_timing_generation

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

  cdef check_receive_timing_owner(self):
    if self.receive_timing_owner != 0 and self.receive_timing_owner != PyThread_get_thread_ident():
      raise RuntimeError("receive timing must be managed by the thread that enabled it")

  def enable_receive_timing(self, bool enabled):
    """Opt in on the receiving thread; disabling preserves previous records."""
    self.check_receive_timing_owner()
    if enabled:
      self.receive_timing_owner = PyThread_get_thread_ident()
    self.receive_timing_enabled = enabled

  def reset_receive_timing(self):
    """Explicitly clear records and counts, without changing enablement."""
    self.check_receive_timing_owner()
    self.receive_timing_next = 0
    self.receive_timing_count = 0
    self.receive_timing_sequence = 0
    self.receive_timing_omitted = 0
    self.receive_timing_generation += 1

  def take_receive_timing(self):
    """Return (oldest-to-newest records, overwritten count), without clearing.

    Each record is (sequence, non_blocking, returned_message, byte_length,
    before_mono_ns, before_thread_cpu_ns, backend_return_mono_ns,
    backend_return_thread_cpu_ns, gil_reacquired_mono_ns,
    gil_reacquired_thread_cpu_ns, python_return_mono_ns,
    python_return_thread_cpu_ns). Failed clocks are -1. The final interval
    includes the bytes copy and message cleanup; gil_handoff includes scheduling.
    """
    self.check_receive_timing_owner()
    cdef unsigned int i
    cdef unsigned int start = (self.receive_timing_next + 64 - self.receive_timing_count) % 64
    cdef ReceiveTiming *record
    records = []
    for i in range(self.receive_timing_count):
      record = &self.receive_timing_ring[(start + i) % 64]
      records.append((record.sequence, record.non_blocking, record.returned_message, record.byte_length,
                      record.before_wall, record.before_cpu, record.backend_return_wall, record.backend_return_cpu,
                      record.gil_reacquired_wall, record.gil_reacquired_cpu, record.python_return_wall, record.python_return_cpu))
    return tuple(records), self.receive_timing_omitted

  cdef receive_timed(self, bool non_blocking):
    cdef cppMessage *msg
    cdef ReceiveTiming record
    cdef uint64_t generation = self.receive_timing_generation
    record.non_blocking = non_blocking
    with nogil:
      msgq_receive_clock_pair(&record.before_wall, &record.before_cpu)
      msg = self.socket.receive(non_blocking)
      msgq_receive_clock_pair(&record.backend_return_wall, &record.backend_return_cpu)
    msgq_receive_clock_pair(&record.gil_reacquired_wall, &record.gil_reacquired_cpu)

    record.returned_message = msg != NULL
    record.byte_length = 0
    if msg == NULL:
      m = None
    else:
      record.byte_length = msg.getSize()
      m = msg.getData()[:record.byte_length]
      with nogil:
        del msg

    msgq_receive_clock_pair(&record.python_return_wall, &record.python_return_cpu)
    # All shared ring access holds the GIL. Only this stack-local record is
    # written while nogil; no Python object is created for the receipt here.
    if generation == self.receive_timing_generation:
      self.receive_timing_sequence += 1
      record.sequence = self.receive_timing_sequence
      self.receive_timing_ring[self.receive_timing_next] = record
      self.receive_timing_next = (self.receive_timing_next + 1) % 64
      if self.receive_timing_count < 64:
        self.receive_timing_count += 1
      else:
        self.receive_timing_omitted += 1
    return m

  def receive(self, bool non_blocking=False):
    cdef cppMessage *msg
    if self.receive_timing_enabled and self.receive_timing_owner == PyThread_get_thread_ident():
      return self.receive_timed(non_blocking)
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
