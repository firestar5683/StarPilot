"""Exception reporting through the packaged Sentry SDK."""
import datetime
import glob
import importlib
import os
import sys
import traceback
from enum import Enum
from pathlib import Path
from types import ModuleType

from openpilot.common.basedir import BASEDIR
from openpilot.common.hardware import HARDWARE, PC
from openpilot.common.hardware.hw import Paths
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.common.version import get_build_metadata


class SentryProject(Enum):
  SELFDRIVE = 'https://7305139359a548fcb348ec09497dc389@bugsink.firestar.link/1'
  SELFDRIVE_NATIVE = SELFDRIVE


EXIT_FLUSH_TIMEOUT = 0.5
HTTP_TIMEOUT = 2
TRANSPORT_QUEUE_SIZE = 32
sdk: ModuleType | None = None
_initialized_pid: int | None = None


def _load_sdk() -> ModuleType:
  # Device prebuilt launches do not install pyproject dependencies. This complete
  # MIT package is tracked and included by the ordinary Git release packager.
  vendor = str(Path(BASEDIR) / "sentry_sdk_repo")
  if vendor not in sys.path:
    sys.path.insert(0, vendor)
  return importlib.import_module("sentry_sdk")


def init(project: SentryProject = SentryProject.SELFDRIVE) -> bool:
  global sdk, _initialized_pid
  if PC:
    return False
  fresh = _initialized_pid != os.getpid()
  try:
    if fresh:
      sdk = _load_sdk()
      transport_module = importlib.import_module("sentry_sdk.transport")
      threading_module = importlib.import_module("sentry_sdk.integrations.threading")

      class BoundedHttpTransport(transport_module.HttpTransport):
        TIMEOUT = HTTP_TIMEOUT

      # Explicit capture and the threading integration own errors. Enabling the
      # logging integration would report cloudlog.exception a second time.
      sdk.init(dsn=project.value, default_integrations=False, auto_enabling_integrations=False,
               integrations=[threading_module.ThreadingIntegration(propagate_scope=True)],
               transport=BoundedHttpTransport, transport_queue_size=TRANSPORT_QUEUE_SIZE,
               shutdown_timeout=EXIT_FLUSH_TIMEOUT, enable_backpressure_handling=False,
               max_value_length=8192, traces_sample_rate=0.0,
               release=os.getenv("GIT_COMMIT", "unknown"), environment="Release")
      _initialized_pid = os.getpid()
    if sdk is None:
      return False
  except Exception:
    cloudlog.warning("Crash reporting unavailable; continuing without remote reporting")
    sdk = None
    _initialized_pid = None
    return False

  # Configure transport before reading metadata: a failed manager_init must be
  # reportable even before registration/logmessaged. Refresh after registration
  # and after fork, using the existing typed Params and current build metadata.
  try:
    build = get_build_metadata()
    params = Params()
    sdk.get_client().options.update(release=build.canonical,
                                    environment="Testing" if "test" in build.channel.lower() else "Release")
    sdk.set_user({"id": params.get("DongleId") or os.getenv("DONGLE_ID", "unregistered")})
    for key, value in {"origin": build.openpilot.git_origin, "branch": build.channel,
                       "commit": build.openpilot.git_commit, "dirty": build.openpilot.is_dirty,
                       "installed": params.get("InstallDate"), "updated": params.get("LastUpdateTime"),
                       "device": HARDWARE.get_device_type()}.items():
      sdk.set_tag(key, str(value) if value is not None else "unknown")
  except Exception:
    cloudlog.warning("Crash reporting metadata unavailable")
  if fresh:
    try:
      sdk.start_session()
    except Exception:
      cloudlog.warning("Crash reporting session unavailable")
  return True


def set_tag(key: str, value: str) -> None:
  if sdk is not None:
    try:
      sdk.set_tag(key, value)
    except Exception:
      cloudlog.warning("Crash reporting tag unavailable")


def _attach_qlog(scope) -> None:
  try:
    qlogs = [path for name in ("qlog.zst", "qlog.bz2", "qlog")
             for path in glob.glob(f"{Paths.log_root()}/*/{name}")]
    if qlogs:
      scope.add_attachment(path=max(qlogs, key=os.path.getmtime))
  except Exception:
    cloudlog.warning("Crash log attachment unavailable")


def save_exception(text: str) -> None:
  path = Path(Paths.log_root()) / "crash"
  path.mkdir(parents=True, exist_ok=True)
  stamp = datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S-%f")
  (path / f"{stamp}.log").write_text(text)
  (path / "error.txt").write_text("\n".join(text.splitlines()[-10:]))


def capture_exception(exc: BaseException | None = None, *, crash_log: bool = True) -> None:
  text = "".join(traceback.format_exception(exc)) if exc is not None else traceback.format_exc()
  if any(message in text for message in ("already exists. To overwrite it, set 'overwrite' to True", "failed after retry")):
    return
  if crash_log:
    try:
      save_exception(text)
    except Exception:
      cloudlog.warning("Local crash report could not be saved")
  if sdk is not None:
    try:
      with sdk.new_scope() as scope:
        _attach_qlog(scope)
        sdk.capture_exception(exc)
    except Exception:
      cloudlog.warning("Crash report could not be queued")


def report_tombstone(fn: str, message: str, contents: str) -> None:
  if sdk is not None:
    try:
      with sdk.new_scope() as scope:
        scope.set_extra("tombstone_fn", fn)
        scope.set_extra("tombstone", contents)
        _attach_qlog(scope)
        sdk.capture_message(message, level="error")
    except Exception:
      cloudlog.warning("Native crash report could not be queued")


def flush() -> None:
  """Only call on fatal process exit; ordinary captures never wait for HTTP."""
  if sdk is not None:
    try:
      sdk.flush(timeout=EXIT_FLUSH_TIMEOUT)
    except Exception:
      cloudlog.warning("Crash report flush interrupted")
