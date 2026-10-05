"""Confirmation text for parked vehicle preferences."""

VEHICLE_BOOL_KEYS = frozenset(("GMPedalLongitudinal", "DisableOpenpilotLongitudinal", "LongPitch", "VoltSNG", "GMAutoHold", "VoltOnePedalMode",
                              "TeslaAOLScreenTap", "TeslaAOLDisengageOnBrake"))


def confirmation_question(request):
  if request.value not in ("On", "Off"):
    raise ValueError("Unsupported vehicle preference value")
  verb = "Enable" if request.value == "On" else "Disable"
  if request.key == "GMPedalLongitudinal":
    return (f"{verb} Pedal Speed Control after the next startup? " +
            "A compatible connected interceptor must be detected before StarPilot can control it.")
  if request.key == "DisableOpenpilotLongitudinal":
    verb = "Turn off" if request.value == "On" else "Turn on"
    return f"{verb} StarPilot speed control after the next startup? Steering stays unchanged."
  if request.key == "VoltSNG":
    return f"{verb} Volt stop-and-go assistance after the next startup?"
  if request.key == "GMAutoHold":
    from opendbc.car.gm.values import CAR
    release = "gas" if request.vehicle_fingerprint == CAR.BUICK_LACROSSE else "gas or regen paddle"
    return f"{verb} Automatic Brake Hold after the next startup? Press the {release} to release a hold."
  if request.key == "VoltOnePedalMode":
    return f"{verb} Volt one-pedal driving after the next startup? Lifting off the accelerator can apply the brakes with cruise disengaged and cruise main on."
  if request.key == "LongPitch":
    return f"{verb} Grade Compensation after the next startup?"
  if request.key == "TeslaAOLScreenTap":
    return f"{verb} three-finger screen taps for Always On Lateral after the next startup? Cruise control stays independent."
  if request.key == "TeslaAOLDisengageOnBrake":
    return f"{verb} disarming Always On Lateral with the brake after the next startup? This applies to screen-tap steering."
  raise ValueError("Unsupported vehicle preference")
