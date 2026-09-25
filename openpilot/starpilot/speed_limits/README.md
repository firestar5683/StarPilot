# Speed-limit decisions

This package combines decision policies with the SLC runtime in card and
plannerd. `feature_runtime` starts optional owners from saved preferences and
finalized vehicle capabilities. Each owner separately checks current source,
clock and control authority. Replay flags remain available for isolated tests.

SLC defaults off. Supported dashboard parsers provide OEM observations when the
vehicle supplies the required messages. Missing, stale and explicitly absent
observations remain distinct. Map, navigation and online providers are not yet
connected as control sources.

Vision uses the pinned camera-sign models when Vision is selected and either
Speed Limit Controller or Show Speed Limits is on. Registered Ioniq 6 and GM
sessions can display camera signs. Speed control additionally requires a
registered system-longitudinal owner, an enabled SLC preference and fresh driver
confirmation for each new sign episode or changed limit. Factory-cruise and
display-only sessions never gain speed authority. Source loss clears an accepted
limit; old dashboard episodes are never adopted as new-drive observations.

Saved preferences are decoded strictly before use. A malformed Boolean, source,
number or unreadable setting disables SLC without rewriting the saved bytes.
Only missing settings use defaults; corruption cannot silently remove confirmation
or change speed units. Without an adopted offset document, the seven legacy
`Offset*` values still use the saved display unit for conversion and band
selection. The final band ends at 44.2 m/s (imperial) or 38.9 m/s (metric);
the offset is zero at and above that boundary, matching the frozen controller.
The earlier open-ended repeat of `Offset7` had no reviewed rationale and was a
migration discrepancy.

An optional versioned `SLCOffsetSchedule` document holds seven signed SI offsets
and eight SI band boundaries. Its tail is always zero. When present and valid,
it is the only numeric offset authority: old `Offset*` bytes and `IsMetric` are
ignored for control, even if malformed. A malformed document or the explicit
`needs_review` state disables SLC without falling back to legacy values or
rewriting the saved control bit. The document helper exposes strict decoding,
serialization and pure adoption of a currently valid legacy schedule. Native
settings UI adoption and display-unit writes are a separate pending integration;
this backend does not write Params.

All transport additions use cereal's reserved custom messages. The official
vehicle schema is unchanged. Slot 9 retains its six historical model-status fields
at ordinals 0–5 and appends SLC state at 6–30. Slots 12–15 carry UI actions,
physical receipts, dashboard observations and one-shot cruise commands. Historical
custom slots already used by the fork remain reserved for compatible restoration.
Earlier unreleased Domathon SLC development recordings require their exact schema
for replay; this layout does not reinterpret them. It also does not convert
recordings made with older divergent vehicle schemas.
The Vision envelope restores the historical `StarPilotModelDataV2` at Event
ordinal 111 with its original turn-direction field and enum, then appends an
independent typed Vision payload. The old ordinal 137 remains reserved and empty.

## Camera sign source

Manager starts the optional onroad VisionIPC producer and plannerd subscribes to
`slcVisionObservation` for an admitted saved source choice. The producer uses
the pinned US detector/classifier ONNX files documented in
[`vision/assets/PROVENANCE.md`](vision/assets/PROVENANCE.md). It reads camerad's
road or wide-road NV12 stream, copies and releases each VisionIPC buffer, and
publishes a typed observation. Source selection does not change stock engagement.

The runtime distinguishes source availability, display permission and speed
control permission. A display-only source can populate the sign widget but
cannot create a planner ceiling or cruise command. Controlling a detected limit
requires current longitudinal authority and matching driver confirmation, even
if general SLC confirmation is off. Unqualified replay observations remain
isolated from normal speed control.

Camera EOF uses CLOCK_BOOTTIME; Python receipt and inference completion use
CLOCK_MONOTONIC. The adapter checks paired clocks, including after suspend,
without assuming a fixed offset. Candidate support expires after two seconds;
each message must also be within 250 ms of its captured frame. Camera reconnects
reset sign support and producer identity. Runtime and source tests do not establish
sign-reading accuracy or onroad timing under load.

`selection.select_limit` supplies this reducer with configured source observations.
It preserves priority order, highest/lowest selection, explicit Vision inclusion
and online-only fallback. The [selection contract](SELECTION.md) describes its
eligibility threshold, uncertainty handling and separate adapter obligations.

## Acceptance contract

