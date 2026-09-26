"""Finite legacy-key mapping to current authoritative settings owners."""

import hashlib

from openpilot.starpilot.favorites.state import FavoriteAction
from openpilot.starpilot.ui.feature_settings_state import row_change

BOOKMARK = "__starpilot_controller_action__:bookmark"
INCREASE_SPEED = "__starpilot_controller_action__:increase_speed"
DECREASE_SPEED = "__starpilot_controller_action__:decrease_speed"
SET_SPEED = "__starpilot_controller_action__:set_speed"
EXPERIMENTAL = "ExperimentalMode"
SCREEN_OFF = "__starpilot_controller_action__:toggle_screen_off"
TRAFFIC = "__starpilot_controller_action__:traffic_mode"
SWITCHBACK = "__starpilot_controller_action__:switchback_mode"
CYCLE_PERSONALITY = "__starpilot_controller_action__:cycle_driving_personality"

# Saved preference shortcuts retain the current owner's authority and dependencies.
FEATURE_KEYS = {
  "slc": ("SpeedLimitController", "ShowSpeedLimits", "SLCConfirmation", "SLCConfirmationHigher", "SLCConfirmationLower", "SLCFallback"),
  "lane": ("LaneCentering", "LaneCenteringPauseOnSignal"),
  "curve": ("CurveSpeedController", "CurveSpeedControllerNoLead", "ShowCSCStatus"),
  "aol": ("AlwaysOnLateral", "NostalgiaMode"),
  "profiles": ("CustomPersonalities",),
}
APPEARANCE_KEYS = ("HideSpeed", "HideMaxSpeed", "HideSteeringWheel", "DriverCamera", "StoppedTimer", "StockConfidenceBallWidget",
                   "EnableTorqueBarWidget", "RainbowPath", "HideLeadMarker", "LeadInfo", "SignalMetrics", "BlindSpotMetrics", "CameraView")


def _row_action(row, apply, section):
  request = row_change(row)
  allowed = (row.available and not row.repair_value and row.value in row.choices and
             2 <= len(row.choices) <= 5 and request is not None and not request.confirmation)
  token = hashlib.sha256(repr(row).encode()).hexdigest()
  return FavoriteAction(row.key, row.label, "toggle" if row.choices == ("Off", "On") else "enum", row.value,
                        allowed, "" if allowed else row.reason or "Available while parked with the required feature enabled",
                        token, (lambda: apply(request)) if allowed else None, section)


def mapped_actions(feature_snapshot, feature_apply, appearance_snapshot, appearance_apply):
  actions = {}
  for page, keys in FEATURE_KEYS.items():
    state = feature_snapshot(page)
    for row in state.rows:
      if row.key in keys:
        actions[row.key] = _row_action(row, feature_apply, state.title)
  appearance = appearance_snapshot()
  for row in appearance.rows:
    if row.key in APPEARANCE_KEYS:
      actions[row.key] = _row_action(row, appearance_apply, "Visual")
  actions[BOOKMARK] = FavoriteAction(BOOKMARK, "Bookmark", reason="Use this control on the device")
  actions[EXPERIMENTAL] = FavoriteAction(EXPERIMENTAL, "Experimental Mode", kind="toggle", state_label="On device",
                                        reason="Use this control on the device")
  actions[CYCLE_PERSONALITY] = FavoriteAction(CYCLE_PERSONALITY, "Cycle Driving Personality", kind="enum", state_label="On device",
                                            reason="Use this control on the device")
  for key, label in ((INCREASE_SPEED, "Increase Set Speed"), (DECREASE_SPEED, "Decrease Set Speed"),
                     (TRAFFIC, "Traffic Mode"), (SWITCHBACK, "Switchback Mode"), (SCREEN_OFF, "Toggle Screen Off")):
    actions[key] = FavoriteAction(key, label, kind="toggle" if key in (TRAFFIC, SWITCHBACK, SCREEN_OFF) else "action",
                                  reason="Use the qualified control on the device", section="Driving")
  return actions
