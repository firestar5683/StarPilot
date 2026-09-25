def supported_pedal_detected(fingerprint, bus, *, supported):
  if not supported:
    return False
  try:
    return fingerprint[bus].get(0x201) == 6
  except (KeyError, IndexError, TypeError, AttributeError):
    return False
