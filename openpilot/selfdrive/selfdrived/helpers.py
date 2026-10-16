import math
import time
from enum import StrEnum, auto

from openpilot.cereal import log, messaging
from opendbc.car.structs import car
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.locationd.helpers import Pose
from opendbc.car import ACCELERATION_DUE_TO_GRAVITY
from opendbc.car.lateral import ISO_LATERAL_ACCEL
from opendbc.car.interfaces import ACCEL_MIN, ACCEL_MAX
from openpilot.starpilot.models.jetlink_adapter import AOL_GRACE_S, aol_in_control

MIN_EXCESSIVE_ACTUATION_COUNT = int(0.25 / DT_CTRL)
MIN_LATERAL_ENGAGE_BUFFER = int(1 / DT_CTRL)
# modeld writes ChestnutLoading/ChestnutActive only at startup, after a load and
# on a failure; selfdrived reads them every 10th frame (10 Hz), not at 100 Hz.
STATUS_PARAM_FRAMES = 10


def throttled_param(owner, key: str, read):
  """read(key), re-read at most every STATUS_PARAM_FRAMES of owner.sm's frames.
  Without a frame counter (a test's message stub) it reads every time."""
  frame = getattr(owner.sm, 'frame', None)
  cache = vars(owner).setdefault('_status_params', {})
  hit = cache.get(key)
  if frame is not None and hit is not None and 0 <= frame - hit[0] < STATUS_PARAM_FRAMES:
    return hit[1]
  value = read(key)
  if frame is not None:
    cache[key] = (frame, value)
  return value


class ExcessiveActuationType(StrEnum):
  LONGITUDINAL = auto()
  LATERAL = auto()


class ExcessiveActuationCheck:
  def __init__(self):
    self._excessive_counter = 0
    self._engaged_counter = 0

  def update(self, sm: messaging.SubMaster, CS: car.CarState, calibrated_pose: Pose) -> ExcessiveActuationType | None:
    # CS.aEgo can be noisy to bumps in the road, transitioning from standstill, losing traction, etc.
    # longitudinal
    accel_calibrated = calibrated_pose.acceleration.x
    excessive_long_actuation = sm['carControl'].longActive and (accel_calibrated > ACCEL_MAX * 2 or accel_calibrated < ACCEL_MIN * 2)

    # lateral
    yaw_rate = calibrated_pose.angular_velocity.yaw
    roll = sm['vehicleParameters'].roll
    roll_compensated_lateral_accel = (CS.vEgo * yaw_rate) - (math.sin(roll) * ACCELERATION_DUE_TO_GRAVITY)

    # Prevent false positives after overriding
    excessive_lat_actuation = False
    self._engaged_counter = self._engaged_counter + 1 if sm['carControl'].latActive and not CS.steeringPressed else 0
    if self._engaged_counter > MIN_LATERAL_ENGAGE_BUFFER:
      if abs(roll_compensated_lateral_accel) > ISO_LATERAL_ACCEL * 2:
        excessive_lat_actuation = True

    # deviceMotion acceleration can be noisy due to bad mounting or aliased deviceMotion measurements
    device_motion_valid = abs(CS.aEgo - accel_calibrated) < 2
    self._excessive_counter = self._excessive_counter + 1 if device_motion_valid and (excessive_long_actuation or excessive_lat_actuation) else 0

    excessive_type = None
    if self._excessive_counter > MIN_EXCESSIVE_ACTUATION_COUNT:
      if excessive_long_actuation:
        excessive_type = ExcessiveActuationType.LONGITUDINAL
      else:
        excessive_type = ExcessiveActuationType.LATERAL

    return excessive_type


