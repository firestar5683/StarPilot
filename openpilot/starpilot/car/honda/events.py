from opendbc.car.honda.stock_aol import qualified
from openpilot.cereal import log
from openpilot.selfdrive.selfdrived.events import EVENTS, ET


def event_rules(cp) -> dict:
  if not qualified(cp, marked_only=True):
    return {}
  names = (log.OnroadEvent.EventName.cruiseDisabled, log.OnroadEvent.EventName.speedTooLow)
  return {name: {ET.USER_DISABLE: EVENTS[name][ET.IMMEDIATE_DISABLE]} for name in names}
