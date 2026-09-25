"""Bounded, read-only live control plots for the local Galaxy session.

The worker owns its IPC sockets. No subscription exists until an authenticated
request arrives, and the worker leaves after six seconds without a viewer.
"""

import math
import secrets
import threading
import time
from dataclasses import dataclass


SAMPLE_INTERVAL_S = 0.75
CLIENT_IDLE_S = 6.0
STALE_AFTER_S = 1.5
SOURCE_MAX_AGE_S = 1.5
BOOT_STABILIZATION_S = 45.0
CLOCK_PAIR_MAX_SKEW_NS = 5_000_000
SERVICES = ('controlsState', 'deviceMotion', 'selfdriveState', 'longitudinalPlan', 'carControl', 'carState')


@dataclass(frozen=True)
class PlotReading:
  values: dict
  source_age_seconds: float | None
  signature: tuple[int, ...]


def boot_stabilizing():
  boottime = getattr(time, 'CLOCK_BOOTTIME', None)
  if boottime is None:
    return False
  try:
    return time.clock_gettime(boottime) < BOOT_STABILIZATION_S
  except OSError:
    return False


def paired_boot_offset_ns():
  """Detect suspend without comparing producer MONOTONIC stamps to BOOTTIME."""
  boottime = getattr(time, 'CLOCK_BOOTTIME', None)
  if boottime is None:
    return None
  try:
    before = time.monotonic_ns()
    boot = time.clock_gettime_ns(boottime)
    after = time.monotonic_ns()
  except OSError:
    return None
  if after - before > CLOCK_PAIR_MAX_SKEW_NS:
    return None
  return boot - (before + after) // 2


def finite(value):
  try:
    number = float(value)
  except (TypeError, ValueError, OverflowError):
    return None
  return round(number, 4) if math.isfinite(number) else None


def _field(source, name):
  try:
    return getattr(source, name)
  except (AttributeError, ValueError, RuntimeError):
    return None


def _measurement(source, name):
  value = _field(source, name)
  return finite(_field(value, 'x')) if _field(value, 'valid') is True else None


