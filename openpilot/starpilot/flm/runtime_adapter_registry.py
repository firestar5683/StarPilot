"""Shared actual-selected controller identities; physical fitting stays in learner."""

from dataclasses import dataclass
import hashlib
import json
import math
import time
from functools import cache
from pathlib import Path
import importlib
from opendbc.car.car_helpers import interfaces
from openpilot.starpilot.lateral.learning_preferences import read_preference, KEY as PREFERENCE_KEY
from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY, LEGACY_KEYS, MAX_DOCUMENT_BYTES, parse_document, interpret_legacy
from openpilot.starpilot.saved_source import read_saved

REVISION = 'actual-controller-registry-v2'


@cache
def implementation_revision(controller_type, interface_type):
  """Startup/optional-process source identity; never invoked by Controls.tick.

  Bind shaping and conversion implementation changes as well as numeric CP
  values. Formatting changes conservatively discard stored priors too.
  """
  here = Path(__file__).resolve().parent
  controller_root = Path(importlib.import_module(controller_type.__module__).__file__).resolve().parent
  brand_root = Path(importlib.import_module(interface_type.__module__).__file__).resolve().parent
  common_root = here.parents[1] / 'common'
  inherited_roots = tuple(
    Path(importlib.import_module(base.__module__).__file__).resolve().parent for base in controller_type.__mro__ if base.__module__.startswith('openpilot.')
  )
  roots = (here, here.parent / 'lateral', controller_root, brand_root, brand_root.parent, common_root, *inherited_roots)
  files = tuple(sorted({path for root in roots for path in root.glob('*.py')}))
  if not files or len(files) > 512:
    raise ValueError('controller implementation identity bound')
  result = hashlib.sha256()
  result.update((controller_type.__module__ + '.' + controller_type.__qualname__).encode('utf-8'))
  result.update((interface_type.__module__ + '.' + interface_type.__qualname__).encode('utf-8'))
  for path in files:
    data = path.read_bytes()
    if len(data) > 2 * 1024 * 1024:
      raise ValueError('implementation source bound')
    result.update(path.name.encode('utf-8'))
    result.update(hashlib.sha256(data).digest())
  return REVISION + ':' + result.hexdigest()


SOURCE_LEASE_NS = 500_000_000
BASELINE_MAX = 32


def digest(value):
  # Called at startup or by the separate learner, never JSON in Controls.tick.
  return hashlib.sha256(
    json.dumps(
      value,
      sort_keys=True,
      separators=(',', ':'),
      allow_nan=False,
      default=lambda item: {'data_hex': item.hex()} if isinstance(item, bytes) else (_ for _ in ()).throw(TypeError('unsupported identity value')),
    ).encode()
  ).hexdigest()


def car_params_digest(cp):
  """Bind all CP values, including legitimate infinity sentinels, without JSON NaN tokens."""
  import struct

  def typed(value):
    kind = type(value)
    if kind is dict:
      if not all(type(key) is str for key in value):
        raise TypeError('non-string CarParams field')
      return ['dict', [[key, typed(value[key])] for key in sorted(value)]]
    if kind in (list, tuple):
      return [kind.__name__, [typed(item) for item in value]]
    if kind is float:
      return ['float64', struct.pack('>d', value).hex()]
    if kind is bytes:
      return ['bytes', value.hex()]
    if value is None or kind in (bool, int, str):
      return [kind.__name__, value]
    raise TypeError('unsupported CarParams identity value')

  return digest(typed(cp.to_dict()))


def canonical_physical_context(value):
  return digest(value)


def physical_model_revision(model):
  from dataclasses import asdict

  return digest(asdict(model))


def native_identity_key(native):
  if native is None:
    return None
  return (
    str(native.axisSessionId),
    str(native.pandaSerial),
    int(native.safetyModel),
    int(native.safetyParam),
    tuple(
      (int(slot.slotIndex), str(slot.hardwareSerial), int(slot.safetyModel), int(slot.safetyParam), int(slot.alternativeExperience))
      for slot in native.pandaInventory
    ),
  )


