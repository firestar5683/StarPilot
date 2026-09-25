# BluePilot Ford angle control

StarPilot adaptation of BluePilotDev/bluepilot `bp-7.0`, pinned to
[e1d051d7ba270261b4455068bd68f1a58db15a4a](https://github.com/BluePilotDev/bluepilot/commit/e1d051d7ba270261b4455068bd68f1a58db15a4a).
The layout follows Alan Polk's September 2026 library proposal. This is an
adaptation, not an upstream library release.

Existing curvature control remains the default. Explicit `FordLateralMode=1`
selects angle control next drive; the saved choice persists when unavailable.
Only this selector is exposed. Fixed defaults and bounds live in
`params/manifest.json`; pinion-yaw correction and curvature-primary tuning are
outside this library. Angle lane-centering trim is available as a default-disabled
core capability, separately sourced from BluePilot bp-dev
`e22afa6be9b881fa784c92ebb316db47728a3d81`; it adds no public settings.

`core/` accepts scalar/model inputs without openpilot, Params or messaging
imports. `can/` owns encoding, `safety/ford_bp.h` owns native enforcement, and
`hosts/starpilot.py` connects the host. `params/protocol.json` generates the wire
constants. The folder is vendored without submodules, LFS or an external runtime.

## Admission

Classic: Bronco Sport Mk1, Escape Mk4, Focus Mk4, Maverick Mk1, Explorer Mk6.
CAN FD: Escape Mk4.5, Expedition Mk4, F150 Mk14, F150 Lightning Mk1, Ranger Mk2,
Mustang Mach-E Mk1.

Exact classic safety parameters 32/33 map to angle 128/129; CAN FD 18/19 and
66/67 map to 130/131. Parameter 131 requires DEBUG; RELEASE retains stock 130.
Longitudinal, radar, fingerprint and parser policy remain host-owned. Admission
uses the final CarParams contract, not brand or steering-control enum alone.

AOL, alternative experiences, Transit, Edge, Mondeo, SecOC, passive, dashcam,
notCar and unsupported static flags are excluded. Auxiliary noOutput requires
parameter zero; production deployments with two Pandas remain unqualified until
actual startup, bus routing and public acknowledgments are verified.

## Safety design

The extension uses small Ford hooks without changing shared safety headers or
existing curvature namespaces. Active steering requires ordinary controls
permission, healthy physical RX and a fresh matching public Panda acknowledgment
of safety parameter, alternative experience, controls, RX validity, heartbeat and
faults. Cruise, gas/brake, checksum, counter, quality and freshness checks apply.
Neutral mode cannot grant permission.

The BluePilot reset-bypass latch is omitted. Rejected frames preserve accepted
actuator history and withdraw the shadow lease; accepted neutral commands or
permission withdrawal reset history. Lost counters recover through neutral
resynchronization. Version or checksum failure cannot fall through to curvature
control.

Active frames carry neutral curvature, offset and curvature rate, with checked
mode, ramp, precision, path angle, counter, checksum and cadence. Native enforcement
checks the shadow against the actual path across gains 0.95–1.3, bounds both by
`min(0.02, 2.4114/v²)`, and bounds the full actual-curvature interval against
measured curvature above 10 m/s. Actual path also obeys the 3.5886 m/s³ equivalent
jerk limit and rolling message-rate limit. Core quantization and timing margins
keep packed commands inside these bounds; an impossible intersection is neutral.

The versioned 0x3CA announcement preserves StarPilot's existing byte 4 bit 1
curvature flag and requires it clear in angle mode. It carries a counter, signed
shadow curvature, protocol version and checksum; its lease expires after 60 ms.
The shadow derives from the final path after rate limiting and saturation.

Control computes at 20 Hz, announces through 33 Hz LKA, then sends the latest
announced result at 20 Hz, adding at most one steering tick. Permission withdrawal
sends neutral immediately. Human-turn recovery uses bounded neutral blips without
a native bypass. The retained Dom factory steering delay is 0.22 s; pinned
BluePilot uses 0.20 s.

These stricter native limits and versioned metadata intentionally differ from
BluePilot 7.0. Identical bytes or safety decisions are not claimed for affected
commands. Runtime and physical ECU qualification remain pending.

## Attribution and notices

See `CREDITS.md`, `ORIGIN_HISTORY.tsv` and the project `THIRD_PARTY_NOTICES.md`.
Both upstream MIT and Custom MIT notices are retained verbatim in `LICENSE`,
`LICENSE.md`, `upstream-root-LICENSE` and `upstream-root-LICENSE.md`. The maintainer
reports author permission to use this adaptation under MIT. Both published notices
remain intact.
