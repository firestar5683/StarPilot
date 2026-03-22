#!/usr/bin/env python3
import cereal.messaging as messaging
from opendbc.car import structs
from openpilot.common.params import Params
from openpilot.common.realtime import config_realtime_process
from openpilot.selfdrive.monitoring.helpers import DriverMonitoring

GearShifter = structs.CarState.GearShifter


def dmonitoringd_thread():
  config_realtime_process([0, 1, 2, 3], 5)

  params = Params()
  pm = messaging.PubMaster(['driverMonitoringState'])
  sm = messaging.SubMaster(['driverStateV2', 'liveCalibration', 'carState', 'selfdriveState', 'modelV2'], poll='driverStateV2')

  DM = DriverMonitoring(rhd_saved=params.get_bool("IsRhdDetected"), always_on=params.get_bool("AlwaysOnDM"))
  demo_mode=False

  # FrogPilot variables
  sm = sm.extend(['frogpilotCarState'])

  driver_view_enabled = params.get_bool("IsDriverViewEnabled")

  # 20Hz <- dmonitoringmodeld
  while True:
    sm.update()
    if not sm.updated['driverStateV2']:
      # iterate when model has new output
      continue

    valid = sm.all_checks()
    if demo_mode and sm.valid['driverStateV2']:
      DM.run_step(sm, demo=demo_mode)
    elif valid:
      DM.run_step(sm, demo=demo_mode)
    # FrogPilot variables
    elif driver_view_enabled:
      DM.face_detected = sm['driverStateV2'].leftDriverData.faceProb > DM.settings._FACE_THRESHOLD or sm['driverStateV2'].rightDriverData.faceProb > DM.settings._FACE_THRESHOLD

    # publish
    dat = DM.get_state_packet(valid=valid or driver_view_enabled)
    pm.send('driverMonitoringState', dat)

    # load live always-on toggle
    if sm['driverStateV2'].frameId % 40 == 1:
      DM.always_on = params.get_bool("AlwaysOnDM")
      demo_mode = params.get_bool("IsDriverViewEnabled") and sm["carState"].gearShifter != GearShifter.reverse

    # save rhd virtual toggle every 5 mins, but only with clear confidence.
    if (sm['driverStateV2'].frameId % 6000 == 0 and not demo_mode and
        DM.wheelpos.prob_offseter.filtered_stat.n > DM.settings._WHEELPOS_FILTER_MIN_COUNT):
      wheelpos_mean = DM.wheelpos.prob_offseter.filtered_stat.M
      save_rhd = DM.settings._WHEELPOS_THRESHOLD_ENTER_RHD + DM.settings._WHEELPOS_SAVE_MARGIN
      save_lhd = DM.settings._WHEELPOS_THRESHOLD_ENTER_LHD - DM.settings._WHEELPOS_SAVE_MARGIN
      if wheelpos_mean >= save_rhd:
        params.put_bool_nonblocking("IsRhdDetected", True)
      elif wheelpos_mean <= save_lhd:
        params.put_bool_nonblocking("IsRhdDetected", False)

def main():
  dmonitoringd_thread()


if __name__ == '__main__':
  main()