def native_identity_digest(key):
  return '' if key is None else hashlib.sha256(repr(key).encode('utf-8')).hexdigest()


def current_authority(sm, cp, *, now_ns, required):
  """Once per optional daemon iteration; reuse existing native verifier."""
  cache_key = (now_ns, bool(required), id(cp))
  cached = getattr(sm, '_flm_authority_cache', None)
  if cached is not None and cached[0] == cache_key:
    return cached[1:]
  allowed, native, identity = False, None, ''
  try:
    if required:
      from openpilot.starpilot.aol.runtime import current_native
      from openpilot.starpilot.aol.transport_pause import _healthy_transport_native

      native = current_native(sm, cp, now_ns=now_ns)
      identity = native_identity_digest(native_identity_key(native))
      # Typed LAT grants are independent of ordinary LONG controlsAllowed.
      # Reuse existing exact current configuration/health semantics, preserving
      # every Panda/RX/heartbeat/fault/serial guard and original native lease.
      allowed = bool(
        native is not None
        and native.requestedLateral
        and native.lateralAllowed
        and _healthy_transport_native(sm, cp, sm['carState'], str(native.axisSessionId), now_ns, native=native, require_longitudinal=False) is not None
      )
    else:
      healthy = bool(
        sm.seen['pandaStates']
        and sm.alive['pandaStates']
        and sm.valid['pandaStates']
        and sm.freq_ok['pandaStates']
        and 0 <= now_ns - int(sm.recv_time['pandaStates'] * 1e9) <= 1_000_000_000
      )
      pandas = sm['pandaStates']
      if len(pandas) != len(cp.safetyConfigs):
        healthy = False
      active = 0
      for panda, config in zip(pandas, cp.safetyConfigs, strict=True):
        healthy &= bool(
          panda.safetyModel == config.safetyModel
          and panda.safetyParam == config.safetyParam
          and panda.alternativeExperience == cp.alternativeExperience
          and not panda.safetyRxChecksInvalid
          and not panda.heartbeatLost
          and not panda.faults
        )
        if str(config.safetyModel) not in ('silent', 'noOutput'):
          active += 1
          healthy &= bool(panda.controlsAllowed)
      allowed = bool(healthy and active >= 1)
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    allowed, native, identity = False, None, ''
  sm._flm_authority_cache = (cache_key, allowed, native, identity)
  return allowed, native, identity


def ford_public_identity_key(cp, pandas):
  # Public configuration provenance only; PandaState has no hardware serial.
  return (
    'ford-public-config-v1',
    str(cp.carFingerprint),
    int(cp.flags),
    int(cp.alternativeExperience),
    tuple(
      (index, int(panda.pandaType.raw), int(panda.safetyModel.raw), int(panda.safetyParam), int(panda.alternativeExperience))
      for index, panda in enumerate(pandas)
    ),
  )


def current_ford_authority(sm, cp, *, now_ns):
  """Optional parent20Hz mirror of the existing successful Ford verifier."""
  key = (now_ns, id(cp))
  cached = getattr(sm, '_flm_ford_authority_cache', None)
  if cached is not None and cached[0] == key:
    return cached[1:]
  allowed, identity = False, ''
  try:
    from opendbc.bluepilot_lateral.params import limits as bounds

    if not ford_downstream(cp):
      raise ValueError('Ford downstream role')
    pandas = sm['pandaStates']
    stamp = int(sm.logMonoTime['pandaStates'])
    receipt = int(sm.recv_time['pandaStates'] * 1e9)
    boot = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    allowed = bool(
      sm.seen['pandaStates']
      and sm.all_checks(['pandaStates'])
      and 0 < stamp <= boot <= stamp + bounds.PANDA_AGE_NS
      and 0 < receipt <= now_ns <= receipt + bounds.PANDA_AGE_NS
      and len(pandas) == len(cp.safetyConfigs)
    )
    for index, (panda, config) in enumerate(zip(pandas, cp.safetyConfigs, strict=True)):
      allowed &= bool(
        panda.safetyModel == config.safetyModel
        and panda.safetyParam == config.safetyParam
        and panda.alternativeExperience == cp.alternativeExperience
        and not panda.safetyRxChecksInvalid
        and not panda.heartbeatLost
        and not panda.faults
        and str(panda.faultStatus) == 'none'
        and bool(panda.controlsAllowed) == (index == len(pandas) - 1)
      )
    if allowed:
      identity = native_identity_digest(ford_public_identity_key(cp, pandas))
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    allowed, identity = False, ''
  sm._flm_ford_authority_cache = (key, allowed, identity)
  return allowed, identity


