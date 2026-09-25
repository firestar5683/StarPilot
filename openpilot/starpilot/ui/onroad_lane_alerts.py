"""Use upstream lane-change notices while lateral control runs independently."""

from typing import Any

from openpilot.selfdrive.selfdrived.events import EVENTS, ET, EventName
from openpilot.starpilot.ui.onroad_state import AlertSize, OnroadAlert


def lateral_lane_alert(native: OnroadAlert, *, car: Any, control: Any, model: Any, selfdrive: Any) -> OnroadAlert:
  """Accept only current display sources; never replace an existing alert."""
  if (native.size != AlertSize.NONE or any(source is None for source in (car, control, model, selfdrive)) or
      not getattr(control, 'latActive', False) or getattr(selfdrive, 'enabled', True) or
      not getattr(car, 'canValid', False) or getattr(car, 'canTimeout', True)):
    return native
  meta = getattr(model, 'meta', None)
  state, direction = str(getattr(meta, 'laneChangeState', 'off')), str(getattr(meta, 'laneChangeDirection', 'none'))
  if direction not in ('left', 'right'):
    return native
  if state == 'preLaneChange':
    blocked = car.leftBlindspot if direction == 'left' else car.rightBlindspot
    event = EventName.laneChangeBlocked if blocked else EventName.preLaneChangeLeft if direction == 'left' else EventName.preLaneChangeRight
  elif state in ('laneChangeStarting', 'laneChangeFinishing'):
    event = EventName.laneChange
  else:
    return native
  warning = EVENTS[event][ET.WARNING]
  name = next(name for name in ('preLaneChangeLeft', 'preLaneChangeRight', 'laneChangeBlocked', 'laneChange')
              if getattr(EventName, name) == event)
  return OnroadAlert((AlertSize.NONE, AlertSize.SMALL, AlertSize.MID, AlertSize.FULL)[warning.alert_size],
                     warning.alert_text_1, warning.alert_text_2, False, name + '/warning')
