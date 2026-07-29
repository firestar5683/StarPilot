# Kia EV9 preinit longitudinal ownership

This directory documents the EV9-only production candidate for taking ownership of the ADAS ECU's normal CAN output
before Linux is available, continuing that ownership through StarPilot startup, and restoring stock ownership only at a
proven vehicle-OFF boundary.

The reviewed hazards, route evidence, failure lessons, and remaining release
matrix are in [PREINIT_SAFETY_CASE.md](PREINIT_SAFETY_CASE.md). The full
route-by-route experiment journal is preserved on the pre-squash backup branch;
its stage, probe, DTC-capture, and one-off deployment instructions are obsolete.

## Production scope and status

The dedicated firmware and host path are restricted to the exact Kia EV9 configuration currently under validation. Do
not select this firmware for another Hyundai/Kia model or broaden its identity, diagnostic, or CAN allowlists to add a
vehicle. A future model must receive its own reviewed profile and build target.

This is still a production **candidate**, not a completed vehicle release. The consolidated firmware, one-way handoff,
orange cluster indications, OFF restoration, and dash reconstruction
pass bench and software regression tests. Direct cold boot, immediate warm restart, remote-climate entry, and fully
locked fob remote start now pass parked vehicle validation with clean next-cycle rearm. Do not use the candidate on road
until the remaining validation matrix passes.

Build all four selectable EV9 images as one coherent set:

```sh
scripts/laptop_device_build.sh scons panda_ev9_long_preinit_firmwares
```

Deploy all four `panda/board/obj/panda_h7_ev9_long_preinit*.bin.signed` files together. Building or copying only the base
filename is unsafe because `HKGRemoteStartBootsComma` and the ignition-line policy select a different filename at runtime.

The production controls are deliberately small:

- `EV9LongPreinitPanda` arms selection of the dedicated Panda image and defaults off.
- `KiaEv9ClusterSideObjectsEnabled` controls validated side-object display and defaults on.
- `KiaEv9ClusterLaneChangeAnimationEnabled` controls the optional lane-change animation and defaults off.

Installing or retaining the dedicated firmware additionally requires the exact EV9 fingerprint and cached ADAS identity,
openpilot longitudinal, `OpenpilotEnabledToggle`, `AlphaLongitudinalEnabled`, and the dedicated EV9 Panda safety
configuration. A failed or ambiguous host gate selects the normal Hyundai CAN-FD image/path. An image that is already
resident necessarily executes before Linux on a cold wake, so its independent current-cycle firmware identity gates are
the authority that prevents suppression on the wrong vehicle.

There are no production stage, probe, DTC-capture, test-SCC, or arbitrary diagnostic switches.

## Architecture

### 1. Resident Panda preinit

The `panda_h7_ev9_long_preinit` image remains powered when the comma SOM is shut down. That resident firmware can reach
the short diagnostic window during a direct vehicle-OFF-to-READY transition, before Linux boots.

For each new wake epoch Panda:

1. Collects a current-cycle EV9 identity proof from CRC-valid bus-0 `0x100`, bus-1 `0x35`, and bus-1 `0xCB` traffic,
   plus a fresh bus-1 `0xA0` sample proving all four raw wheel speeds are at or below the stock standstill threshold.
   Because those IDs and lengths also occur on other HDA2 vehicles, `0x100` must additionally match the complete
   route-backed EV9 body signature; only CRC, counter, brake, and accelerator bits are masked as dynamic. A generic
   Hyundai/Kia HDA2 tuple or moving/stale wheel-speed sample cannot authorize diagnostic TX. The stationary proof is
   retained as fingerprint bit `0x80`; a complete successful EV9 profile therefore reports `0xff`.
