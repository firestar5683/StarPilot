import time

from opendbc.car import get_safety_config, structs
from opendbc.car.disable_ecu import disable_ecu, ecu_log
from opendbc.car.interfaces import CarInterfaceBase
from opendbc.car.isotp_parallel_query import IsoTpParallelQuery
from opendbc.car.nissan.carcontroller import CarController
from opendbc.car.nissan.carstate import CarState
from opendbc.car.nissan.values import CAR, CarControllerParams, NissanSafetyFlags, \
                                       NISSAN_DIAGNOSTIC_REQUEST_KWP, NISSAN_DIAGNOSTIC_RESPONSE_KWP, NISSAN_RX_OFFSET


LEAF_ADAS_ECU_ADDR = 0x707
LEAF_ADAS_ECU_BUS = 0
LEAF_ADAS_COMMAND_BUS = 1
LEAF_ADAS_COMMAND_ADDRS = frozenset((0x1C3, 0x2B0))
LEAF_2025_SV_PLUS_CAMERA_FW = b'6WK2CDB\x04\x18\x00\x00\x00\x00\x00R=1\x18\x99\x10\x00\x00\x00\x80'

# This Leaf camera uses KWP2000 rather than UDS for session management.
LEAF_KWP_DATA_MONITOR_REQUEST = b"\x10\xF0"
LEAF_KWP_DATA_MONITOR_RESPONSE = b"\x50\xF0"
LEAF_KWP_DISABLE_NORMAL_TX = b"\x28\x01"

LEAF_KWP_TAKEOVER_SESSIONS = (
  (LEAF_KWP_DATA_MONITOR_REQUEST, LEAF_KWP_DATA_MONITOR_RESPONSE),
)


def is_leaf_2025_sv_plus_longitudinal(candidate, car_fw):
  return candidate == CAR.NISSAN_LEAF and any(
    fw.address == LEAF_ADAS_ECU_ADDR and bytes(fw.fwVersion) == LEAF_2025_SV_PLUS_CAMERA_FW
    for fw in car_fw
  )


def leaf_adas_commands_silent(can_recv, settle_time=0.05, observe_time=0.15):
  """Confirm the stock ADAS command sender stopped while bus 1 is still observable."""
  if can_recv is None:
    return False

  try:
    # Let already-published CAN batches age out, then discard everything queued
    # before the communication-control response.
    time.sleep(settle_time)
    can_recv()

    saw_adas_bus_traffic = False
    deadline = time.monotonic() + observe_time
    while time.monotonic() < deadline:
      packets = can_recv(wait_for_one=True)
      for packet in packets:
        for msg in packet:
          if msg.src != LEAF_ADAS_COMMAND_BUS:
            continue
          saw_adas_bus_traffic = True
          if msg.address in LEAF_ADAS_COMMAND_ADDRS:
            ecu_log(f"Nissan Leaf ADAS TX still active: {hex(msg.address)} on bus {msg.src}")
            return False
  except Exception as e:
    ecu_log(f"Nissan Leaf ADAS TX silence verification exception: {e}")
    return False

  if not saw_adas_bus_traffic:
    ecu_log("Nissan Leaf ADAS TX silence could not be verified: no bus 1 traffic observed")
  return saw_adas_bus_traffic


def leaf_adas_commands_present(can_recv, settle_time=0.05, observe_time=0.15):
  """Confirm the stock ADAS command sender resumed on bus 1."""
  if can_recv is None:
    return False

  try:
    time.sleep(settle_time)
    can_recv()

    deadline = time.monotonic() + observe_time
    while time.monotonic() < deadline:
      for packet in can_recv(wait_for_one=True):
        if any(msg.src == LEAF_ADAS_COMMAND_BUS and msg.address in LEAF_ADAS_COMMAND_ADDRS for msg in packet):
          return True
  except Exception as e:
    ecu_log(f"Nissan Leaf ADAS TX recovery verification exception: {e}")
    return False

  ecu_log("Nissan Leaf ADAS normal TX recovery could not be verified")
  return False