@dataclass(frozen=True)
class SourceState:
  enabled: bool
  manual: bool
  reset: str
  source_epoch: str
  observed_ns: int
  expires_ns: int
  cp_sha256: str
  calibration: tuple[float, ...] = ()


def read_source(cp, params, *, now_ns, cp_sha256=None, calibration=(), vehicle_session=""):
  """Only startup/separate-process settings work; errors disable learning."""
  cp_sha256 = car_params_digest(cp) if cp_sha256 is None else cp_sha256
  try:
    preference = read_preference(params, cp)
    keys = tuple(dict.fromkeys((PREFERENCE_KEY, 'ForceAutoTuneOff', DOCUMENT_KEY, 'AutoSteeringLearningReset', 'LateralControllerSelection', *LEGACY_KEYS)))
    snapshots = []
    for key in keys:
      raw, readable = read_saved(params, key, MAX_DOCUMENT_BYTES)
      if not readable:
        raise ValueError('unreadable source')
      snapshots.append((key, raw))
    raw_by_key = dict(snapshots)
    from openpilot.starpilot.lateral.controller_selection import selection_from_bytes

    if selection_from_bytes(cp, raw_by_key['LateralControllerSelection']).source == 'invalid':
      raise ValueError('invalid saved controller configuration')
    reset_raw = raw_by_key['AutoSteeringLearningReset']
    reset = '0' if reset_raw is None else reset_raw.decode('ascii')
    if not 1 <= len(reset) <= 64 or any(c not in '0123456789abcdef' for c in reset):
      raise ValueError('reset generation')
    document = raw_by_key[DOCUMENT_KEY]
    manual = False
    if document is not None:
      profile = parse_document(document).get(str(cp.carFingerprint))
      if profile is not None:
        if cp.lateralTuning.which() == 'torque':
          tune = cp.lateralTuning.torque
          if profile.basis != (float(tune.latAccelFactor), float(tune.latAccelOffset), float(tune.friction)):
            raise ValueError('incompatible saved tuning basis')
        manual = (
          profile.factor.mode == 'custom'
          or profile.friction.mode == 'custom'
          or profile.proportional_gain.mode == 'custom'
          or profile.flm is not None
          or profile.geometry is not None
          and (profile.geometry.ratio.mode == 'custom' or profile.geometry.full_delay.mode == 'custom')
        )
        if profile.geometry is not None and profile.geometry.learning == 'force_off':
          preference = type(preference)(False, preference.valid, preference.source, preference.raw)
    else:
      # Legacy numeric manual intent preempts optional learning. False legacy
      # switches themselves remain source-bound, but are not numeric overrides.
      if cp.lateralTuning.which() == 'torque':
        tune = cp.lateralTuning.torque
        choice = interpret_legacy(
          {key: raw_by_key[key] for key in LEGACY_KEYS},
          (float(tune.latAccelFactor), float(tune.latAccelOffset), float(tune.friction)),
          fingerprint=str(cp.carFingerprint),
        )
        manual = choice.factor is not None or choice.friction is not None
    calibration = tuple(calibration)
    if len(calibration) != 3 or not all(math.isfinite(v) for v in calibration):
      raise ValueError("uncertain calibration")
    from opendbc.car.vin import is_valid_vin, VIN_UNKNOWN

    vin = str(cp.carVin)
    if not is_valid_vin(vin) or vin == VIN_UNKNOWN:
      if not vehicle_session or len(vehicle_session) > 64:
        raise ValueError('unknown vehicle needs a fresh drive session')
      unit = vehicle_session
    else:
      unit = vin
    epoch = digest((tuple((key, None if raw is None else raw.hex()) for key, raw in snapshots), calibration, unit))
    return SourceState(bool(preference.valid and preference.enabled), manual, reset, epoch, now_ns, now_ns + SOURCE_LEASE_NS, cp_sha256, calibration)
  except (AttributeError, UnicodeError, TypeError, ValueError, OSError, OverflowError):
    return SourceState(False, False, '', '', now_ns, now_ns + SOURCE_LEASE_NS, cp_sha256)


