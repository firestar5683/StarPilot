import os
import threading

from openpilot.common.params import Params, UnknownKeyName
from openpilot.common.swaglog import cloudlog


class CalibrationReset:
  def __init__(self):
    self._lock = threading.Lock()
    self._pending = False
    self._error: str | None = None

  @property
  def pending(self) -> bool:
    with self._lock:
      return self._pending

  def request(self, params: Params) -> bool:
    with self._lock:
      if self._pending or params.get_bool("OnroadCycleRequested"):
        return False
      self._pending = True
      self._error = None
    threading.Thread(target=self._run, args=(params,), name="calibration-reset", daemon=True).start()
    return True

  def _run(self, params: Params) -> None:
    try:
      for key in ("CalibrationParams", "LiveTorqueParameters", "LiveParametersV2", "LiveDelay"):
        params.remove(key)
        if os.path.lexists(params.get_param_path(key)):
          raise OSError(f"Could not clear {key}")
      params.put_bool("OnroadCycleRequested", True, block=True)
    except (OSError, RuntimeError, UnknownKeyName):
      cloudlog.exception("Calibration reset failed")
      with self._lock:
        self._error = "Calibration could not be reset. Please try again."
    finally:
      with self._lock:
        self._pending = False

  def take_error(self) -> str | None:
    with self._lock:
      error, self._error = self._error, None
      return error


calibration_reset = CalibrationReset()
