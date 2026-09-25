# Causal cruise-action contract

`action_arbitration` preserves the relationship between an input action and its
later cruise-speed effects. It does not infer a button press from a scalar speed
change, authorize control, read messages or change cruise speed. The runtime
adapter connects it to physical receipts, UI requests and the override policy.

The input adapter must establish real action identities and final ownership.
If a vehicle exposes only a scalar change without a reliable button/effect
association, this capability remains unresolved. A guessed frame window is not
a substitute for causal evidence.

## Lifecycle

1. Create `new_ledger(unique_session_id)` once for a session. Use that same session
   for acceptance and action sequencing; never reuse it across drives.
2. `BeginAction` records a monotonically increasing action ID, its observed origin
   and an explicit `context_id`. Origins distinguish a driver cruise action, another
   driver action and an automatic operation. The context must bind the adapter's
   accepted-limit and authority/policy episode. This ledger carries it unchanged;
   the override policy must check current applicability independently.
3. `ResolveAction` supplies a final disposition after arbitration: unconsumed
   driver intent, consumed by SLC, automatic or unrelated. `resolve_acceptance`
   instead binds a matching final receipt from the actual acceptance reducer.
   It checks session, action ID, action/decision timing and receipt consumption.
   An acknowledgment, replay, missing receipt or errored decision cannot establish
   final ownership. A final unconsumed receipt does not swallow a real cruise action.
4. `CruiseChange` supplies its own increasing effect ID, causal action ID, and
   normalized previous/selected speeds. It emits immutable classification data,
   including the original action time and context. Multiple effects can refer to
   one action until explicitly completed. Effects may arrive after other actions
   have begun or resolved; they keep their own origin.
5. `CompleteAction` releases the transaction after its effects have been resolved
   or explicitly abandoned. Button release alone does not prove completion.
   Effects arriving after completion are unresolved and cannot recreate intent.

Consumed confirmation/adoption transactions remain consumed regardless of delay;
there is no one-frame Boolean or elapsed-time guess. Automatic and unrelated
effects likewise cannot become driver intent. A first scalar sample, an unchanged
speed or an unknown origin never establishes a new driver selection. An effect
received before ownership resolution is explicitly unresolved and watermarked;
it is not retroactively emitted as fresh intent when resolution arrives later.

## Bounds and failure behavior

The ledger holds at most 128 active transactions. Explicit completion frees
capacity. Exhaustion latches `reset_required` without forgetting consumed actions.
Conflicting final dispositions, impossible origin/disposition pairs, malformed
events and reversed clocks also require a fresh session. Duplicate action/effect
IDs are acknowledged by status without reopening transactions or emitting an
effect twice. Foreign sessions cannot advance current watermarks or close actions.

Invalid state is inert and remains unchanged for diagnosis. A latched ledger emits
no classified changes. Callers must inspect `status`/`errors` and clear any pending
interpretation; lack of new data must not be treated as a retained control target.
The ledger has no actuator output or persistence proposal.

## Separate policy and adapter obligations

`DRIVER_INTENT` means a supplied, positively associated, unconsumed cruise change;
it does **not** mean that an SLC override is currently eligible. Both increases
and decreases remain visible. The ordinary above-limit override and qualified
stock-setpoint policies have different rules and must retain that distinction.
They must check current longitudinal authority, mode, display-only state, source
freshness, accepted/effective target, action context and origin eligibility before
using a classified change. Context changes must invalidate old applicability;
an action begun while inactive cannot become eligible merely because its effect
arrived after re-enable.

Offsets, cluster conversions, pedal behavior, suspension/rearm policy and vehicle
button handling are not implemented by this ledger. All speeds at this boundary
must use one documented normalized coordinate. The acceptance helper and tests
establish pure composition, not a complete physical causal association or a fix
deployed in the current controller.
