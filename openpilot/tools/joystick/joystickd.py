#!/usr/bin/env python3

import math
import os
import time
import numpy as np

from openpilot.cereal import messaging
from opendbc.car.structs import car
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.realtime import DT_CTRL, Ratekeeper
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.controls.lib.drive_helpers import should_stop
from openpilot.starpilot.feature_runtime import enabled as feature_enabled
from openpilot.starpilot.aol.runtime import current_axis, current_native, ordinary_lateral_requested, ordinary_axis_acknowledged
from openpilot.starpilot.aol.vehicle import policy_for as axis_policy_for, ordinary_axis_request_allowed, allow_lateral_onset

LongCtrlState = car.CarControl.Actuators.LongControlState
MAX_LAT_ACCEL = 3.0


def joystickd_thread():
  params = Params()
  cloudlog.info("joystickd is waiting for CarParams")
  CP = messaging.log_from_bytes(params.get("CarParams", block=True), car.CarParams)
  VM = VehicleModel(CP)

  aol_replay = feature_enabled(params, CP, 'aol', os.environ)
  ordinary_axis_ack_required = axis_policy_for(CP).ordinary_axis_ack_required

  services = ['carState', 'onroadEvents', 'vehicleParameters', 'selfdriveState', 'testJoystick']
  if aol_replay or ordinary_axis_ack_required:
    services += ['aolAxisState', 'aolSafetyWire']
  sm = messaging.SubMaster(services, frequency=1. / DT_CTRL)
  pm = messaging.PubMaster(['carControl', 'controlsState'])

  previous_lateral_active = False
  rk = Ratekeeper(100, print_delay_threshold=None)
  while 1:
    sm.update(0)
    CS = sm['carState']

    cc_msg = messaging.new_message('carControl')
    cc_msg.valid = True
    CC = cc_msg.carControl
    CC.enabled = sm['selfdriveState'].enabled
    CC.longActive = CC.enabled and not any(e.overrideLongitudinal for e in sm['onroadEvents']) and CP.openpilotLongitudinalControl

    # Lateral gate mirrors controlsd so the stick steers in AOL as well as full engagement
    CC.latActive = ordinary_lateral_requested(sm['selfdriveState'].active, CS, CP)
    if aol_replay:
      now_ns = time.monotonic_ns()
      standstill = abs(CS.vEgo) <= max(CP.minSteerSpeed, 0.3) or CS.standstill
      axis = current_axis(sm, now_ns=now_ns)
      native = current_native(sm, CP, now_ns=now_ns, axis_session_id=str(axis.sessionId) if axis is not None else None)
      acknowledged = axis is not None and native is not None and axis.nativeAcknowledged
      CC.latActive = bool(acknowledged and axis.lateralActive and
                          bool(axis.desiredLateral) == bool(native.requestedLateral) and native.lateralAllowed and
                          not CS.steerFaultTemporary and not CS.steerFaultPermanent and
                          (not standstill or CP.steerAtStandstill))
      CC.longActive = bool(acknowledged and axis.longitudinalActive and
                           bool(axis.desiredLongitudinal) == bool(native.requestedLongitudinal) and native.longitudinalAllowed and
                           CP.openpilotLongitudinalControl and
                           not any(e.overrideLongitudinal for e in sm['onroadEvents']))
    elif ordinary_axis_ack_required:
      CC.latActive = bool(CC.latActive and CS.canValid and not CS.canTimeout and
                          ordinary_axis_request_allowed(CP, CS) and
                          ordinary_axis_acknowledged(sm, CP, now_ns=time.monotonic_ns()))
    CC.latActive = allow_lateral_onset(CP, requested=bool(CC.latActive), normal_enabled=bool(CC.enabled),
                                      steering_pressed=bool(CS.steeringPressed), previous_active=previous_lateral_active)
    previous_lateral_active = bool(CC.latActive)

    CC.cruiseControl.override = CC.enabled and not CC.longActive and CP.openpilotLongitudinalControl
    CC.cruiseControl.cancel = sm['carState'].cruiseState.enabled and (not CC.enabled or not CP.pcmCruise)
    CC.hudControl.leadDistanceBars = 2

    actuators = CC.actuators

    # reset joystick if it hasn't been received in a while
    should_reset_joystick = sm.recv_frame['testJoystick'] == 0 or (sm.frame - sm.recv_frame['testJoystick'])*DT_CTRL > 0.2

    if not should_reset_joystick:
      joystick_axes = sm['testJoystick'].axes
    else:
      joystick_axes = [0.0, 0.0]

    if CC.longActive:
      actuators.accel = 4.0 * float(np.clip(joystick_axes[0], -1, 1))
      actuators.longControlState = LongCtrlState.stopping if should_stop(sm['carState'].vEgo, actuators.accel) else LongCtrlState.pid
      CC.cruiseControl.resume = actuators.accel > 0.0

    if CC.latActive:
      max_curvature = MAX_LAT_ACCEL / max(sm['carState'].vEgo ** 2, 5)
      max_angle = math.degrees(VM.get_steer_from_curvature(max_curvature, sm['carState'].vEgo, sm['vehicleParameters'].roll))

      actuators.torque = float(np.clip(joystick_axes[1], -1, 1))
      actuators.steeringAngleDeg, actuators.curvature = actuators.torque * max_angle, actuators.torque * -max_curvature

    pm.send('carControl', cc_msg)

    cs_msg = messaging.new_message('controlsState')
    cs_msg.valid = True
    controlsState = cs_msg.controlsState
    controlsState.lateralControlState.init('debugState')

    lp = sm['vehicleParameters']
    steer_angle_without_offset = math.radians(sm['carState'].steeringAngleDeg - lp.angleOffsetDeg)
    controlsState.curvature = -VM.calc_curvature(steer_angle_without_offset, sm['carState'].vEgo, lp.roll)

    pm.send('controlsState', cs_msg)

    rk.keep_time()


def main():
  joystickd_thread()


if __name__ == "__main__":
  main()
