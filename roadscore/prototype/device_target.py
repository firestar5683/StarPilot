"""Event device selection; CLI --bench overrides ROADSCORE_DEVICE."""
import os
DEFAULT_DEVICE = "comma@192.168.8.156"
def device_target():
 return os.environ.get("ROADSCORE_DEVICE", DEFAULT_DEVICE)