2. Remains passive on door, lock, charging, remote-climate, restored-OFF, and generic ADAS wakes even when that complete
   stationary identity is available. Diagnostic TX additionally requires a physical ignition start while the
   powertrain state is still nonterminal; fresh brake, qualified climate takeover, and EV9 `0x35` pre-READY facts retain
   explicit trigger attribution and retry coverage. The global start window is 300 ms, while each UDS request retains an
   independent 50 ms P2 timeout. A late host ELM327 firmware-query mutation is rejected only during this bounded start
   window so it cannot reset the CAN core between identity and diagnostic dispatch.
3. Sends extended-session request `10 03` to ADAS ECU `0x730` and requires the exact positive `50 03` response.
4. Immediately sends CommunicationControl `28 01 01` and requires the exact positive `68 01` response.
5. Confirms that the critical stock ADAS streams actually stopped. A positive UDS response alone is not ownership.
6. Enters `ACTIVE`, maintains Tester Present, and publishes a non-actuating neutral replacement set with continued
   counters and valid Hyundai CAN-FD CRCs.

The managed replacement set is bus-0 `0x100` plus bus-1 `0x12A`, `0xCB`, `0x160`, `0x161`, `0x162`, `0x1A0`, `0x1BA`,
`0x1DA`, `0x1E0`, `0x1E5`, `0x1EA`, `0x200`, `0x345`, and `0x38C`. Physical `0x57A` is not suppressed or replayed.

Malformed/negative responses, identity mismatch, deadline exhaustion, unhealthy CAN controllers, internal TX rejection,
or stock traffic that does not disappear abort the attempt without enabling host actuation. Requests are bounded and
Panda never overlaps unanswered CommunicationControl transactions.

### 2. Host claim and continuation

`pandad` exposes coherent preinit status and timing pages to `card`. The host does not begin normal EV9 output merely
because Panda reports a UDS acknowledgement. It first verifies the exact firmware/profile, suppression state, bus health,
unchanged error counters, and a fresh ownership epoch.

During `CLAIMING`, the host sends every managed replacement, the bus-0 heartbeat, and Tester Present. Panda phase-gates
these attempts, rewrites counters/CRC where required, and records claims only after the frame is loaded into FDCAN
hardware. Slow streams receive bounded reservations so a warm restart cannot remain phase-locked behind resident output.

Panda enters `HANDOFF` only after the complete claim mask is observed at the hardware boundary with healthy managed
buses. During incremental transfer Panda remains the arbiter and fallback: each managed tuple has one admitted wire
publisher, while accepted host tuples may already reach hardware before the full claim is complete. After handoff,
`card` owns the dynamic reconstruction for the rest of the ignition epoch and frames use the ordinary Panda safety path;
resident publication, cadence arbitration, body rewriting, and runtime reclaim stop. Panda retains only rolling-counter
and CRC continuity between the frozen claim retry and live host epochs. The existing phase gate remains for only the
first 500 ms of `HANDOFF`, covering card's 10 Hz observation boundary without allowing 333 Hz claim retries onto CAN.
This claim is intentionally not gated on gear,
standstill, or vehicle speed: only the firmware UDS
knockout must be stationary. A driver may pull away while the comma boots, and the host may adopt the already-suppressed
ECU in motion exactly as the normal openpilot ECU-disable handoff does.

### 3. Host reconstruction and dash

Host reconstruction starts from live pre-suppression templates, preserves vehicle-specific body fields, and continues
stock counters rather than starting a second message epoch. Longitudinal commands retain distinct requested, safety-
bounded, and applied acceleration values. Every current Panda fault and every permanent Panda fault status hard-inhibits
SCC and steering/angle actuation. Panda's temporary fault status is historical for the rest of the MCU boot even after
`fault_recovered()` clears the current bitmap; that empty historical state is not a current fault. The exact startup-
present singleton `faultTemp/interruptRateCan3` may pass the separate 2.25-second recovered-fault policy only to complete
neutral reconstruction and preserve truthful warnings; it never authorizes vehicle actuation while the bitmap remains
set. Actuation resumes only after the current bitmap clears and all ordinary Panda safety checks pass.