@dataclass(frozen=True)
class ControllerDescriptor:
  domain: str
  controller_mode: str
  policy: str
  controller_revision: str
  stage_revision: str
  cp_sha256: str
  conversion_revision: str
  turn_assist: bool


def selected_descriptor(cp, ci, controller):
  """Use the registered constructor plus the object actually selected by Controls."""
  from openpilot.selfdrive.controls.lib.latcontrol_pid import LatControlPID
  from openpilot.selfdrive.controls.lib.latcontrol_angle import LatControlAngle
  from openpilot.selfdrive.controls.lib.latcontrol_curvature import LatControlCurvature
  from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque

  if (
    cp.notCar
    or cp.passive
    or cp.dashcamOnly
    or str(cp.carFingerprint) not in interfaces
    or type(ci) is not interfaces[str(cp.carFingerprint)]
    or ci.CP.to_dict() != cp.to_dict()
  ):
    return None
  mode = str(getattr(controller, 'controller_mode', 'native'))
  policy = str(getattr(controller, 'controller_policy', None) or 'native_standard')
  conversion = ''
  if isinstance(controller, LatControlTorque) and str(cp.steerControlType) == "torque" and cp.lateralTuning.which() == "torque":
    domain, stage = 'torque', 'torque-post-baseline-prefriction-v1'
    forward = controller.torque_from_lateral_accel
    function = getattr(forward, '__func__', forward)
    conversion = function.__module__ + '.' + function.__qualname__
    extension = getattr(controller, 'starpilot_extension', None)
    if extension is not None:
      policy += ':' + type(extension).__module__ + '.' + type(extension).__qualname__
  elif isinstance(controller, (LatControlPID, LatControlAngle, LatControlCurvature)):
    return None  # Explicit non-torque disposition: preserve the selected baseline.
  else:
    return None
  turn_assist = bool(
    getattr(controller, 'turn_assist', None) or getattr(getattr(getattr(controller, 'starpilot_extension', None), 'policy', None), 'turn_assist', False)
  )
  return ControllerDescriptor(domain, mode, policy, implementation_revision(type(controller), type(ci)), stage, car_params_digest(cp), conversion, turn_assist)


def baseline_values(controller):
  """Bounded actual numeric controller token. No saved/default tune inference."""
  values = [float(controller.steer_max)]
  torque = getattr(controller, 'torque_params', None)
  if torque is not None:
    values.extend(float(getattr(torque, key)) for key in ('latAccelFactor', 'latAccelOffset', 'friction', 'steeringAngleDeadzoneDeg'))
  values.extend(float(getattr(controller, key)) for key in ('ff_factor', 'kf') if hasattr(controller, key))
  pid = getattr(controller, 'pid', None)
  if pid is not None:
    values.extend((float(pid.neg_limit), float(pid.pos_limit)))
    for key in ('_k_p', '_k_i'):
      for row in getattr(pid, key):
        values.extend(float(v) for v in row)
  if not 1 <= len(values) <= BASELINE_MAX or not all(math.isfinite(v) for v in values):
    raise ValueError('actual baseline envelope')
  return tuple(values)


