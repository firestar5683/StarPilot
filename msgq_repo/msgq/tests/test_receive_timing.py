import uuid
import msgq
import pytest


def sockets(*, timeout=5, conflate=False):
    endpoint = "receive_timing_" + uuid.uuid4().hex
    pub = msgq.pub_sock(endpoint)
    sub = msgq.sub_sock(endpoint, timeout=timeout, conflate=conflate)
    return pub, sub


def check(report):
    assert report["schema_version"] == 1 and report["clock"] == "MONOTONIC"
    assert report["blocking_calls"] + report["nonblocking_calls"] == report["messages"] + report["nulls"]
    assert report["invalid_clock_samples"] == 0
    assert all(v >= 0 for v in report["totals_ns"].values())
    for key in ["slowest_blocking_ns", "slowest_nonblocking_ns"]:
        points = report[key]
        assert len(points) == 8
        nonzero = [p for p in points if p]
        assert nonzero == sorted(nonzero)


def test_disabled_then_enabled_data_and_reset():
    pub, sub = sockets()
    pub.send(b"old")
    assert sub.receive() == b"old"
    report = sub.take_receive_timing()
    assert not report["enabled"] and report["messages"] == 0
    sub.set_receive_timing(True)
    pub.send(b"new")
    assert sub.receive() == b"new"
    report = sub.take_receive_timing()
    check(report)
    assert report["enabled"] and report["blocking_calls"] == 1 and report["messages"] == 1
    assert report["slowest_blocking_ns"][4] > 0
    empty = sub.take_receive_timing()
    check(empty)
    assert empty["messages"] == 0 and empty["slowest_blocking_ns"] == (0,) * 8
    assert report["messages"] == 1  # detached after reset
    sub.set_receive_timing(False)
    pub.send(b"off")
    assert sub.receive() == b"off"
    assert sub.take_receive_timing()["messages"] == 0


@pytest.mark.parametrize("timeout", [0, 5])
def test_empty_timeout_and_nonblocking(timeout):
    pub, sub = sockets(timeout=timeout)
    sub.set_receive_timing(True)
    assert sub.receive() is None
    assert sub.receive(non_blocking=True) is None
    report = sub.take_receive_timing()
    check(report)
    assert report["blocking_calls"] == report["nonblocking_calls"] == 1
    assert report["nulls"] == 2 and report["messages"] == 0
    assert report["slowest_blocking_ns"][4:] == (0,) * 4
    assert report["slowest_nonblocking_ns"][4:] == (0,) * 4
    assert report["totals_ns"]["copy"] == report["totals_ns"]["delete_native"] == 0


@pytest.mark.parametrize("conflate", [False, True])
def test_burst_no_diagnostic_cap_or_drop(conflate):
    pub, sub = sockets(conflate=conflate)
    sub.set_receive_timing(True)
    expected = [str(i).encode() for i in range(80)]
    for message in expected:
        pub.send(message)
    actual = msgq.drain_sock_raw(sub, wait_for_one=True)
    assert actual == ([expected[-1]] if conflate else expected)
    report = sub.take_receive_timing()
    check(report)
    assert report["messages"] == len(actual)
    assert report["blocking_calls"] == 1
    assert report["nonblocking_calls"] == len(actual)  # includes terminal null
    assert report["nulls"] == 1
    assert report["slowest_nonblocking_ns"][0] > 0
    assert len(report["slowest_nonblocking_ns"]) == 8