The EV9 dash path derives lane geometry, lead/object presentation, speed-limit state, and side-object warnings from fresh
model, radar, native corner-radar, and car-state inputs. Stale or invalid inputs neutralize the affected display; frozen
objects are never replayed. `0x1BA` and its `0x1E5` companion move together. EV9 does not use the unrelated Ioniq 6
`0x3C1` lane-animation path.

The cluster intentionally indicates the real availability boundary:

- Panda `ACTIVE`: orange FCA and orange LKA indicate that stock ADAS functions are unavailable and host takeover is not
  complete.
- Host `HANDOFF`: orange FCA remains because OEM FCA/AEB is still unavailable; orange LKA clears after host ownership is
  established.
- Host/Panda fault after handoff: ordinary Panda safety inhibits unsafe
  actuation and normal process/communication alerts represent a crashed host.
  Resident neutral reconstruction does not restart during that ignition epoch.

OEM FCA/AEB and blind-spot collision-avoidance braking are not preserved while ADAS normal transmission is disabled.
Radar tracks and a clean dash do not imply that those stock functions are available.

## Safety and failure behavior

The EV9 uses dedicated Panda safety model `hyundaiCanfdEv9` (model 36) with the exact EV9 safety parameter and a narrow,
length-specific TX allowlist. Generic Hyundai CAN-FD safety does not inherit the EV9 reconstruction or diagnostic
permissions. The EV9 hook independently requires reconstruction `0x12A` to carry zero torque/assist request and requires
the parallel ACI/FCA emergency-steering fields in direct-angle `0xCB` to remain inactive. The preinit firmware applies
the same neutral invariants plus its own final internal allowlist immediately before hardware TX.

Only the bounded ownership sequence, Tester Present, OFF restoration, and bounded `10 01` default-session cleanup after
abort/restore are part of the runtime diagnostic surface. Production code does not read or clear DTCs and does not
authorize diagnostic requests to the camera, cluster, radar, or EPS ECUs.

Failure handling is intentionally asymmetric:

| Condition | Required behavior |
|---|---|
| Gate/identity/UDS failure before suppression | Abort the attempt; stock remains authoritative; no actuation. |
| Suppressed, Panda `ACTIVE`, host not ready | Panda publishes neutral reconstruction and orange FCA/LKA warnings. |
| Healthy complete host claim | Enter `HANDOFF`; host publishes reconstruction; orange FCA remains. |
| Host crash, stale traffic, queue clear, or openpilot error after `HANDOFF` | Stop host output/actuation through normal openpilot behavior. Keep `HANDOFF`; do not restart resident reconstruction or originate another knockout. |
| Panda current or latched safety/CAN fault | Hard-inhibit SCC and steering/angle commands; do not conceal the fault or promise reconstruction that faulty hardware cannot deliver. |
| Ignition falling edge, off-boundary release, or proven OFF/sleep | Quiesce replacement, send `28 00 01`, and prove restoration by exact `68 00` or complete fresh critical-stock convergence. |
| Reset or brownout while ownership may be active | Enter restore-only recovery; never assume stock ownership from lost RAM state. |

Cached EV9 safety is also treated as untrusted compatibility input. The
production `CarParams` profile is `0x0495`; a cached StarPilot profile may add
only optional AOL `0x0800`. Card canonicalizes that value before republishing
it, and pandad independently masks all other StarPilot bits before installing
`hyundaiCanfdEv9`. This prevents an old generic CCNC/button cache from making
the strict safety hook fall back to `noOutput` during resident handoff.

Route `00000180` exposed a mixed-firmware deployment: the base image was current while the selected HKG-remote image was
stale, so Panda rejected safety model 36. Route `00000181` then proved that the original "route-backed" heartbeat identity
body was actually a returned host replacement, not a physical EV9 frame. Production identity now combines invariant bits
mined from physical `0x100`, `0x35`, and `0xCB` bodies across routes 128/144/146/148/16d/16e/170/181. The warning rewrite
is also part of the firmware neutral-body allowlist; a fresh native `libpanda` rebuild is required before firmware tests.