def extract(
  controls,
  pose,
  *,
  controls_fresh: bool,
  pose_fresh: bool,
  controls_valid: bool,
  pose_valid: bool,
  state=None,
  state_fresh: bool = False,
  plan=None,
  plan_fresh: bool = False,
  car_control=None,
  car_control_fresh: bool = False,
  car_state=None,
  car_state_fresh: bool = False,
):
  """Project a fixed allowlist; absent/invalid input stays null, never zero."""
  result = {
    'desiredLateralAccel': None,
    'actualLateralAccel': None,
    'desiredLongitudinalAccel': None,
    'actualLongitudinalAccel': None,
    'lateralP': None,
    'lateralI': None,
    'lateralD': None,
    'lateralF': None,
    'longitudinalP': None,
    'longitudinalI': None,
    'longitudinalF': None,
    'speedMps': None,
    'controlsActive': None,
    'lateralControlActive': None,
    'longitudinalControlActive': None,
    'lateralSource': 'unavailable',
    'longitudinalSource': 'unavailable',
    'lateralTermsSource': 'unavailable',
    'longitudinalTermsSource': 'unavailable',
    'poseFresh': bool(pose_fresh and pose_valid),
    'controlsFresh': bool(controls_fresh and controls_valid and state_fresh),
    'speedSource': 'unavailable',
  }
  if not controls_fresh or not controls_valid or not state_fresh:
    return result

  result['controlsActive'] = bool(_field(state, 'active'))
  result['lateralControlActive'] = bool(_field(car_control, 'latActive')) if car_control_fresh else False
  result['longitudinalControlActive'] = bool(_field(car_control, 'longActive')) if car_control_fresh else False
  speed = _measurement(pose, 'velocityDevice') if pose_fresh and pose_valid else None
  if speed is not None:
    result['speedSource'] = 'deviceMotion'
  elif car_state_fresh:
    speed = finite(_field(car_state, 'vEgo'))
    if speed is not None:
      result['speedSource'] = 'carState'
  result['speedMps'] = abs(speed) if speed is not None else None

  lateral = _field(controls, 'lateralControlState')
  try:
    kind = lateral.which()
  except (AttributeError, ValueError, RuntimeError):
    kind = None
  if kind == 'torqueState':
    torque = _field(lateral, 'torqueState')
    for output, field in (('lateralP', 'p'), ('lateralI', 'i'), ('lateralD', 'd'), ('lateralF', 'f')):
      result[output] = finite(_field(torque, field))
    result['lateralTermsSource'] = 'torqueState'
    desired = finite(_field(torque, 'desiredLateralAccel'))
    actual = finite(_field(torque, 'actualLateralAccel'))
    if desired is not None and actual is not None:
      result['desiredLateralAccel'], result['actualLateralAccel'] = desired, actual
      result['lateralSource'] = 'torqueState'
  elif kind == 'pidState':
    pid = _field(lateral, 'pidState')
    for output, field in (('lateralP', 'p'), ('lateralI', 'i'), ('lateralF', 'f')):
      result[output] = finite(_field(pid, field))
    result['lateralTermsSource'] = 'pidState'
  if result['lateralSource'] == 'unavailable' and speed is not None:
    desired = finite(_field(controls, 'desiredCurvature'))
    actual = finite(_field(controls, 'curvature'))
    if desired is not None and actual is not None:
      result['desiredLateralAccel'] = finite(desired * speed * speed)
      result['actualLateralAccel'] = finite(actual * speed * speed)
      result['lateralSource'] = 'curvature' if result['desiredLateralAccel'] is not None and result['actualLateralAccel'] is not None else 'unavailable'

  result['desiredLongitudinalAccel'] = finite(_field(plan, 'aTarget')) if plan_fresh else None
  if result['desiredLongitudinalAccel'] is not None:
    result['longitudinalSource'] = 'aTarget'
  for output, field in (('longitudinalP', 'upAccelCmd'), ('longitudinalI', 'uiAccelCmd'), ('longitudinalF', 'ufAccelCmd')):
    result[output] = finite(_field(controls, field))
  p, i, f = result['longitudinalP'], result['longitudinalI'], result['longitudinalF']
  if isinstance(p, float) and isinstance(i, float) and isinstance(f, float):
    result['longitudinalTermsSource'] = 'controlsState'
    pid_sum = finite(p + i + f)
    if result['desiredLongitudinalAccel'] is None and pid_sum not in (None, 0):
      result['desiredLongitudinalAccel'] = pid_sum
      result['longitudinalSource'] = 'pidSum'
  if pose_fresh and pose_valid:
    result['actualLongitudinalAccel'] = _measurement(pose, 'accelerationDevice')
  return result


class MessagingPlotsReader:
  def __init__(self):
    from openpilot.cereal import messaging

    self.started_ns = time.monotonic_ns()
    self.boot_offset_ns = paired_boot_offset_ns()
    self.sm = messaging.SubMaster(list(SERVICES), poll='controlsState')

  def sample(self, now: float):
    sm = self.sm
    if sm is None:
      raise OSError('Plot reader closed')
    sm.update(0)
    now = time.monotonic()
    current_offset = paired_boot_offset_ns()
    clock_ok = True
    if getattr(time, 'CLOCK_BOOTTIME', None) is not None:
      if current_offset is None:
        clock_ok = False
      elif self.boot_offset_ns is None or abs(current_offset - self.boot_offset_ns) > CLOCK_PAIR_MAX_SKEW_NS:
        # An old queued message can look MONOTONIC-fresh just after resume.
        self.started_ns = time.monotonic_ns()
        self.boot_offset_ns = current_offset
        clock_ok = False
    ages = {}

    def fresh(key):
      event_ns = sm.logMonoTime[key]
      event_age = now - event_ns / 1e9
      receipt_age = now - sm.recv_time[key]
      accepted = bool(
        clock_ok
        and sm.valid[key]
        and sm.seen[key]
        and sm.recv_time[key] > 0
        and event_ns > self.started_ns
        and 0 <= receipt_age <= SOURCE_MAX_AGE_S
        and 0 <= event_age <= SOURCE_MAX_AGE_S
      )
      if accepted:
        ages[key] = max(event_age, receipt_age)
      return accepted

    controls_fresh = fresh('controlsState')
    state_fresh = fresh('selfdriveState')
    pose_fresh = fresh('deviceMotion')
    plan_fresh = fresh('longitudinalPlan')
    car_control_fresh = fresh('carControl')
    car_state_fresh = fresh('carState')
    values = extract(
      sm['controlsState'],
      sm['deviceMotion'],
      controls_fresh=controls_fresh,
      pose_fresh=pose_fresh,
      controls_valid=bool(sm.valid['controlsState']),
      pose_valid=bool(sm.valid['deviceMotion']),
      state=sm['selfdriveState'],
      state_fresh=state_fresh,
      plan=sm['longitudinalPlan'],
      plan_fresh=plan_fresh,
      car_control=sm['carControl'],
      car_control_fresh=car_control_fresh,
      car_state=sm['carState'],
      car_state_fresh=car_state_fresh,
    )
    source_age = max(ages.values()) if controls_fresh and state_fresh else None
    signature = tuple(sm.logMonoTime[key] if key in ages else 0 for key in SERVICES)
    return PlotReading(values, source_age, signature)

  def close(self):
    # SubMaster/IPC sockets are released by their Python owners; SubSocket has
    # no public close method in this runtime.
    self.sm = None


