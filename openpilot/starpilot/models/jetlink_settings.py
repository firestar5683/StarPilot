"""Parked Jetlink selection and its read-only provisioning status."""
from __future__ import annotations

from openpilot.starpilot.models.jetlink_adapter import UNSUPPORTED
from openpilot.starpilot.models.jetlink_status import connection_state

MODES = ("off", "usb", "ios")

# jetlink's Status.phase in Galaxy's words, where they differ
PHASES = {"waiting": "waiting for disengagement", "reconnecting": "fallback / reconnecting"}


class JetlinkSettings:
  def __init__(self, *, params=None, link=None, device_type=None, chestnut=None):
    self._params = params
    self._link = link
    self._device_type = device_type
    self._chestnut = chestnut

  def params(self):
    if self._params is None:
      from openpilot.common.params import Params
      self._params = Params()
    return self._params

  def snapshot(self):
    try:
      return self._snapshot()
    except (OSError, RuntimeError, ValueError, ImportError):
      return {"mode": "unknown", "supported": False, "chestnut": False, "enabled": False,
              "present": False, "prepared": False, "active": False, "runtimeState": "unavailable", "state": "unavailable",
              "reason": "Jetlink status is unavailable; the local model remains in use.",
              "progress": "", "model": None, "transport": "USB", "chargePhone": False}

  def _snapshot(self):
    from openpilot.starpilot.models.jetlink_adapter import adapter, hooks, supported_device
    supported = supported_device(self._device_type() if self._device_type is not None else None)
    chestnut = self._chestnut() if self._chestnut is not None else adapter().chestnut_present()
    params = self.params()
    raw = params.get("JetlinkMode")
    mode = MODES[raw] if type(raw) is int and 0 <= raw < len(MODES) else "off"
    try:
      status = (self._link() if self._link is not None else hooks()).status()
    except (OSError, RuntimeError, ValueError, ImportError):
      status = None
    reason = "" if supported else UNSUPPORTED + "."
    if mode != "off" and status is None:
      reason = reason or "Jetlink is unavailable; the local model remains in use."
    if chestnut and mode != "off":
      reason = "Chestnut is connected; Jetlink is not in use."
    elif status is not None and status.reason:
      reason = reason or str(status.reason)
    usable = mode != "off" and supported and not chestnut and status is not None and status.enabled
    # the big model drives modeld's frames now, by modeld's runtime record
    phase = connection_state(status)
    active = bool(usable and phase == "active")
    state = "off" if mode == "off" else "unavailable" if not supported or chestnut else PHASES.get(phase, phase)
    progress = status.progress if status is not None and isinstance(status.progress, dict) else {}
    return {"mode": mode, "supported": supported, "chestnut": chestnut, "enabled": bool(usable and status.enabled),
            "present": bool(usable and status.present and status.port != "empty"), "prepared": bool(usable and status.ready),
            "active": active, "runtimeState": (status.running if status is not None else None) or "unavailable",
            "activeArtifactSha256": status.running_sha256 if active else None,
            "activeCheckpoint": status.running_checkpoint if active else None,
            "state": state, "reason": reason, "progress": str(progress.get("msg", "")),
            "model": status.model if status is not None else None,
            "activeModel": status.active_model if active else None,
            "transport": status.transport if status is not None else "USB",
            "chargePhone": params.get_bool("JetlinkChargePhone")}

  @staticmethod
  def _wired_session_running():
    """Wired Android Auto holds the comma's USB-C port while a session runs."""
    try:
      from openpilot.starpilot.system.android_auto.protocol import AndroidAutoClient
      status = AndroidAutoClient().status()
      return status.get("connection") == "wired" and bool(status.get("running"))
    except Exception:
      return False

  def configure(self, payload):
    if not payload or set(payload) - {"mode", "chargePhone"}:
      raise ValueError("Invalid Jetlink settings")
    if "mode" in payload and payload["mode"] not in MODES:
      raise ValueError("Choose Off, USB host (Android / PC / Jetson), or iPhone / iPad")
    if "chargePhone" in payload and type(payload["chargePhone"]) is not bool:
      raise ValueError("Invalid mobile device charging setting")
    view = self.snapshot()
    if payload.get("mode", "off") != "off" and not view["supported"]:
      raise ValueError("Jetlink requires a comma 3X or comma 4")
    if payload.get("mode", "off") != "off" and view["chestnut"]:
      raise ValueError("Chestnut is connected; Jetlink cannot run alongside it")
    if payload.get("mode", "off") != "off" and self._wired_session_running():
      raise ValueError("Disconnect wired Android Auto before enabling Jetlink")
    params = self.params()
    if "chargePhone" in payload:
      params.put_bool("JetlinkChargePhone", payload["chargePhone"], block=True)
    if "mode" in payload:
      params.put("JetlinkMode", MODES.index(payload["mode"]), block=True)
    return {"message": "Jetlink settings saved. Check connection status before driving."}
