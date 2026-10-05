"""Shared fixtures for the generic longitudinal boundary."""
from openpilot.starpilot.longitudinal.inputs import LongitudinalInputs


def extension_state(controller, name):
  return getattr(controller.extension, name, None)


def attach_inputs(controls):
  from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences
  controls.vehicle_startup_preferences = VehicleStartupPreferences()
  controls.turn_assist_enabled = lambda: False
  inputs = LongitudinalInputs.__new__(LongitudinalInputs)
  inputs.messages = lambda: controls.sm
  for name in ('ev9_long_enabled', 'blended_longitudinal_enabled', 'toyota_sienna_replay',
               'ioniq6_start_enabled', 'gm_start_enabled', 'gm_volt_enabled', 'gm_euv_enabled',
               'gm_cc_enabled', 'gm_ascm_enabled', 'gm_suburban_enabled'):
    setattr(inputs, name, False)
  inputs.gm_cc_evidence = None
  controls.longitudinal_inputs = inputs