def restore_leaf_adas_tx(can_recv, can_send):
  """Return to the confirmed KWP default session and verify normal TX resumes."""
  if can_recv is None or can_send is None:
    return False

  try:
    ecu_log("Nissan Leaf ADAS TX restore using KWP default session 1081")
    query = IsoTpParallelQuery(
      can_send, can_recv, LEAF_ADAS_ECU_BUS, [LEAF_ADAS_ECU_ADDR],
      [NISSAN_DIAGNOSTIC_REQUEST_KWP], [NISSAN_DIAGNOSTIC_RESPONSE_KWP],
      response_offset=NISSAN_RX_OFFSET,
    )
    if query.get_data(0.2) and leaf_adas_commands_present(can_recv):
      ecu_log("Nissan Leaf ADAS normal TX restored and command traffic confirmed")
      return True
  except Exception as e:
    ecu_log(f"Nissan Leaf ADAS TX restore exception: {e}")

  ecu_log("Nissan Leaf ADAS normal TX restore was not confirmed")
  return False


class CarInterface(CarInterfaceBase):
  CarState = CarState
  CarController = CarController

  @staticmethod
  def get_pid_accel_limits(CP, current_speed, cruise_speed):
    if CP.carFingerprint == CAR.NISSAN_LEAF and CP.openpilotLongitudinalControl:
      return CarControllerParams.ACCEL_MIN, CarControllerParams.ACCEL_MAX
    return CarInterfaceBase.get_pid_accel_limits(CP, current_speed, cruise_speed)

  @staticmethod
  def _get_params(ret: structs.CarParams, candidate, fingerprint, car_fw, alpha_long, is_release, docs) -> structs.CarParams:
    ret.brand = "nissan"
    ret.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.nissan)]
    ret.autoResumeSng = False

    ret.steerLimitTimer = 1.0

    ret.steerActuatorDelay = 0.1

    ret.steerControlType = structs.CarParams.SteerControlType.angle
    ret.radarUnavailable = True

    ret.alphaLongitudinalAvailable = is_leaf_2025_sv_plus_longitudinal(candidate, car_fw)
    ret.openpilotLongitudinalControl = alpha_long and ret.alphaLongitudinalAvailable
    ret.pcmCruise = not ret.openpilotLongitudinalControl

    if ret.openpilotLongitudinalControl:
      ret.safetyConfigs[0].safetyParam |= NissanSafetyFlags.LONG_CONTROL.value
      ret.autoResumeSng = True
      ret.stopAccel = -2.0
      ret.vEgoStopping = 0.5
      ret.vEgoStarting = 0.5
      ret.stoppingDecelRate = 0.8

    if candidate == CAR.NISSAN_ALTIMA:
      # Altima has EPS on C-CAN unlike the others that have it on V-CAN
      ret.safetyConfigs[0].safetyParam |= NissanSafetyFlags.ALT_EPS_BUS.value

    return ret

  @staticmethod
  def init(CP, can_recv, can_send):
    if not (CP.openpilotLongitudinalControl and CP.alphaLongitudinalAvailable and CP.carFingerprint == CAR.NISSAN_LEAF):
      return

    from openpilot.common.params import Params
    params = Params()
    ecu_disabled = False
    for diag_request, diag_response in LEAF_KWP_TAKEOVER_SESSIONS:
      ecu_log(f"Nissan Leaf ADAS takeover using KWP session {diag_request.hex()}")
      ecu_disabled = disable_ecu(can_recv, can_send, bus=LEAF_ADAS_ECU_BUS, addr=LEAF_ADAS_ECU_ADDR,
                                 com_cont_req=LEAF_KWP_DISABLE_NORMAL_TX, require_response=True, retry=1,
                                 diag_request=diag_request, diag_response=diag_response, response_offset=NISSAN_RX_OFFSET)
      if ecu_disabled:
        break

    takeover_confirmed = ecu_disabled and leaf_adas_commands_silent(can_recv)
    params.put_bool("EcuDisableFailed", not takeover_confirmed)
    if takeover_confirmed:
      ecu_log("Nissan Leaf ADAS TX disable and command silence confirmed; experimental longitudinal control enabled")
    else:
      # A response can be lost after the ECU accepts 0x28. Always attempt to
      # restore stock transmission before falling back to stock longitudinal.
      restore_leaf_adas_tx(can_recv, can_send)
      CP.safetyConfigs[-1].safetyParam &= ~NissanSafetyFlags.LONG_CONTROL.value
      CP.openpilotLongitudinalControl = False
      CP.pcmCruise = True
      ecu_log("Nissan Leaf ADAS takeover was not confirmed; falling back to stock longitudinal control")

  @staticmethod
  def deinit(CP, can_recv, can_send):
    if not (CP.openpilotLongitudinalControl and CP.alphaLongitudinalAvailable and CP.carFingerprint == CAR.NISSAN_LEAF):
      return

    restore_leaf_adas_tx(can_recv, can_send)
