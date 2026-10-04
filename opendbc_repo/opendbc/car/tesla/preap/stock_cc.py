from opendbc.car.tesla.preap.buttons import CruiseButtons
from opendbc.car import structs

GearShifter = structs.CarState.GearShifter

_PHASE_IDLE = 0
_PHASE_ENGAGING = 1
CANCEL_DELAY_FRAMES = 10
CC_ENGAGE_TIMEOUT_FRAMES = 50


class StockCCSpoofer:
  def __init__(self):
    self.cc_engage_phase = _PHASE_IDLE
    self.cc_engage_start_frame = 0
    self.cancel_pending = False
    self.cancel_frame = -1_000_000
    self.prev_di_cc_engaged = False
    self.pcc_event = None

  def update(self, CS, frame: int, tesla_can, can_bus_party: int):
    can_sends = []
    safe = bool(CS.out.canValid and not CS.out.canTimeout and not CS.out.brakePressed and
                not CS.out.doorOpen and not CS.out.seatbeltUnlatched and
                CS.out.gearShifter == GearShifter.drive and not CS.out.steerFaultPermanent and
                not CS.out.steeringDisengage and not CS.out.steerFaultTemporary)
    if not safe:
      self.cc_engage_phase = _PHASE_IDLE
      CS.preap_cc_engage_needed = False
    source_current = bool(CS.out.canValid and not CS.out.canTimeout and CS.msg_stw_actn_req and
                          0 <= CS.can_now_ns - CS.physical_stw_stamp_ns <= 300_000_000)

    if getattr(CS, "preap_cc_cancel_needed", False):
      self.cancel_pending = True
      self.cancel_frame = frame
      self.cc_engage_phase = _PHASE_IDLE
      CS.preap_cc_cancel_needed = False

    if safe and getattr(CS, "preap_cc_engage_needed", False) and self.cc_engage_phase == _PHASE_IDLE:
      self.cc_engage_phase = _PHASE_ENGAGING
      self.cc_engage_start_frame = frame
      CS.preap_cc_engage_needed = False

    if not source_current:
      self.cancel_pending = False
      self.cc_engage_phase = _PHASE_IDLE
    if source_current and self.cancel_pending and (frame - self.cancel_frame) >= CANCEL_DELAY_FRAMES and frame % 10 == 0:
      sent = self._send(CS, tesla_can, can_bus_party, CruiseButtons.CANCEL)
      if sent is not None:
        can_sends.append(sent)
        self.cancel_pending = False
    elif safe and source_current and self.cc_engage_phase == _PHASE_ENGAGING and frame % 10 == 0:
      if (frame - self.cc_engage_start_frame) >= CC_ENGAGE_TIMEOUT_FRAMES or getattr(CS, "di_cruise_state", "OFF") == "ENABLED":
        self.cc_engage_phase = _PHASE_IDLE
      else:
        sent = self._send(CS, tesla_can, can_bus_party, CruiseButtons.SET_ACCEL)
        if sent is not None:
          can_sends.append(sent)

    di_cc_engaged = getattr(CS, "di_cruise_state", "OFF") == "ENABLED"
    if di_cc_engaged and not self.prev_di_cc_engaged:
      self.pcc_event = "teslaCCEngaged"
    elif not di_cc_engaged and self.prev_di_cc_engaged:
      self.pcc_event = "teslaCCDisengaged"
    else:
      self.pcc_event = None
    self.prev_di_cc_engaged = di_cc_engaged

    return can_sends

  @staticmethod
  def _send(CS, tesla_can, can_bus_party: int, button: int):
    msg_stw = getattr(CS, "msg_stw_actn_req", None)
    if msg_stw is None:
      return None
    counter = (int(msg_stw.get("MC_STW_ACTN_RQ", 0)) + 1) % 16
    return tesla_can.create_action_request(button, can_bus_party, counter, msg_stw)