Call `new_session(unique_session_id, qualified_accepted_history)` once for an
explicit session, then pass each returned `Decision.state` into `step`. A session
ID must not be reused; creating a new state resets rejection and action history.
History supplied by a caller needs a separate schema, origin, and applicability
check. This module neither loads nor qualifies stored history. `history_write` is
an optional proposal produced only by an acceptance; persistence remains outside
the reducer. Its timestamp is session-relative monotonic nanoseconds, not UTC or
a source freshness measurement.

The four observation kinds have different meanings:

| Kind | Caller assertion | Accepted-history fallback |
| --- | --- | --- |
| `VALID` | A source has an eligible, normalized candidate | Previous accepted limit is held while a new candidate awaits a decision or remains rejected |
| `ABSENT` | Eligible sources explicitly have no current candidate | Only when `fallback_previous` is enabled |
| `UNKNOWN` | Evidence is incomplete or cannot be classified | No control target |
| `STALE` | Available evidence fails the caller's freshness contract | No control target |

Only `VALID` carries a `Candidate(source, observation_identity, speed_mps)`.
`ObservationIdentity` explicitly distinguishes three forms:

| Kind | Required identity | Meaning |
| --- | --- | --- |
| `GEOGRAPHIC` | Nonempty `value`, no session field | Source-supplied road/zone identity |
| `PRODUCER_EPISODE` | Nonempty `value`, no session field | Source-supplied stable observation episode |
| `SESSION_VALUE` | Current `session_id`, no free-form value | Source and exact normalized speed within this session; no geographic claim |

The same source, typed identity and exact normalized speed form the candidate
identity. A dashboard producer without road identity can use `SESSION_VALUE`.
It remains stable across dropout and provider switching. Rejected dashboard 45
therefore remains rejected for this session even if a later 45 belongs to another
road; explicit adoption is available to accept it. Do not invent new episode IDs
on signal loss to evade rejection. Geographic or episode IDs require independent
source evidence; selecting a tag does not establish that evidence.

Values must be finite and positive; no comparison epsilon or universal source TTL
is hidden in the reducer. Unit conversion, meaningful rounding, source eligibility
and freshness belong to adapters. `observation_is_valid` exposes structural
validation; its optional `session_id` enforces session-value applicability.
The reducer always supplies its current session. `new_session` rejects prior-session
session-value history without silently rekeying it. Independently qualified
geographic/episode history can retain its original accepted-session metadata.

Rejections are not global cross-source equivalence claims. A rejected dashboard
limit that appears from a map is a different candidate, even with the same identity
string and numeric speed. It still follows directional confirmation relative to
the last accepted limit. Returning to the original rejected identity stays
rejected. Cross-provider canonical road identity has not been implemented.

State keeps current observation, pending decision, rejected candidates and last
accepted history separately. A rejection never updates accepted history. Source
loss, reconnection and intervening sources retain rejections. A changed identity or
speed is a new candidate. Rejection storage is bounded at 256 distinct candidates;
attempting another rejection latches all control output off until an explicit new
session. It never evicts a rejection and later silently accepts that candidate.

## Authority and confirmation

`Authority` supplies the selected mode (off, lateral-only, longitudinal-only or
combined), longitudinal owner (none, system or stock), each effective host axis,
stock ACC activity, and explicit full disengagement. Contradictory combinations
fail closed. Selected mode and assigned owner can remain set while inactive.
Full disengagement requires both host axes and stock ACC to be inactive; inactive
axes alone do not imply full disengagement.

A control target or consumed driver action requires active system longitudinal
authority in longitudinal-only or combined mode. Stock ACC never gains a target
through this reducer. Explicit full disengagement accepts an eligible candidate
without a button or control output, unless that candidate was rejected. With no
longitudinal authority and no full disengagement, history is preserved and any
required confirmation is paused. `display_only` shows a valid candidate but emits
no target, acceptance, fallback or consumed action, and clears pending confirmation.

Lower and higher limits have independent confirmation settings. The first limit
uses `confirm_higher` as an explicit initial-limit policy. Exactly equal speeds
need no directional confirmation even if source/identity changes; accepting the new
identity can still propose a history update. Adjacent representable unequal
floating-point values are changes and follow the corresponding direction policy.

