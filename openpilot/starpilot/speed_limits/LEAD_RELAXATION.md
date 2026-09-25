# Lead-drop easing contract

`lead_relaxation.step` is a pure, optional operation after a qualified SLC cap
has been converted to planner m/s coordinates. It returns a cap proposal and a
`PriorApplied` value for the next call. It does not write cruise settings,
request acceleration, read a lead service or enter the runtime control loop.
The caller passes the actual speed-domain cap only after acceptance, source
freshness, offset and cluster/ego conversion have been qualified. Easing never
adds an offset or changes speed coordinates again.
`cap_qualified=True` must come from a valid speed-domain resolution and its
positive planner-coordinate cap bound to the same acceptance decision. This
module does not infer that qualification from a bare number.

`SourceEvidence` distinguishes `VALID`, `ABSENT`, `UNKNOWN` and `STALE` using
the acceptance observation kind. A valid cap from an explicitly qualified
previous-limit fallback may be `ABSENT`; it passes through raw without easing.
`UNKNOWN`, `STALE`, an unqualified cap, no cap or an inactive control path
returns no contribution and clears the previous target. The caller must mark
force-stop and inactive system-longitudinal paths inactive. It must also rotate
`continuity_id` on mode, longitudinal-owner or force-deceleration discontinuity.
`PriorApplied` binds the previous *output* to drive session and control
continuity, not to accepted-limit identity: an accepted limit drop is exactly
when the prior output may be needed. A mismatched prior returns the qualified
raw cap with an error and clears previous state. Active override returns the
raw cap and clears prior so later release cannot inherit the driver's raised
override target.

`LeadEvidence` explicitly classifies current lead validity. Missing, unknown
or stale lead evidence passes through a qualified raw cap without easing.
Valid evidence includes tracking, lead presence, distance in meters, lead
speed in m/s and signed acceleration in m/s². Malformed evidence, policy or
elapsed time also passes through a qualified raw cap with an error and clears
prior. It never turns an unqualified source into a cap. The helper invents no
source or lead TTL, and a long valid elapsed interval reaches the raw cap.

The caller supplies every `Policy` value. First, a current tracked lead and a
lower target must be present without an active override. Ego speed must meet
the minimum and exceed the raw cap by the configured guard. The lead must be
at least the greater of minimum distance and ego speed times headway; its
speed must not be too far below the new cap; its braking must not exceed the
configured maximum. Then the policy's positive deceleration curve is linearly
interpolated over current overspeed and the output is
`max(raw_cap, prior_cap - deceleration × elapsed_seconds)`. The near-equality
guards, distance thresholds and curve are explicit fixture values, not
fresh-install defaults or validated safe calibration. The frozen source used
a fixed 0.05 s model period and defaulted missing lead fields to zero. This
unit requires typed evidence and caller-supplied elapsed time.

Scoped tests reproduce the frozen two-frame `24.9325 → 24.865` m/s trace from
raw `20`, prior `25`, ego `27` m/s, a far nonbraking lead and the frozen
policy. A 0.1 s step gives the same endpoint within floating-point tolerance.
Tests cover source/lead loss, fallback, close or braking lead, prior continuity,
invalid inputs, elapsed-time bounds and actual native planner/MPC composition.
The native case confirms that lead and e2e braking remain below the cruise
candidate and force deceleration stays authoritative. These are software
contracts, not vehicle qualification.
