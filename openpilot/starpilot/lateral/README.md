# Lateral control

The lane-centering contribution, torque controller and torque parameter source
have separate owners. None grants steering permission: controlsd, the vehicle
controller and Panda retain their existing authority and limits. See
[TORQUE.md](TORQUE.md) for controller selection, learned parameters and manual
factor/friction preferences.

## Lane centering

`LaneCenteringController.update` returns a bounded curvature contribution and
an unclipped candidate. The host applies it after selecting the model or
maneuver curvature and before the native curvature limiter. Longitudinal-only
operation cannot authorize a lateral contribution.

Both inner lane lines must have probability at least 0.6 and standard deviation
at most 0.3 m, with lane width between 2.6 and 4.8 m. Offset is limited to
0.3 m and 1.1 m center-to-line clearance. Lookahead follows speed within 8–35 m;
the center-error deadband is 0.08 m. End-to-end authority controls how strongly
a confident model path reduces the contribution between 0.15 and 0.50 m of
center error. Raw curvature is capped at 0.004 and scaled by 0.30.

Acquisition uses a 0.4 s exponential filter. Signal pause and confidence loss
release the contribution over 0.2 s; driver override resets it immediately.
Signal pause takes precedence over the lane-change reset when both apply.
Malformed inputs and nonfinite settings are rejected. The host supplies elapsed
time, model freshness and explicit clock discontinuities. The filter advances
on each valid control tick even when the same model sample is held.

`LaneCenteringHost` reads saved preferences at 1 Hz, including when a drive
starts with Lane Centering off, so Favorites can enable it during the drive.
Normal startup currently admits the tagged Ioniq 6 longitudinal configuration;
other vehicles are not yet admitted. `LANE_CENTERING_REPLAY_RUNTIME=1` provides
the separate offline replay path. Runtime checks require valid CAN, effective
lateral authority, enabled preferences, and fresh carState, selfdriveState, modelV2 and
vehicleParameters within 2.5 service periods. Missing evidence removes the
contribution without changing the saved preferences.

Tests cover geometry, filtering, overrides, curvature-source priority, native
limiting and unchanged longitudinal commands. They do not establish vehicle
qualification. This module derives from the lane-centering work introduced by
jc01rho in `9f1066ce8380a2602beaf5d43fdb38ee6ec2dcbe`; the applicable MIT notice
is retained in the repository LICENSE.

## Automatic lane changes

The ordinary lane-change path requires a driver nudge. The saved Auto option
adds a delay of 0–5 s and minimum adjacent-lane width of 0–15 ft (stored in
meters), defaulting to 1 s and 0 ft. Auto additionally requires
`STARPILOT_AUTO_LANE_CHANGE_DEV` at modeld startup; saving the option alone does
not enable it.

DesireHelper owns the transition, blindspot check and signal latch. Auto uses
same-frame model evidence, current calibration, fresh carState/carControl,
engaged lateral control and a recognized vehicle. Camera EOF age uses
CLOCK_BOOTTIME; message and calibration timestamps use CLOCK_MONOTONIC. The
adjacent-lane confidence thresholds remain experimental.

The typed status in Event Data @126 supplies pre-change alert wording only when
its model frame, camera EOF, direction and lifetime match. Missing or stale
status produces neutral text and cannot affect engagement checks.

## Vehicle-specific torque policies

The Ioniq 6 policy retains separate 2023 and observed-firmware 2025 shaping for
curvature history, low-speed control, asymmetric feedforward, friction and
stop/pull-away behavior. The 2025 selection requires both firmware markers;
missing evidence selects the standard variant. The policy applies its factor
multiplier once per parameter update. Vehicle initialization uses factor 3.0
and friction 0.09, with the original startup PID limits; subsequent learned or
manual updates use the parameter-update contract described in TORQUE.md.

Reference fixtures cover both Ioniq variants through stops, pull-away, highway,
reversal and driver override, with independent non-Ioniq regression cases.
Other explicit policies and the standard controller remain separate; tuning
one platform must not change another platform's controller or parameter source.
