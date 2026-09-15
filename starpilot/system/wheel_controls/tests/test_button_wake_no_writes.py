"""An unmapped controller listener must stay idle without persistent writes."""
import pytest

from openpilot.starpilot.system.wheel_controls import wheel_controlsd
from test_wheel_controlsd import FakeParams


@pytest.mark.parametrize('initially_enabled,expected_writes', [(False, []), (True, [(wheel_controlsd.ENABLED_PARAM, False)])])
def test_standby_listener_disables_unused_mappings_at_most_once(initially_enabled, expected_writes):
  class RecordingParams(FakeParams):
    def __init__(self):
      super().__init__({'IsOffroad': False, 'ScreenManagement': True, 'StandbyMode': True,
                        wheel_controlsd.ENABLED_PARAM: initially_enabled})
      self.writes = []

    def put_bool(self, key, value):
      self.writes.append((key, value))
      super().put_bool(key, value)

  params = RecordingParams()
  daemon = wheel_controlsd.WheelControlsDaemon(params, FakeParams())
  try:
    for frame in range(20):
      daemon._update_learning(frame / 10)
    assert not params.get_bool(wheel_controlsd.ENABLED_PARAM)
    assert params.writes == expected_writes
  finally:
    daemon.close()
