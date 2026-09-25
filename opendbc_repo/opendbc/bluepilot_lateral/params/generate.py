"""Generate protocol constants without loading a host or vehicle module."""
import json
from pathlib import Path

root = Path(__file__).parent
spec = json.loads((root / "protocol.json").read_text())
(root / "protocol.py").write_text('"""Generated from protocol.json; layout preserves the existing curvature flag."""\n' +
                                "".join(f"{key.upper()} = {value!r}\n" for key, value in spec.items()))
(root / "protocol.h").write_text("#pragma once\n// Generated from protocol.json; do not allocate bit 1 to angle metadata.\n" +
                               "".join(f"#define FORD_BP_{key.upper()} {int(value)}U\n" for key, value in spec.items() if key != "shadow_scale"))

manifest = json.loads((root / "manifest.json").read_text())
defaults, bounds = manifest["defaults"], manifest["bounds"]
limits = {"BLEND": defaults["blend"], "VLT_EXTRA": defaults["vlt_extra_max"],
          "PATH_MIN": bounds["path_angle_wire"][0], "PATH_MAX": bounds["path_angle_wire"][1],
          "GAIN_MIN": bounds["gain"][0], "GAIN_MAX": bounds["gain"][1],
          "CURVATURE_MAX": bounds["curvature"], "CURVATURE_ERROR": bounds["curvature_error"],
          "LATERAL_ACCEL": bounds["lateral_accel"], "RX_AGE_US": bounds["rx_age_us"],
          "SHADOW_AGE_US": bounds["shadow_age_us"], "PATH_ROUNDING_MARGIN": bounds["path_rounding_margin"],
          "SHADOW_ROUNDING_MARGIN": bounds["shadow_rounding_margin"], "LATERAL_JERK": bounds["lateral_jerk"],
          "RT_INTERVAL_US": bounds["rt_interval_us"], "STEER_PERIOD_US": bounds["steer_period_us"],
          "CORE_STEER_PERIOD_S": bounds["core_steer_period_s"], "PANDA_AGE_NS": bounds["panda_age_ns"]}
(root / "limits.py").write_text('"""Generated from manifest.json; host and core use this manifest contract."""\n' +
                               "".join(f"{key} = {value!r}\n" for key, value in limits.items()))
(root / "limits.h").write_text("#pragma once\n// Generated from manifest.json; native and Python bounds share a source.\n" +
                              "".join(f"#define FORD_BP_{key} {str(value) + 'F' if isinstance(value, float) else str(value) + 'U'}\n"
                                      for key, value in limits.items()))

# Optional angle trim settings are Python-only; native safety limits stay unchanged.
trim = manifest["angle_lane_trim"]
types = {"enabled": "bool", "offset_m": "float", "gain": "float"}
defaults_fields = "".join(f"  {key}: {types[key]}\n" for key in trim["defaults"])
bounds_fields = "".join(f"  {key}: {'list[float]' if isinstance(value, list) else 'float'}\n" for key, value in trim["bounds"].items())
(root / "trim.py").write_text('"""Generated Python-only angle trim defaults; no native bound or registry changes."""\n' +
                             "from typing import TypedDict\n\n\n" +
                             "class TrimDefaults(TypedDict):\n" + defaults_fields + "\n\n" +
                             "class TrimBounds(TypedDict):\n" + bounds_fields + "\n\n" +
                             f"SOURCE_REVISION = {trim['source_revision']!r}\n" +
                             f"DEFAULTS: TrimDefaults = {trim['defaults']!r}\n" +
                             "BOUNDS: TrimBounds = {\n" +
                             "".join(f"  {key!r}: {value!r},\n" for key, value in trim["bounds"].items()) + "}\n")
