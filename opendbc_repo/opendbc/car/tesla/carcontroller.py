import numpy as np
from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.lateral import apply_steer_angle_limits_vm
from opendbc.car.interfaces import CarControllerBase
from opendbc.car.tesla.coop_steering import CooperativeSteeringController
from opendbc.car.tesla.teslacan import TeslaCAN
from opendbc.car.tesla.preap.carcontroller import PreAPLongController, init_preap_can
from opendbc.car.tesla.preap.stock_cc_spoofer import StockCCSpoofer
from opendbc.car.tesla.values import CANBUS, CAR, CarControllerParams, TeslaSafetyFlags
from opendbc.car.vehicle_model import VehicleModel

def get_safety_CP():
  from opendbc.car.tesla.interface import CarInterface
  return CarInterface.get_non_essential_params(CAR.TESLA_MODEL_Y)


class CarController(CarControllerBase):
  def __init__(self, dbc_names, CP):
    super().__init__(dbc_names, CP)
    self.apply_angle_last = 0
    self.apply_angle_command_last = 0
    self.coop_steer = CooperativeSteeringController()
    self.coop_enabled = CP.carFingerprint == CAR.TESLA_MODEL_3 and any(
      config.safetyParam & TeslaSafetyFlags.COOP_STEERING.value for config in CP.safetyConfigs
    )
    self._clear_steering_limit_info()
    self.packer = CANPacker(dbc_names[Bus.party])
    self.tesla_can = TeslaCAN(self.packer)
    self.preap_long = None
    self.stock_cc = None

    # Vehicle model used for lateral limiting
    self.VM = VehicleModel(get_safety_CP())

    if CP.carFingerprint == CAR.TESLA_MODEL_S_PREAP:
      self.tesla_can = init_preap_can(dbc_names)
      self.preap_long = PreAPLongController()
      self.stock_cc = StockCCSpoofer()
      from opendbc.car.tesla.interface import CarInterface
      self.VM = VehicleModel(CarInterface.get_non_essential_params(CAR.TESLA_MODEL_S_PREAP))

  def _clear_steering_limit_info(self):
    self.steering_limit_info_valid = False
    self.model_limit_error_deg = 0.0
    self.resume_limit_error_deg = 0.0
    self.cooperative_limit_error_deg = 0.0
    self.cooperative_offset_deg = 0.0
    self.steering_limit_mono_time = 0
    self.combined_limit_error_deg = 0.0

  def _write_steering_limit_info(self, actuators):
    info = actuators.steeringLimitInfo
    info.valid = self.steering_limit_info_valid
    info.modelLimitErrorDeg = self.model_limit_error_deg
    info.resumeLimitErrorDeg = self.resume_limit_error_deg
    info.cooperativeLimitErrorDeg = self.cooperative_limit_error_deg
    info.cooperativeOffsetDeg = self.cooperative_offset_deg
    info.monoTime = self.steering_limit_mono_time
    info.combinedLimitErrorDeg = self.combined_limit_error_deg

  def update(self, CC, CS, now_nanos, starpilot_toggles):
    if self.CP.carFingerprint == CAR.TESLA_MODEL_S_PREAP:
      self._clear_steering_limit_info()
      return self._update_preap(CC, CS)

    actuators = CC.actuators
    can_sends = []

    # Preserve the stock controller path unless cooperative steering is explicitly enabled.
    lat_active = CC.latActive and (not CS.out.steeringDisengage if self.coop_enabled else CS.hands_on_level < 3)
    if not (self.coop_enabled and lat_active):
      self._clear_steering_limit_info()

    if self.frame % 2 == 0:
      requested_angle = actuators.steeringAngleDeg

      # Angular rate limit based on speed
      self.apply_angle_last = apply_steer_angle_limits_vm(actuators.steeringAngleDeg, self.apply_angle_last, CS.out.vEgoRaw, CS.out.steeringAngleDeg,
                                                          lat_active, CarControllerParams, self.VM)

      self.apply_angle_command_last, lat_active = self.coop_steer.update(
        self.apply_angle_last, lat_active, self.coop_enabled, CS, self.VM,
      )

      if self.coop_enabled and lat_active:
        model_limit_error_deg = abs(requested_angle - self.apply_angle_last)
        resume_limit_error_deg = self.coop_steer.resume_limit_error_deg
        cooperative_limit_error_deg = self.coop_steer.cooperative_limit_error_deg
        cooperative_offset_deg = self.coop_steer.cooperative_offset_deg
        combined_limit_error_deg = abs(requested_angle + cooperative_offset_deg - self.apply_angle_command_last)
        limit_values = (model_limit_error_deg, resume_limit_error_deg, cooperative_limit_error_deg,
                        cooperative_offset_deg, combined_limit_error_deg)

        if all(np.isfinite(value) for value in limit_values):
          self.steering_limit_info_valid = True
          self.model_limit_error_deg = model_limit_error_deg
          self.resume_limit_error_deg = resume_limit_error_deg
          self.cooperative_limit_error_deg = cooperative_limit_error_deg
          self.cooperative_offset_deg = cooperative_offset_deg
          self.steering_limit_mono_time = now_nanos
          self.combined_limit_error_deg = combined_limit_error_deg
        else:
          self._clear_steering_limit_info()

      can_sends.append(self.tesla_can.create_steering_control(self.apply_angle_command_last, lat_active))

    if self.frame % 10 == 0:
      can_sends.append(self.tesla_can.create_steering_allowed())

    # Longitudinal control
    if self.CP.openpilotLongitudinalControl:
      if self.frame % 4 == 0:
        state = 13 if CC.cruiseControl.cancel else 4  # 4=ACC_ON, 13=ACC_CANCEL_GENERIC_SILENT
        accel = float(np.clip(actuators.accel, CarControllerParams.ACCEL_MIN, CarControllerParams.ACCEL_MAX))
        cntr = (self.frame // 4) % 8
        can_sends.append(self.tesla_can.create_longitudinal_command(state, accel, cntr, self.frame, CS.out.vEgo, CS.out.gasPressed))

    else:
      # Increment counter so cancel is prioritized even without openpilot longitudinal
      if CC.cruiseControl.cancel:
        cntr = (CS.das_control["DAS_controlCounter"] + 1) % 8
        can_sends.append(self.tesla_can.create_longitudinal_command(13, 0, cntr, self.frame, CS.out.vEgo, False))

    # TODO: HUD control
    new_actuators = actuators.as_builder()
    new_actuators.steeringAngleDeg = self.apply_angle_command_last
    self._write_steering_limit_info(new_actuators)

    self.frame += 1
    return new_actuators, can_sends

  def _update_preap(self, CC, CS):
    actuators = CC.actuators
    can_sends = []
    lat_active = CC.latActive and CS.hands_on_level < 3

    if CC.cruiseControl.cancel and CS.cruiseEnabled:
      CS.cruiseEnabled = False
      CS.enableLongControl = False
      CS.enableJustCC = False
      CS.pedal_speed_kph = 0.0
      CS.preap_cc_cancel_needed = True
      if hasattr(CS, "engagement"):
        CS.engagement.cruiseEnabled = False
        CS.engagement.enableLongControl = False
        CS.engagement.enableJustCC = False
        CS.engagement.pending_enable = False
        CS.engagement.pedal_speed_kph = 0.0

    if self.frame % 2 == 0:
      self.apply_angle_last = apply_steer_angle_limits_vm(
        actuators.steeringAngleDeg, self.apply_angle_last, CS.out.vEgoRaw, CS.out.steeringAngleDeg,
        lat_active, CarControllerParams, self.VM,
      )
      cntr = (self.frame // 2) % 16
      can_sends.append(self.tesla_can.create_steering_control(cntr, self.apply_angle_last, lat_active))
      can_sends.append(self.tesla_can.create_epas_control(cntr, 1))

    CS.pccEvent = None
    if self.CP.openpilotLongitudinalControl and self.preap_long is not None:
      can_sends.extend(self.preap_long.update(CC, CS, self.frame, self.tesla_can, CANBUS.party))

    if self.stock_cc is not None:
      can_sends.extend(self.stock_cc.update(CS, self.frame, self.tesla_can, CANBUS.party))
      if self.stock_cc.pcc_event:
        CS.pccEvent = self.stock_cc.pcc_event

    new_actuators = actuators.as_builder()
    new_actuators.steeringAngleDeg = self.apply_angle_last
    self._write_steering_limit_info(new_actuators)

    self.frame += 1
    return new_actuators, can_sends
