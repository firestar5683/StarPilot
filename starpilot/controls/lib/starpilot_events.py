#!/usr/bin/env python3
import random

from openpilot.common.constants import ACCELERATION_DUE_TO_GRAVITY, CV
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.controls.lib.desire_helper import TurnDirection
from openpilot.selfdrive.selfdrived.events import ET, EVENT_NAME, STARPILOT_EVENT_NAME, EventName, StarPilotEventName, Events

from openpilot.starpilot.common.starpilot_variables import CRUISING_SPEED, NON_DRIVING_GEARS

DEJA_VU_G_FORCE = 0.75
RANDOM_EVENTS_CHANCE = 0.01 * DT_MDL
RANDOM_EVENTS_LENGTH = 5

RANDOM_EVENT_START = StarPilotEventName.accel30
RANDOM_EVENT_END = StarPilotEventName.youveGotMail

class StarPilotEvents:
  def __init__(self, StarPilotPlanner, error_log, ThemeManager):
    self.starpilot_planner = StarPilotPlanner
    self.theme_manager = ThemeManager

    self.events = Events(starpilot=True)

    self.always_on_lateral_allowed_previously = False
    self.previous_traffic_mode = False
    self.previous_switchback_mode = False
    self.random_event_playing = False
    self.startup_seen = False
    self.stopped_for_light = False

    self.max_acceleration = 0
    self.random_event_timer = 0
    self.tracked_lead_distance = 0

    self.played_events = set()

    self.error_log = error_log

  def update(self, long_control_active, v_cruise, sm, starpilot_toggles):
    current_alert = sm["selfdriveState"].alertType
    current_starpilot_alert = sm["selfdriveState"].alertType
    switchback_mode_enabled = self.starpilot_planner.params_memory.get_bool("SwitchbackModeEnabled")

    alerts_empty = (sm["selfdriveState"].alertText1 == "" and sm["selfdriveState"].alertText2 == "" and
                    sm["starpilotSelfdriveState"].alertText1 == "" and sm["starpilotSelfdriveState"].alertText2 == "")

    self.events.clear()

    if not sm["deviceState"].started:
      self.previous_switchback_mode = False
      self.previous_traffic_mode = False

    acceleration = sm["carControl"].actuators.accel

    if long_control_active:
      self.max_acceleration = max(acceleration, self.max_acceleration)
    else:
      self.max_acceleration = 0

    if sm["starpilotCarState"].alwaysOnLateralAllowed != self.always_on_lateral_allowed_previously:
      if sm["starpilotCarState"].alwaysOnLateralAllowed:
        self.events.add(StarPilotEventName.lkasEnable)
      else:
        self.events.add(StarPilotEventName.lkasDisable)

    if self.starpilot_planner.starpilot_vcruise.forcing_stop:
      self.events.add(StarPilotEventName.forcingStop)

    if not self.starpilot_planner.tracking_lead and sm["carState"].standstill and sm["carState"].gearShifter not in NON_DRIVING_GEARS:
      if not self.starpilot_planner.model_stopped and self.stopped_for_light and starpilot_toggles.green_light_alert:
        self.events.add(StarPilotEventName.greenLight)

      self.stopped_for_light = self.starpilot_planner.longitudinal_intent.stop_detected
    else:
      self.stopped_for_light = False

    if starpilot_toggles.current_holiday_theme != "stock" and "holidayActive" not in self.played_events and self.startup_seen and alerts_empty and len(self.events) == 0:
      self.events.add(StarPilotEventName.holidayActive)

    if self.starpilot_planner.tracking_lead and sm["carState"].standstill and sm["carState"].gearShifter not in NON_DRIVING_GEARS:
      if self.tracked_lead_distance == 0:
        self.tracked_lead_distance = self.starpilot_planner.lead_one.dRel

      lead_departing = self.starpilot_planner.lead_one.dRel - self.tracked_lead_distance >= 1
      lead_departing &= self.starpilot_planner.lead_one.vLead >= 1

      if lead_departing and starpilot_toggles.lead_departing_alert:
        self.events.add(StarPilotEventName.leadDeparting)
    else:
      self.tracked_lead_distance = 0

    if starpilot_toggles.nnff and "nnffLoaded" not in self.played_events and self.startup_seen and alerts_empty and len(self.events) == 0 and self.starpilot_planner.params.get("NNFFModelName") is not None:
      self.events.add(StarPilotEventName.nnffLoaded)

    if self.random_event_playing:
      self.random_event_timer += DT_MDL

      if self.random_event_timer >= RANDOM_EVENTS_LENGTH:
        self.theme_manager.update_wheel_image(starpilot_toggles.wheel_image)
        self.starpilot_planner.params_memory.put_bool("UpdateWheelImage", True)

        self.random_event_playing = False
        self.random_event_timer = 0

    if not self.random_event_playing and starpilot_toggles.random_events:
      if "accel30" not in self.played_events and 3.5 > self.max_acceleration >= 3.0 and acceleration < 1.5:
        self.events.add(StarPilotEventName.accel30)

        self.theme_manager.update_wheel_image("accel30", random_event=True)
        self.starpilot_planner.params_memory.put_bool("UpdateWheelImage", True)

        self.max_acceleration = 0

      elif "accel35" not in self.played_events and 4.0 > self.max_acceleration >= 3.5 and acceleration < 1.5:
        self.events.add(StarPilotEventName.accel35)

        self.theme_manager.update_wheel_image("accel35", random_event=True)
        self.starpilot_planner.params_memory.put_bool("UpdateWheelImage", True)

        self.max_acceleration = 0

      elif "accel40" not in self.played_events and self.max_acceleration >= 4.0 and acceleration < 1.5:
        self.events.add(StarPilotEventName.accel40)

        self.theme_manager.update_wheel_image("accel40", random_event=True)
        self.starpilot_planner.params_memory.put_bool("UpdateWheelImage", True)

        self.max_acceleration = 0

      if "dejaVuCurve" not in self.played_events and sm["carState"].vEgo > CRUISING_SPEED:
        if self.starpilot_planner.lateral_acceleration >= DEJA_VU_G_FORCE * ACCELERATION_DUE_TO_GRAVITY:
          self.events.add(StarPilotEventName.dejaVuCurve)

      if "hal9000" not in self.played_events and (ET.NO_ENTRY in current_alert or ET.NO_ENTRY in current_starpilot_alert):
        self.events.add(StarPilotEventName.hal9000)

      if f"{EVENT_NAME[EventName.steerSaturated]}/" in current_alert or f"{STARPILOT_EVENT_NAME[StarPilotEventName.goatSteerSaturated]}/" in current_starpilot_alert:
        event_choices = []
        if "firefoxSteerSaturated" not in self.played_events:
          event_choices.append("firefoxSteerSaturated")
        if "goatSteerSaturated" not in self.played_events:
          event_choices.append("goatSteerSaturated")
        if "thisIsFineSteerSaturated" not in self.played_events:
          event_choices.append("thisIsFineSteerSaturated")

        if event_choices and random.random() < RANDOM_EVENTS_CHANCE:
          event_choice = random.choice(event_choices)

          if event_choice == "firefoxSteerSaturated":
            self.events.add(StarPilotEventName.firefoxSteerSaturated)

            self.theme_manager.update_wheel_image("firefoxSteerSaturated", random_event=True)
            self.starpilot_planner.params_memory.put_bool("UpdateWheelImage", True)
          elif event_choice == "goatSteerSaturated":
            self.events.add(StarPilotEventName.goatSteerSaturated)

            self.theme_manager.update_wheel_image("goatSteerSaturated", random_event=True)
            self.starpilot_planner.params_memory.put_bool("UpdateWheelImage", True)
          elif event_choice == "thisIsFineSteerSaturated":
            self.events.add(StarPilotEventName.thisIsFineSteerSaturated)

            self.theme_manager.update_wheel_image("thisIsFineSteerSaturated", random_event=True)
            self.starpilot_planner.params_memory.put_bool("UpdateWheelImage", True)

      if "vCruise69" not in self.played_events and 70 > max(sm["carState"].vCruise, sm["carState"].vCruiseCluster) * (1 if starpilot_toggles.is_metric else CV.KPH_TO_MPH) >= 69:
        self.events.add(StarPilotEventName.vCruise69)

      if f"{EVENT_NAME[EventName.fcw]}/" in current_alert or f"{EVENT_NAME[EventName.stockAeb]}/" in current_alert:
        event_choices = []
        if "toBeContinued" not in self.played_events:
          event_choices.append("toBeContinued")
        if "yourFrogTriedToKillMe" not in self.played_events:
          event_choices.append("yourFrogTriedToKillMe")

        if event_choices:
          event_choice = random.choice(event_choices)
          if event_choice == "toBeContinued":
            self.events.add(StarPilotEventName.toBeContinued)
          elif event_choice == "yourFrogTriedToKillMe":
            self.events.add(StarPilotEventName.yourFrogTriedToKillMe)

      if "youveGotMail" not in self.played_events and sm["starpilotCarState"].alwaysOnLateralAllowed and not self.always_on_lateral_allowed_previously:
        if random.random() < RANDOM_EVENTS_CHANCE / DT_MDL:
          self.events.add(StarPilotEventName.youveGotMail)

      self.random_event_playing |= bool({event for event in self.events.names if RANDOM_EVENT_START <= event <= RANDOM_EVENT_END})

    if self.error_log.is_file():
      if starpilot_toggles.random_events:
        self.events.add(StarPilotEventName.openpilotCrashedRandomEvent)
      else:
        self.events.add(StarPilotEventName.openpilotCrashed)

    if self.starpilot_planner.starpilot_vcruise.slc.speed_limit_changed_timer == DT_MDL and starpilot_toggles.speed_limit_changed_alert:
      self.events.add(StarPilotEventName.speedLimitChanged)

    self.startup_seen |= sm["starpilotSelfdriveState"].alertText1 == starpilot_toggles.startup_alert_top and sm["starpilotSelfdriveState"].alertText2 == starpilot_toggles.startup_alert_bottom

    if sm["starpilotCarState"].trafficModeEnabled != self.previous_traffic_mode:
      if self.previous_traffic_mode:
        self.events.add(StarPilotEventName.trafficModeInactive)
      else:
        self.events.add(StarPilotEventName.trafficModeActive)

      self.previous_traffic_mode = sm["starpilotCarState"].trafficModeEnabled

    if switchback_mode_enabled != self.previous_switchback_mode:
      if self.previous_switchback_mode:
        self.events.add(StarPilotEventName.switchbackModeInactive)
      else:
        self.events.add(StarPilotEventName.switchbackModeActive)

      self.previous_switchback_mode = switchback_mode_enabled

    if sm["starpilotModelV2"].turnDirection == TurnDirection.turnLeft:
      self.events.add(StarPilotEventName.turningLeft)
    elif sm["starpilotModelV2"].turnDirection == TurnDirection.turnRight:
      self.events.add(StarPilotEventName.turningRight)

    self.always_on_lateral_allowed_previously = sm["starpilotCarState"].alwaysOnLateralAllowed
    self.played_events.update(STARPILOT_EVENT_NAME[event] for event in self.events.names)
