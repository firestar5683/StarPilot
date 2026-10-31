# Speed Limit Controller

SLC uses the ordinary cruise set speed as its only vehicle-speed target. A qualified
limit from the selected Dashboard, Maps, or Vision source is an input to adoption.
Acceptance applies the configured offset within the existing 8–145 km/h cruise
bounds and sends a qualified command to card,
which owns `vCruise` and `vCruiseCluster`. SLC supplies no separate planner ceiling.
Lead, curve, stop and actuator safety constraints retain their existing owners.

## New limits and adoption

On SET or RES engagement, a currently qualified limit from the selected source
initializes SET with its existing offset and mph/km/h rounding, even with Automatic
adoption off. Sources keep updating while disengaged. This explicit adoption clears
the matching prompt, decline or set-speed override; later limits keep the normal
confirmation policy. Without a qualified current limit, RESUME restores the previous
SET and normal SET initialization applies. An early Maps proposal does not replace
the current road's limit at engagement. Toyota still requires native cruise capacity
and release approval before applying the target.

A different numeric limit from the selected source starts a new decision, including
while a set-speed override is active. A source/road identity change at the same
numeric limit does not start another decision. A decline remains effective across
a source gap or same-value provider change; a later different limit starts a new
window, including when an earlier numeric limit returns.

A different provider proposing a different numeric limit must remain the proposed
replacement for two seconds before confirmation or automatic adoption. A competing
qualified reading cancels that check; missing readings do not restart it. Adoption
still requires fresh evidence at the end. Same-provider limit changes, explicit
driver adoption and latched early Maps proposals keep their existing timing.

While StarPilot owns speed control, a proposed limit whose adjusted, rounded target
already matches both current SET values is recorded without another confirmation
or cruise command. The comparison uses the same mph/km/h rounding as Card, not
actual traveling speed. A presented Accept or Decline takes priority, and a decline
remains effective for that proposal. If SET reaches the target during a prompt,
the prompt closes without changing speed. An earlier command must first settle,
and SET must be observed after its receipt or expiry, before alignment is trusted.
Received-limit memory still manages proposal changes and declined choices.
An expired confirmation stays declined even if SET now matches. Changing only
display units renews pending actions while preserving accepted limits, declines, manual
overrides and the already applied SET.

With Automatic adoption on, qualified new limits are adopted immediately.
With it off, the stationary confirmation card gives two gentle purple pulses
(700 ms each, separated by 200 ms), then rests until the 3.2-second cycle repeats.
Only the lower part of the card pulses; the speed and source remain steady.
The arrow remains relative to vehicle speed.
Outside manual confirmation, large UI uses the same US or Vienna sign at 1.25×
scale beside SET speed.
US signs share a cached antialiased white outline with a transparent interior;
the offset fits inside the fixed sign height on both screens.
Both sign styles identify the displayed source: DASH for Dashboard, OSM for offline
Maps, and VISION for the vision model. Explicit Mapbox readings in historical
replay use NAV; unidentified sources keep SPEED. Retained readings keep their
original source label.
Both styles place only this source above the number, beside any pending arrow.
The source and arrow share a centered row; all sign contents use the same geometry
on both screens. Small arrows are baked at double resolution and text is aligned
to final pixels for clear native rendering.
Steering-wheel + accepts and − declines. Tapping the sign opens the same
Accept / Reject choices on either native screen. Manual confirmations appear only
while system longitudinal control is engaged, including a temporary accelerator
override. Disengaged and AOL lateral-only modes keep displaying limits without
prompting. Losing longitudinal engagement cancels the pending choice without
declining it; re-engaging starts a fresh choice if needed. A pending manual choice
expires after ten monotonic seconds while engaged, including source gaps. The same
decision, card and expanded controls remain during a gap, with Accept disabled and
an unavailable label. Reject still dismisses that decision. Recovery renews the
action presentation without restarting the decision, deadline or attention cycle.
Wheel confirmation presses remain consumed during a gap, so they cannot become
ordinary SET adjustments. An unavailable Accept is never queued for recovery.
Decline and timeout leave set speed unchanged. An action at the exact deadline
can still complete its presented decision; a later action cannot accept it.

