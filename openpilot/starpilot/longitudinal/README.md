# Longitudinal control

## Vehicle extensions

`LongControl` keeps the shared state machine, PID, stopping ramp and final acceleration limits. A startup-selected `LongitudinalExtension` applies the vehicle's existing transition, feedforward and output policies around those stages. Vehicle-specific behavior belongs in its policy module; adding a vehicle must not add another brand branch or argument to the upstream controller.

`LongitudinalInputs` owns the required message subscriptions and builds one `LongitudinalContext` from the current messages. Source freshness, drive identity, lead interpretation and saved profile checks remain with this owner. Missing evidence retains the selected policy's existing fallback behavior; a context does not grant CAN ownership or steering/braking permission.

Policy order matters. Target shaping precedes PID preparation; vehicle output shaping precedes launch handoff and mode-transition shaping; the shared acceleration clip remains last. `reset_start=False` resets the PID and ordinary policy state while retaining the existing launch/stop state. New policies need regressions for inactive control, driver override, missing evidence, stop/start transitions and unchanged neighboring configurations.

## Optional planner cruise ceiling

`LongitudinalPlanner.update(sm, *, cruise_ceiling=None, profile_tuning=None)` accepts an optional
`CruiseCeiling(speed_mps, authority)` in addition to the existing driver cruise
message. The default caller supplies no ceiling. The planner still reads
`carState.vCruise` for the driver's selected ceiling and leaves every supplied
Cap'n Proto message unchanged. The opt-in SLC runtime in `plannerd` supplies
the ceiling after source, acceptance and authority qualification.

The `CruiseCeiling` dataclass validates no source or acceptance history by
construction. Its caller must first establish a fresh, accepted, normalized
m/s ceiling in the correct speed coordinate. The planner validates its numeric
shape and the shared four-mode `Authority` contract. It applies the lower of
the supplied ceiling and the existing driver ceiling only when native system
longitudinal control is available, the supplied authority grants active system
longitudinal control, `selfdriveState.enabled` is true,
`longControlState` is active, and the driver's cruise speed is initialized and
positive. An invalid, absent, higher, or inactive ceiling leaves the original
cruise path unchanged. `forceDecel` still sets the cruise candidate to zero.
The planner records the decision in `last_cruise_ceiling_status`; it does not
publish that diagnostic or alter the longitudinal plan schema.

This optional input changes only the cruise candidate before the planner's
existing jerk limiting. A qualified SLC ceiling below driver cruise uses the
frozen coast window above 4 m/s to soften only that candidate's
braking floor. An enabled, validated named Eco or Sport braking personality
selects its original window and coast floor; custom and default personalities
use Standard. A relevant braking lead, stop intent, force deceleration or
throttle veto retains its ordinary floor; Traffic's separate floor is unchanged.
The native MPC, lead, e2e, stop and acceleration
arbitration remain in place. An inactive planner may still compute a nonzero
target; the host owns actuation gating. Stock setpoint control has a different
output domain.

For the exact tagged Ioniq 6 LONG configuration while native longitudinal
control is active, the model gas-probability coast veto uses the frozen
StarPilot 0.35/0.45 thresholds with a 250 ms source-timed hold. Each accepted
model sample must be valid, alive, current and newer than the previous sample;
repeated, stale, future or unknown input revokes throttle permission without
advancing the hold. A fresh model sample at or below 2.5 m/s keeps the native
low-speed bypass. Stock Ioniq, other vehicles and inactive longitudinal control
retain the native one-frame 0.4 threshold. This comfort policy has not been
qualified on the vehicle.

Native tests use real Cap'n Proto messages and the compiled acados MPC on two
independent planner instances. They compare default/absent, lower and higher
ceilings, lead and e2e braking, force deceleration, uninitialized or zero driver
cruise, inactive control, and inconsistent authority. They verify input bytes
remain unchanged and observe the original MPC reset function. Passing these
tests establishes the bounded planner input behavior, not vehicle qualification.

## Opt-in longitudinal profiles

An exact tagged Ioniq 6 system-longitudinal session starts saved personality
settings when their validated document is present. The
`LONG_PLANNER_REPLAY_RUNTIME=1` development flag remains available for replay.
Fresh installations retain the native planner: `CustomPersonalities` defaults
off, and the new input is absent unless the driver explicitly opts in. Existing
saved follow and jerk values keep their frozen
names, units and defaults. The strict versioned profile document migrates
supported older versions, rejects malformed persisted values, and may choose
named or custom acceleration, braking and following curves. The local Params
cache refreshes once per second; invalid or unavailable values fade to native
behavior. A model frame uses the log timeline only under `REPLAY`; otherwise it
uses the host monotonic clock and requires fresh car, control and selfdrive
messages.

Only native system longitudinal control with active `carControl.longActive` may
apply a profile. The bounded transition changes the existing MPC follow time,
acceleration upper bound and jerk costs, plus the cruise candidate's
acceleration/braking limits. It cannot widen the native car acceleration range.
Valid saved curves above native acceleration bounds are intersected with those
bounds without dropping their other tuning or rewriting the saved document.
Lead, e2e and SLC candidates still arbitrate normally. A lower accepted SLC
ceiling retains at least native cruise braking even when a saved profile asks
for a softer approach; stronger configured braking may still apply.
`forceDecel` keeps the native cruise braking response. Stock ACC and lateral-only control receive
no profile effect. The acados model and cereal schemas are unchanged.

