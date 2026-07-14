# Kia EV9 longitudinal transmit-disable test framework

This framework is developer-only and disabled by default. It is designed for parked testing that determines which EV9
ADAS_DRV messages must be restored after UDS receive-enabled/transmit-disabled communication control is applied to ECU
`0x730`.

It does not preserve OEM FCA/AEB. Raw radar availability is not equivalent to retaining Hyundai's fused emergency-braking
logic. EV9 BSM detection remains available directly from the corner-radar traffic and the validated stage-15 path
dynamically recreates `0x1BA/0x1E5` for the vehicle. Blind-spot collision-avoidance braking requests remain disabled.

## Current working state (2026-07-12)

The verified software-only state is **stage 15, probe mode 2**, using UDS `28 01 03` against ADAS ECU `0x730`. ADAS
reception remains enabled, normal/network-management transmission is disabled, and StarPilot continuously supplies the
complete non-actuating replacement stream. The final parked validation is route `000000ff--4a1113195d`.

Proven in both IGN-ON and READY/Park:

- no vehicle DTC count, orange ADAS icons, warning dings, or comma vehicle error;
- `KIA_EV9`, `openpilotLongitudinalControl=True`, `pcmCruise=False`, and `carState.canValid=True`;
- positive CommunicationControl response, `EcuDisableFailed=False`, and Tester Present maintained at 1 Hz;
- every staged replacement at its target rate: `0x100`, `0x12A`, `0xCB`, `0x160`, `0x161`, `0x162`, `0x1A0`,
  `0x1BA`, `0x1E0`, `0x1E5`, `0x1EA`, `0x200`, `0x345`, `0x38C`, and `0x57A`;
- all 32 MRR35 raw tracks, `radarState.valid=True`, active lead tracks, and no radar errors;
- direct corner-radar BSM input plus dynamic vehicle-facing BSM status;
- Panda Hyundai CAN-FD longitudinal safety with no faults, blocked transmissions, or invalid receive checks;
- `SCC_CONTROL` forcibly inactive: `ACCMode=0`, zero acceleration, no stop request, and no longitudinal actuation.

Intentionally unavailable or not yet validated:

- OEM FCA/AEB and blind-spot collision-avoidance braking are not retained while ADAS transmission is disabled;
- openpilot longitudinal actuation remains untested and unavailable at stage 15;
- stage 16 is non-actuating preflight only; stage 17 is the separately gated bounded actuation stage;
- direct OFF-to-READY ownership and verified `28 00 03` stock-restore behavior are not production-ready;
- steering-wheel vibration was not found in `0x162.VIBRATE` and remains a separate investigation.

### Why the changes were required

1. **Complete, continuous reconstruction:** the 12 displayed DTCs are active missing-message faults. They appear whenever
   ADAS remains transmit-disabled and reconstruction is absent or interrupted. Restoring the complete stage-15 stream
   clears them without clearing DTC memory or sleeping the ECU.
2. **Startup ownership and handoff:** cached EV9 identity and ADAS firmware permit the tightly gated suppression attempt
   before normal controls initialization. The same process owns the diagnostic request, captures the last stock bodies and
   counters, starts inactive reconstruction, and hands control to the normal interface without a second publisher.
3. **Payload continuity:** live pre-suppression bodies preserve READY/IGN state and unknown equipment bits, while rolling
   counters continue from stock. `0x160` deliberately reports AEB unavailable rather than copying an unavailable function.
4. **BSM validity:** suppressed ADAS-originated `0x1BA` cannot remain a required receive-side parser input. BSM detection is
   instead read from live corner-radar traffic and used to generate dynamic `0x1BA/0x1E5`; frozen object state is never
   replayed and BCA brake-request fields remain zero.
5. **Single CAN publisher:** diagnostic reads, Tester Present, reconstruction, and normal controls share the existing
   `card` publisher. A second `sendcan` publisher can evict `card`, interrupt reconstruction, and trigger relay faults.
6. **Radar messaging freshness:** polling only `modelV2` starved non-polled `carState` after its initial sample in this
   messaging build. `radard` now polls every input but runs fusion only on model updates. It requires valid/fresh vehicle
   state and full model/live-track checks while treating `starpilotPlan` as optional enrichment.
7. **Real Params backend:** device arming must use `/usr/local/venv/bin/python`. Plain system Python can load the in-memory
   source fallback and appear to write test parameters without updating `/data/params/d`.

Relevant local checkpoints:

- `86523c407` — gated EV9 HDA2 reconstruction and dynamic BSM foundation;
- `810efa93c` — non-actuating preflight and bounded safety gates;
- `9650efe5d` — startup continuity, payload/counter handoff, and fail-closed ownership;
- `716c9c6d3` — keep all radar inputs fresh while publishing at model rate;
- `645d2eb5f`, `e33eee65c` — verified stage-15 procedure and successful radar-valid route record.

The comma used for route `000000ff--4a1113195d` remains configured with enable=true, stage=15, probe mode=2,
`AlphaLongitudinalEnabled=true`, and DTC capture disabled. Do not disable reconstruction while ADAS transmission remains
suppressed. Either keep stage 15 active for the next wake or first verify that stock ADAS transmission has been restored.

Do not replay a frozen `0x1BA`: a valid counter/checksum with stale object state could falsely clear or assert a warning.
Stage 2 must first establish whether `0x1BA` disappears, whether the mirror lamps continue through another path, and which
live corner-radar inputs can safely regenerate it.

## EV9 result: continuous stage-15 reconstruction satisfies the parked vehicle

