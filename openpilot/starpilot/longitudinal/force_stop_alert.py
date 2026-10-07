"""Fresh Force Stop hold presentation; physical release suppresses stale hold copy."""
from types import SimpleNamespace

from openpilot.cereal.services import SERVICE_LIST
from openpilot.starpilot.longitudinal.stop_resume import StopResume

MAX_AGE_NS = 150_000_000
EVENT_TYPE = 'forceStopHold'


class HoldAlertState:
  def __init__(self):
    self.drive_id = 0
    self.released = False
    self.resume = StopResume()
    self.pair = None

  def active(self, sm, cp, cs, *, enabled, car_ns, car_valid, now_ns):
    if not enabled or not cp.openpilotLongitudinalControl or cp.passive or cp.dashcamOnly or cp.notCar:
      self.drive_id = 0
      self.released = False
      self.resume.reset()
      self.pair = None
      return False
    try:
      device = sm['deviceState']
      drive_id = int(device.startedMonoTime)
      names = ('deviceState', 'modelV2', 'longitudinalPlan', 'starpilotLongitudinalPlan', 'carControl')
      if (not device.started or not 0 < drive_id < car_ns <= now_ns or
          not car_valid or not cs.canValid or cs.canTimeout or now_ns - car_ns > MAX_AGE_NS):
        return False
      if drive_id != self.drive_id:
        self.drive_id, self.released = drive_id, False
        self.pair = None
        self.resume.reset()
      self.resume.observe(SimpleNamespace(logMonoTime=car_ns, valid=car_valid, carState=cs), now_ns=now_ns, drive_id=drive_id)
      resume = self.resume.consume(now_ns=now_ns, drive_id=drive_id, car_ns=car_ns)
      if cs.gasPressed or resume:
        self.released = True
      for name in names:
        stamp, received = int(sm.logMonoTime[name]), int(sm.recv_time[name] * 1e9)
        max_age = max(MAX_AGE_NS, int(2.5e9 / SERVICE_LIST[name].frequency))
        if (not sm.seen[name] or not sm.valid[name] or not sm.alive[name] or
            not drive_id < stamp <= received <= now_ns or now_ns - stamp > max_age):
          return False
      plan = sm['longitudinalPlan']
      hold = sm['starpilotLongitudinalPlan']
      source_ns, model_ns = int(hold.sourcePlanMonoTime), int(hold.modelMonoTime)
      if (hold.version != 1 or hold.driveStartMonoTime != drive_id or
          not drive_id < model_ns <= source_ns <= sm.logMonoTime['starpilotLongitudinalPlan'] or
          model_ns > sm.logMonoTime['modelV2'] or now_ns - model_ns > MAX_AGE_NS):
        return False
      plan_ns = int(sm.logMonoTime['longitudinalPlan'])
      if source_ns == plan_ns:
        if model_ns != plan.modelMonoTime:
          return False
        self.pair = (source_ns, model_ns, bool(hold.forceStopHolding))
      # Retain only the last matched, still-fresh pair during staggered delivery.
      if self.pair is None or now_ns - self.pair[0] > MAX_AGE_NS or now_ns - self.pair[1] > MAX_AGE_NS:
        return False
      if not self.pair[2]:
        self.released = False
        return False
      if not plan.shouldStop or not sm['carControl'].longActive:
        return False
      return bool(not self.released and cs.standstill and not cs.brakePressed)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      return False