The profile runtime accepts an explicit current Traffic-mode verdict. With
Traffic known active, base follow and all five jerk values interpolate over
0–25 m/s from the Traffic value to the Relaxed low-speed value; the frozen
Traffic defaults apply even when Custom Personalities is off. Traffic also
uses the frozen seven-point acceleration ceiling and 0.42 m/s² cruise-braking
magnitude before intersection with native limits. Saved Traffic following,
acceleration and braking categories replace their respective defaults only
when the master, document and Traffic profile are enabled. Historical v3
Traffic braking as low as 0.35 m/s² is admitted only for a Traffic target;
ordinary profiles retain their 0.5 m/s² lower bound. A fresh explicit Traffic OFF
immediately changes the status and fades following, jerk, acceleration and
cruise-braking values toward the ordinary native personality;
unknown or stale Traffic authority clears the applied profile immediately.
Ordinary personalities keep their existing 45/70 mph follow curve. The saved
Long Planner document also carries an independent global braking response.
Standard is the default and preserves the native cruise floor; choosing Eco
or Sport requests the frozen -0.6 or -2.4 m/s² cruise floor and matching SLC
coast style without enabling Custom Personalities. A validated personality
braking category, then Traffic, takes priority. A braking-relevant lead,
force deceleration or stop context returns the global choice to native
braking; a lower accepted speed ceiling retains at least native approach
braking. MPC lead and e2e candidates still arbitrate. The original global preference
defaulted to Eco when Longitudinal Tune was on; the migrated selector defaults
to Standard to preserve current driving output. Frozen weather, Traffic
hazard-context braking and other vehicle-special-case policies remain outside
this slice. The current
effective StarPilot follow floor is 0.5 s, matching saved profile admission.
Stock planner following remains independent of StarPilot preferences. The
6 m stopping distance and braking-distance guard remain unchanged. Offline native tests compare the committed planner and MPC outputs
with the new default path, then verify a selected profile changes real solver
parameters and plan outputs. No device or physical-timing qualification is
claimed.

The versioned profile document and preset curves are adapted from StarPilot
`678af78347d9656bc2f5dacd4204b012db861fa7`; its applicable MIT notice is retained
in `LICENSE`. The new runtime composes these settings with the current upstream
planner rather than retaining the older planner's unrelated policies.

## Lane-change close gap

The shared versioned Lane Change Preferences document now has an explicit,
default-off close-gap choice and a 0.75–1.0 s requested follow time. Older
documents decode with this choice off. A bounded reader accepts only a valid
saved document; the planner requires current valid model, car, radar, control
and selfdrive sources, active system longitudinal control, and a model-reported
pre/starting/finishing lane-change state with a known side. It reuses the saved
minimum lane-change speed. A blinker alone never starts the reduction.

The reduction ramps into the native MPC follow-time input and ramps out on an
ordinary lane-state exit. An occupied target-side blindspot, standstill,
strong braking by either lead, stop intent, force deceleration, driver pedal,
invalid source or lost authority restores the ordinary follow time immediately.
The MPC still arbitrates lead and stop targets and enforces its acceleration
limits. Current StarPilot MPC input admission supports follow time at or above 0.5 s;
the frozen StarPilot default was 0.6 s and could accept 0.25 s. Those smaller
saved requests are rejected, not clamped or silently rewritten. The restored
behavior and this protective hard-veto reset require vehicle evaluation.

## Ioniq 6 launch state

The separately tagged Ioniq 6 HDA-II LONG configuration can emit the starting
state consumed by its acceleration calibration. Stock Ioniq configurations and
other vehicles retain the native state machine. This policy does not grant ECU
ownership: the separate saved DEBUG opt-in must pass the live Ioniq prearm
handoff before the tagged LONG session can use it. Deprecated CarParams start
fields are not used.

Admission requires a current drive, recent valid car/planner/radar evidence,
both radar leads known absent, no pedal press, and valid CAN. At up to 0.1 m/s,
the planner target and native acceleration ceiling must both permit at least
0.75 m/s² for 35 control samples spanning at least 340 ms. A drive change,
clock discontinuity, gap above 20 ms, or lost evidence restarts that window.
Several control samples can use the same still-fresh 20 Hz source observation.
The start command cannot exceed the planner target, native ceiling, or 1 m/s².
Ordinary PID release remains available under its native conditions.

This deliberately changes the frozen soft-launch behavior: a weak lead or
profile request cannot be raised to the old launch floor. The car controller
also withdraws that floor immediately when a later target becomes softer or
negative, including between its 20 Hz calibration updates. Its existing bounded
decrease handles residual output rather than abruptly clipping acceleration.
Tests cover continuous reference traces, the host-to-decoded-SCC path for both
supported layouts, and unchanged native behavior outside this configuration.
Physical launch response and ECU ownership still require vehicle qualification.
