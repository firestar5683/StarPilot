import threading
import time

from openpilot.starpilot.galaxy.software_operations import SoftwareOperations


class NativeSoftwareUpdate:
  def __init__(self, permitted):
    self.permitted = permitted
    self.owner = SoftwareOperations()
    self.status = None
    self.error = ""
    self.busy = False
    self.refreshing = False
    self.lock = threading.Lock()
    self.next_refresh = 0.0

  def refresh(self):
    if self.busy or self.refreshing or time.monotonic() < self.next_refresh:
      return
    self.next_refresh = time.monotonic() + 1.0
    self.refreshing = True
    self._start(None)

  def submit(self, action):
    if self.busy or not self.permitted():
      return False
    self.busy = True
    self.error = ""
    self._start(action)
    return True

  def _start(self, action):
    def work():
      try:
        with self.lock:
          if action is not None:
            status = self.owner.status.snapshot()
            status["operations"] = self.owner.snapshot()
            branch = status["installed"]["branch"] if action == "rollback" else status["operations"]["selectedTarget"] or status["installed"]["branch"]
            self.owner.action(action, {"action": action, "branch": branch}, authorized=self.permitted)
          status = self.owner.status.snapshot()
          status["operations"] = self.owner.snapshot()
          self.status = status
          self.error = ""
      except Exception as error:
        self.error = str(error)
      finally:
        if action is None:
          self.refreshing = False
        else:
          self.busy = False

    threading.Thread(target=work, daemon=True).start()

  def available(self, action):
    key = "canRollback" if action == "rollback" else "canFastUpdate"
    return self.permitted() and not self.busy and self.status is not None and self.status["operations"].get(key) is True

  def detail(self):
    if self.error:
      return self.error
    if self.status is None:
      return ""
    fast = self.status["updater"].get("fast")
    return fast["detail"] if fast is not None else ""
