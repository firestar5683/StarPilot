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

  def active(self, sm, cp, cs, *, enabled, car_ns, car_valid, now_ns):
    if not enabled or not cp.openpilotLongitudinalControl or cp.passive or cp.dashcamOnly or cp.notCar:
      self.drive_id = 0
      self.released = False
      self.resume.reset()
      return False
    try:
      device = sm['deviceState']
      drive_id = int(device.startedMonoTime)
      names = ('deviceState', 'modelV2', 'longitudinalPlan', 'carControl')
      if (not device.started or not 0 < drive_id < car_ns <= now_ns or
          not car_valid or not cs.canValid or cs.canTimeout or now_ns - car_ns > MAX_AGE_NS):
        return False
      for name in names:
        stamp, received = int(sm.logMonoTime[name]), int(sm.recv_time[name] * 1e9)
        max_age = max(MAX_AGE_NS, int(2.5e9 / SERVICE_LIST[name].frequency))
        if (not sm.seen[name] or not sm.valid[name] or not sm.alive[name] or
            not drive_id < stamp <= received <= now_ns or now_ns - stamp > max_age):
          return False
      if drive_id != self.drive_id:
        self.drive_id, self.released = drive_id, False
      self.resume.observe(SimpleNamespace(logMonoTime=car_ns, valid=car_valid, carState=cs), now_ns=now_ns, drive_id=drive_id)
      resume = self.resume.consume(now_ns=now_ns, drive_id=drive_id, car_ns=car_ns)
      plan = sm['longitudinalPlan']
      if not plan.forceStopHolding:
        self.released = False
        return False
      if cs.gasPressed or resume:
        self.released = True
      # A newer model can arrive before its plan. Keep the still-fresh hold
      # through that normal handoff without accepting future or old-drive data.
      model_ns = int(plan.modelMonoTime)
      if (not drive_id < model_ns <= sm.logMonoTime['modelV2'] or now_ns - model_ns > MAX_AGE_NS or
          not plan.shouldStop or not sm['carControl'].longActive):
        return False
      return bool(not self.released and cs.standstill and not cs.brakePressed)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      return False
