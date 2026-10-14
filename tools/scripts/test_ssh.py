import importlib.util
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch
import queue

import pytest


@pytest.fixture
def device_ssh():
  spec = importlib.util.spec_from_file_location("device_ssh", Path(__file__).with_name("ssh.py"))
  assert spec is not None and spec.loader is not None
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


def test_read_banner_accepts_ssh_and_rejects_other_services(device_ssh):
  device_ssh.read_banner(BytesIO(b"SSH-2.0-OpenSSH\r\n"))
  with pytest.raises(ConnectionError, match="no ssh banner"):
    device_ssh.read_banner(BytesIO(b"HTTP/1.1 200 OK\r\n"))


def test_athena_probe_kills_its_proxy_after_reading_banner(device_ssh):
  process = Mock(stdout=BytesIO(b"SSH-2.0-OpenSSH\r\n"))
  processes = []
  command = ["ssh", "-W", "comma-device:22", "proxy"]
  with patch.object(device_ssh.subprocess, "Popen", return_value=process) as spawn:
    device_ssh.probe_athena(command, processes)
  assert processes == [process]
  assert spawn.call_args.args == (command,)
  process.kill.assert_called_once_with()


@pytest.mark.parametrize("routes,results,expected", [
  ({"local": "local", "athena": "proxy"}, [("local", 1.0, None)], "local"),
  ({"local": "local", "athena": "proxy"}, [("athena", 2.0, None), ("local", None, "refused")], "athena"),
  ({"local": "local", "athena": "proxy"}, [("athena", 2.0, None), ("local", 1.0, None)], "local"),
  ({"local": "local", "athena": "proxy"}, [("local", None, "not found"), ("athena", 2.0, None)], "athena"),
  ({"local": "local", "athena": "proxy"}, [("local", None, "refused"), ("athena", None, "refused")], None),
  ({"athena": "proxy"}, [("athena", 2.0, None)], "athena"),
])
def test_probe_routes_selects_only_a_successful_available_route(device_ssh, routes, results, expected):
  completed = queue.Queue()
  for result in results:
    completed.put(result)
  with patch.object(device_ssh.queue, "Queue", return_value=completed), \
       patch.object(device_ssh.threading, "Thread") as threads, \
       patch.object(device_ssh.time, "monotonic", return_value=0.0):
    choice, status = device_ssh.probe_routes(routes, ["ssh", "proxy"])
  assert choice == expected
  assert status == {name: (ms, error) for name, ms, error in results}
  assert threads.call_count == len(routes)
  assert all(call.kwargs["daemon"] for call in threads.call_args_list)


def test_probe_routes_deadline_without_a_banner_returns_no_route(device_ssh):
  completed = Mock(get=Mock(side_effect=queue.Empty))
  with patch.object(device_ssh.queue, "Queue", return_value=completed), \
       patch.object(device_ssh.threading, "Thread"), \
       patch.object(device_ssh.time, "monotonic", return_value=0.0):
    choice, status = device_ssh.probe_routes({"local": "local", "athena": "proxy"}, ["ssh", "proxy"])
  assert choice is None
  assert status == {}
  completed.get.assert_called_once_with(timeout=device_ssh.ATHENA_TIMEOUT)


def test_probe_routes_deadline_retains_successful_proxy_while_local_is_pending(device_ssh):
  completed = Mock(get=Mock(side_effect=[("athena", 2.0, None), queue.Empty]))
  with patch.object(device_ssh.queue, "Queue", return_value=completed), \
       patch.object(device_ssh.threading, "Thread"), \
       patch.object(device_ssh.time, "monotonic", return_value=0.0):
    choice, status = device_ssh.probe_routes({"local": "local", "athena": "proxy"}, ["ssh", "proxy"])
  assert choice == "athena"
  assert status == {"athena": (2.0, None)}
  assert completed.get.call_count == 2
  assert all(call.kwargs["timeout"] == device_ssh.ATHENA_TIMEOUT for call in completed.get.call_args_list)