The 2026-07-10 probe showed that `28 01 01` can return a positive UDS response without silencing the EV9 ADAS ECU.
The later 2026-07-11 parked test established that `28 01 03` (enable receive, disable transmit, normal and
network-management messages) does suppress ADAS ECU `0x730` output. Persistent suppression requires Tester Present;
the ECU resumes transmission about five seconds after Tester Present stops.

With `28 01 03` active but reconstruction absent or interrupted, the vehicle displays 12 active ADAS DTCs, five orange
warning icons, two warning dings, and the comma reports `Unknown Vehicle Variant`. These are live missing-message faults,
not DTCs that require a clear. Resuming the complete stage-15 replacement stream clears the dash and comma state without
sleeping the vehicle or restoring stock ADAS transmission. The comma message was independently traced to suppressed BSM
frame `0x1BA` being treated as required; the EV9 parser now treats that ADAS-originated frame as optional while reading
live BSM state from the corner radar.

Progressive parked testing reconstructed every observed suppressed ADAS frame through stage 15: radar heartbeat `0x100`,
ADAS status `0x160`, CCNC `0x161/0x162`, inactive SCC `0x1A0`, BSM `0x1BA/0x1E5`, cluster `0x1E0`, status frames
`0x1DA/0x1EA/0x200/0x345/0x38C/0x57A`, and inactive steering messages `0x12A/0xCB`. Frame rates, counters, checksums,
bus placement, and Panda acceptance were verified. Early incremental tests still showed the 12-DTC state because they
started or changed reconstruction after the receiving ECUs had already detected missing traffic. The completed stage-15
stream clears those active faults when it owns the startup continuously. Stages 16 and 17 are not required for this
non-actuating parked result.

Verified clean suppressed routes:

- `000000dc--35ea20cd7b`: stage 15, successful `68 01`, no dash DTCs; the comma still showed the pre-fix optional-BSM
  validity error.
- `000000dd--496fbfd1d8`: stage 15, successful `68 01`, normal comma screen after the parser fix, no dash DTCs or
  warnings, all reconstructed messages and Tester Present sustained.
- `000000fc--5aefd6f768`: stage 15 resumed while ADAS remained suppressed from the preceding test. The initial active
  12-DTC/unknown-variant state cleared immediately once reconstruction resumed; IGN-ON to READY remained clean. This
  proves ECU sleep and DTC clearing are not recovery requirements when the complete stream is restored.
- `000000ff--4a1113195d`: stage 15 with the final radar messaging fix (`716c9c6d3`). IGN-ON and READY remained free of
  dash/comma errors, `radarState.valid=True`, both leads were active, `carState.canValid=True`, Panda reported no faults
  or blocked transmissions, and every reconstructed address plus Tester Present remained at its target rate.

`radard` must poll all of `modelV2`, `carState`, `liveTracks`, and `starpilotPlan`, then run fusion only on model updates.
Polling only `modelV2` starves the non-polled `carState` socket in this messaging build after its first sample. The radar
validity envelope therefore enforces full model/live-track checks and fresh, valid `carState`, ignores only its conflated
average-frequency estimate, and treats `starpilotPlan` as optional enrichment.

The clean stock/disarmed recovery route is `000000d3--78bb8fa04a`; it identified `KIA_EV9`, produced valid `carState` for
985/985 sampled updates, and showed no vehicle DTCs. The feature flag, stage, probe mode, and alpha-longitudinal toggle
were explicitly persisted as zero and verified again after reboot.

A separate bounded diagnostic-only probe entered extended session with `10 03` (`50 03`), waited one second, and restored
the default session with `10 01` (`50 01`). It produced no vehicle DTCs. This isolates the warning trigger to
CommunicationControl `28 01 01`, not extended diagnostic session entry itself.

StarPilot verifies that stock `0x1A0` actually stops after the positive response. If it remains live, the interface
requests normal communication again and falls back to stock SCC before controls become ready. A positive UDS
acknowledgement alone is never accepted as longitudinal ownership; the `28 01 03` test proved suppression through the
disappearing address set and sustained message-rate measurements.

EV9 CommunicationControl remains developer-only and parked-test-only. The successful suppression and reconstruction
ladder demonstrate message-generation capability, not a driveable longitudinal implementation.

The demonstrated CarrotPilot HDA2 approach uses a modified ADAS harness to place the ADAS E-CAN output on a separately
controlled Panda bus, then selectively processes and retransmits live traffic. That physical isolation—not UDS-only
CommunicationControl—is the evidence-backed next architecture for this EV9. CarrotPilot also clears selected CCNC alert,
fault, and sound fields, so a clean dashboard alone must not be treated as proof that stock functionality was restored.

Before another suppression run, capture DTCs from the receiving ECUs rather than replaying the same static ladder. Cached
EV9 CarParams identified these physical diagnostic request/response pairs:

| ECU | Request | Response |
|---|---:|---:|
| ADAS | `0x730` | `0x738` |
| Forward camera | `0x7C4` | `0x7CC` |
| Combination meter | `0x7C6` | `0x7CE` |
| Forward radar | `0x7D0` | `0x7D8` |
| EPS | `0x7D4` | `0x7DC` |

The normal Hyundai CAN-FD Panda safety mode intentionally blocks arbitrary DTC requests. A diagnostic capture therefore
needs a separately reviewed, fail-safe procedure that restores communication before restarting openpilot; do not modify
the safety allowlist merely to hide this restriction.

The staged `read_dtc_live.py` observer keeps `pandad` and route logging active. Panda permits only the exact UDS
`ReadDTCInformation/DTCByStatusMask` request (`19 02 FF`) and ISO-TP flow control on the known EV9 addresses; clear-DTC,
session-control, communication-control, memory access, and other diagnostic payloads remain blocked. The observer requires
the EV9 to be stationary in Park, verifies cached firmware-query bus evidence, and always resets its one-shot authorization
flag after success or failure. It never opens `sendcan`: `CarController` emits the one-shot requests through its existing
publisher after suppression has been stable for five seconds. This is required because a second publisher can evict `card`,
drop Tester Present, restore stock ADAS traffic, and latch a Panda relay fault.