class Plots:
  def __init__(self, reader_factory=MessagingPlotsReader, clock=time.monotonic):
    self.reader_factory = reader_factory
    self.session_id = secrets.token_hex(8)
    self.clock = clock
    self.lock = threading.Lock()
    self.stop_event = threading.Event()
    self.worker = None
    self.last_request = 0.0
    self.last_sample = 0.0
    self.source_age_seconds = None
    self.signature = None
    self.index = 0
    self.values = None
    self.error = ''
    self.closed = False

  def snapshot(self):
    now = self.clock()
    with self.lock:
      if self.closed:
        raise OSError('Plots closed')
      self.last_request = now
      if self.worker is None or not self.worker.is_alive():
        self.stop_event.clear()
        self.worker = threading.Thread(target=self._run, daemon=True, name='galaxy-plots')
        self.worker.start()
      age = max(0.0, now - self.last_sample) + self.source_age_seconds if self.last_sample and self.source_age_seconds is not None else None
      stale = age is None or age > STALE_AFTER_S or self.values is None or not self.values.get('controlsFresh')
      return {
        'schemaVersion': 1,
        'state': 'unavailable' if self.error and stale else 'stale' if stale else 'current',
        'sessionId': self.session_id,
        'sampleIndex': self.index,
        'sampleAgeSeconds': math.ceil(age * 1000) / 1000 if age is not None else None,
        'values': None if stale else dict(self.values),
        'error': self.error if stale else '',
        'bootStabilizing': boot_stabilizing() and bool(self.values and self.values.get('controlsFresh')),
      }

  def _run(self):
    reader = None
    try:
      reader = self.reader_factory()
      while not self.stop_event.is_set():
        with self.lock:
          if self.clock() - self.last_request >= CLIENT_IDLE_S:
            break
        try:
          sample_started = self.clock()
          reading = reader.sample(self.clock())
          with self.lock:
            self.values = reading.values
            self.last_sample = self.clock()
            self.source_age_seconds = (
              reading.source_age_seconds + max(0.0, self.last_sample - sample_started) if reading.source_age_seconds is not None else None
            )
            if self.signature != reading.signature:
              self.index += 1
            self.signature = reading.signature
            self.error = ''
        except Exception as error:
          with self.lock:
            self.values = None
            self.source_age_seconds = None
            self.error = type(error).__name__
        self.stop_event.wait(max(SAMPLE_INTERVAL_S, 1.0) if boot_stabilizing() else SAMPLE_INTERVAL_S)
    except Exception as error:
      with self.lock:
        self.values = None
        self.source_age_seconds = None
        self.error = type(error).__name__
    finally:
      if reader is not None:
        try:
          reader.close()
        except Exception:
          pass
      with self.lock:
        self.values = None
        self.last_sample = 0.0
        self.source_age_seconds = None
        self.signature = None
        self.worker = None

  def close(self):
    with self.lock:
      self.closed = True
      self.stop_event.set()
      worker = self.worker
    if worker is not None:
      worker.join(timeout=0.25)
