# Speed limit override contribution

`overrides.step` is a pure reducer for the system-owned longitudinal SLC target. It
returns a proposed contribution in m/s, not a vehicle command or final planner
target. It requires the actual `acceptance.Decision` from the same session and
monotonic timestamp. The decision carries the authority and policy snapshot used
by acceptance; a mismatch, invalid decision, or inconsistent accepted target is
an error and yields no contribution. `UNKNOWN` and `STALE` observations have no
target. Explicit `ABSENT` may use only the actual acceptance decision's qualified
previous-limit fallback. The selected-speed and pedal observations carry explicit
validity; missing or stale evidence suppresses output. Valid ego speed may be
zero at standstill; selected and accepted limit speeds remain positive.

The reducer issues a `Context` in an eligible prior output. A caller can place
its `context_id` in `BeginAction`. A fresh ledger `ClassifiedChange` can affect
persistence only if it is `DRIVER_INTENT`, has a changed previous speed, matches
that prior context and current selected-speed observation, and originated after
the context was issued while the reducer remained eligible. A selected-speed
number alone cannot arm intent. Same-session effect IDs are watermarked even when
ineligible, including while display-only. `EventReceipt.acknowledged` means the
event was observed; `consumed` means qualified intent changed override state.
Automatic, unresolved, consumed, foreign, replayed and completed effects never
arm persistence. The action ledger supplies causal classification; the override
reducer never guesses a physical button association or time window.

The reducer rotates context on accepted numeric target change, temporary
inactivity and re-enable, mode or owner change, and each new consumed adoption.
An accepted identity or provider change at the same numeric speed retains both
intent and context. This policy uses the numeric accepted target as the override
boundary; acceptance still owns candidate identity and rejection history. A new
lower accepted target clears persistence before processing the event or emitting
output. A higher target preserves it until the target reaches the selected speed.
Pending and rejected candidates leave the accepted target unchanged. Adoption
clears persistence once per action sequence and invalidates previous contexts;
the current pedal is then evaluated normally. A delayed reconciliation effect
remains classified `SLC_CONSUMED` by the ledger.

The current valid pedal press contributes the current ego speed when above the
accepted target, temporarily preceding persistent intent. Releasing the pedal
reveals retained persistence. Pedal speed is never latched. Temporary inactive
system-longitudinal authority suppresses output immediately and invalidates the
origin context. Persistent intent remains latent for less than 750 ms in the same
mode and owner; at or after 750 ms it clears before a resumed output. Mode or
owner changes clear immediately. Display-only never contributes or consumes an
effect. Stock setpoint buttons are a separate capability and output domain.

Malformed evidence, a reversed clock, or an invalid acceptance snapshot clears
intent and origin context, then latches `reset_required`. Further calls in that
state remain inert. Recovery requires `new_session` with a distinct session ID
and a fresh acceptance/ledger lifecycle; old effects belong to the prior session
and cannot arm the new one. A malformed `State` itself returns an explicit error
without trusting or modifying its fields.

This unit assumes normalized m/s inputs and supplies no source TTL, Params,
CAN, or vehicle adapter behavior. The accepted decision is still the gate:
`control_target_mps=None` cannot be bypassed by stored intent.

An optional qualified `speed_domain.DomainResolution` now supplies an effective
limit threshold and same-frame raw/cluster deltas. Without it, the existing
zero-offset identity-coordinate behavior remains. With it, the reducer compares
driver-selected and pedal speeds in cluster coordinates against accepted limit
plus offset, while retaining causal selected intent in raw m/s. A lower raw
accepted limit still clears intent; a higher effective threshold clears intent
when it catches the converted retained value. Offset decrease alone cannot arm
intent. An effective-threshold change rotates action context, while cluster
delta jitter alone does not. Unknown or stale coordinate evidence suppresses
contribution; malformed or mismatched context latches the existing session
reset contract. [Speed domain](SPEED_DOMAIN.md) describes construction and
planner-coordinate conversion.