Run after suppression has stabilized in READY and the vehicle remains in Park:

```bash
cd /data/openpilot
source ./launch_env.sh

/usr/local/venv/bin/python3 tools/ev9_longitudinal/read_dtc_live.py --label suppressed
```

The observer arms `KiaEv9DtcCaptureEnabled`, passively reconstructs the replies, and appends results to
`/data/ev9_dtc_capture.jsonl`. ADAS `0x730` is intentionally skipped to preserve CommunicationControl. The tool never
clears DTCs. The clean-stock baseline is already captured; do not use a standalone diagnostic publisher while `card` runs.

Use the resulting ECU/code list to maintain a functionality matrix:

| Function | Evidence required | Allowed disposition |
|---|---|---|
| OEM FCA/AEB | ADAS/FCA DTCs and controlled functional evidence | Expected unavailable; show an honest unavailable state |
| BSM mirror warnings | Live corner-radar input plus dynamic `0x1BA` output | Recreate dynamically or mark unavailable; never replay frozen object state |
| EPS/lateral steering | EPS DTCs, `carState`, and parked steering checks | Must remain functional and fault-free |
| ESC/service braking | ESC/brake DTCs and pedal/brake-state evidence | Must remain functional; do not suppress a real brake-system fault |
| Radar perception | All MRR35 tracks and openpilot radar output | Retain and continuously validate |
| Cluster-only ADAS UI | Receiving-ECU DTC mapped to decoded alert fields | May suppress only after the underlying function is classified |
| DAW/sign/lane features | Source ECU, live inputs, and output messages identified | Recreate when evidence is sufficient; otherwise mark unavailable |

## Gates

Three conditions are required before StarPilot can request EV9 ADAS transmit-disable:

1. The detected car is `KIA_EV9`.
2. `KiaEv9LongitudinalTestEnabled` is true and the stage is at least 2.
3. The normal `AlphaLongitudinalEnabled` developer toggle is true.

Changing the stage while onroad is unsupported. Configure it while the vehicle is OFF and verify the values before the
next ignition transition. Never stop stage-15 reconstruction while ADAS remains transmit-disabled: doing so immediately
recreates the active 12-DTC/unknown-variant state.

## Verified stage-15 clean path

This is the only currently verified software-only suppressed startup. It is non-actuating.

1. Keep the vehicle OFF. Restart manager first if a restart/deployment is needed; do not restart it after arming without
   re-verifying the parameters.
2. Use the comma runtime Python. Plain system `python3` can load the source-tree in-memory Params fallback and appear to
   write values without touching `/data/params/d`.
3. Arm stage 15 and mode 2:

   ```bash
   cd /data/openpilot
   /usr/local/venv/bin/python - <<'PY'
   from openpilot.common.params import Params

   p = Params()
   p.put_bool("KiaEv9LongitudinalTestEnabled", True)
   p.put_int("KiaEv9LongitudinalTestStage", 15)
   p.put_int("KiaEv9LongitudinalProbeMode", 2)
   p.put_bool("AlphaLongitudinalEnabled", True)
   p.put_bool("KiaEv9DtcCaptureEnabled", False)
   PY
   ```

4. Verify those exact values from `Params()` or `/data/params/d`. Do not proceed if any value is absent or different.
5. Turn IGN-ON without pressing the brake. Require all of the following before READY:
   `EcuDisableFailed=False`, `KIA_EV9`, `openpilotLongitudinalControl=True`, `carState.canValid=True`, Hyundai CAN-FD
   LONG safety, no Panda faults/blocked transmissions, positive `68 01`, and the complete returned replacement set.
6. Confirm the dash has no DTCs/icons/dings, then transition directly from IGN-ON to READY and remain in Park.
7. Verify the same health state in READY. Stage 15 always forces `ACCMode=0`, zero requested acceleration, and no stop
   request; it cannot command longitudinal motion.

If ADAS remains suppressed from a prior cycle and reconstruction is absent, do not diagnose the resulting warnings as
stored faults. Re-arm this exact stage-15 path while OFF and resume reconstruction. A full ECU sleep is needed only to
return to stock ADAS transmission when a verified `28 00 03` restore path is unavailable.

## Cumulative stages

| Stage | Addition |
|---:|---|
| 0 | Disabled; stock SCC |
| 1 | Shadow/log analysis only; no ECU command |
| 2 | Confirmed `ENABLE_RX_DISABLE_TX` to `0x730`; no longitudinal/support replacements beyond Tester Present |
| 3 | Add EV9 `0x100` radar heartbeat at 100 Hz |
| 4 | Add `ADRV_0x160` at its stock rate |
| 5 | Add `ADRV_0x1DA` |
| 6 | Add `ADRV_0x1EA` |
| 7 | Add `ADRV_0x200` |
| 8 | Add `ADRV_0x345` |
| 9 | Add `SCC_CONTROL` (`0x1A0`) at 50 Hz, forcibly inactive with zero requested acceleration |
| 10 | Add captured CCNC `0x161/0x162`; stage 15/16 can render engagement and supported radar-object slots |
| 11 | Add neutral BSM status `0x1BA/0x1E5` |
| 12 | Add neutral cluster status `0x1E0` |
| 13 | Add captured ADAS status `0x38C` |
| 14 | Add captured raw ADAS status `0x57A` |
| 15 | Add inactive steering status `0x12A/0xCB` |
| 16 | Actuation preflight: evaluate and log every abort gate while SCC remains forcibly inactive/zero |
| 17 | Permit tightly bounded requested acceleration/braking; closed-course test only |