Confirmation expires after 30 seconds of accumulated authoritative active-long
time. An interval counts only when the same pending decision exists and both
endpoint samples have active longitudinal authority. A pause/resume boundary does
not count the uncertain transition interval. Callers must deliver authority
transitions; two active endpoint samples cannot reveal an omitted inactive period.
Equal timestamps are allowed; negative, non-integer or reversed clocks fail
closed, clear the prompt and preserve history/rejections. A valid long gap is
counted, because freshness has already been classified by the caller.

This accumulated timer, uncertainty suppression, stable rejection retention and
authority-gated button handling are explicit design choices requiring integration
review. They are not claims of exact prior-runtime behavior.

## Driver actions and outputs

Each action includes session ID, monotonic sequence ID, pending decision ID and
accept/reject kind. A new same-session sequence is watermarked even when an action
is unrelated, ineligible, or another input is invalid. A foreign session cannot
advance the current sequence watermark. Repeated or older events are acknowledged
but never consumed. A decision must have appeared in the previous state; an action
cannot guess a newly created prompt ID. Loss or change of the candidate creates a
new decision ID. An eligible driver action at the timeout boundary takes priority.

`ActionReceipt.acknowledged` means an event was identified; only `consumed=True`
means SLC handled that input. The adapter must not swallow ordinary cruise actions
based on acknowledgment or watermarking alone. Malformed actions produce an input
error and no receipt. The runtime arbitrates identified physical receipts and UI
requests. The live UI action publisher is not yet connected.

## Explicit adoption

`AdoptRequest(session_id, sequence_id, presentation_id, candidate)` is separate from
pending confirmation. It can accept the currently displayed candidate after a
rejection. Each valid observation produces `state.presentation`; its ID remains
stable until the candidate changes, disappears or an invalid input clears the
context. An adoption must match the exact candidate and a presentation from the
prior reducer output. Guessing the ID of a same-frame arrival is ineligible.

Adoption requires active system longitudinal authority, ordinary control policy,
and an unexhausted session. It removes only the matching rejection, accepts that
candidate, clears pending confirmation, and emits an `AdoptionProposal` with an
explicit action sequence and presentation ID. The proposal asks the composition
and runtime adapters to clear override intent and reconcile cruise selection.
The acceptance reducer itself performs neither action. An already accepted
candidate still produces this proposal, but need not produce a duplicate history
write. The initial proposed
speed has no offset or cluster conversion; those require a later effective-target
adapter bound to the same accepted context.

`adoption_receipt` distinguishes acknowledgment from consumption. Adoption and
confirmation share one sequence watermark. Supplying both in one step is an
ambiguous input error: neither is consumed, no output/effect is proposed, and
valid same-session IDs are watermarked. Replays, foreign sessions, changed or lost
presentations, display-only mode and missing longitudinal authority cannot produce
an adoption effect. Exhausted rejection storage requires a new session; adoption
cannot bypass its latch. Eligible adoption precedes confirmation timeout handling.

An ineligible adoption does not disable independent observation processing. For
example, the existing fully-disengaged autoaccept rule can still record a new,
unrejected observation, while its adoption receipt remains unconsumed and no
reconciliation proposal is emitted. Callers must inspect the receipt/proposal,
not mistake a history update for successful adoption.

The [causal action ledger](ACTIONS.md) preserves ownership across delayed effects.
The runtime binds it to physical receipts and the override policy. Card consumes
a qualified confirmation on press and suppresses its release and held repeats.
If a cached prompt cannot be qualified, the ordinary cruise-button path handles
the press. A consumed press is never replayed later.

Only card changes its software-owned selected speed. A higher accepted limit or
identified adoption may produce a one-shot command. Card requires matching
session, source episode, presentation, current selected speed and active system
longitudinal control, with bounded message age and no unrelated button action.
Stock PCM cruise is excluded. Applied and rejected receipts are separate from
limit acceptance; accepting a limit does not prove a selected-speed change.

`control_target_mps` is optional decision data, never a cruise or actuator command.
A missing target must clear any adapter's previous SLC contribution; callers must
not retain an old target on an error. `errors` is explicit and history proposals
are absent on errors. Invalid state remains inert until the caller replaces it
with valid state through an explicit lifecycle decision.

## Remaining integration

Map lookahead, Vision control qualification, online provider permissions and their actual
producers remain separate work. The live UI action publisher, stock-button speed
control, replay of recorded vehicle routes and device timing are also outstanding.
Stock ACC ownership does not grant permission to change its setpoint through this
API. Runtime tests and source compatibility checks are evidence for their scoped
contracts, not whole-feature migration or fleet safety.
