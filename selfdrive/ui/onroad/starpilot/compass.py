from openpilot.selfdrive.ui.ui_state import ui_state

def get_compass_text() -> str | None:
  params = ui_state.ui_params
  if not params.get_bool("Compass"):
    return None

  # Retrieve bearing
  bearing = 0.0
  gps = ui_state.sm["gpsLocationExternal"] if ui_state.sm.valid.get("gpsLocationExternal", False) else None
  if gps and gps.bearingDeg != 0:
    bearing = gps.bearingDeg
  else:
    try:
      last_gps = ui_state.params_memory.get("LastGPSPosition")
      if last_gps:
        import json
        data = json.loads(last_gps)
        bearing = data.get("bearing", 0.0)
    except Exception:
      pass

  bearing = bearing % 360
  directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
  idx = int((bearing + 22.5) // 45) % 8
  return f"- {directions[idx]} -"