`0x51` is intentionally excluded because it was absent from the stock EV9 reference route. EV9 HDA2 also does not send
the legacy `0x1E0` cluster replacement. Live CCNC `0x161/0x162` traffic should be observed, not duplicated.

The already-established EV9 lateral path continues to transmit its steering ownership/status messages at every armed
stage. Those are the test baseline, not part of this longitudinal replay ladder.

## Configure offroad

Use `/usr/local/venv/bin/python` as shown in the verified procedure above. The Python body is:

```python
from openpilot.common.params import Params

params = Params()
params.put_bool("KiaEv9LongitudinalTestEnabled", True)
params.put_int("KiaEv9LongitudinalTestStage", 15)
params.put_int("KiaEv9LongitudinalProbeMode", 2)
params.put_bool("AlphaLongitudinalEnabled", True)
params.put_bool("KiaEv9DtcCaptureEnabled", False)
```

To disarm after stock ADAS transmission has been restored or the ECU has slept:

```python
from openpilot.common.params import Params

params = Params()
params.put_bool("KiaEv9LongitudinalTestEnabled", False)
params.put_int("KiaEv9LongitudinalTestStage", 0)
params.put_bool("AlphaLongitudinalEnabled", False)
```

## Analyze captures

Compare a stock baseline segment with a post-disable segment:

```bash
python3 tools/ev9_longitudinal/analyze_route_diff.py \
  /data/media/0/realdata/ROUTE--0 \
  /data/media/0/realdata/ROUTE--1
```

The report shows message rates, MRR35 track continuity, and nonzero CCNC `0x162` fault fields. Returned Panda buses are
excluded by default so forwarded copies are not mistaken for independent transmitters.

Use `rlog` captures for decisions. `qlog` is downsampled and can make healthy message rates or MRR35 address coverage look
incomplete.

The progressive ladder through stage 15 is complete and should not be repeated. The individual incremental stages did not
clear the warning state, while the continuously owned completed stage-15 startup did. All 32 MRR35 radar tracks remained
live. Stock driving routes `000000d4--5296076dfd` and
`000000d6--f9d3fb2962` prove the EV9 `0x1BA` BSM encoding: `0x02` neither side, `0x0A` right, `0x12` left, and `0x1A`
both sides. The reconstructed output preserves both the vehicle mirror warnings and openpilot BSM state. `0x162.VIBRATE`
remained zero in those routes; steering-wheel vibration must not be claimed from that signal without new evidence.

Stage 16 is the required preflight and cannot actuate. Stage 17 is limited in both controller code and Panda safety to
`-0.50` through `+0.30 m/s²`, and the controller permanently aborts it for the rest of the ignition cycle on any of:
not in Drive, brake pressed, accelerator/override, invalid CAN, invalid radar, Panda fault, or speed above `5.0 m/s`.
These limits come from the active stock-SCC samples in the same two routes; no stock standstill/resume sample was captured,
so stop-and-go testing is out of scope. Do not enter stage 17 with a dash warning, invalid comma vehicle state, or outside a
flat closed private test area.

## EV6-style engagement and EV9 CCNC display

The EV9 keeps the existing Hyundai CAN-FD/openpilot engagement contract used by the EV6. CC Main is not an actuation
enable edge. Pressing and releasing SET- or RES+ is the intentional openpilot enable edge enforced independently by both
`CarState` and Panda safety. Cancel and the normal pedal rules disengage. Always On Lateral remains controlled by its
normal StarPilot setting; CC Main is not remapped into an AOL or longitudinal enable command.

At stage 15/16, dynamic `0x161/0x162` remains display-only because SCC is still forced inactive with zero requested
acceleration. The reconstruction preserves the captured EV9 payload body, overwrites only named DBC fields, and
regenerates the rolling counter and CRC. An enabled state uses the stock-route values `HDA_ICON=2`, `LFA_ICON=1`, and
`TARGET=3`, along with set speed, following-distance display, and lane-state fields.

The cluster has a finite object model rather than a raw radar point cloud. The reconstruction maps `radarState.leadOne`
to the primary lead, `leadTwo` to the alternate slot, and valid `starpilotRadarState` adjacent leads to one left and one
right slot. Radard keeps adjacent-lead extraction active for the EV9 cluster path even when the optional on-comma
adjacent-lead visualization toggle is off. Rear BSM status uses the stock fixed 25 m / 3 m display convention because the
retained corner-radar BSM
signal does not contain a measured range. No precise rear distance is fabricated, and arbitrary extra MRR35 tracks are
not rendered. `0x162.VIBRATE` remains zero until a route proves the EV9 uses that field for steering-wheel vibration.

### First driving validation: route `00000103--5353927d39`

The 2026-07-12 stage-15 drive covered segments 0 through 18 with no dash DTCs or Panda faults. SET- successfully enabled
openpilot from segment 6 monotonic time 405.165 through 422.565 (about 17.4 seconds). Stage 15 behaved as designed:
`SCC_CONTROL.ACCMode`, `aReqRaw`, and `aReqValue` stayed zero, so the drive did not test longitudinal actuation.

Panda was not the source of the reported weak lateral control. During the real engagement, `controlsAllowed` was true,
`safetyTxBlocked` did not increment, and every active `0x110` angle command was received on CAN with
`LKAS_ANGLE_ACTIVE=2`, `LKA_SysIndReq=2`, and a nonzero torque-reduction gain. The EV9-specific controller instead
hard-snapped its applied angle back to measured steering angle whenever `steeringPressed` was true. Normal hands-on torque
triggered that state for a substantial portion of the drive, reducing the commanded correction to zero. Any adjustment to
this behavior must remain separately feature-gated and retain Panda angle, rate, driver, and Drive-gear limits.

