"""Manager's opt-in Jetlink owner and bounded remote power-off handoff."""
from __future__ import annotations


def enabled(params) -> bool:
  # Keep off/default startup independent of the transport and model runtime.
  raw = params.get('JetlinkMode')
  if type(raw) is not int or raw not in (1, 2):
    return False
  from openpilot.starpilot.models.jetlink_adapter import get_jetlink, supported_device
  if not supported_device():
    return False
  link = get_jetlink()
  return link is not None and link.enabled()


def shutdown(params) -> None:
  reason = next((key for key in ('DoUninstall', 'DoReboot', 'DoShutdown') if params.get_bool(key)), None)
  if reason is None or not enabled(params):
    return
  from openpilot.starpilot.models.jetlink_adapter import get_jetlink
  # The resident owner must still be alive to lend the shutdown worker its link.
  link = get_jetlink()
  if link is not None:
    link.shutdown(reason, timeout=25.0)
