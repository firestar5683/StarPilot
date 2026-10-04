import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CoastPlan:
  force_decel: bool = False
  brake_floor: float | None = None
  speed_ceiling_mps: float | None = None
  pulse_coasting: bool = False


class CoastOwner:
  def __init__(self):
    self.force_coast = False
    self.pulse_glide = False
    self.coasting = False
    self.hill_paused = False

  def reset(self):
    self.__init__()

  def toggle(self, action, *, long_active):
    if action == 2:
      self.force_coast = not self.force_coast
      return True
    if action == 14 and (long_active or self.pulse_glide):
      self.pulse_glide = not self.pulse_glide
      return True
    return False

  def sample(self, *, admitted, active, gas, brake, speed_mps, target_mps, delta_mps, pitch,
             lead_relevant, stop_context):
    values = (speed_mps, target_mps, delta_mps)
    if (not admitted or not all(type(value) in (int, float) and math.isfinite(value) for value in values) or
        speed_mps < 0 or delta_mps < 0 or type(active) is not bool or type(gas) is not bool or
        type(brake) is not bool or type(lead_relevant) is not bool or type(stop_context) is not bool):
      self.reset()
      return CoastPlan()
    self.force_coast &= not (gas or brake)
    if not active:
      return CoastPlan()
    ceiling = None
    if not self.pulse_glide:
      self.coasting = False
      self.hill_paused = False
    else:
      if type(pitch) in (int, float) and math.isfinite(pitch):
        if self.hill_paused:
          if abs(pitch) <= math.radians(2.5):
            self.hill_paused = False
        elif abs(pitch) >= math.radians(3.0):
          self.hill_paused = True
      lower = target_mps - delta_mps
      if (self.hill_paused or target_mps <= 5.0 or lower < 3.0 or delta_mps <= 0 or
          lead_relevant or stop_context):
        self.coasting = False
      elif self.coasting:
        if speed_mps <= lower + 0.25:
          self.coasting = False
      elif speed_mps >= target_mps - 0.25:
        self.coasting = True
      if self.coasting:
        ceiling = lower
    return CoastPlan(self.force_coast, -0.6 if self.force_coast else -0.03 if self.coasting else None,
                     ceiling, self.coasting)


class CoastRuntime:
  def __init__(self):
    from openpilot.starpilot.controllers.wheel_actions import WheelConsumer
    self.consumer = WheelConsumer()
    self.owner = CoastOwner()
    self.session = None
    self.drive = 0
    self.traffic_toggles = 0
    self.cp_signature = None
    self.conditional_stop = False

  def receive(self, event, params, cp, sm, *, now_ns):
    command = self.consumer.accept(event, params, cp, sm, now_ns=now_ns)
    if command is None:
      return False
    if command.session != self.session or command.drive_id != self.drive:
      self.owner.reset()
      self.session, self.drive = command.session, command.drive_id
    from openpilot.starpilot.controllers.wheel_actions import cp_fingerprint
    self.cp_signature = cp_fingerprint(cp)
    if command.action in (2, 6, 14):
      from openpilot.starpilot.conditional_mode.ui_action import current_authority
      from openpilot.starpilot.saved_source import read_saved
      active_required = command.action == 6 or command.action == 14 and not self.owner.pulse_glide
      if (not cp.openpilotLongitudinalControl or
          read_saved(params, "SafeMode", 8) not in ((None, True), (b"0", True)) or
          active_required and not current_authority(sm, cp, command.drive_id, now_ns)):
        return False
      if command.action == 6:
        self.traffic_toggles += 1
        return True
      return self.owner.toggle(command.action, long_active=bool(sm["carControl"].longActive))
    return False

  def sample(self, params, cp, sm, *, now_ns, target_mps, lead_relevant, stop_context):
    from openpilot.starpilot.controllers.wheel_actions import eligible, LIFETIME_NS, cp_fingerprint
    from openpilot.starpilot.conditional_mode.ui_action import fresh_service
    from openpilot.starpilot.saved_source import read_saved
    drive = int(sm["deviceState"].startedMonoTime)
    raw, readable = read_saved(params, "PulseGlideSpeedDelta", 32)
    units, unit_readable = read_saved(params, "IsMetric", 8)
    try:
      delta = 5.0 if raw is None else float(raw)
    except (ValueError, TypeError, OverflowError):
      delta = math.nan
    admitted = bool(eligible(cp) and self.cp_signature == cp_fingerprint(cp) and cp.openpilotLongitudinalControl and sm["deviceState"].started and
                    drive == self.drive and 0 < drive < self.consumer.last_heartbeat <= now_ns and
                    now_ns - self.consumer.last_heartbeat <= LIFETIME_NS and
                    all(fresh_service(sm, name, drive, now_ns) for name in ("carState", "carControl")) and
                    sm["carState"].canValid and not sm["carState"].canTimeout and
                    read_saved(params, "SafeMode", 8) in ((None, True), (b"0", True)) and
                    readable and unit_readable and units in (None, b"0", b"1") and
                    math.isfinite(delta) and 0.5 <= delta <= 30.0)
    state, control = sm["carState"], sm["carControl"]
    pitch = control.orientationNED[1] if len(control.orientationNED) == 3 else None
    return self.owner.sample(admitted=admitted, active=bool(control.enabled and control.longActive),
                             gas=bool(state.gasPressed), brake=bool(state.brakePressed), speed_mps=float(state.vEgo),
                             target_mps=target_mps, delta_mps=delta * (1 / 3.6 if units == b"1" else 0.44704),
                             pitch=pitch, lead_relevant=lead_relevant, stop_context=bool(stop_context or self.conditional_stop))
