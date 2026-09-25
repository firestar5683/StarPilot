"""Saved Ford controller selection; no onroad CP mutation or saved-byte repair."""
from openpilot.starpilot.saved_source import read_saved

KEY = "FordLateralMode"
CHOICES = {0: "Current curvature", 1: "BluePilot angle"}


def read_choice(params):
  raw, readable = read_saved(params, KEY, 8)
  valid = readable and raw in (None, b"0", b"1")
  return (1 if valid and raw == b"1" else 0), raw, readable, valid


def selected(params, *, enabled):
  value, _, readable, valid = read_choice(params)
  safe, safe_ok = read_saved(params, "SafeMode", 8)
  aol, aol_ok = read_saved(params, "AlwaysOnLateral", 8)
  return int(enabled and readable and valid and value == 1 and safe_ok and safe in (None, b"0") and
             aol_ok and aol in (None, b"0"))