def baseline_revision(descriptor, values):
  # Fixed bounded ASCII bytes, no JSON/Params/I/O/model work on a changed token.
  return hashlib.sha256(repr((descriptor, tuple(values))).encode('ascii')).hexdigest()


def selected_identity(descriptor, source_epoch, baseline=""):
  if len(source_epoch) != 64:
    raise ValueError('source epoch')
  return hashlib.sha256(repr((descriptor, source_epoch, baseline)).encode('ascii')).hexdigest()


def ford_downstream(cp):
  # The existing final admitted CP safety word selects the actual library;
  # no settings read or generic angle-output inference establishes this role.
  from opendbc.bluepilot_lateral.hosts.starpilot import qualified

  return bool(str(cp.carFingerprint) in interfaces and qualified(cp))


def adapter_for_ford(cp, context):
  return None  # Ford's downstream angle/curvature controller is excluded.


def adapter_for_evidence(cp, evidence, key=None):
  """Strict learner factory: consume actual descriptor, never read a mode default."""
  # Actual stage replay must be supplied by the family module; absent trace or
  # baseline reconstruction rejects the family rather than claiming validation.
  from openpilot.starpilot.flm.learner_factory import from_evidence

  return from_evidence(cp, evidence, key)


def collection_keys(evidence):
  from openpilot.starpilot.flm.learner_factory import collection_keys as keys

  return keys(evidence)


def objective_key(evidence):
  from openpilot.starpilot.flm.learner_factory import objective_key as key

  return key(evidence)


def vm_regime(values, anchor=None):
  """Learning-only geometry boundary; exact inputs continue into replay."""
  try:
    point = tuple(float(values['vm.' + name]) for name in ('sR', 'cF', 'cR'))
    if not all(math.isfinite(value) and value != 0.0 for value in point):
      return None
    if anchor is None:
      return point
    if len(anchor) != 3 or not all(math.isfinite(value) and value != 0.0 for value in anchor):
      return None
    return (
      anchor if all(min(base * 0.98, base * 1.02) <= current <= max(base * 0.98, base * 1.02) for current, base in zip(point, anchor, strict=True)) else point
    )
  except (KeyError, TypeError, ValueError, OverflowError):
    return None


