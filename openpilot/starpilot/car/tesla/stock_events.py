from openpilot.cereal import log
from opendbc.car.tesla.preap.aol import qualified


def add_stock_events(events, CP, CS, CS_prev):
  if not qualified(CP) or not CS.canValid or CS.canTimeout:
    return
  names = log.OnroadEvent.EventName
  if CS.teslaStockCruiseEngaged and not CS_prev.teslaStockCruiseEngaged:
    events.add(names.teslaCCEngaged)
  elif not CS.teslaStockCruiseEngaged and CS_prev.teslaStockCruiseEngaged:
    events.add(names.teslaCCDisengaged)
  if CS.teslaStockCruiseNotArmed:
    events.add(names.teslaCCNotArmed)