The default-on `KiaEv9HighAngleFaultProtectionEnabled` latch inhibits angle authority at 85 degrees and releases it only
at or below 70 degrees. While inhibited, the angle-active status and camera LFA suppression stay continuous, gain is zero,
and the existing vehicle-model rate limiter moves the command toward measured angle. It does not loosen Panda safety.
The independent `KiaEv9DynamicSteeringIconEnabled` flag displays grey while lateral is engaged without usable gain,
during driver override, or during high-angle inhibition. Both LKAS_ALT and CCNC remain green while openpilot has lateral
authority, including while tracking straight with a zero-degree angle command. Disabling either flag restores its prior
behavior for isolated testing.

Route `00000106` showed that stage-15 Drive/AOL emitted active `LKAS_ALT` (`0x110`) with nonzero gain but no downstream
`ADAS_CMD_35_10ms` (`0xCB`); EPS torque remained near zero hands-off. Stock EV9 routes instead keep `LKAS_ALT` inactive
and use `0xCB` for actual steering. Once ADAS transmission is disabled it cannot perform that translation, so the
default-on `KiaEv9DirectAngleCommandEnabled` path replaces synthetic active `0x110` with `0xCB` on ECAN in Drive while
lateral is active. It uses the same vehicle-model/Panda-limited angle and gain; high-angle inhibition retains active
status with zero gain. Inactive commands use the MDPS angle, and MDPS `LKA_ANGLE_FAULT` fails closed. This flag does not
enable longitudinal actuation, and the cluster remains grey when the required downstream path is unavailable.

The same route invalidated direct `radarState.leadTwo` cluster mapping. Both model leads were simultaneously valid 5,421
times; 5,358 pairs described nearly the same object, and neither carried a radar track ID. This caused the duplicate front
car. In stock EV9 routes `000000d4--5296076dfd` and `000000d6--f9d3fb2962`, `CCNC_0x162.LEAD_ALT` remained zero in all
2,400 inspected samples. Stock CCNC used stable, radar-backed, mutually exclusive primary/left/right slots, confirmed new
objects for several samples, held short dropouts, and atomically promoted an adjacent track into the primary slot when it
crossed lanes. Cluster reconstruction therefore needs its own feature-gated tracker rather than raw model-lead passthrough.

Additional stock semantics from the same references:

- Cluster objects stay off while HDA/SCC is inactive even if radar tracks exist.
- Active stock values include `HDA_ICON=2`, `LFA_ICON=1`, `TARGET=3`, while `LKA_ICON`, `CENTERLINE`, and lane-line fields
  remain zero.
- `LCA_LEFT_ICON=LCA_RIGHT_ICON=1` represents feature availability, not a current blind-spot detection.
- The OEM rear marker can precede the mirror BSM warning, so BSM is only an approximate optional fallback and must not be
  presented as a measured rear distance.
- `TARGET_DISTANCE` does not match the primary or adjacent object distances and must not be synthesized from radar.

Those stock routes also establish the conservative speed-limit reconstruction. The camera-provided
`FR_CMR_02_100ms.ISLW_SpdCluMainDis` value is copied literally to `CCNC_0x162.SPEEDLIMIT`; the accompanying stock state is
`SPEEDLIMIT_FLASH=2`, `COUNTRY=7`, and `SPEEDLIMIT_WEATHER=0`. Values 254 and 255 are reserved/invalid and are rendered as
zero. `SIGNS` remains zero because road-sign classes have not yet been mapped exactly. The independent default-on
`KiaEv9ClusterSpeedLimitEnabled` flag can restore the prior all-zero/dashes output for isolated testing.

Route `00000106--2e49e586a6` also demonstrated why camera recognition and map data must remain separate. During segment 6,
the camera speed-limit field stayed zero while `starpilotPlan` selected a 25 mph `Map Data` limit for 111 of 120 qlog
samples. The default-off `KiaEv9ClusterMapSpeedLimitFallbackEnabled` flag can use a valid, live selected Map Data,
Mapbox, or Vision limit for the display only when the camera reports zero. Camera values always take precedence; the
fallback uses neither the configured offset, next limit, cruise set speed, nor longitudinal plan, and clears immediately
when the selected source becomes invalid. This changes the cluster from strict OEM camera semantics and is therefore kept
independently opt-in for testing.

Route `00000106--2e49e586a6` exposed a distinct CCNC lane-curvature encoding issue. Its reconstructed `0x161` always used
physical `LANELINE_CURVATURE=0`, which this DBC packs as raw bits `17` and the cluster renders as a right curve. All 3,600
full-rlog stock samples inspected across routes `000000d4--5296076dfd` and `000000d6--f9d3fb2962` used raw bits `0`,
decoded by this DBC as physical `15`, even while the camera lane curvature changed in both directions. The default-on
`KiaEv9NeutralLaneCurvatureEnabled` flag restores that stock-neutral physical `15` / raw `0` value at the existing 20 Hz
CCNC rate. Disabling it restores the legacy physical `0` / raw `17` encoding strictly for A/B testing; no model, steering,
or camera-derived lane animation is synthesized.

`KiaEv9RadarQualityFilterEnabled` is retained as the persisted compatibility key for a display-only discriminator; the
name does not establish radar quality semantics. It independently applies the stock-correlated MRR35 raw field
`UNKNOWN_7 > 200` only to reconstructed EV9 CCNC objects. The physical meaning and units of bit 152 remain unknown, so
this discriminator is not used for validity, `RadarData`, `liveTracks`, fusion, planning, or safety decisions. Full
stock-route comparison retained 99.23%/99.93% of displayed objects, while all 12,791 parked garage-track samples in route
`00000106--2e49e586a6` measured 124–126 and were rejected. Disabling the flag restores the previous display-only tracker
behavior.