The existing saved `SLCConfirmation` bit is retained: `0` means Automatic adoption
on and `1` means off. Both native settings layouts show the inverse as Automatic
adoption. Legacy directional confirmation and override preferences do not change
this confirmation policy.

## Optional early adoption

The existing SLC settings page adds **Adopt limits early**: Off by default, or
1–10 whole seconds (`SLCAdvanceSeconds`). It applies to both increases and
decreases from offline Maps. Other sources keep their current-limit behavior.
The upcoming Map proposal must win the configured source-selection policy.
There is no new onroad widget, caption, or countdown. The existing New Limit
confirmation presents the proposed limit and its own offset; the ordinary sign
and source readings continue to describe the current road.

A fresh, qualified along-road distance becomes eligible when
`0 < distance <= carState.vEgo * seconds`. Only physical vehicle speed is used;
SET, cluster speed, acceleration forecasts and wheel-distance propagation do not
estimate arrival. A first offer requires motion and active system speed control.
This is approximate timing, not a promise to reach the target speed at the sign.

The first offer latches one boundary encounter. Slowing or stopping does not
retract it or restart the existing ten-second confirmation deadline. Source loss
removes authority and retains the pending choice; fresh recovery of the same
boundary uses the original deadline and a current presentation. Losing longitudinal
engagement cancels an unanswered choice; re-engaging starts a fresh deadline.
Decline, expiry, manual override and completed application survive the boundary
becoming current.
An unchanged approach limit cannot be offered again solely because the preview
is lost or disabled. Current-source evidence, command freshness, expected SET,
driver-button checks and Toyota's native capacity/release checks still apply.
The configured adopt wheel action continues to adopt the displayed current limit
when no confirmation is pending.

Timing-only edits preserve the runtime session and driver decisions. Off cancels
unapplied advance work and leaves an applied SET intact; normal current-limit
behavior resumes at the boundary. Offset and unit edits retain their existing
meaning. A short lower-limit zone can immediately qualify its exit increase;
there is no hidden minimum dwell time. GPS uncertainty, missing map data and an
unresolved continuation can prevent advance adoption; ordinary current-limit SLC
remains the fallback. No accepted SET is rolled back just because data vanishes.

On the wire, `slcState.speedLimit` remains the current selected observation.
`upcomingSpeedLimit` and `upcomingBoundaryId` identify a qualified early proposal;
an early `slcCruiseCommand` must carry the same boundary ID. The boundary record
is in memory for this runtime session, not a saved decision database.

Only a finite positive source observation can propose a limit. Missing, stale and
unknown observations stay distinct. Source loss retains an engaged manual choice
until its original deadline and creates no authority to change set speed. Automatic
adoption retains accepted history and does not reapply an unchanged limit on
recovery. While the publisher remains fresh, the widget retains the latest
received limit, offset and original source with an unavailable status, independently
of accepted history. Cruise continues using its current SET, including a driver's
manual adjustment. Source loss creates no speed target and cannot select a
different Conditional Experimental or Conditional Chill mode. Normal mode triggers
and live braking safeguards remain with their existing owners.

Previous accepted limit and its legacy Experimental fallback are retired.
`SLCFallback` remains registered without a default solely to preserve existing
saved bytes for older versions; current code neither reads nor writes it.
Missing, 0, 1, 2 and malformed old values all use the same behavior above.
Old Quick Select assignments remain saved but unavailable.

Offsets use only the saved `SLCOffsetSchedule`, with fixed physical speed ranges
and adjustments. Without a saved schedule, all seven ranges start at zero and
can be edited immediately in Galaxy, Large UI, or Compact UI. Retired
`Offset1`–`Offset7` values are ignored; users with only those values must configure
their offsets again. Existing schedules are preserved, including across display
unit changes. There is no separate offset-adoption step.
Converted offsets display as whole mph or km/h, and edits use whole units.
Unit switches retain the saved precision so repeated conversions do not drift.