Route `00000182` exposed a separate production-rebase regression: repeated high-rate ADAS tuples filled the deferred RX
ring during startup CAN/safety configuration and displaced the first pre-READY `0x35` identity frame. The resident state
therefore completed identity only on terminal READY and correctly sent no UDS request. The ring now coalesces repeated
CAN-FD tuples while retaining each tuple's earliest pending sample, with separate masks for normal and rearm epochs;
distinct diagnostic-event overflow remains fail-closed. This preserves the working pre-rebase trigger sample without
moving replay/state work back into the FDCAN interrupt.

Route `00000183` then proved the coalesced identity/early trigger, but exposed a second rebase ordering defect: resident
identity completed while pandad was temporarily in ELM327 firmware-query safety. The diagnostic timeout started when
`10 03` entered software, although the CAN-core transition held it until its `10 01` cleanup reached hardware in the same
batch; the ECU's exact `50 03` arrived 21.464 ms later and was therefore ignored. Startup dispatch now installs and
verifies exact `NOOUTPUT` before enqueueing `10 03` or starting any diagnostic clock. Active/HANDOFF EV9 safety behavior
is unchanged.

Route `00000184` exposed the remaining production-rebase scheduler regression. The exact route-17a working archive
serviced preinit directly from each CAN RX; the production queue instead consumed only four events from the outer Panda
main loop. Once power saving disabled, that loop spent roughly 0.5-0.8 seconds inside each blocking LED fade. The
route-184 firmware timestamps prove the complete physical EV9 identity arrived within 152.905 ms, but its retained
`0x35` event was not consumed until about three seconds later. No `10 03` was sent; firmware failed closed with
`ABORTED/0x23`, zero attempts, and a deadline miss.

Route `00000185` showed that merely polling the deferred queue during the LED fade was not equivalent to the proven
implementation. It did enqueue one `10 03`, but no `50 03` was accepted before the single 50 ms timeout and no warning
reconstruction began. The production firmware therefore restores the exact route-17a/17b scheduling architecture:
validated physical CAN RX directly drives identity, diagnostic response handling, and preinit service at the hardware
receive boundary. The later physical-body identity masks, stable-`NOOUTPUT` guard, hardware-qualified handoff,
restoration, warning, and safety hardening remain in force. An unanswered `10 03` also receives one non-overlapping retry
after a complete P2 interval while the original 200 ms physical-trigger deadline remains authoritative.

Route `00000187` proves that restored scheduler after the diagnostic matcher was corrected to accept the EV9's exact
eight-byte positive response when carried in a CAN-FD packet. The direct OFF-to-READY knockout, suppression, resident
warnings, complete host claim, and `HANDOFF` all succeeded. Its later fallback exposed a host-health interpretation bug,
not a lost knockout: pressing the LKA button withdrew Panda's always-on-lateral permission while four host frames were
already queued, so safety rejected them and its cumulative `safetyTxBlocked` counter advanced. Card treated that
historical enforcement count as a permanent fault even after output was neutral.

Production continuation now ends the special preinit transaction monitor at a
confirmed `HANDOFF`. Runtime `safetyTxBlocked`, process liveness, and Panda
faults follow the same safety and alert paths as ordinary openpilot operation;
they cannot cause Panda to resume resident reconstruction. Panda's TX allowlist
and actuation checks remain authoritative.

