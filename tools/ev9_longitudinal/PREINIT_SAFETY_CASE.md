# EV9 resident preinit safety case

Status: production candidate, parked validation complete for the supported start
paths. This document records the intended safety boundary and the evidence that
must remain true as the implementation changes. It is not an ISO certification
or a claim that OEM ADAS functionality is retained.

## Scope

The feature is restricted to the Kia EV9 profile selected by all of the
following host-side facts:

- explicit `EV9LongPreinitPanda` opt-in;
- openpilot and experimental longitudinal enabled;
- cached `KIA_EV9` identity with ADAS ECU `0x730`;
- exact Hyundai CAN-FD flags and dedicated safety model 36;
- safety parameter `0x0495`, with only optional AOL bit `0x0800` permitted;
- the internal H7 Panda and one of the four EV9-only signed images.

The resident firmware does not trust that cache. Before originating diagnostic
traffic in each wake epoch it independently requires CRC-valid, route-backed
masked EV9 bodies on bus-0 `0x100` and bus-1 `0x35`/`0xCB`, plus a bus-1 `0xA0`
wheel-speed sample no older than 100 ms with all four raw speeds at or below 12.

## Safety goals and containment

| Hazard | Prevention or containment |
|---|---|
| Diagnostic request on a wrong vehicle | Separate EV9 firmware target, strict host selection, current-cycle masked physical identity, exact bus/address/length checks, and no generic model fallback. |
| Knockout while moving | Fresh four-wheel stationary proof is checked immediately before both `10 03` and `28 01 01`. Motion or stale proof returns to default session and aborts. |
| Ambiguous or partial UDS ownership | Only exact `50 03` chains the request and exact `68 01` proves control. P2 is 50 ms per request, the physical-start deadline is 300 ms, retries never overlap an unresolved request, and ambiguity enters restore instead of bridge ownership. |
| Replacement before ownership | Resident output is blocked until exact `68 01`. Suppression is then independently confirmed from quiet critical stock streams while the rest of the vehicle remains live. |
| Two publishers for one managed tuple | Before handoff, Panda phase-arbitrates each tuple, rewrites counter/CRC at its TX critical section, and credits host ownership only after the packet reaches FDCAN hardware. `HANDOFF` is then one-way for the ignition epoch and resident publication stops. Stock reappearance immediately quiesces host replacement and enters restore. |
| Host crash, stale output, or queue clear | After `HANDOFF`, resident reconstruction does not restart. Host output ceases and normal openpilot process/Panda safety behavior applies; no new knockout or active stock restore is originated while the vehicle remains on. |
| Panda fault or health regression | Every current or latched Panda fault hard-inhibits steering and longitudinal actuation through the normal openpilot safety path. A narrowly recovered startup CAN3 fault may permit the pre-handoff neutral claim only; it never authorizes actuation. |
| Unsafe stock restoration in motion | There is no normal mid-drive restore. A debounced ignition-fall or proven quiet/off release first quiesces and purges host/resident TX, then sends `28 00 01`; exact `68 00` or complete fresh stock convergence is required. |
| Stale state reused across starts | OFF latches the old epoch, cancels software and hardware queues, and requires a fresh physical CAN epoch. A warm token cannot be consumed by door, lock, charging, or restored body-network chatter. |
| Misleading driver display | Resident `ACTIVE` shows orange FCA and LKA. Host `HANDOFF` keeps orange FCA because OEM FCA/AEB remains unavailable and clears orange LKA only after complete host ownership. Stale object/lane inputs neutralize rather than freeze. |

## Diagnostic and transmit boundaries

The resident diagnostic allowlist is exact:

- `10 03` extended session;
- `28 01 01` enable reception / disable normal transmission;
- `3e 80` response-suppressed Tester Present;
- `28 00 01` restore normal transmission;
- `10 01` default-session cleanup.

The host safety model allows only Tester Present at runtime. It does not permit
DTC reads, DTC clearing, session control, CommunicationControl, ISO-TP flow
control, or diagnostics to the camera, cluster, radar, or EPS.

The resident replacement set is bus-0 `0x100` and bus-1 `0x12A`, `0xCB`,
`0x160`, `0x161`, `0x162`, `0x1A0`, `0x1BA`, `0x1DA`, `0x1E0`, `0x1E5`,
`0x1EA`, `0x200`, `0x345`, and `0x38C`. Physical `0x57A` is never replayed.
The final resident TX gate independently enforces zero actuation on `0x12A`,
`0xCB`, and `0x1A0`. The dedicated openpilot safety hook repeats the neutral
`0x12A` and inactive `0xCB` emergency-channel checks, then applies the normal
Hyundai steering-angle, acceleration, brake, gas, gear, and cruise controls.
Before handoff, Panda replaces only the inactive host `0xCB` non-actuating
requested-angle field with a CRC-valid physical `0xEA` steering measurement no
older than 100 ms before running safety. After handoff, host cadence and body
fields traverse the ordinary Panda safety path unchanged. Panda updates only
the rolling counter and CRC so the frozen claim retry epoch joins the live host
epoch without a counter discontinuity. The pre-claim phase gate remains for a
bounded 500 ms after firmware enters `HANDOFF`, covering card's 10 Hz status
observation without allowing its 333 Hz claim retries to burst onto CAN.

