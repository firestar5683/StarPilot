"""Parked Jetlink selection and its read-only provisioning status."""
from __future__ import annotations

MODES = ("off", "usb", "ios")


class JetlinkSettings:
  def __init__(self, *, params=None, link=None, device_type=None, chestnut=None, runtime=None):
    self._params = params
    self._link = link
    self._device_type = device_type
    self._chestnut = chestnut
    self._runtime = runtime

  def params(self):
    if self._params is None:
      from openpilot.common.params import Params
      self._params = Params()
    return self._params

  def snapshot(self):
    try:
      return self._snapshot()
    except (OSError, RuntimeError, ValueError, ImportError):
      return {"mode": "off", "supported": False, "chestnut": False, "enabled": False,
              "present": False, "prepared": False, "active": False, "runtimeState": "unavailable", "state": "unavailable",
              "reason": "Jetlink status is unavailable; the local model remains in use.",
              "progress": "", "model": None, "transport": "USB", "chargePhone": False}

  def _snapshot(self):
    from openpilot.starpilot.models.jetlink_adapter import adapter, get_jetlink, runtime_status, supported_device
    if self._device_type is None:
      from openpilot.common.hardware import HARDWARE
      device = HARDWARE.get_device_type()
    else:
      device = self._device_type()
    supported = supported_device(device)
    chestnut = self._chestnut() if self._chestnut is not None else adapter().chestnut_present()
    params = self.params()
    raw = params.get("JetlinkMode")
    mode = MODES[raw] if type(raw) is int and 0 <= raw < len(MODES) else "off"
    link = self._link() if self._link is not None else get_jetlink()
    status = link.status() if link is not None else None
    reason = "" if supported else "Jetlink requires a comma 3X or comma 4."
    if mode != "off" and status is None:
      reason = reason or "Jetlink is unavailable; the local model remains in use."
    if status is not None and status.reason:
      reason = str(status.reason)
    progress = status.progress if status is not None and isinstance(status.progress, dict) else {}
    runtime = self._runtime() if self._runtime is not None else runtime_status()
    active = mode != "off" and supported and not chestnut and runtime.get("active") is True
    runtime_state = runtime.get("state", "unavailable")
    stage = str(progress.get("stage", ""))
    state = "off" if mode == "off" else "unavailable" if reason else "prepared" if status.ready else stage or "pending"
    if active:
      state = "active"
    elif mode != "off" and not reason and runtime_state in ("joining", "retrying", "ready"):
      state = {"joining": "connecting", "retrying": "fallback / reconnecting", "ready": "waiting for disengagement"}[runtime_state]
    return {"mode": mode, "supported": supported, "chestnut": chestnut, "enabled": bool(status and status.enabled and supported),
            "present": bool(status and status.present), "prepared": bool(mode != "off" and status and status.ready and supported),
            "active": active, "runtimeState": runtime_state,
            "activeArtifactSha256": runtime.get("artifact_sha256") if active else None,
            "activeCheckpoint": runtime.get("model_checkpoint") if active else None,
            "state": state, "reason": reason, "progress": str(progress.get("msg", "")),
            "model": status.model if status is not None else None,
            "transport": status.transport if status is not None else "USB",
            "chargePhone": params.get_bool("JetlinkChargePhone")}

  def configure(self, payload):
    if not payload or set(payload) - {"mode", "chargePhone"}:
      raise ValueError("Invalid Jetlink settings")
    if "mode" in payload and payload["mode"] not in MODES:
      raise ValueError("Choose Off, USB, or iPhone")
    if "chargePhone" in payload and type(payload["chargePhone"]) is not bool:
      raise ValueError("Invalid phone charging setting")
    view = self.snapshot()
    if payload.get("mode", "off") != "off" and not view["supported"]:
      raise ValueError("Jetlink requires a comma 3X or comma 4")
    if payload.get("mode", "off") != "off" and view["chestnut"]:
      raise ValueError("Chestnut is connected; Jetlink cannot run alongside it")
    params = self.params()
    if "chargePhone" in payload:
      params.put_bool("JetlinkChargePhone", payload["chargePhone"], block=True)
    if "mode" in payload:
      params.put("JetlinkMode", MODES.index(payload["mode"]), block=True)
    return {"message": "Jetlink settings saved. Check connection status before driving."}
