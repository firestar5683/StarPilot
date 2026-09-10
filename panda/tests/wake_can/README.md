# Optional Tesla wake-on-CAN

The Vehicle settings page offers **Wake Comma with Tesla** for detected Tesla Model 3,
Model Y and Model X platforms that use `VCFRONT_LVPowerState` on the party bus.
It is hidden for other makes, unknown vehicles and pre-AP Tesla Model S.
`TeslaWakeOnCAN` is a persistent boolean, default off. Changing it while parked
uses the existing confirmed Panda firmware update/reboot flow.

## Wake and ignition contract

- Only firmware built with `PANDA_TESLA_WAKE_ON_CAN` enables the extra wake path.
  Startup and manual update select it only with the toggle enabled and a matching
  supported Tesla identity. Conflicting selected vehicle or corrupt CarParams
  disables selection. Other firmware variants never set the extra wake flag.
- Accepted wake packets are standard CAN frames on bus 0, ID `0x221`, length 8.
  Byte 7 must equal the sum of address bytes and payload bytes 0–6 modulo 256.
  Two checksum-valid frames with consecutive modulo-16 upper-byte-6 counters are
  required. Invalid checksum or extended frames break that wake counter sequence.
- `(data[0] >> 5U) & 0x3U`: OFF=0, CONDITIONING=1, ACCESSORY=2, DRIVE=3.
  Valid non-OFF states set the independent wake flag. Accepted OFF clears it.
  Invalid traffic cannot refresh it; the existing tick expiry clears stale wake.
- The original DRIVE ignition decoder is unchanged, including its own counter
  tracking. Extra wake never asserts ignition or enters watchdog/control inputs.
- Bootkick tracks ignition and wake edges separately. A fresh wake edge can boot
  while ignition is false. A held ACCESSORY state cannot mask a later DRIVE edge.
  Harness, heartbeat priority, reset countdown/cancellation and one-reset-per-MCU-
  boot behaviour remain intact.
- Stock host timeout, battery, voltage, thermal and forced shutdown remain in
  force. This feature does not keep the host or car awake. Held wake does not
  repeatedly boot the host; a new wake edge can wake it after shutdown.

The checksum layout is defined in
`opendbc_repo/opendbc/dbc/tesla_model3_party.dbc`; the checksum algorithm is in
`opendbc_repo/opendbc/car/tesla/teslacan.py`. Checksum validation is integrity
checking, not authentication. Physical early-message availability and vehicle
wake behaviour still require hardware validation.

## Repeatable local checks

```
ulimit -c 0
python3 panda/tests/wake_can/run.py --evidence /absolute/evidence/green
python3 panda/tests/wake_can/host_policy.py --evidence /absolute/evidence/host
```

The runner compiles verbatim production decoder, full 8Hz tick, bootkick,
ignition-line and safety-mode predicates, and Cuatro GPIO callback, with fixture
peripherals. Each scenario runs in a fresh process. It covers 48 configurations:
Tesla, HKG, GM, IgnoreIgnitionLine, and three DEBUG/ALLOW_DEBUG combinations.
There are 600 scenario executions, 960,000 ignition/watchdog parity frames and
960,000 no-wake boot/reset/harness/GPIO parity frames against Dom
`bb04e935272ccbc7551dd5f46d18197757a35587`. Compilation uses warnings-as-errors and
UBSan. `--base REV` selects another stock reference. `--red` verifies that stock
lacks the extra non-OFF wake; optional `--regression-ref REV` can test a historical
version that masked the DRIVE edge if available locally.

Host tests cover Tesla detection, stale identity, firmware-selection combinations,
missing files and normal update/signature behaviour. Galaxy/native settings tests
cover Tesla-only visibility and capability checks, parked-only writes, required
confirmation, cancellation and firmware preflight. `host_policy.py` exercises
actual shutdown methods with synthetic clocks and Params, without device access.

## Firmware

SCons supplies F4/H7 Tesla variants, each with and without IgnoreIgnitionLine:

```
cd panda
scons --minimal -j4 board/obj/panda_tesla_wake.bin.signed \
  board/obj/panda_h7_tesla_wake.bin.signed \
  board/obj/panda_tesla_wake_can_ignition_only.bin.signed \
  board/obj/panda_h7_tesla_wake_can_ignition_only.bin.signed
```

These use the existing signing configuration. No bootstub, trust key or safety
limit changes are required. Comma 3/3X and comma 4 use H7; comma 4 retains its
Cuatro GPIO callback. A local signed image is not installed firmware or physical
wake/sleep validation. The target Params binding/library must be rebuilt with
the new key before installation of the settings UI.

Initial wake mechanism attribution: dzid26's
[commaai/panda PR2393](https://github.com/commaai/panda/pull/2393/files) and
[AmyJeanes/sunnypilot](https://github.com/AmyJeanes/sunnypilot/commit/57487d8c48be2907760a1553113f7ae7288025dc).
