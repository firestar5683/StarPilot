# SLC composition contract

`composition.step` joins the existing pure source selector, acceptance
reducer, offset/coordinate adapter, override reducer, lead easing helper and
optional `CruiseCeiling`. It never reads Params, changes cruise set speed,
publishes a message or invokes the planner. No runtime caller supplies it yet.
Its `Result` returns every intermediate decision and receipt with immutable
next state, even if a later stage prevents a ceiling.

The caller supplies all four normalized source observations and an explicit
selection policy. Source adapters own eligibility, freshness and geographic or
episode identity. The caller also supplies an offset schedule, current ego
raw/cluster pair stamped to the decision frame, pedal state, qualified lead,
actual host gates and optional action/adoption events. `classified_cruise` must
be the actual same-frame result of a causal ledger cruise-change event. A
stale ledger result or simultaneous acceptance action and cruise effect is
rejected; the event sequencer must resolve or defer the effect. This module
cannot infer physical button association from a speed change.

`HostState.driver_v_cruise_kph` is the single raw selected-speed input. The
composer converts it to m/s once for the domain and override reducers;
`selected_cluster_kph` is a separate display-coordinate measurement. It does
not compare a second raw copy using a tolerance, so float32 CarState precision
cannot create a contradictory duplicate. The uninitialized 255 km/h sentinel
and zero selected speed suppress the cap. The selected and ego pair stamps
represent a caller-qualified common decision frame, not their original
producer timestamps. No universal source or lead TTL is invented.

Frame order is selection, acceptance, offset/domain resolution, override
reduction, one planner-coordinate conversion, lead easing, then an optional
`CruiseCeiling`. The composer derives `SourceEvidence.cap_qualified` only from
a valid domain and positive coordinate; the caller cannot set that Boolean.
Only the two active system-longitudinal modes can emit a ceiling. Stock ACC
ownership has no system cap or stock setpoint command through this API.
Display-only, source uncertainty, absent coordinates, missing driver set
speed, force stop and force deceleration yield no ceiling. A qualified
previous-limit fallback can emit the raw SLC cap without lead easing.

The actual `Authority` is passed unchanged into acceptance and overrides.
When system-longitudinal host flags disagree with that authority, the
composition fails closed, clears lead prior and requires a new session. It
does not run acceptance on that contradictory frame, which avoids crediting
unobserved active time to a pending confirmation. A consistent inactive
authority does run acceptance, so its timer pauses under the reducer's own
rules. A downstream domain failure after acceptance still returns the
acceptance receipt and accepted history in the result; the caller must not
discard an already consumed action disposition merely because no cap was
produced.

Lead prior uses an internal control generation, not accepted-limit identity.
It clears immediately on host loss, mode or owner change, force stop,
force deceleration, missing cap and source loss. A resumed active path starts
a new generation and cannot ease from the old one. The override reducer may
retain selected driver intent through its own short inactivity policy, but
neither that latent intent nor an old ceiling is output while the host gate is
off. Elapsed time comes from monotonic frame timestamps without an invented
maximum gap. Lead or policy errors suppress this composition's ceiling and
clear lead prior, while preserving the returned helper diagnostic.

Scoped tests use actual selector, acceptance, action ledger, override,
coordinate and lead objects. They cover offset/ego delta once, source fallback
and uncertainty, missing coordinates, all four modes and stock ownership,
host-authority disagreement, a consumed acceptance action followed by a
downstream error, rejection through absent-source fallback and reconnection,
reversed monotonic time, causal driver intent, lead easing and continuity reset.
Native tests use real Cap'n Proto messages and compiled MPC on independent
planners over no-cap, ordinary, lead, e2e and force-deceleration transitions;
their ego and selected raw/cluster fields match the composition frame before
the byte snapshot, and they check unchanged input bytes. These establish
software composition, not vehicle qualification or safe tuning.

Physical action/UI association, saved-setting mapping, source and lead
freshness, dashboard/schema production, stock bidirectional setpoint control
and plannerd transport remain separate integration work. Retained source
notices and attribution must be preserved if later runtime code is adapted.
