"""One action catalogue for native favourites and Bluetooth controls."""
CONTROLLER_ACTION_CYCLE_PERSONALITY = "__starpilot_controller_action__:cycle_driving_personality"
CONTROLLER_ACTION_SET_SPEED = "__starpilot_controller_action__:set_speed"
CONTROLLER_ACTION_SELFIE = "__starpilot_controller_action__:selfie"
CONTROLLER_ACTION_BOOKMARK = "__starpilot_controller_action__:bookmark"
CONTROLLER_ACTION_PULSE_AND_GLIDE = "__starpilot_controller_action__:pulse_and_glide"
CONTROLLER_ACTION_FORCE_COAST = "__starpilot_controller_action__:force_coast"
CONTROLLER_ACTION_TOGGLE_AOL = "__starpilot_controller_action__:toggle_aol"
CONTROLLER_ACTION_ENGAGE = "__starpilot_controller_action__:engage_openpilot"
CONTROLLER_ACTION_DISENGAGE = "__starpilot_controller_action__:disengage_openpilot"
CONTROLLER_ACTION_COUNTERS = {
  CONTROLLER_ACTION_BOOKMARK: "WheelButtonBookmarkCounter",
  CONTROLLER_ACTION_PULSE_AND_GLIDE: "WheelControlPulseGlideCounter",
  CONTROLLER_ACTION_FORCE_COAST: "WheelControlForceCoastCounter",
  CONTROLLER_ACTION_TOGGLE_AOL: "WheelControlAOLCounter",
  CONTROLLER_ACTION_ENGAGE: "WheelControlEngageCounter",
  CONTROLLER_ACTION_DISENGAGE: "WheelControlDisengageCounter",
}
CONTROLLER_ACTION_OPTIONS = (
  {
    "key": CONTROLLER_ACTION_CYCLE_PERSONALITY,
    "label": "Cycle Driving Personality",
    "description": "Cycles Aggressive → Standard → Relaxed. Requires longitudinal control and Safe Mode off; leaves Traffic Mode unchanged.",
    "section": "Controller Actions",
  },
  {
    "key": CONTROLLER_ACTION_SET_SPEED,
    "label": "Set Speed To",
    "description": "Immediately changes the software-controlled cruise set speed while engaged.",
    "section": "Controller Actions",
    "value_type": "speed",
    "default_value": 30,
  },
  {
    "key": CONTROLLER_ACTION_SELFIE,
    "label": "Take Comma Selfie",
    "description": "Captures the driver camera and saves it in Sentry history.",
    "section": "Controller Actions",
  },
  {
    "key": CONTROLLER_ACTION_BOOKMARK,
    "label": "Bookmark",
    "description": "Creates a driving bookmark without changing the on-screen Favorites.",
    "section": "Controller Actions",
  },
  {
    "key": CONTROLLER_ACTION_PULSE_AND_GLIDE,
    "label": "Pulse and Glide",
    "description": "Toggles Pulse and Glide using the same transient control as a mapped vehicle button.",
    "section": "Controller Actions",
  },
  {
    "key": CONTROLLER_ACTION_FORCE_COAST,
    "label": "Force Coasting",
    "description": "Toggles forced coasting using the same transient control as a mapped vehicle button.",
    "section": "Controller Actions",
  },
  {
    "key": CONTROLLER_ACTION_TOGGLE_AOL,
    "label": "Toggle AOL",
    "description": "Toggles Always On Lateral like the vehicle LKAS button; it does not change the AOL setting.",
    "section": "Controller Actions",
  },
  {
    "key": CONTROLLER_ACTION_ENGAGE,
    "label": "Engage Openpilot",
    "description": "Requests engagement through the normal openpilot readiness and safety checks.",
    "section": "Controller Actions",
  },
  {
    "key": CONTROLLER_ACTION_DISENGAGE,
    "label": "Disengage Openpilot",
    "description": "Immediately disengages openpilot like the vehicle cancel button.",
    "section": "Controller Actions",
  },
)
CONTROLLER_ACTION_KEYS = {option["key"] for option in CONTROLLER_ACTION_OPTIONS}


def controller_speed_bounds(is_metric: bool) -> tuple[int, int]:
  return (8, 145) if is_metric else (5, 90)
