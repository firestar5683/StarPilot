import contextlib
import gc
import os
import platform
import sys
from pathlib import Path

import pytest


try:
  int(os.environ.get("DEBUG", "0"))
except ValueError:
  os.environ["DEBUG"] = "0"

if platform.system() == "Darwin":
  os.environ["SP_HEADLESS_TEST"] = "1"


def _prepend_host_pytest_runtime() -> None:
  if platform.system() != "Darwin" or os.getenv("SP_DISABLE_HOST_PYTEST_REDIRECT") == "1":
    return

  root_dir = Path(__file__).resolve().parent
  work_dir = root_dir / ".host_runtime" / "darwin" / "worktree"
  required_extension = work_dir / "msgq_repo" / "msgq" / "ipc_pyx.so"
  if not required_extension.exists():
    return

  extra_paths = [work_dir, work_dir / "starpilot" / "third_party"]
  extra_paths.extend(sorted(work_dir.glob("*_repo")))
  acados_dir = work_dir / "third_party" / "acados"
  if acados_dir.is_dir():
    extra_paths.append(acados_dir)

  existing = set(sys.path)
  insert_at = 0
  for path in [str(p) for p in extra_paths if p.exists()]:
    if path in existing:
      continue
    sys.path.insert(insert_at, path)
    insert_at += 1


_prepend_host_pytest_runtime()

from openpilot.common.prefix import OpenpilotPrefix
from openpilot.system.manager import manager
from openpilot.system.hardware import TICI, HARDWARE

# TODO: pytest-cpp doesn't support FAIL, and we need to create test translations in sessionstart
# pending https://github.com/pytest-dev/pytest-cpp/pull/147
collect_ignore = [
  "selfdrive/ui/tests/test_translations",
  "selfdrive/test/process_replay/test_processes.py",
  "selfdrive/test/process_replay/test_regen.py",
]
collect_ignore_glob = [
  "selfdrive/debug/*.py",
  "selfdrive/modeld/*.py",
]


def pytest_sessionstart(session):
  # TODO: fix tests and enable test order randomization
  if session.config.pluginmanager.hasplugin('randomly'):
    session.config.option.randomly_reorganize = False


@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_runtest_call(item):
  # ensure we run as a hook after capturemanager's
  if item.get_closest_marker("nocapture") is not None:
    capmanager = item.config.pluginmanager.getplugin("capturemanager")
    with capmanager.global_and_fixture_disabled():
      yield
  else:
    yield


@contextlib.contextmanager
def clean_env():
  starting_env = dict(os.environ)
  yield
  os.environ.clear()
  os.environ.update(starting_env)


@pytest.fixture(scope="function", autouse=True)
def openpilot_function_fixture(request):
  with clean_env():
    # setup a clean environment for each test
    with OpenpilotPrefix(shared_download_cache=request.node.get_closest_marker("shared_download_cache") is not None) as prefix:
      prefix = os.environ["OPENPILOT_PREFIX"]

      yield

      # ensure the test doesn't change the prefix
      assert "OPENPILOT_PREFIX" in os.environ and prefix == os.environ["OPENPILOT_PREFIX"]

      manager.manager_cleanup()

    # some processes disable gc for performance, re-enable here
    if not gc.isenabled():
      gc.enable()
      gc.collect()

# If you use setUpClass, the environment variables won't be cleared properly,
# so we need to hook both the function and class pytest fixtures
@pytest.fixture(scope="class", autouse=True)
def openpilot_class_fixture():
  with clean_env():
    yield


@pytest.fixture(scope="function")
def tici_setup_fixture(request, openpilot_function_fixture):
  """Ensure a consistent state for tests on-device. Needs the openpilot function fixture to run first."""
  if 'skip_tici_setup' in request.keywords:
    return
  HARDWARE.initialize_hardware()
  HARDWARE.set_power_save(False)
  os.system("pkill -9 -f athena")


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
  skipper = pytest.mark.skip(reason="Skipping tici test on PC")
  darwin_fake_event_skipper = pytest.mark.skip(reason="Fake socket events are unavailable on macOS")
  darwin_tmpfs_skipper = pytest.mark.skip(reason="tmpfs mount tests require Linux")
  darwin_proxy_skipper = pytest.mark.skip(reason="Athena local proxy socket test requires Linux select semantics")
  for item in items:
    if "tici" in item.keywords:
      if not TICI:
        item.add_marker(skipper)
      else:
        item.fixturenames.append('tici_setup_fixture')

    if "xdist_group_class_property" in item.keywords:
      class_property_name = item.get_closest_marker('xdist_group_class_property').args[0]
      class_property_value = getattr(item.cls, class_property_name)
      item.add_marker(pytest.mark.xdist_group(class_property_value))

    if platform.system() == "Darwin" and item.path.name in ("test_fuzzy.py", "test_processes.py") and "process_replay" in item.path.parts:
      item.add_marker(darwin_fake_event_skipper)

    if platform.system() == "Darwin" and item.path.name == "test_git.py" and "updated" in item.path.parts:
      item.add_marker(darwin_tmpfs_skipper)

    if platform.system() == "Darwin" and item.name == "test_start_local_proxy" and "athena" in item.path.parts:
      item.add_marker(darwin_proxy_skipper)


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
  config_line = "xdist_group_class_property: group tests by a property of the class that contains them"
  config.addinivalue_line("markers", config_line)

  config_line = "nocapture: don't capture test output"
  config.addinivalue_line("markers", config_line)

  config_line = "shared_download_cache: share download cache between tests"
  config.addinivalue_line("markers", config_line)
