import math
import threading
import time

from openpilot.starpilot.system.bluetooth import BluetoothClient, BluetoothStatus


class BluetoothManager:
  def __init__(self):
    self._client = BluetoothClient(timeout=5.0)
    self._lock = threading.Lock()
    self._client_lock = threading.Lock()
    self._status = BluetoothStatus()
    self._active = False
    self._exit = False
    self._operation_error = ""
    self._power_pending = False
    self._operations = {}
    self._audio_test_deadline = 0.0
    self._thread = threading.Thread(target=self._poll, daemon=True)
    self._thread.start()

  @property
  def status(self) -> BluetoothStatus:
    with self._lock:
      return self._status

  def set_active(self, active: bool) -> None:
    self._active = active

  def stop(self) -> None:
    self._exit = True

  def consume_error(self) -> str:
    with self._lock:
      error = self._operation_error
      self._operation_error = ""
      return error

  def operation_for(self, address: str) -> str:
    with self._lock:
      return self._operations.get(address.upper(), "")

  def audio_test_phase(self) -> str:
    with self._lock:
      deadline = self._audio_test_deadline
    if deadline <= 0:
      return "starting"
    remaining = deadline - time.monotonic()
    if remaining > 0:
      return str(max(1, math.ceil(remaining)))
    if remaining > -3.0:
      return "NOW"
    return "complete"

  def _poll(self) -> None:
    while not self._exit:
      if self._active:
        self._poll_status()
      time.sleep(1.0 if self._active else 2.0)

  def _poll_status(self) -> None:
    # Power-on bootstraps the daemon before its RPC completes; do not report a
    # transient status timeout while that transition owns the client.
    with self._lock:
      if self._power_pending:
        return

    with self._client_lock:
      with self._lock:
        if self._power_pending:
          return
      try:
        status = self._client.status()
        with self._lock:
          self._status = status
      except Exception as error:
        with self._lock:
          self._status = BluetoothStatus(error=str(error))

  def _run(self, fn, *args, operation: str = "", address: str = "") -> None:
    normalized_address = address.upper()
    if normalized_address:
      with self._lock:
        self._operations[normalized_address] = operation

    def worker():
      try:
        with self._client_lock:
          fn(*args)
      except Exception as error:
        with self._lock:
          self._operation_error = str(error)
      finally:
        if normalized_address:
          with self._lock:
            if self._operations.get(normalized_address) == operation:
              self._operations.pop(normalized_address, None)
    threading.Thread(target=worker, daemon=True).start()

  def _run_result(self, fn, *args, operation: str = "", address: str = "", callback=None) -> None:
    normalized_address = address.upper()
    if normalized_address:
      with self._lock:
        self._operations[normalized_address] = operation

    def worker():
      result = None
      error = None
      try:
        result = fn(*args)
      except Exception as exception:
        error = str(exception)
      finally:
        if normalized_address:
          with self._lock:
            if self._operations.get(normalized_address) == operation:
              self._operations.pop(normalized_address, None)
      if callback is not None:
        callback(result, error)
      elif error:
        with self._lock:
          self._operation_error = error

    threading.Thread(target=worker, daemon=True).start()

  def set_power(self, enabled: bool) -> None:
    with self._lock:
      if self._power_pending:
        return
      self._power_pending = True

    def worker():
      try:
        with self._client_lock:
          self._client.set_power(enabled)
      except Exception as error:
        with self._lock:
          self._operation_error = str(error)
      finally:
        with self._lock:
          self._power_pending = False

    threading.Thread(target=worker, daemon=True).start()

  def set_scanning(self, scanning: bool) -> None:
    self._run(self._client.start_scan if scanning else self._client.stop_scan)

  def pair(self, address: str) -> None:
    self._run(self._client.pair, address, operation="pairing", address=address)

  def connect(self, address: str) -> None:
    self._run(self._client.connect, address, operation="connecting", address=address)

  def disconnect(self, address: str) -> None:
    self._run(self._client.disconnect, address, operation="disconnecting", address=address)

  def forget(self, address: str) -> None:
    self._run(self._client.forget, address, operation="forgetting", address=address)

  def select_audio(self, address: str) -> None:
    self._run(self._client.select_audio, address)

  def test_audio(self, address: str) -> None:
    def worker():
      try:
        with self._client_lock:
          delay = self._client.test_audio(address)
        with self._lock:
          self._audio_test_deadline = time.monotonic() + delay
      except Exception as error:
        with self._lock:
          self._operation_error = str(error)
          self._audio_test_deadline = 0.0
    threading.Thread(target=worker, daemon=True).start()

  def elm_open(self, address: str, callback=None) -> None:
    self._run_result(self._client.elm_open, address, operation="elm_open", address=address, callback=callback)

  def elm_close(self, address: str, callback=None) -> None:
    self._run_result(self._client.elm_close, address, operation="elm_close", address=address, callback=callback)

  def elm_command(self, address: str, value: str, callback=None) -> None:
    self._run_result(self._client.elm_command, address, value, operation="elm_command", address=address, callback=callback)

  def elm_read_dtcs(self, address: str, callback=None) -> None:
    self._run_result(self._client.elm_read_dtcs, address, operation="elm_read_dtcs", address=address, callback=callback)

  def respond(self, prompt_id: str, accepted: bool, value: str = "") -> None:
    self._run(self._client.respond, prompt_id, accepted, value)