Mirror BSM remains separate from CCNC adjacent-object rendering and the
`LCA_LEFT_ICON`/`LCA_RIGHT_ICON` availability indicators. Stock routes show
that `0x36A.SIDE_DETECT_STATE` uses `0x02` as a constant base/equipment bit plus
`0x08` right and `0x10` left, but has no confidence or lifecycle fields and does
not faithfully match genuine `0x1BA` mirror indications. The default-off
`KiaEv9RawBsmReconstructionEnabled` experiment therefore preserves genuine
`0x1BA` only while it is fresh (100 ms) and otherwise reconstructs neutral BSM.
If explicitly enabled, raw `0x36A` is accepted only when fresh, the base bit is
present, the vehicle is in Drive, and speed is at least 4.3 m/s. That threshold
is the lowest active-lamp speed observed across the complete d4/d6 stock routes
and prevents the confirmed stationary false warnings. Synthetic EV9 `0x1BA`
changes only the stock-correlated BCW/OSM left/right state fields; it leaves
`BCW_Sta`, `FL_INDICATOR`, `FR_INDICATOR`, and sound/braking requests neutral.
The still-live ACAN `0x235`–`0x248`
corner-object group was evaluated against the July 11 stock-ADAS routes
`000000d4--5296076dfd`, `000000d5--ed0c9e21bb`, and
`000000d6--f9d3fb2962`. These routes have openpilot longitudinal disabled,
PCM cruise enabled, genuine bus-1 `0x1BA`, and no synthetic `sendcan 0x1BA`.
Their 17 canonical `userBookmark` events include visually confirmed adjacent
vehicles and genuine lamp transitions: both sides in d4 segment 7, right in d4
segment 16, left across d4 segments 17/18, and left in d6 segment 13.

Those labeled scenes disprove a geometry-only reconstruction. In d4 segment 7
the near side tracks first enter `0x235`–`0x248` while or after both mirror
warnings clear; d4 segment 9 likewise exposes its plausible left-side object
only after the left warning ends. Across d4 segments 17/18 one continuous q35
track persists through a stock on/off/on lamp sequence, while the route-106
garage wall is also a stable q35 side-zone track. An exhaustive search across
11 genuine BCW activations and 12,711 upstream bit-transition candidates found
no side-specific ACAN/CAM decision bit with useful precision and recall. The
best `0x235`–`0x248` candidates reached only 0.7%–4% precision. ADAS_DRV is
therefore deriving `0x1BA` internally from information/history not faithfully
available in the retained decoded streams, so no forward mirror-BSM classifier
is guessed here. A single reverse event suggests `0x1E5` byte 4 value `0x11`
may be an object-presence envelope for the stock 0.8 s on/0.2 s OSM flashing,
but one event is insufficient to enable reconstruction.

### Route 00000108 follow-up: fail-closed BSM and object rendering

The 2026-07-13 drive `00000108--6951984998` validated the direct-angle steering path, but exposed three display issues.
First, `0x36A` asserted the proposed left/right bits for about 46/10 seconds even though the stock-route comparison gives
those bits only roughly 16–23% precision against genuine `0x1BA` warnings. It remains an experimental input and is not
safe to enable as the device's BSM source. Side CCNC objects now require a matching BSM decision by default, so the
fail-closed configuration renders neither false mirror warnings nor raw-track side cars.

Second, the captured pre-suppression `0x1BA` body can contain `OSMrrLamp_* = 3`. The original delta overlay left those
nonzero fields untouched: 15,321 of 16,357 synthetic frames in route 108 decoded as neutral BCW state but both OSM lamps
at 3. Reconstruction now explicitly overwrites all four verified BCW/OSM left/right fields and recomputes the checksum.

Third, the filtered primary object was calculated after `openpilot_lead_*` had already been copied into `CarState`.
Consequently all 2,787 transmitted front-object samples had `LEAD_DISTANCE=0.0`. The final filtered result is now copied
after tracking, and the default display path requires the fused radar-backed primary track instead of falling back to an
arbitrary center raw track. `KiaEv9ClusterObjectsOnMainEnabled` permits confirmed objects in CC Main standby. CC Main
renders the stock gray `HDA_ICON=1`; SET/RES engagement renders green `HDA_ICON=2`. The LCA icons remain gray availability
indicators and never encode a blind-spot detection.

The display tracker mirrors the observed stock lifecycle more closely: a stable physical radar track requires three
samples to acquire, survives at most four missing 20 Hz radar frames, and is hard-cleared on Main-off, radar invalidity,
standstill, or any gear other than Drive. The primary slot is reserved for the fused/selected radar-backed lead and uses
the white-box type 2; unique adjacent tracks use gray-box type 1 with the fixed 3 m side marker. `LEAD_ALT` remains
disabled because no stock EV9 reference used it and fused `leadTwo` frequently duplicated `leadOne`. Displayed range
applies the stock-correlated 0.2 m encoding offset.

Adjacent display objects are independent from mirror BSM by default. `KiaEv9ClusterStrictSideObjectFilterEnabled`
uses the stock-correlated mature MRR35 lifecycle (`UNKNOWN_7 > 280`, states 2/10/2/1) plus the observed adjacent-lane
geometry. Across the stock d4+d6 corpus this classified left-side display frames at 92.7% precision and 87.8% recall.
The original symmetric right rule reached only 42.8% precision and created multi-second ghosts in the d6 holdout. A
stateful asymmetric rule now requires a mature track to enter at `2.8 < |y| < 4.3 m`, below 60 m and with at least
2.78 m/s absolute longitudinal motion, then retains the same address inside a wider exit envelope. With three-frame
acquisition it reached 97.0% precision / 75.5% recall and produced zero d6 right ghosts. The display-only
`KiaEv9ClusterRightObjectsEnabled` gate defaults on and remains independently disableable. It is not a BSM decision.
`KiaEv9ClusterSideObjectsRequireBsmEnabled` can additionally require an experimental BSM permission decision.