def physical_observer(sm, cp, collector, now_ns):
  """Convert independently measured BOOT pose source into the evidence MONO clock."""
  from openpilot.starpilot.flm.fullrate_collector import PhysicalEvidence
  from openpilot.selfdrive.locationd.helpers import PoseCalibrator, Pose

  services = ('deviceMotion', 'extrinsicsCalibration', 'carState', 'lateralDelay', 'driverMonitoringState')
  if not sm.all_checks(list(services)):
    return None
  try:
    mono_before = time.monotonic_ns()
    boot = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    mono_after = time.monotonic_ns()
    offset = boot - (mono_before + mono_after) // 2
    cache = getattr(collector, '_physical_clock', None)
    if cache is None:
      collector._physical_clock = offset
    elif abs(offset - cache) > 1_000_000 + (mono_after - mono_before) // 2:
      collector.split('physical_clock_discontinuity', reset=True)
      collector._physical_clock = offset
      return None
    dm, calibration, cs = sm['deviceMotion'], sm['extrinsicsCalibration'], sm['carState']
    pose_ns = int(dm.timestamp) - collector._physical_clock
    if (
      not 0 < pose_ns <= now_ns
      or now_ns - pose_ns > 100_000_000
      or not dm.inputsOK
      or not dm.sensorsOK
      or not dm.posenetOK
      or not dm.angularVelocityDevice.valid
      or not dm.orientationNED.valid
      or str(calibration.calStatus) != 'calibrated'
    ):
      return None
    state_ns, delay_ns = int(sm.logMonoTime['carState']), int(sm.logMonoTime['lateralDelay'])
    if not 0 < state_ns <= now_ns or now_ns - state_ns > 100_000_000 or not 0 < delay_ns <= now_ns or now_ns - delay_ns > 500_000_000:
      return None
    generation = digest(tuple(float(v) for v in calibration.rpyCalib))
    cache = getattr(collector, '_physical_calibrator', None)
    if cache is None or cache[0] != generation:
      calibrator = PoseCalibrator()
      calibrator.feed_extrinsics_calibration(calibration)
      collector._physical_calibrator = (generation, calibrator)
    calibrator = collector._physical_calibrator[1]
    if not calibrator.calib_valid:
      return None
    pose = calibrator.build_calibrated_pose(Pose.from_device_motion(dm))
    live_lag = float(sm['lateralDelay'].lateralDelay)
    if not math.isfinite(live_lag) or not 0 <= live_lag <= 0.5:
      return None
    lag = getattr(collector, '_physical_lag', None)
    if lag is None:
      lag = collector._physical_lag = round(live_lag * 1e9)
    # Freeze an external lag before model/training/heldout; no optimization or
    # noisy numeric drift invents a new evidence identity on each publication.
    ready = getattr(collector, 'ready', ())
    history = {}
    if ready and getattr(getattr(collector, 'adapter', None), 'command_domain', None) != 'ford_path_angle':
      command = ready[-1][0]
      anchor = getattr(collector, '_physical_vm_anchor', None)
      regime = vm_regime(dict(command.replay_inputs), anchor)
      if regime is None:
        collector.split('vehicle_model_unavailable', reset=True)
        collector._physical_vm_anchor = None
        return None
      if anchor is not None and regime != anchor:
        collector.split('vehicle_model_material_change', reset=True)
        collector._physical_vm_anchor = regime
        return None
      collector._physical_vm_anchor = regime
      native_epoch = command.native_identity
      native = bool(
        getattr(collector, '_learning_current_native_allowed', False) and ready[-1][1].native_allowed and 0 <= now_ns - ready[-1][1].apply_ns <= 100_000_000
      )
      for command, _ in ready:
        values = dict(command.replay_inputs)
        if 'vEgo' in values and 'steeringAngleDeg' in values:
          history[command.state_ns] = (float(values['vEgo']), float(values['steeringAngleDeg']))
    else:
      return None
    if not native:
      return None
    override = bool(
      cs.steeringPressed
      or cs.brakePressed
      or cs.gasPressed
      or cs.regenBraking
      or any(str(button.type) == 'cancel' for button in cs.buttonEvents)
      or sm['driverMonitoringState'].noResponseForceDecel
    )
    fault = bool(cs.canTimeout or not cs.canValid or cs.steerFaultTemporary or cs.steerFaultPermanent or cs.accFaulted)
    # Use independently timestamped actual CarState primitives at the pose
    # source, without pretending the latest speed/angle occurred earlier.
    before = [stamp for stamp in history if stamp <= pose_ns]
    after = [stamp for stamp in history if stamp >= pose_ns]
    if not before or not after:
      return None
    left, right = max(before), min(after)
    if pose_ns - left > 100_000_000 or right - pose_ns > 100_000_000:
      return None
    weight = 0.0 if left == right else (pose_ns - left) / (right - left)
    speed, steering_angle = tuple(a + (b - a) * weight for a, b in zip(history[left], history[right], strict=True))
    # CP geometry is startup static; exact VM inputs are captured per command
    # and replayed by the actual-controller family adapter.
    return PhysicalEvidence(
      pose_ns,
      int(sm.recv_time['deviceMotion'] * 1e9),
      generation,
      digest((float(cp.steerRatio), float(cp.wheelbase), float(cp.centerToFront), float(cp.mass), collector._physical_clock, native_epoch, regime)),
      digest((lag,)),
      lag,
      speed,
      float(pose.angular_velocity.xyz[2]),
      float(pose.orientation.xyz[0]),
      steering_angle,
      True,
      override,
      fault,
      native,
      source_boot_ns=int(dm.timestamp),
      clock_offset_ns=collector._physical_clock,
      clock_uncertainty_ns=(mono_after - mono_before) // 2,
    )
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return None
