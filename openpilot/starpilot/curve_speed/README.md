# Curve Speed Controller

This feature separates learned cornering comfort, future curve geometry, and
runtime control ownership. Its numerical policy is derived from StarPilot
`678af78347d9656bc2f5dacd4204b012db861fa7`; the applicable notice is in `LICENSE`.
The pure modules do not read Params, publish commands, or enable longitudinal control.

`LearnedCurve` keeps 24 logarithmic curvature buckets and a weighted monotone
comfort fit. Historical sample weight is capped at 600 when adding observations;
the stored count continues to track calibration. Driver feedback uses a separate
20-sample weight. Ordinary observations and feedback require runtime permission:
calling these methods alone does not establish driver ownership of speed.

The loader accepts the legacy bucket mapping or a version-1 document. Loading
does not write, mark data dirty, or silently rewrite a damaged document. Invalid
entries reject the whole document; the caller must preserve the original bytes
and require explicit reset before collecting replacement data. Counts must be
positive integers within the exact JSON integer range. Missing data is distinct
from a storage read failure. A successful asynchronous write acknowledges only
the revision it actually saved, preserving any newer dirty samples.

`CurveProfile` validates an immutable, bounded forward profile. `evaluate`
produces a target and binding distance using the learned comfort, approach
deceleration and distance-dependent curvature correction. Its weather reduction
argument requires an independently qualified source; absent weather supplies
zero reduction. Runtime must establish freshness and authority before a target
can become a planner ceiling. Invalid or stale geometry is unavailable, not a
straight road with an invented speed target.

`TargetFilter` preserves the frozen 20 Hz seeding, filter, release and slew
behavior. A gap longer than 0.2 seconds resets it; runtime must handle restart and
clock discontinuity before reentry. Lowering driver cruise immediately caps the
filtered target. Saved malformed data and malformed geometry receive stricter
validation than the frozen implementation; these changes are deliberate.

The planner integration requires the default-off saved switch and an exact
tagged Ioniq 6 system-longitudinal session; `CURVE_REPLAY_RUNTIME=1` retains
the explicit developer path. A candidate only lowers the cruise
ceiling after SLC composition; native lead/MPC braking, experimental model
braking, force-deceleration and driver overrides retain their authority.
Feedback is attributed to Curve only after the actual acceleration composition
selects it. Card supplies separately identified physical acceleration presses
after excluding SLC-owned actions. A stale event cannot become new feedback.

Live input validation checks the original model event and camera EOF in their
respective clock domains. Startup and suspend/resume require new source events.
Explicit offline replay uses the recorded event timeline. Tiny negative model
origins caused by numerical roundoff are normalized only within one micrometre;
negative later points and decreasing paths remain invalid.

Native settings and Galaxy share one calibration owner. Their confirmed parked
actions require the saved switch already Off, unchanged source bytes and no
active learning session. Adoption writes validated legacy samples to the current
format. Reset writes an empty current document so older saved samples cannot
silently reappear. Both retain the legacy bytes and leave the switch Off. A
conflicting editor or second learner prevents activation for that session;
recovery requires starting a new session after the conflict ends. Persistence
uses the ordinary Params lock and an atomic replacement, and distinguishes a
completed rename from a verified, durable save.

Live diagnostics share the existing planner status publisher but have their own
session, model timestamp and expiry. SLC availability does not imply Curve
availability. The optional large-screen glow and compact curve cue consume these
diagnostics and independent longitudinal authority; saved progress and comfort
remain explicitly separate from live learning.

Source-bound tests cover numerical learning and target traces, native planner
composition, driver events, persistence races, reset/adoption and both UI
profiles. Runtime weather adjustment still requires a qualified producer and
currently contributes zero reduction. Device timing, current-model calibration,
road comfort and full vehicle qualification remain required; host tests and
recorded geometry alone do not establish them.