Stock warning scenes kept `CCNC_0x161.BCA_LEFT/BCA_RIGHT`, lane-change arrows/sounds, and `CCNC_0x162.VIBRATE` at zero;
those fields must remain neutral. Mirror/dash BSM warnings use `0x1BA`. When a trustworthy BSM decision exists, the
reconstructed per-side warning animation now matches stock: BCW state 2 remains asserted, OSM flashes 0.8 seconds on and
0.2 seconds off from a warning-relative phase, and a same-side signal starts the one-shot approximately 1.8-second
`BCW_*SndWrngSta` envelope. The car produces its audible/steering-wheel-haptic warning downstream from that state; it does
not require a synthetic CCNC `VIBRATE` command. `KiaEv9SoftwareBsmWarningOutputEnabled` is a separate default-off gate.

An experimental software BSM estimator is staged behind three independent, persistent default-off gates:

- `KiaEv9SoftwareBsmEnabled` runs and logs the shadow estimator only.
- `KiaEv9SoftwareBsmCommaOutputEnabled` permits that estimator to populate comma left/right blind-spot state.
- `KiaEv9SoftwareBsmVehicleOutputEnabled` permits the estimator to feed the synthetic `0x1BA` mirror state and,
  when the separate rear-display fallback is enabled, the CCNC rear object slots.

Fresh native `0x1BA` remains authoritative. Without it, the estimator requires fresh raw `0x36A`, Drive, at least
20 km/h to retain (40 km/h to acquire), less than 10 degrees steering angle, and qualified measured radar tracks for
the empirically weaker left-side signal. It never feeds longitudinal planning, braking, AEB, or BCA. When the separate
comma-output flag is enabled, its `CarState` blind-spot state also conservatively blocks an openpilot lane change, just
like native BSM; keep that output disabled during shadow validation. A same-side turn signal promotes BCW to persistent
state 2 while the outside mirror lamp follows the observed cadence; hazards never escalate. Brake and BCA request fields
remain untouched.

A second route-held-out search tested 82,780 samples with retained payload history at 0.1, 0.2, 0.5, 1, 2, 4, and 5
seconds. No forward BSM precursor transferred between routes: useful-recall thresholds achieved only about 26%–32%
precision, while high-precision pockets covered 1%–4% of native warnings. `0x449` and `0x472` are downstream generic
warning envelopes without side identity; they did not precede ordinary state-1 BSM onset. This rules out treating raw
track history as a decoded OEM warning bit. The software estimator remains explicitly heuristic.

### Rear cross-traffic and CCNC headway decoding

The Saturday reverse routes contain three clear right-side rear cross-traffic warning episodes. Their target decision is
ADAS-originated `0x1E5.RCTA_TARGET_STATE=1` (`2` is the neutral state), followed by native `0x1BA` right OSM warning and
retained downstream warning envelopes `0x449.SIDE_WARNING_ACTIVE=1` and
`0x472.SIDE_WARNING_OUTPUT_STATE=0x80` (neutral `0x40`). Messages `0x449` and `0x472` still transmit when ADAS TX is
suppressed, proving their output ECU remains online, but they become neutral because they are downstream consumers rather
than independent target sensors. Cross-route testing of the retained raw rear-radar tracks could not reproduce the ADAS
target decision: the best aggregate bit had only 29.1% precision, and route-held-out classifiers had zero recall. Thus
RCCA warning and braking are currently lost with ADAS TX disabled. No braking-tier event was captured, so no synthetic
RCCA braking request is staged.

The horizontal line rendered ahead of the vehicle is `CCNC_0x161.TARGET=3` at `TARGET_DISTANCE`. Stock copies the SCC
desired following-headway distance: it tracks ego speed at approximately 1.626 seconds and has essentially no correlation
with lead range, requested acceleration, or braking. Reconstruction now sends that headway marker instead of the prior
zero/sentinel placement. Front vehicle range continues to use the fused SCC/radar-selected lead independently.

The same route showed EV9-only invalid-message cascades lasting at most 0.651 seconds while every service remained alive
and at frequency. The invalid-only debounce is one second; dead or slow services still trigger immediately. The separate
`locationdTemporaryError` events are not hidden by this debounce.

Probe mode 4 is a reset-assisted diagnostic-only experiment using the validated mode-2 request. It sends an ADAS ECU
reset before re-entering extended diagnostics and requesting `28 01 03`. The 2026-07-11 direct OFF-to-READY test entered
extended diagnostics successfully after reset but returned NRC `0x22` for all ten CommunicationControl attempts. It then
fell back cleanly to stock SCC with no dash DTC, Panda fault, or blocked transmission. Mode 4 is retained only to make that
negative result reproducible; it is not a working startup mode and must not be used for actuation.

The same test session ruled out the Ioniq-6-style `28 01 01` and community-style `28 03 01` requests in READY; both
returned NRC `0x22`. With the vehicle OFF, neither immediate shutdown nor driver-door wake powered `0x730` enough to enter
extended diagnostics. At present the EV9 accepts verified transmit-disable only in ignition-on/non-READY state.

