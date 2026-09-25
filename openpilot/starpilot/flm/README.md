# Offline Ioniq 6 FLM observations

`offline.py` accepts at most five explicitly supplied, already decoded Cereal
event streams. It does not discover files or read Params. Only a valid Ioniq 6
torque `controlsState` joined to recent valid `carState` and `carControl` can
produce a sample. The original steering-override exclusion is 0.35 seconds
before and 1 second after a press; segment ends and data gaps split intervals.

Reports contain bounded desired/actual lateral acceleration samples and
contiguous observation windows (at least five eligible samples), counts of
missing or ineligible data, and measured tracking error. Windows are measured
intervals, not classified tuning events. `carOutput` is optional
in frozen logs and never substitutes for the controller's measured acceleration.
Each plotted point carries a continuity ID; a renderer must break lines when
that ID changes, including a short invalid or inactive interval.
These observations neither recommend a tune nor qualify steering behavior.

## Desktop diagnostic tool

Use the existing developer runner with an explicitly selected local recording
directory and up to five closed segment names:

```sh
./dev python -m openpilot.starpilot.flm.analyze \
  --log-root /absolute/local/recordings --output /absolute/new/report.json \
  1234abcd--0123456789--0
```

The optional output file must not already exist. It avoids mixing the developer
runner's build progress with the JSON report. The tool processes one segment at
a time and returns no report if any selected segment fails admission, decoding
or analysis. Full rlogs are required; a qlog is not silently substituted.

Admission rechecks lock files, regular-file identity and modification metadata
through a bounded read. The report identifies the exact compressed source hash.
Compressed input is capped at 32 MiB and expanded input at 64 MiB per segment;
complete zstd or bzip2 stream termination and every Event envelope must decode.
Peak memory exceeds the expanded-input limit because verification buffers and
Event readers coexist. Raw logs, images and locations are not copied into the
report. The configured recording root is an explicit local path, never a URL.

This command refuses device hardware. Use the parked Galaxy operation below
for managed device analysis. Neither entry point writes settings, applies or
recommends a tune, or claims vehicle qualification.

## Parked Galaxy analysis

The newest Vue Galaxy exposes Offline tracking under Tuning and Recordings.
Select up to five closed full-rlog segments from the local inventory. Exact
segment basenames survive older route-name normalization and are revalidated
when read. The report includes desired/actual plots with explicit gaps, source
hashes, measured errors and exclusion counts. Missing samples remain missing.

One owner runs a single isolated worker and retains one report in memory. It
checks fresh parked evidence independently of browser polling, withholds results
after authority loss, and stops/reaps the child on cancellation or shutdown.
The long-lived monitor thread creates the worker so Linux parent-death signals
do not follow a short-lived HTTP request thread. Workers also verify their
parent identity before reading logs. Linux limits address space to 2 GiB and
CPU time to 240 seconds; the parent enforces a five-minute wall deadline and a
1 MiB report bound. The worker runs at reduced scheduling priority.

Authenticated local access is required. Leaving or hiding the page stops its
requests; it does not cancel the accepted operation. Cancel analysis explicitly
or return to retrieve status. Reports are diagnostic observations only; saved
FLM profiles, controller behavior and tune trial/apply/restore are separate work.

## Ioniq 6 torque-surface core

`torque_surface.py` is a pure, inactive reconstruction of the frozen Ioniq 6
surface stages. It accepts one immutable `standard` or `firmware_2025` profile
with finite knobs checked against the historical Ioniq-specific numeric bounds;
those bounds are not a live-trial or safety qualification. The
controller's existing firmware-marker helper, not a model-year guess, must
select the variant in any future integration. It returns center deadband,
center taper, the directional-taper **target**, FF scale with an explicitly
supplied filtered taper, friction threshold and low-speed angle-assist output.
The filtered taper is required: the caller computes the raw target, updates
its existing directional filter, then calls the pure evaluator. Its FF scale
excludes center taper, so multiply those once; the returned threshold already
includes the center-taper division.
The controller still owns its filter, PID, 2023 unwind term, friction fade,
highway output tapers, 2025 output limit and reset order. Missing or invalid
profile data must leave the current Ioniq controller entirely unchanged.

The Ioniq branch in the frozen controller already consumed its own FLM knobs;
the frozen generic full-surface FF/friction branch expressly excluded Ioniq.
Applying both would double shape FF. This module has no Params reader, gate or
trial selector. Its output is a computation contract, not a qualified tune or
permission to actuate. Reference provenance: frozen
`latcontrol_vehicle_tunes.py` SHA256
`2a7793c6ee4b53b45070d3267a01e8c7105dfd8df9d38cdfc96cfe4b672a125b`;
baseline `ioniq6_policy.py` before the replay seam, SHA256
`398353f28e8a367acb300a45dabc61967977aa5e952dd12888e1663b3b864bfb`.

Historical numeric admission is not safe combination admission: setting all
30 knobs to their allowed highs yields a negative directional taper near
18 m/s, +0.9 m/s² setpoint and -3 m/s³ jerk. The pure module preserves this
negative result and accepts a signed finite filtered-stage value for offline
parity. It never clips or authorizes it. Any future live profile owner must
reject or separately qualify coordinated knob combinations before application.

`Ioniq6TorquePolicy` accepts an optional immutable surface at construction for
offline replay. It validates exact Ioniq identity and the firmware-derived
variant before modifying controller state. The normal controller constructor
supplies no surface. Replay uses the same PID, request buffer, directional and
jerk filters, driver override/reset order, and final output stages as the
default Ioniq controller. No saved-profile or live selection path exists.

Standalone frozen-controller fixtures cover both firmware variants, default
and tuned surfaces, left/right transitions, driver override, reset, saturation,
and the first actual torque-parameter update. That longer comparison exposed
and corrected a prior startup-limit mismatch: the original Ioniq PID limits
use the raw vehicle calibration until a learned/custom parameter update. The
1.22 conversion factor alone must not silently widen those initial limits.
