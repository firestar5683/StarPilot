import ctypes
import threading
import time
import uuid

import msgq
import pytest


def sockets(timeout=10):
  endpoint = f"receive_timing_{uuid.uuid4().hex}"
  pub = msgq.pub_sock(endpoint)
  sub = msgq.sub_sock(endpoint, timeout=timeout)
  return pub, sub


def assert_clocks(record):
  assert len(record) == 12
  assert all(t >= 0 for t in record[4:])
  assert list(record[4::2]) == sorted(record[4::2])
  assert list(record[5::2]) == sorted(record[5::2])


def test_receive_timing_opt_in_and_preserves_messages():
  pub, sub = sockets()
  for payload in (b"x", b"unchanged\x00message"):
    pub.send(payload)
    assert sub.receive() == payload
  assert sub.receive(non_blocking=True) is None
  assert sub.take_receive_timing() == ((), 0)

  sub.enable_receive_timing(True)
  for payload in (b"x", b"unchanged\x00message"):
    pub.send(payload)
    assert sub.receive() == payload
  assert sub.receive(non_blocking=True) is None
  assert sub.receive() is None
  records, omitted = sub.take_receive_timing()
  assert omitted == 0
  assert [r[:4] for r in records] == [(1, False, True, 1), (2, False, True, 17),
                                     (3, True, False, 0), (4, False, False, 0)]
  for record in records:
    assert_clocks(record)
  assert sub.take_receive_timing() == (records, omitted)

  sub.enable_receive_timing(False)
  pub.send(b"disabled again")
  assert sub.receive() == b"disabled again"
  assert sub.receive(non_blocking=True) is None
  assert sub.take_receive_timing() == (records, omitted)
  sub.reset_receive_timing()
  assert sub.take_receive_timing() == ((), 0)


def test_receive_timing_bounded_ring_and_explicit_reset():
  _, sub = sockets()
  sub.enable_receive_timing(True)
  for _ in range(150):
    assert sub.receive(non_blocking=True) is None
  records, omitted = sub.take_receive_timing()
  assert len(records) == 64
  assert omitted == 86
  assert [r[0] for r in records] == list(range(87, 151))
  sub.reset_receive_timing()
  assert sub.take_receive_timing() == ((), 0)
  assert sub.receive(non_blocking=True) is None
  assert sub.take_receive_timing()[0][0][0] == 1


def test_receive_timing_thread_owner_and_socket_isolation():
  _, sub = sockets()
  _, other_sub = sockets()
  sub.enable_receive_timing(True)
  failures = []

  def other_thread():
    try:
      # The receive itself remains valid and uninstrumented on other threads.
      assert sub.receive(non_blocking=True) is None
      for op in (sub.take_receive_timing, sub.reset_receive_timing,
                 lambda: sub.enable_receive_timing(False), lambda: sub.enable_receive_timing(True)):
        with pytest.raises(RuntimeError, match="thread that enabled"):
          op()
    except BaseException as exc:
      failures.append(exc)

  worker = threading.Thread(target=other_thread)
  worker.start()
  worker.join(timeout=3)
  assert not worker.is_alive()
  assert not failures
  assert sub.take_receive_timing() == ((), 0)
  assert sub.receive(non_blocking=True) is None
  assert len(sub.take_receive_timing()[0]) == 1
  assert other_sub.receive(non_blocking=True) is None
  assert other_sub.take_receive_timing() == ((), 0)


def test_receive_timing_exposes_gil_handoff_delay():
  # PyDLL deliberately retains the main thread's GIL while libc sleeps.
  # The receiving thread's native timeout can expire independently of it.
  libc = ctypes.PyDLL(None)
  libc.usleep.argtypes = [ctypes.c_uint]
  libc.usleep.restype = ctypes.c_int
  ready = threading.Event()
  results = []
  failures = []

  def receiver():
    try:
      _, sub = sockets(timeout=40)
      sub.enable_receive_timing(True)
      ready.set()
      assert sub.receive() is None
      results.append(sub.take_receive_timing()[0][0])
    except BaseException as exc:
      failures.append(exc)

  worker = threading.Thread(target=receiver)
  worker.start()
  assert ready.wait(timeout=3)
  time.sleep(0.01)
  assert libc.usleep(150_000) == 0
  worker.join(timeout=3)
  assert not worker.is_alive()
  assert not failures
  record = results[0]
  assert_clocks(record)
  assert record[6] - record[4] >= 30_000_000
  assert record[8] - record[6] >= 50_000_000
  assert record[9] - record[7] < 20_000_000