Probe mode 5 tests a distinct READY-state transition proposed after those results: `28 03 03` first disables reception
and transmission for normal plus network-management communication, then `28 01 03` re-enables reception while keeping
transmission disabled. Both responses must be positive. Failure of the second step explicitly sends `28 00 03` before
the normal stock-SCC fallback. This mode is experimental, feature-gated, and non-actuating at stage 16.

## Actuation preflight and closed-course sequence

Every stage change below is made while the vehicle is fully OFF, followed by a comma reboot. Do not change parameters
while controls are running. Keep a clear path, seat belt fastened, service brake covered, and have a second person record
the cluster/comma if available.

### Run D: stage 16 non-actuating preflight

1. Configure enable=true, stage=16, probe mode=2, and `AlphaLongitudinalEnabled=true`; reboot the comma.
2. Turn ignition ON without READY. Confirm normal vehicle identification and no dash DTC/warning state.
3. Enter READY in Park and wait 30 seconds. Confirm the comma remains normal and the dash remains clear.
4. With the brake held, shift to Drive. Release the brake only on a flat, secured test surface, remain below `5 m/s`, and
   engage openpilot briefly. The car must not accelerate or brake in response to openpilot at stage 16.
5. Disengage, shift to Park, power fully OFF, and provide the route/segment plus whether any warning or motion occurred.

The log must show `EV9 ACTUATION PREFLIGHT`, healthy radar/CAN/Panda inputs, and an inactive SCC command. Any abort or
unexpected motion stops the test; do not proceed to stage 17.

### Run E: stage 17 bounded actuation

Only after Run D is reviewed, configure stage 17 offroad and reboot. The first test is a single straight-line engage below
`5 m/s` on a flat closed course, with no lead vehicle, no stop/resume, and immediate manual brake takeover. Start from a
stable slow roll rather than a standstill. One clean engage/disengage is enough for the first route; review requested versus
actual acceleration and every safety/gate state before any follow-up test.

## First test sequence

Do not drive on a public road during this sequence. Keep the vehicle in Park with room around it, and have a second person
record the instrument cluster and both mirror indicators if possible.

For every run, record the stage number, route name, wall-clock start time, whether the vehicle is OFF/IGN-ON/READY, and
every visible or audible warning. Change only the stage between runs.

### Run A: stock baseline (stage 0)

1. Set `KiaEv9LongitudinalTestEnabled=false`, `KiaEv9LongitudinalTestStage=0`, and
   `AlphaLongitudinalEnabled=false`; reboot the comma.
2. Start with the vehicle fully off, then switch to IGN-ON without pressing the brake.
3. Wait 30 seconds, transition to READY while remaining in Park, and wait 60 seconds.
4. Hold the left turn signal for 10 seconds, wait 10 seconds, then hold the right signal for 10 seconds.
5. Save every full `rlog.zst` segment covering the run plus a cluster/mirror video.

### Run B: shadow baseline (stage 1)

Repeat Run A with `KiaEv9LongitudinalTestEnabled=true`, `KiaEv9LongitudinalTestStage=1`, and
`AlphaLongitudinalEnabled=true`. Stage 1 must not send CommunicationControl; its traffic should match stock behavior.

### Run C: transmit-disable only (stage 2)

1. Configure stage 2 offroad and reboot the comma while the vehicle is fully off.
2. Switch to IGN-ON without pressing the brake. Wait at least 30 seconds so the confirmed `0x730` UDS transaction can
   finish before entering READY.
3. Record the exact time of the first dash warning. Do not clear warnings or change settings.
4. Transition to READY while remaining in Park. Wait 60 seconds, then repeat the left/right turn-signal sequence.
5. Power the vehicle fully off. Restore stage 0 and both enable flags to false, reboot the comma, and allow the vehicle to
   complete a normal sleep/wake cycle before checking that warnings clear.

Stop after Run C and compare its logs with A and B. Do not advance to stage 3 until the disappearing address set, UDS
success, CCNC faults, `0x1BA`, and MRR35 continuity have been reviewed.

## Capture markers and required bundle

Normal route logging should be active whenever ignition is on. When SSH access is available, run the bounded helper in a
second terminal to add precise markers (replace `DEVICE_IP` and the label):

```bash
python3 ~/.codex/skills/starpilot-can-log-capture/scripts/starpilot_can_capture.py \
  --target comma@DEVICE_IP --ssh-key ~/.ssh/id_ed25519 \
  start --label ev9-stage2 --duration 600

python3 ~/.codex/skills/starpilot-can-log-capture/scripts/starpilot_can_capture.py \
  --target comma@DEVICE_IP --ssh-key ~/.ssh/id_ed25519 \
  mark --label ev9-stage2 --action ignition_on

python3 ~/.codex/skills/starpilot-can-log-capture/scripts/starpilot_can_capture.py \
  --target comma@DEVICE_IP --ssh-key ~/.ssh/id_ed25519 \
  mark --label ev9-stage2 --action ready_in_park

python3 ~/.codex/skills/starpilot-can-log-capture/scripts/starpilot_can_capture.py \
  --target comma@DEVICE_IP --ssh-key ~/.ssh/id_ed25519 \
  mark --label ev9-stage2 --action first_dash_warning

python3 ~/.codex/skills/starpilot-can-log-capture/scripts/starpilot_can_capture.py \
  --target comma@DEVICE_IP --ssh-key ~/.ssh/id_ed25519 \
  stop --label ev9-stage2
```

For analysis, provide:

- The route identifier and every full `rlog.zst` covering Runs A-C; do not substitute qlogs.
- The helper capture/marker files when used.
- Cluster and mirror video with the phone clock visible, or a timestamped written warning list.
- A note confirming the three parameter values, the IGN-ON-to-READY timing, and whether UDS disable reported success.
- No VIN, precise location, access token, SSH private key, or other credential.
