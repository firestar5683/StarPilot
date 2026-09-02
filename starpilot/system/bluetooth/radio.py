import subprocess
import time

from pathlib import Path


RADIO_HELPER = "/usr/comma/bluetooth-radio"
L2CAP_DEBUG_PATH = "/sys/kernel/debug/bluetooth/l2cap"
SMP_FIXED_CID = "0x0006"


class BluetoothRadio:
  def __init__(self, helper: str = RADIO_HELPER):
    self.helper = helper

  @property
  def available(self) -> bool:
    return Path(self.helper).is_file()

  @property
  def ready(self) -> bool:
    return Path("/sys/class/bluetooth/hci0").exists()

  def start(self, timeout: float = 50.0) -> None:
    if not self.available:
      raise RuntimeError("Bluetooth radio support is not installed")
    subprocess.run(["sudo", "-n", "systemctl", "start", "starpilot-bluetooth-radio.service"], check=True, timeout=timeout)
    deadline = time.monotonic() + timeout
    while not self.ready:
      if time.monotonic() >= deadline:
        raise RuntimeError("Bluetooth radio did not become ready")
      time.sleep(0.1)
    self.ensure_le_security_manager()

  @staticmethod
  def _le_security_manager_registered(timeout: float = 2.0) -> bool | None:
    """Check whether the kernel registered the LE SMP fixed channel."""
    result = subprocess.run(
      ["sudo", "-n", "grep", "-q", SMP_FIXED_CID, L2CAP_DEBUG_PATH],
      check=False,
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL,
      timeout=timeout,
    )
    if result.returncode == 0:
      return True
    if result.returncode == 1:
      return False
    return None

  def ensure_le_security_manager(self, timeout: float = 10.0) -> None:
    """Repair the old AGNOS Bluetooth power-ordering failure when detected."""
    if self._le_security_manager_registered() is not False:
      return

    # Recreate the fixed channels after bluetoothd owns the controller.
    for state in ("off", "on"):
      subprocess.run(
        ["bluetoothctl", "power", state],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
      )

    deadline = time.monotonic() + timeout
    while True:
      registered = self._le_security_manager_registered()
      if registered is True:
        return
      if registered is None:
        raise RuntimeError("Unable to verify the Bluetooth LE security manager")
      if time.monotonic() >= deadline:
        raise RuntimeError("Bluetooth LE security manager did not initialize")
      time.sleep(0.1)

  def stop(self, timeout: float = 10.0) -> None:
    if self.available:
      subprocess.run(["sudo", "-n", "systemctl", "stop", "starpilot-bluetooth-radio.service"], check=True, timeout=timeout)

  def set_connectable(self, enabled: bool, timeout: float = 5.0) -> None:
    """Set connectability without changing pairing visibility."""
    subprocess.run(
      ["sudo", "-n", "btmgmt", "--index", "0", "connectable", "on" if enabled else "off"],
      check=True,
      timeout=timeout,
    )