Route `000001a7--762a425044` exposed a distinct parking-lock boundary after a clean knockout and HANDOFF. As the driver
turned past `-360` degrees, Panda rewrote inactive mode-1 `0xCB` to the exact fresh physical angles (`-394.7` through
`-404.3` degrees), but the shared safety helper applied the active-command clamp to those non-actuating mirrors. The EV9
safety profile now retains the strict `+/-360`-degree active ceiling while allowing only inactive, zero-gain,
non-emergency `0xCB` to equal the measured 14-bit physical angle. Once handoff is confirmed, the preinit layer no longer
interprets cumulative safety rejection telemetry or rewrites host body fields; only rolling counter/CRC continuity remains.

Route `00000189` extended that proof to the normal physical Drive-to-Park edge. Panda rejected one still-queued active
`0xCB` after its gear input left Drive, 6.448 ms before host `CarState` published Park. Earlier continuation code added a
special receipt/quarantine exception for this expected safety race. The final one-way design removes that post-handoff
transaction monitor entirely: the ordinary Panda safety hook rejects the individual output, while the preinit layer
does not reinterpret its cumulative counter as ownership loss.

Route `0000018a` proved that the rejection was ordinary safety enforcement rather than a CAN transport fault. Its OFF
edge also showed that raw ignition low can be published with the old HANDOFF status page before the firmware debounce
completes. Card enters OFF from that valid resident low sample, and firmware latches fresh HANDOFF qualification at the
raw low edge so main-loop delay cannot discard the warm token and reopen cold diagnostics during ignition-low body-
network chatter.

Routes `000001aa--28f26ea1d7` and `000001ab--0cbb5f68d6` exposed the difference between current and historical Panda
fault state. Both publications had an empty `faults` list and healthy CAN cores, but `faultStatus=faultTemp` remained
latched from an earlier recovered CAN3 interrupt-rate event. Host startup treated the historical latch as a new fault,
refused claim, and displayed Driver Assistance Unavailable until unplugging Panda reset the MCU. The production gate now
rejects every nonempty current bitmap and every permanent status, while accepting an empty historical temporary status.

Route `000001ac--4a2f534eb3` then completed HANDOFF and drove normally, but all 32 MRR35 channels remained `STATE=0`,
`liveTracks` contained zero points for the full route, and reconstructed `0x162` object plus `0x1BA` blindspot fields
stayed neutral. Its returned host `0x100` body matched the physical EV9 identity tuple rather than the ADAS_DRV radar-
alive body. In comparison, route `0000016e--e01ce0903b` returned the verified radar-alive body and normally carried
roughly 12-24 live radar points plus populated primary/side object slots. Firmware and host now preserve the verified
radar-alive body across preinit and HANDOFF, inheriting only its counter and live brake/accelerator bits. The same route
also proved that the captured neutral `0x161` template retained `LKA_ICON=1`; host reconstruction now explicitly clears
that bit after HANDOFF while keeping the persistent orange FCA indication.

The passive post-route-187 OFF sample remained in `RESTORING/0x8f` without a
restore timestamp and with a temporary relay-malfunction latch. `0x8f` proves
the FDCAN purge latched `INTERNAL_TX_REJECTED` before `RESTORE_SENT`; no restore
request reached the queue. Its multi-phase 20 ms reset was advanced only by the
outer Panda loop, while the production LED fade can block that loop for hundreds
of milliseconds. The EV9 build now services only an already-pending FDCAN purge
inside both fades. All diagnostics, ownership transitions, bridge publication,
and restore completion remain on the normal state-machine tick. The later seated
shutdown capture proved `28 00 01`, exact `68 00`, fresh five-stream stock
convergence, default-session cleanup, and clean rearm.

There is deliberately **no actively originated mid-drive stock restoration**.
After handoff, a host failure stops host output and uses normal openpilot fault
behavior; Panda does not become a second reconstruction publisher. If the OEM
ECU naturally resumes after its diagnostic session expires, the existing stock-
reappearance guard quiesces host replacement. Normal restoration/rearm remains
reserved for OFF/release.

If restoration cannot be proven, remain quiescent/faulted and require intervention or a new power cycle. Never treat a
diagnostic acknowledgement, a normal camera screen, or disappearance of a dash icon as proof of restored ownership.

