# Tesla wake-on-CAN, retaining stock power management

Prepared against Dom `b7775991bf673f565c8f31e2a4df027014fe7882`.
Historical integration: `9e8a2fa50`; DRIVE-edge correction follows `b46bede790`.
Early wake only: not continuous-awake or a protective/manual shutdown lockout.

## Production contract

- Existing Tesla Model 3/Y decoder: bus 0, ID `0x221`, length 8,
  consecutive modulo-16 upper-byte-6 counter check unchanged.
- `(data[0] >> 5U) & 0x3U`: OFF=0, CONDITIONING=1, ACCESSORY=2, DRIVE=3.
  Non-OFF sets an independent wake flag. Only DRIVE asserts ignition.
- `main.c` passes original `started`, original `recent_heartbeat`, and separate
  `wake_on_can` to `bootkick_tick`. Original ignition-line/HKG composition stays
  unchanged; wake never enters heartbeat/watchdog or control authority.
- `bootkick.h` tracks ignition and wake previous values independently. Original
  ignition rising edge and harness insertion retain priority over heartbeat.
  Added wake rising edges trigger only while original started/ignition is false.
  Wake transitions while started are recorded, not deferred until ignition falls.
  Reset countdown, cancellation and one-reset-per-MCU-boot logic are unchanged.
- Independent wake expiry retains the `> 2U` tick counter and existing tick order
  (bootkick precedes expiry). OFF clears wake immediately in the decoder.

Production closure: `board/drivers/{can_common.h,can_common_declarations.h,
bootkick.h,bootkick_declarations.h}` and `board/main.c`. The DRIVE correction
itself touches only bootkick implementation/declaration and its sole main caller.
No host changes, Params/schema/protocol changes, transmit/keepalive, timer
suppression, retained shutdown lockout, safety-limit, bootstub/trust-key or
prebuilt changes. Host shutdown, low-voltage, battery, thermal and power-saving
code stays byte-identical to the integration base.

## Provenance and regression

Initial decoder/wake mechanism derives from dzid26's
[commaai/panda PR2393](https://github.com/commaai/panda/pull/2393/files),
head `222d6d16f49096317cf99679c31ed6d0b7235aef`, and
[Amy's implementation](https://github.com/AmyJeanes/sunnypilot/commit/57487d8c48be2907760a1553113f7ae7288025dc).
The original `started || wake_on_can` bootkick argument masked a later stock
DRIVE edge when ACCESSORY remained fresh through host shutdown. This is a
regression, not an accepted limitation. Separate edge tracking corrects it.

Comma 4 uses Cuatro H7. Its unchanged callback drives GPIOA0 low only for
BOOT_BOOTKICK; BOOT_RESET deasserts bootkick, not Tres's separate reset pin.
Physical signal availability before brake and physical wake are unverified.

## Repeatable isolated host checks

```
ulimit -c 0
python3 panda/tests/wake_can/run.py --evidence /absolute/evidence/nonoff-red --red
python3 panda/tests/wake_can/run.py --evidence /absolute/evidence/green
python3 panda/tests/wake_can/host_policy.py --evidence /absolute/evidence/host
```

The runner compiles actual C decoder, full 8Hz tick, bootkick, ignition-line
predicate, safety-mode predicate and Cuatro callback. Peripherals are fixtures,
not a full MCU simulation. Historical bootkick removes only its declaration
include (the current signature differs); a test-only adapter supplies no wake to
legacy stock two-argument calls. Production bodies remain unmodified.

Each scenario uses a fresh process. GCC warnings-as-errors and UBSan cover the
original 16 HKG/GM/IgnoreIgnitionLine and DEBUG/ALLOW_DEBUG configurations, plus
8 default-stock ALLOW_DEBUG-without-DEBUG configurations: 24 configurations,
336 candidate scenario executions, 480,000 ignition/watchdog parity frames and
480,000 no-wake boot/reset/harness/GPIO parity frames against the pinned Dom baseline above.
The identical long-ACCESSORY/shutdown/DRIVE scenario also executes against stock
in every configuration. Ordinary red proves stock lacks the newly requested non-OFF wake feature.
If the historical pre-fix commit is available locally, optional
`--regression-ref b46bede790` checks that it fails the preserved DRIVE assertion.
That historical commit is absent from the handover; it is not needed for the
current DRIVE regression scenario or stock parity checks. `--base REV` can
select another stock baseline explicitly.

Coverage retains all prior decoder/expiry/watchdog/other-car/reset scenarios and
adds independent edges, wake suppression while started, no deferred wake on
ignition fall, heartbeat/harness priority and active-reset dominance with wake.
`host_policy.py` executes actual shutdown-method AST with synthetic time/Params:
normal timeout, exhausted capacity, sustained voltage and forced shutdown still
act with a synthetic wake attribute true. Thermal preservation is source
identity, not a thermal simulation or hardware claim.

## Firmware and remaining gates

The selected build is the unchanged default H7 SCons signed application target,
`--minimal -j1 board/obj/panda_h7.bin.signed`, with existing ALLOW_DEBUG and no
DEBUG/RELEASE/CERT/remote/ignore overrides. Parent verified stock tracked/default
H7 and loaded PandaSignatures use this existing development signer. This is not
a trust change. Do not build/replace bootstub or edit Nissan to force an artificial
no-ALLOW_DEBUG path. That separate mode retains its known unchanged Nissan
unused-variable build failure.

This PR preparation excludes the imported signed binary: it cannot be treated
as a rebuild of this Dom-based source tree. Rebuild the application with the
existing signer/toolchain and record source/artifact hashes before firmware
delivery. A signed offline image is not installed firmware or hardware/vehicle
clearance.

Limitations: held wake is not level-triggered; wake does not keep host/car awake
or inhibit protective/manual shutdown. A genuinely new wake edge can re-wake
without a shutdown-reason lockout. The inherited decoder has no vehicle-specific
enable or Model 3 checksum gate; matching sequential traffic can false-wake.
Parent review and explicitly authorised parked wake/sleep/power, recovery and
vehicle validation remain required. No device contact is part of these tests.
