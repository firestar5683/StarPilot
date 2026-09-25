# Ioniq 6 reference fixtures

These synthetic fixtures check source behavior and CAN payloads. They contain
no recorded routes, VINs, or location data.

- `ioniq6_long_calibration.json` records 100 successive calls to the reference
  acceleration calibration. The test also checks intentional
  disengagement and override resets separately.
- `ioniq6_heartbeat.json` records the reference 24-byte radar heartbeat at
  counters 0, 1, 255, and 256 for all four physical pedal combinations.
  It checks payload integrity and counter rollover.
- `ioniq6_bsm_frozen.json` records all 16 left/right presence and blinker
  combinations from the reference blind-spot encoder, using a
  synthetic neutral base and counters 0–15. The frozen indicator mirror bits
  remain in the raw payload even though the current DBC omits their names; one
  alias is decoded as a sound-warning field, so this fixture proves bytes,
  not audible behavior.
- `scc_parent_frames.json` records the default SCC packer's output before the
  Ioniq-specific options were added. Other vehicles retain these defaults.

These are source and wire-format regression checks. They do not establish
device startup timing, ECU takeover behavior, or on-road qualification.