The 2026-07-27 seated shutdown capture proved the normal OFF restore path:
exact `28 00 01 -> 68 00`, immediate default-session cleanup, and fresh
physical `0x100/12A/CB/160/1A0`. It also found that a qualified warm token
could enter the generic ABORTED/silent-bus rearm path before a new ignition
rise. Route 18c then showed that a shutdown ignition transition could consume
that token before the real warm start, after which stationary body/ADAS identity
spent the bounded attempt. Firmware now keeps all such collection passive until
fresh brake plus asserted ignition (or pre-READY) proves a real start. The
safety case records the exact shutdown timeline and containment proof.

Routes 191 and 192 identified the separate remote-climate entry case: the EV9
can transition to READY on driver entry with no brake/Start event, and its
pre-READY state arrives only about 60 ms before READY while pandad is in
temporary ELM327 safety. Production firmware now recognizes this earlier path
only when recent physical remote-climate-active `0x384`, recent driver-door-open
`0x411`, and a new ignition rise occur together. The existing masked EV9
identity and fresh stationary wheel-speed proof remain mandatory. Climate,
door, lock/unlock, and ignition-less remote actions alone remain passive.

Route `00000193--484f0d3839` validates that policy from locked/asleep remote
climate through automatic READY: exact `10 03 -> 50 03 -> 28 01 01 -> 68 01`,
fingerprint `0xff`, resident orange reconstruction before host startup, complete
HANDOFF 1.656 seconds after READY, 40 seconds of stable continuation, and clean
post-OFF rearm with zero off-state attempts. The production implementation is
commit `ac3849ce0c`; detailed timing is retained in the safety case.

## Validation

Software validation must cover the dedicated firmware state machine, USB status coherence, exact safety isolation,
host-claim phase boundaries, one-way post-handoff behavior, fault inhibition, and dash input freshness.

Before road use, run and retain passive logs for this parked matrix:

1. Cold comma SOM with warm resident Panda: locked/asleep vehicle, unlock, then direct OFF-to-READY without an ignition-on
   dwell. Confirm the EV9 heartbeat-body identity and fresh stationary `0xA0` proof are established before the first
   `10 03` and `28 01 01`.
2. Fresh Panda MCU power-on followed by direct OFF-to-READY.
3. Warm OFF-to-READY restart without exiting or allowing the vehicle/comma to sleep.
4. Conventional ignition-on-to-READY startup.
5. READY-to-OFF while body CAN remains awake: verify immediate replacement quiescence, `28 00 01`, fresh stock critical
   streams, and complete release.
6. A second start after each successful restoration, proving a clean new ownership epoch.
7. Host/card crash and host-heartbeat loss after handoff: verify host output stops,
   Panda remains in `HANDOFF`, resident reconstruction does not restart, ordinary
   process/Panda safety alerts occur, and any natural stock reappearance causes
   quiescence rather than dual publication.
8. Unexpected stock ADAS reappearance and CAN-error/fault injection on the bench: verify no dual publisher and no
   actuation.
9. With the vehicle parked and selfdrive disengaged, toggle the physical LKA button off after a stable `HANDOFF`: verify
   any bounded queued-frame safety rejects stabilize, host continuation remains in `HANDOFF`, FCA remains visible, LKA
   follows the requested state, and neither `adasUnavailable` nor Panda fallback appears. Toggle LKA back on and verify
   safe lateral resumption without another counter increase.
For every run, correlate Panda preinit page 0/page 1 timing, `pandaStates`, `sendcan`, receive-side CAN, `carState`,
`selfdriveState`, and dash observations. A successful knockout requires exact UDS responses,
independent suppression confirmation, continuous single-publisher reconstruction, a complete hardware-qualified handoff,
and a clean OFF restoration. Any missing element is a failed test, even if the dash looks normal.
