"""Short-lived controller requests; Card owns the software cruise speed."""

import re
import secrets

from openpilot.cereal import messaging
from opendbc.car.structs import car
from openpilot.starpilot.conditional_mode.ui_action import fresh_service

LIFETIME_NS = 250_000_000
SESSION = re.compile(r"[0-9a-f]{32}\Z")


def eligible(cp) -> bool:
  return bool(cp is not None and not cp.pcmCruise and cp.openpilotLongitudinalControl and
              not cp.passive and not cp.dashcamOnly and not cp.notCar)


def ui_authority(sm, cp, now_ns: int) -> bool:
  try:
    drive = int(sm["deviceState"].startedMonoTime)
    return bool(eligible(cp) and sm["deviceState"].started and
                fresh_service(sm, "deviceState", drive, now_ns, 1_000_000_000) and
                all(fresh_service(sm, name, drive, now_ns) for name in ("carState", "carControl", "selfdriveState")) and
                sm["carState"].canValid and not sm["carState"].canTimeout and
                sm["carControl"].enabled and sm["selfdriveState"].enabled)
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return False


class CruiseActionPublisher:
  def __init__(self):
    self.session = secrets.token_hex(16)
    self.sequence = 0

  def dispatch(self, increase: bool, sm, cp, publisher, *, now_ns: int) -> bool:
    if not ui_authority(sm, cp, now_ns):
      return False
    self.sequence += 1
    msg = messaging.new_message("slcAction", valid=True)
    msg.logMonoTime = now_ns
    msg.slcAction.kind = "cruiseIncrease" if increase else "cruiseDecrease"
    msg.slcAction.controllerCruise = {
      "version": 1, "sessionId": self.session, "sequence": self.sequence,
      "observedMonoTime": now_ns, "validUntilMonoTime": now_ns + LIFETIME_NS,
      "driveStartMonoTime": int(sm["deviceState"].startedMonoTime),
      "carFingerprint": cp.carFingerprint, "sourceCarControlMonoTime": int(sm.logMonoTime["carControl"]),
    }
    publisher.send("slcAction", msg)
    return True


class CruiseActionConsumer:
  def __init__(self):
    self.sequences = {}
    self.drive = 0
    self.last_apply_ns = 0

  def apply(self, msg, cp, cs, sm, helper, *, now_ns: int, is_metric: bool, enabled: bool) -> bool:
    try:
      kind = str(msg.slcAction.kind)
      if kind not in ("cruiseIncrease", "cruiseDecrease") or not msg.valid:
        return False
      request = msg.slcAction.controllerCruise
      drive = int(sm["deviceState"].startedMonoTime)
      if drive != self.drive:
        self.sequences.clear()
        self.drive = drive
        self.last_apply_ns = 0
      session, sequence = str(request.sessionId), int(request.sequence)
      observed, expires = int(request.observedMonoTime), int(request.validUntilMonoTime)
      source = int(request.sourceCarControlMonoTime)
      if not (eligible(cp) and enabled and not cs.buttonEvents and now_ns - self.last_apply_ns >= 100_000_000 and
              cs.canValid and not cs.canTimeout and cs.cruiseState.available and
              sm["deviceState"].started and fresh_service(sm, "deviceState", drive, now_ns, 1_000_000_000) and
              fresh_service(sm, "carControl", drive, now_ns) and sm["carControl"].enabled and
              int(request.version) == 1 and int(request.driveStartMonoTime) == drive and
              str(request.carFingerprint) == cp.carFingerprint and SESSION.fullmatch(session) and
              sequence > self.sequences.get(session, 0) and drive < observed <= now_ns <= expires and
              expires - observed <= LIFETIME_NS and int(msg.logMonoTime) == observed and
              drive < source <= int(sm.logMonoTime["carControl"]) <= now_ns and now_ns - source <= LIFETIME_NS):
        return False
      if len(self.sequences) >= 8 and session not in self.sequences:
        return False
      self.sequences[session] = sequence
      self.last_apply_ns = now_ns
      button = car.CarState.ButtonEvent.Type.accelCruise if kind == "cruiseIncrease" else car.CarState.ButtonEvent.Type.decelCruise
      return helper.adjust_v_cruise(button, cs, is_metric)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      return False