## Route evidence

Successful representative routes:

| Path | Route | `10 03` from trigger | `68 01` from trigger | READY | Host handoff |
|---|---|---:|---:|---:|---:|
| Direct OFF-to-READY | `00000187--2d276303a9` | 0.020 ms | 39.122 ms | 800.839 ms | 1.105 s after READY |
| Cold comma/SOM boot | `0000018c--7b28efa2e9` | before first rlog | 39.046 ms | 817.536 ms | 55.142 s after READY; route log shows claim completed 3.495 s after route start |
| Immediate warm restart | `0000018e--1f8d2b1cbd` | 125.225 ms | 167.426 ms | 431.418 ms | 1.642 s after READY |
| Remote-climate entry | `00000193--484f0d3839` | 125.172 ms | 170.350 ms | 425.850 ms | 1.656 s after READY |
| Locked fob remote start | `0000019d--6cc955b36b` | 220.296 ms | 255.347 ms | 1.014814 s | 1.146808 s after READY |

All five paths reached exact positive responses, independently confirmed stock
silence, resident orange reconstruction, dedicated safety model 36, complete
hardware-qualified handoff, a fresh host lease, and clean next-cycle rearm.

The main failed routes established the negative requirements:

| Evidence | Failure | Production requirement derived from it |
|---|---|---|
| 144 | A post-READY CommunicationControl request returned NRC `7f 28 22`. | No new knockout request after terminal READY. |
| 171 | A second unanswered `28 01 01` overlapped the first; no positive arrived and CAN errors accumulated. | One unresolved request maximum; simultaneous two-core purge and restore on ambiguity. |
| 172 | Reconstruction began about 4.5 ms before `68 01`. | No replacement before exact ownership. |
| 177/17b | Slow managed frames remained phase-locked behind resident cadence. | Three-millisecond host retries, bounded slow-stream reservation, and hardware receipts for every tuple. |
| 180 | Base firmware was new but the selected HKG image was stale. | Build and deploy all four selectable EV9 images as one versioned set. |
| 181 | The assumed stock heartbeat body was actually a returned host frame. | Identity uses invariant physical bodies from multiple routes, never a returned replacement. |
| 182 | Deferred RX overflow displaced the early pre-READY identity frame. | Direct exact-tuple RX scheduling and fail-closed overflow behavior. |
| 183-185 | ELM327 safety changes and the blocking LED fade delayed or erased the diagnostic window. | Stable NOOUTPUT before clocks start, raw-ignition ELM327 preemption, late-query veto, and direct RX response chaining. |
| 187/189/18a | Expected queued direct-angle rejects at LKA-off and Drive-to-Park advanced the cumulative safety counter, which the continuation monitor mistook for a failed preinit transaction. | Restrict strict transaction health proof to claim establishment. After confirmed handoff, ordinary Panda safety rejects the individual output without revoking ownership or starting resident fallback. |
| Post-187 OFF | FDCAN purge stalled in the LED fade and never queued restore. | Advance only an already-pending reset during the fade; keep diagnostics on the normal state-machine tick. |
| 18c | Restored OFF traffic consumed the next diagnostic attempt without driver start intent. | Identity is collection-only; a real ignition/brake, pre-READY, climate-entry, or fob start boundary is required. |
| 191-192 | Remote-climate entry reached READY too soon after pre-READY while ELM327 was active. | Recent remote-climate plus driver-door plus ignition-rise trigger, while retaining identity and stationary gates. |
| 194-19c | Fob wakes entered ELM327 before identity; the 200 ms global deadline then expired just before normal `68 01`. | Reject only the late start-window ELM327 mutation and use a 300 ms global deadline while keeping 50 ms P2 and terminal-READY vetoes. |
| 1a4/1a6 | Valid active `0xCB` commands were safety-rejected at a VM limit or gear edge. The preinit continuation monitor interpreted normal cumulative safety enforcement as transaction failure. | End special transaction monitoring at confirmed `HANDOFF`; ordinary Panda safety and openpilot process alerts own runtime enforcement. |
| 1a5 | The 333 Hz claim retried a frozen inactive `0xCB` angle after the physical wheel angle changed; Panda correctly rejected eleven stale bodies and host claim failed. | Canonicalize only inactive `0xCB` to Panda's fresh physical `0xEA` measurement immediately before CRC/safety; retain the exact-angle check and fail closed when the measurement is stale. |
| 1a7 | At parking speed the driver turned through `-394.7` to `-404.3` degrees. Panda correctly canonicalized four inactive mode-1 `0xCB` bodies to those exact physical values, but the shared angle helper clamped even inactive mirrors to the `+/-360`-degree actuation ceiling. The cumulative rejects then triggered resident fallback and an unavailable alert. | Keep the active direct-angle command hard-limited to `+/-360` degrees, permit only an inactive zero-gain/non-emergency mirror over the signed 14-bit range, and never re-enter resident ownership after confirmed handoff. |
| 1aa/1ab | Panda had recovered its temporary CAN3 event and published an empty current fault bitmap, but the historical `faultTemp` status remained latched. Host treated that historical status as a new current fault and refused every warm claim until MCU power was removed. | Current fault bitmap and permanent status remain fail-closed; an empty historical temporary status is not a current fault and must not poison later warm starts. |
| 1ac versus 16e | Handoff adopted a physical EV9 `0x100` identity body as the radar heartbeat. All MRR35 channels stayed idle, so live radar, reconstructed objects, and qualified BSM were absent. Route 16e's verified ADAS_DRV heartbeat kept normal live tracks and object slots. | Preserve the verified radar-alive body in resident firmware and host output; inherit only counter and pedal bits across the boundary. Never seed the heartbeat body from the physical identity tuple. |

