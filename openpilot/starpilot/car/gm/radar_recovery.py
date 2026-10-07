"""Drive-local notification from the GM radar's explicit health reports."""

KEY = "RadarRecoveryAlert"
RECOVERY_NS = 2_000_000_000
MAX_UPDATE_GAP_NS = 200_000_000
NOTIFICATION_NS = 3_000_000_000
ALERT_TYPE = "voltRadarRecovery/notification"
EVENT_TYPE = "radarRecoveryNotification"


def capability(cp) -> tuple | None:
  from opendbc.car import Bus
  from opendbc.car.gm.values import CAR, DBC
  from opendbc.car.structs import CarParams

  try:
    volts = (CAR.CHEVROLET_VOLT, CAR.CHEVROLET_VOLT_ASCM, CAR.CHEVROLET_VOLT_2019,
             CAR.CHEVROLET_VOLT_CAMERA, CAR.CHEVROLET_VOLT_CC)
    if (cp.brand != "gm" or cp.carFingerprint not in volts or cp.radarUnavailable or
        cp.notCar or cp.passive or cp.dashcamOnly or len(cp.safetyConfigs) != 1 or
        cp.safetyConfigs[0].safetyModel != CarParams.SafetyModel.gm or
        DBC[cp.carFingerprint].get(Bus.radar) != "gm_global_a_object"):
      return None
    return (str(cp.carFingerprint), cp.carVin, int(cp.flags), int(cp.alternativeExperience),
            int(cp.safetyConfigs[0].safetyParam), bool(cp.openpilotLongitudinalControl), bool(cp.pcmCruise))
  except (AttributeError, IndexError, KeyError, TypeError, ValueError):
    return None


class RecoveryMonitor:
  def __init__(self):
    self.reset()

  def reset(self):
    self.context = None
    self.after_ns = 0
    self.last_update_ns = 0
    self.last_now_ns = 0
    self.fault_seen = False
    self.healthy_since_ns = None
    self.notification_until_ns = 0

  def interrupt(self):
    self.healthy_since_ns = None
    self.notification_until_ns = 0

  def update(self, cp, *, enabled: bool, drive_id: int, now_ns: int, stamp_ns: int,
             updated: bool, alive: bool, valid: bool, errors: dict | None) -> bool:
    binding = capability(cp)
    if not enabled or binding is None or drive_id <= 0:
      self.reset()
      return False
    context = (binding, drive_id)
    if context != self.context or now_ns < self.last_now_ns:
      self.reset()
      self.context, self.after_ns = context, now_ns
    self.last_now_ns = now_ns
    fresh = alive and self.after_ns < stamp_ns <= now_ns <= stamp_ns + MAX_UPDATE_GAP_NS
    if not fresh:
      self.interrupt()
      return False
    if not updated:
      return False
    if stamp_ns <= self.last_update_ns:
      self.interrupt()
      return False
    if self.last_update_ns and stamp_ns - self.last_update_ns > MAX_UPDATE_GAP_NS:
      self.interrupt()
    self.last_update_ns = stamp_ns
    if (not isinstance(errors, dict) or not {"canError", "radarFault", "radarUnavailableTemporary"} <= errors.keys() or
        any(type(value) is not bool for value in errors.values())):
      self.interrupt()
      return False
    # Card marks a genuine radar-fault report invalid; CAN loss alone is not a radar fault.
    fault = not errors["canError"] and (errors["radarFault"] or errors["radarUnavailableTemporary"])
    if fault:
      self.fault_seen = True
    if not valid or any(errors.values()):
      self.interrupt()
      return False
    if not self.fault_seen:
      return False
    if self.healthy_since_ns is None:
      self.healthy_since_ns = stamp_ns
    if stamp_ns - self.healthy_since_ns < RECOVERY_NS:
      return False
    self.fault_seen = False
    self.healthy_since_ns = None
    self.notification_until_ns = now_ns + NOTIFICATION_NS
    return True

  def visible(self, now_ns: int) -> bool:
    return now_ns < self.notification_until_ns


class RecoveryNotification:
  def __init__(self):
    self.monitor = RecoveryMonitor()
    self.alert = None
    self.sound_presented = False

  def update(self, cp, sm, *, enabled: bool, now_ns: int):
    ready = False
    try:
      drive = int(sm["deviceState"].startedMonoTime) if sm["deviceState"].started and sm.all_checks(["deviceState"]) else 0
      errors = sm["radarTracks"].errors.to_dict()
      ready = self.monitor.update(cp, enabled=enabled, drive_id=drive, now_ns=now_ns,
                                  stamp_ns=int(sm.logMonoTime["radarTracks"]), updated=sm.updated["radarTracks"],
                                  alive=sm.seen["radarTracks"] and sm.alive["radarTracks"],
                                  valid=sm.valid["radarTracks"], errors=errors)
    except (AttributeError, KeyError, TypeError, ValueError):
      self.monitor.reset()
    if ready:
      from openpilot.selfdrive.selfdrived.events import Alert, AlertSize, AlertStatus, AudibleAlert, Priority, VisualAlert
      self.alert = Alert("Radar available again", "", AlertStatus.normal, AlertSize.small,
                         Priority.LOWEST, VisualAlert.none, AudibleAlert.prompt, 3.)
      self.alert.alert_type, self.alert.event_type = ALERT_TYPE, EVENT_TYPE
      self.sound_presented = False
      return self.alert
    if not self.monitor.visible(now_ns):
      self.alert = None
      self.sound_presented = False
    return None

  def selected(self, current):
    if current.alert_type == ALERT_TYPE:
      self.sound_presented = True
    elif self.sound_presented and self.alert is not None:
      from openpilot.selfdrive.selfdrived.events import AudibleAlert
      self.alert.audible_alert = AudibleAlert.none
