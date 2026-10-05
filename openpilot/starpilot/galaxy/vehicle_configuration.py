import hashlib

from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.vehicle_selection import read_selection


STARTUP_KEYS = ('AlphaLongitudinalEnabled', 'IsReleaseBranch', 'OpenpilotEnabledToggle', 'SafeMode',
                'DisableOpenpilotLongitudinal', 'ToyotaAutoHold', 'TurnAssist', 'LongPitch',
                'HondaBoschARadar', 'NAPPedalEnabled', 'NAPRadarEnabled', 'NAPRadarBehindNosecone')


def configuration_context(params, physical_cp, physical_raw):
  selection = read_selection(params)
  if not selection.readable or not selection.valid:
    return None, None
  if selection.platform is None:
    return physical_cp, physical_raw
  saved = tuple((key, *read_saved(params, key, 512)) for key in STARTUP_KEYS)
  revision = hashlib.sha256(repr((selection.raw, saved)).encode()).digest()
  if physical_cp is not None and physical_cp.carFingerprint == selection.platform:
    return physical_cp, b'vehicle-configuration:' + revision + (physical_raw or b'')
  try:
    from opendbc.car import gen_empty_fingerprint
    from opendbc.car.car_helpers import interfaces
    from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences
    from openpilot.cereal import messaging
    from opendbc.car.structs import car
    values = {key: (raw, readable) for key, raw, readable in saved}
    release = values['IsReleaseBranch'] == (b'1', True)
    alpha = not release and values['AlphaLongitudinalEnabled'] == (b'1', True)
    cp = interfaces[selection.platform].get_params(selection.platform, gen_empty_fingerprint(), [], alpha, release, False)
    VehicleStartupPreferences.read(params, enabled=values['OpenpilotEnabledToggle'] == (b'1', True)).prepare(cp)
    if read_selection(params) != selection or tuple((key, *read_saved(params, key, 512)) for key in STARTUP_KEYS) != saved:
      return None, None
    raw = cp.to_bytes()
    reader = messaging.log_from_bytes(raw, car.CarParams)
    return reader, b'vehicle-configuration:' + revision + raw
  except (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError, OverflowError):
    return None, None
