# SLC offset and speed coordinates

`speed_domain.resolve` binds an actual acceptance decision to an explicit offset
schedule and current raw/cluster speed pairs. Every number is m/s except the
input to `selected_pair_from_kph`, which converts a selected cluster value from
km/h. Each valid pair carries the same session ID and monotonic nanosecond
timestamp as the acceptance decision; a mismatch is invalid. The schedule
contains explicit half-open bands with signed m/s offsets;
it supplies no settings defaults or source freshness policy. A missing band or
unavailable target/pair produces `UNAVAILABLE`; malformed values produce
`INVALID`. `SpeedPair` contains measured cluster speed, which may be below raw
speed; resolution clamps each delta to `max(cluster - raw, 0)`. A nonvalid
resolution with a context is malformed and triggers the override session-reset
contract. Only a `VALID` context may enter `overrides.step(domain=...)`.

Call order is acceptance, domain resolution, override reduction, then
`to_planner_coordinate(context, contribution_raw_mps, basis)`. The reducer
compares current selected and retained intent against `accepted raw + offset`
in cluster coordinates. It keeps retained intent in raw selected-speed units,
even when the current selected value later changes for an unrelated reason.
The conversion adds the *current qualified selected cluster delta* to that
retained raw speed. A current pedal contribution uses the current ego cluster
delta. The larger of limit plus offset and override is converted to planner
coordinates by subtracting the ego cluster delta exactly once. A nonpositive
result gives no cap. The host may then build the optional
`CruiseCeiling(speed_mps, authority)`; the native planner still owns its driver
ceiling and lead, e2e, force-deceleration and acceleration arbitration.

This is a pure integration contract. No caller activates it, and it has no
Params access, UI action, stock setpoint command, source TTL, lead relaxation
or vehicle output. Stock bidirectional selection needs a separate owner and
output domain. The frozen implementation compared raw ego speed with an
offset-adjusted threshold, then used cluster ego speed as the override. This
unit deliberately compares both values in the same cluster coordinate. It
prevents a pedal override from arming when raw ego speed crosses one coordinate
while the effective cluster threshold is in another.

The tests compose actual acceptance and causal override decisions, including
retained raw intent with a changed current selected value, offset changes,
negative offsets, missing coordinates, and one native planner/MPC case. These
are deterministic software contracts, not on-road qualification.
