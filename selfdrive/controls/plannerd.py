#!/usr/bin/env python3
from cereal import car
from openpilot.common.params import Params
from openpilot.common.realtime import Priority, config_realtime_process
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.controls.lib.ldw import LaneDepartureWarning
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.selfdrive.controls.lib.mvl_accord_longitudinal_planner import MVLAccordLongitudinalPlanner
from opendbc.car.honda.values import CAR as HONDA_CAR
import cereal.messaging as messaging

from openpilot.starpilot.common.starpilot_variables import get_starpilot_toggles


def main():
  config_realtime_process(5, Priority.CTRL_LOW)

  cloudlog.info("plannerd is waiting for CarParams")
  params = Params()
  CP = messaging.log_from_bytes(params.get("CarParams", block=True), car.CarParams)
  cloudlog.info("plannerd got CarParams: %s", CP.brand)

  ldw = LaneDepartureWarning()
  longitudinal_planner = MVLAccordLongitudinalPlanner(CP) if CP.carFingerprint == HONDA_CAR.HONDA_ACCORD_11G else LongitudinalPlanner(CP)
  pm = messaging.PubMaster(['longitudinalPlan', 'driverAssistance'])
  sm = messaging.SubMaster(['carControl', 'carState', 'controlsState', 'liveParameters', 'radarState', 'modelV2', 'selfdriveState'],
                           poll='modelV2')

  sm = sm.extend(['starpilotCarState', 'starpilotPlan'])

  starpilot_toggles = get_starpilot_toggles()

  while True:
    sm.update()
    if sm.updated['modelV2']:
      longitudinal_planner.update(sm, starpilot_toggles)
      longitudinal_planner.publish(sm, pm)

      ldw.update(sm.frame, sm['modelV2'], sm['carState'], sm['carControl'])
      msg = messaging.new_message('driverAssistance')
      msg.valid = sm.all_checks(['carState', 'carControl', 'modelV2', 'liveParameters'])
      msg.driverAssistance.leftLaneDeparture = ldw.left
      msg.driverAssistance.rightLaneDeparture = ldw.right
      pm.send('driverAssistance', msg)

    starpilot_toggles = get_starpilot_toggles(sm)


if __name__ == "__main__":
  main()