Offset-only edits preserve accepted and
rejected state and renew action identities. A changed offset can update the set
speed of the accepted current limit; source loss defers this command until that
limit is qualified again.

## Set speed and accelerator

A qualified manual change to a different set speed marks an override, for increases
and decreases. An X crosses the sign while override is active. Returning to the
applied set speed clears it, using card's receipt to account for whole-unit rounding. Adopting
a new limit also clears it. Adoption retains the ordinary buttons' 0.1 km/h internal
precision, including for mph targets. New-limit decisions continue during override.

Ordinary software SET adjustments use the saved short-press and held-press intervals
on every make, including PCM vehicles while SLC owns SET. Toyota uses Swap Toyota
Cruise Steps for both native cruise and software SET: off selects short 1 / hold 5,
and on selects short 5 / hold 1. Other makes use CustomCruise and CustomCruiseLong.
Confirmation presses and native resume keep their existing meanings; they do not
also apply an interval step. Toyota's native cruise ceiling still limits software SET.

The accelerator temporarily allows higher vehicle speed without changing set speed
or creating an SLC override. Adoption and confirmation can update software set
speed while accelerator override temporarily suspends actuator output. On release the ordinary planner approaches set speed
using the currently selected braking profile. Existing lead and stopping constraints
continue to apply.

The onroad screen does not offer a separate button to reapply the displayed limit.
The configured wheel action to adopt a limit remains available, as do the normal
set-speed buttons and confirmation for a different limit.

With SLC enabled and system longitudinal control available, card owns software set
speed even on PCM vehicles; PCM still owns engagement. Native PCM setpoint changes
cannot overwrite an adopted software set speed. When SLC is off, the original PCM
set-speed path is restored. Stock longitudinal control never gains SLC commands.

## Source and command qualification

Source selection, registered vehicle capabilities, strict saved-setting decoding,
Dashboard parser freshness, Maps road qualification, and Vision clock/inference
checks remain in their source adapters. Vision still requires its separate display
and control qualification. Online providers are not connected as live control
sources. See [selection](SELECTION.md), [Maps](MAP_SOURCE.md), and the pinned camera
[model provenance](vision/assets/PROVENANCE.md).

Vision interprets sign numerals using the existing Metric setting: km/h when on,
mph when off. The producer converts once to m/s for both UI layouts and cruise SET.
Changing Metric clears Vision's retained sign and supporting reads, including
in-flight results and cached heartbeats; fresh evidence must confirm the next limit.
The current applied SET remains unchanged by this reset.

Every action binds the current session, decision and presentation. The causal ledger
keeps consumed confirmation presses out of the ordinary cruise-button path, through
held repeats and release. Accept and Reject cannot follow a replaced source
candidate, including a replacement at the same numeric speed in the action's
planner cycle. Such a replacement preserves the decision and its deadline but
renews its presentation. Card checks active system-longitudinal authority, command
and state age, matching presentation and source, expected current set speed, legal
speed bounds, and intervening buttons before applying a command once. Dashboard
commands also match the local OEM episode. Maps and Vision commands bind the fresh
qualified planner presentation. A command receipt distinguishes application from
limit acceptance. Rejected or expired commands may retry with current evidence
while the accepted limit and expected set speed remain current, with no pending
decision or manual override. Applied commands are not repeated.
Declining or timing out a returned limit never revives an earlier adoption command;
the historical adoption remains recorded independently of the new rejection.

Transport changes append to reserved custom messages. `SlcState` retains automatic
pending metadata at ordinals 51–52 and latest-received display metadata at 53–55.
`SlcCruiseCommand` appends its source at 14 and
a bidirectional adoption kind; historical fields and enum ordinals remain reserved.
Official vehicle schemas are unchanged. Historical SLC ceiling fields stay empty.

Host tests cover decisions, source validation, commands, cruise buttons, profile
selection and both UI layouts. Synthetic captures and host tests do not establish
camera accuracy, device timing under load, or onroad behavior.
