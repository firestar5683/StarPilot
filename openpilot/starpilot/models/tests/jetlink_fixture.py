"""The Jetlink adapter's in-control rule over fixed messages, for its tests and selfdrived's."""
from types import SimpleNamespace

from jetlink.openpilot.testing import FakeSubMaster
from openpilot.starpilot.models import jetlink_adapter

IDLE = {"selfdriveState": SimpleNamespace(enabled=False, active=False),
        "carControl": SimpleNamespace(enabled=False, latActive=False, longActive=False)}
AXES_IDLE = SimpleNamespace(desiredLateral=False, desiredLongitudinal=False, lateralActive=False, longitudinalActive=False)
ARMED_PAUSED = SimpleNamespace(allowedLatch=False, lateralArmed=True)


def rule(core=None, aol=None):
  """The adapter, its in_control() reading openpilot's services (idle unless given) and AOL's."""
  op = jetlink_adapter.adapter()
  op._sm = FakeSubMaster(op.IN_CONTROL_SERVICES, **{**IDLE, **(core or {})})
  op._aol = FakeSubMaster(jetlink_adapter.AOL_SERVICES, **(aol or {}))
  return op
