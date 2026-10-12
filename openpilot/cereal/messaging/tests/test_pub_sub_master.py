import random
import time
from typing import cast
from collections.abc import Sized
from unittest.mock import Mock, patch

from openpilot.common.test import OpenpilotTestCase
import openpilot.cereal.messaging as messaging
from openpilot.cereal.messaging.tests.test_messaging import events, random_sock, random_socks, \
                                                  random_bytes, random_carstate, assert_carstate
from openpilot.cereal.services import SERVICE_LIST


class TestSubMaster(OpenpilotTestCase):

  def test_init(self):
    sm = messaging.SubMaster(events)
    for p in [sm.updated, sm.recv_time, sm.recv_frame, sm.alive,
              sm.sock, sm.data, sm.logMonoTime, sm.valid]:
      assert len(cast(Sized, p)) == len(events)

  def test_init_state(self):
    socks = random_socks()
    sm = messaging.SubMaster(socks)
    assert sm.frame == -1
    assert not any(sm.updated.values())
    assert not any(sm.seen.values())
    on_demand = {s: SERVICE_LIST[s].frequency <= 1e-5 for s in sm.services}
    assert all(sm.alive[s] == sm.valid[s] == sm.freq_ok[s] == on_demand[s] for s in sm.services)
    assert all(t == 0. for t in sm.recv_time.values())
    assert all(f == 0 for f in sm.recv_frame.values())
    assert all(t == 0 for t in sm.logMonoTime.values())

    for p in [sm.updated, sm.recv_time, sm.recv_frame, sm.alive,
              sm.sock, sm.data, sm.logMonoTime, sm.valid]:
      assert len(cast(Sized, p)) == len(socks)

  def test_getitem(self):
    sock = "carState"
    pub_sock = messaging.pub_sock(sock)
    sm = messaging.SubMaster([sock,])

    msg = random_carstate()
    pub_sock.send(msg.to_bytes())
    sm.update(1000)
    assert_carstate(msg.carState, sm[sock])

  # TODO: break this test up to individually test SubMaster.update and SubMaster.update_msgs
  def test_update(self):
    sock = "carState"
    pub_sock = messaging.pub_sock(sock)
    sm = messaging.SubMaster([sock,])

    for i in range(10):
      msg = messaging.new_message(sock)
      pub_sock.send(msg.to_bytes())
      sm.update(1000)
      assert sm.frame == i
      assert all(sm.updated.values())

  def test_update_timeout(self):
    sock = random_sock()
    sm = messaging.SubMaster([sock,])
    timeout = random.randrange(10, 30)
    start_time = time.monotonic()
    sm.update(timeout)
    t = time.monotonic() - start_time
    assert t >= timeout/1000.
    assert t < 0.1
    assert not any(sm.updated.values())

  def test_nonblocking_update(self):
    services = ["modelV2", "carState", "carParams"]
    for poll in (None, "modelV2"):
      with self.subTest(poll=poll):
        pm = messaging.PubMaster(services)
        sm = messaging.SubMaster(services, poll=poll)
        sm.poller = Mock()
        sm.poller.poll.side_effect = AssertionError("nonblocking updates must not poll")

        sm.update(0)
        assert sm.frame == 0
        assert not any(sm.updated.values())
        assert not any(sm.seen.values())
        assert not sm.alive["carState"] and not sm.alive["modelV2"]
        assert not any(sm.valid.values())

        for i, service in enumerate(services):
          msg = messaging.new_message(service)
          msg.logMonoTime = 100 + i
          msg.valid = service != "carState"
          pm.send(service, msg)

        with patch.object(messaging, "recv_one_or_none", wraps=messaging.recv_one_or_none) as recv:
          sm.update(0)
          order = [s for s in services if s not in sm.non_polled_services] + list(sm.non_polled_services)
          assert [call.args[0] for call in recv.call_args_list] == [sm.sock[s] for s in order]

        assert all(sm.updated.values()) and all(sm.seen.values())
        assert sm.logMonoTime == dict(zip(services, (100, 101, 102), strict=True))
        assert sm.valid == {"modelV2": True, "carState": False, "carParams": True}
        assert not sm.all_valid() and sm.all_valid(["modelV2", "carParams"])
        assert len(set(sm.recv_time.values())) == 1
        assert all(f == sm.frame for f in sm.recv_frame.values())

        received = (sm.recv_time.copy(), sm.recv_frame.copy(), sm.logMonoTime.copy())
        sm.update(0)
        assert not any(sm.updated.values())
        assert received == (sm.recv_time, sm.recv_frame, sm.logMonoTime)

        for speed in range(3):
          msg = messaging.new_message("carState")
          msg.carState.vEgo = speed
          pm.send("carState", msg)
        sm.update(0)
        assert sm["carState"].vEgo == 2
        assert sm.updated == {"modelV2": False, "carState": True, "carParams": False}
        sm.poller.poll.assert_not_called()
        del sm, pm

  def test_positive_timeout_uses_poller(self):
    sm = messaging.SubMaster(["carState"])
    sm.poller = Mock()
    sm.poller.poll.return_value = []
    sm.update(1)
    sm.poller.poll.assert_called_once_with(1)

  def test_avg_frequency_checks(self):
    for poll in (True, False):
      sm = messaging.SubMaster(["modelV2", "carParams", "carState", "cameraOdometry", "extrinsicsCalibration"],
                               poll=("modelV2" if poll else None),
                               frequency=(20. if not poll else None))

      checks = {
        "carState": (20, 20),
        "modelV2": (20, 20 if poll else 10),
        "cameraOdometry": (20, 10),
        "extrinsicsCalibration": (4, 4),
        "carParams": (None, None),
        "userBookmark": (None, None),
      }

      for service, (max_freq, min_freq) in checks.items():
        if max_freq is not None:
          assert min_freq is not None
          assert sm._check_avg_freq(service)
          assert sm.freq_tracker[service].max_freq == max_freq*1.2
          assert sm.freq_tracker[service].min_freq == min_freq*0.8
        else:
          assert not sm._check_avg_freq(service)

  # SubMaster should always conflate
  def test_conflate(self):
    sock = "carState"
    pub_sock = messaging.pub_sock(sock)
    sm = messaging.SubMaster([sock,])

    pub_sock.send(messaging.new_message(sock).to_bytes())
    sm.update(1000)  # synchronize the PUB/SUB connection

    n = 10
    for i in range(n+1):
      msg = messaging.new_message(sock)
      msg.carState.vEgo = i
      pub_sock.send(msg.to_bytes())
    sm.update(1000)
    assert sm[sock].vEgo == n


class TestPubMaster(OpenpilotTestCase):

  def test_init(self):
    messaging.PubMaster(events)

  def test_send(self):
    socks = random_socks()
    pm = messaging.PubMaster(socks)
    sub_socks = {s: messaging.sub_sock(s, conflate=True, timeout=1000) for s in socks}

    # PubMaster accepts either a capnp msg builder or bytes
    for capnp in [True, False]:
      for i in range(100):
        sock = socks[i % len(socks)]

        if capnp:
          try:
            msg = messaging.new_message(sock)
          except Exception:
            msg = messaging.new_message(sock, random.randrange(50))
        else:
          msg = random_bytes()

        pm.send(sock, msg)
        recvd = sub_socks[sock].receive()

        if capnp:
          msg.clear_write_flag()
          msg = msg.to_bytes()
        assert msg == recvd, i
