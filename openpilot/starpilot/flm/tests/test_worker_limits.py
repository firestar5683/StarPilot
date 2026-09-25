from unittest.mock import patch

from openpilot.starpilot.flm import operation_worker as worker


def test_unlimited_linux_limits_get_finite_ceiling():
  with patch.object(worker.sys, "platform", "linux"), patch.object(worker.os, "nice"), \
       patch.object(worker.resource, "getrlimit", return_value=(-1, -1)), \
       patch.object(worker.resource, "setrlimit") as set_limit:
    worker._limits()
  assert set_limit.call_args_list[0].args == (worker.resource.RLIMIT_AS, (worker.LINUX_ADDRESS_SPACE_BYTES, -1))
  assert set_limit.call_args_list[1].args == (worker.resource.RLIMIT_CPU, (worker.LINUX_CPU_SECONDS, -1))


def test_existing_tighter_linux_limits_are_preserved():
  with patch.object(worker.sys, "platform", "linux"), patch.object(worker.os, "nice"), \
       patch.object(worker.resource, "getrlimit", side_effect=[(1000000, 2000000), (-1, 60)]), \
       patch.object(worker.resource, "setrlimit") as set_limit:
    worker._limits()
  assert set_limit.call_args_list[0].args == (worker.resource.RLIMIT_AS, (1000000, 2000000))
  assert set_limit.call_args_list[1].args == (worker.resource.RLIMIT_CPU, (60, 60))