def update_big_model_status(owner) -> bool:
  big_active = throttled_param(owner, "ChestnutActive", owner.params.get)
  fresh = owner.sm.seen['modelV2'] and owner.sm.alive['modelV2'] and owner.sm.valid['modelV2']
  published_big = fresh and owner.sm['modelV2'].big
  if published_big and (big_active is True or owner.sm['deviceState'].chestnutPresent):
    owner.big_model_chestnut = True
  model_unavailable = owner.big_model_active and owner.sm.seen['modelV2'] and not fresh
  # a big model Jetlink joined (no chestnut this drive) hands back to the small model, which drives on
  jetlink = big_active is None and not owner.big_model_chestnut
  demoted = owner.big_model_active and fresh and not published_big and not jetlink
  chestnut_lost = owner.big_model_active and owner.big_model_chestnut and not owner.sm['deviceState'].chestnutPresent
  load_mismatch = big_active is True and fresh and not published_big
  big_failed = (big_active is False and not published_big) or load_mismatch or model_unavailable or demoted or chestnut_lost
  if big_failed and not owner.big_model_failed:
    owner.events.add(log.OnroadEvent.EventName.bigModelFailed)
    owner.big_model_ready_t = time.monotonic()
  owner.big_model_failed = big_failed
  # A successful load is not yet an executed frame; warmup output can be invalid.
  if published_big:
    owner.big_model_active = True
  control_current = owner.sm.seen['carControl'] and owner.sm.alive['carControl'] and owner.sm.valid['carControl']
  axis_active = control_current and (owner.sm['carControl'].latActive or owner.sm['carControl'].longActive)
  if not owner.enabled and not axis_active and not model_unavailable:
    owner.big_model_active = False
    owner.big_model_chestnut = False
  return big_failed


def jetlink_in_control(owner) -> bool:
  """The rule the swap itself waits on, over selfdrived's own state: openpilot enabled or active, or the adapter's
  AOL rule over the intent as heard on aolIntentWire and the axis decision selfdrived publishes as aolAxisState."""
  if owner.enabled or owner.active:
    return True
  sm, axes = owner.sm, owner.aol_axis_decision
  heard = owner.aol_replay and sm.seen['aolIntentWire']
  return aol_in_control(sm['aolIntentWire'] if heard else None, heard and sm.alive['aolIntentWire'],
                        (axes.desired_lateral, axes.desired_longitudinal, axes.lateral_active, axes.longitudinal_active)
                        if owner.axis_transport_required else (),
                        waiting=sm.frame * DT_CTRL < AOL_GRACE_S)


def update_jetlink_swaps(owner, in_control, state=None):
  """One tick of Jetlink's swap events (a big model that joins mid-drive and can hand back), onto selfdrived's
  events. `state` is the joining model's; without it jetlink reads modeld's runtime record, and a gap in it holds
  the last state rather than reading as a switch."""
  model_ok = owner.sm.seen['modelV2'] and owner.sm.alive['modelV2'] and owner.sm.valid['modelV2']
  swap = owner.jetlink_swaps.update(model_ok, model_ok and owner.sm['modelV2'].big, in_control, state=state)
  if swap.no_entry:
    owner.events.add(log.OnroadEvent.EventName.bigModelLoading)  # no engaging for the second after a swap
  if swap.settling and not owner.jetlink_settling:
    owner.big_model_ready_t = time.monotonic()  # a swap drops a frame: hold its comm and localizer errors
  owner.jetlink_settling, owner.jetlink_link_lost = swap.settling, swap.link_lost
  return swap


def jetlink_lost_alert():
  """The Jetlink big model left while in control: the small model drives on and nothing disengages."""
  from openpilot.selfdrive.selfdrived.events import ET, Alert, Priority
  alert = Alert("Big Model Lost", "Using small model", log.SelfdriveState.AlertStatus.userPrompt,
                log.SelfdriveState.AlertSize.mid, Priority.MID, car.CarControl.HUDControl.VisualAlert.steerRequired,
                log.SelfdriveState.AudibleAlert.warningSoft, .2)
  alert.alert_type, alert.event_type = 'jetlinkLinkLost/warning', ET.WARNING
  return alert