## Driver-facing and functional limitations

- OEM FCA/AEB and blind-spot collision-avoidance braking are unavailable while
  the ADAS ECU's normal transmission is disabled. Radar tracks, reconstructed
  objects, or a normal camera screen do not imply those functions are present.
- The driver must remain responsible and able to brake, steer, or cancel. This
  work does not weaken openpilot driver monitoring or excessive-actuation
  checks.
- If host software fails after handoff, host reconstruction stops and normal
  openpilot process/communication alerts apply. Panda does not synthesize a
  second runtime fallback. The ADAS ECU may resume only through its own session
  behavior, detected stock reappearance, or the normal ignition-OFF release.
- Stock restoration is reserved for OFF. If restoration cannot be proven, the
  system remains quiescent/faulted and requires intervention or a power cycle.

## Standards and openpilot alignment

The implementation follows relevant engineering principles from ISO 26262:
explicit safety goals, independent gates, bounded timing, freedom from
ambiguous ownership, fail-closed diagnostics, configuration control, and
requirement-based regression tests. ISO 21448 is relevant to the loss of OEM
perception/ADAS functions and foreseeable driver interpretation of reconstructed
displays; the persistent orange FCA indication and explicit limitations address
that risk but do not constitute a complete SOTIF argument.

This is not an ISO 26262 assessment, ASIL decomposition, safety manual, FMEDA,
production validation campaign, or ISO 21448 release. Those require independent
hazard analysis, requirements traceability, tool qualification decisions,
vehicle-level fault injection, environmental testing, and review outside this
repository.

The code keeps openpilot's safety architecture intact: vehicle actuation passes
through a dedicated C safety model; normal longitudinal and angle limits remain;
brake, gas, gear, cruise, heartbeat, and RX checks remain authoritative; and
every change under `opendbc/safety` requires the complete safety suite and MISRA
checks before merge.

### Review status (2026-07-30)

- All four selectable EV9 H7 firmware images compile, link, and sign with the
  repository-supported Arm GNU 15.2 toolchain under `-Wall -Wextra
  -Wstrict-prototypes -Werror`. The generic H7 image also builds with the
  feature disabled.
- The resident, Panda-host, Car/card, Hyundai reconstruction, and full Hyundai
  CAN-FD safety suites pass. The exact safety profile was rerun after the final
  fail-closed initializer change.
- Cppcheck/MISRA exposed and drove correction of an EV9 initializer early return
  and feature-disabled CAN-send constants. The repository-wide check remains
  red on pre-existing findings in unrelated safety modes and fork code.
- A separate feature-defined Cppcheck run reaches the resident state machine.
  It reports no non-MISRA correctness diagnostic in `ev9_long_preinit.h`, but
  reports unresolved MISRA deviations, principally rules 8.9, 10.x, and 15.5,
  plus incomplete-analysis notices for hardware-register macros. These require
  formal disposition or refactoring before any claim of strict MISRA conformity;
  passing compiler and regression tests do not waive them.

## Required release validation

Before road use, retain automatic rlogs for:

1. fresh Panda MCU power-on followed by direct OFF-to-READY;
2. repeated cold, warm, ignition-on, remote-climate-entry, and locked-fob starts;
3. READY-to-OFF restore while body CAN stays awake, including exact `68 00` or
   complete fresh stock convergence and a subsequent clean start;
4. host/card crash, heartbeat loss, stale traffic, and queue clear after handoff,
   proving that resident publication does not restart;
5. bench CAN fault, overflow, reset, invalid-RX, and unexpected stock
   reappearance injection;
6. LKA-button off/on and Drive/Park/Reverse/Neutral transitions after handoff;
7. braking, gas override, cancel, steering override, and controls disable;
8. motion before host handoff, proving takeover can complete without weakening
   the firmware's stationary-only knockout rule.

Do not launch a second direct `Panda()` client during READY or preinit. Panda
connection setup reinitializes CAN hardware and can itself cause lease loss.
Early-boot validation must use the automatic rlog; even a Panda-free broad
Cereal subscriber has caused enough load to interrupt host continuation.
