# Local and release checks

On Linux, use the managed host runtime to run the same source, unit, vehicle and pinned
recording checks and process replay as GitHub Actions:

```sh
./dev python tools/ci/run_predeploy.py --output /tmp/starpilot-predeploy --download
```

The default run first builds the host native graph, then also runs the native
Panda protocol executables and required Go/Python IPC checks.
Use a new output directory per run. `--download` permits only the pinned public
recordings; omit it when they are already cached. Node.js 24 must be on PATH (or
set `STARPILOT_NODE`), and the pinned Go toolchain/dependencies are needed for map
provider checks. A failure stops the run with a named log and preserves its exit
status in `results.json`. `--stage build`, `source`, `host`, `native`, `vehicles`, `recorded`, or `replay` can
select a stage while diagnosing a failure; a selected-stage pass is not a full
release result.

The replay stage runs the full process suite with its existing coverage and
reference comparisons. It can download replay logs independently of the pinned
recording `--download` flag. Unaccounted missing routes and unqualified historical schema caches fail.
Volvo C1/V40 is explicitly reported as lacking a recording, with its source and
native suites required separately; see the process replay README for details. Passing the pinned recorded vehicle checks does not qualify this
separate suite.

The full runner requires Linux: its USB/native transport and executable map
IPC tests use Linux facilities. Run `tools/setup_dependencies.sh` first, provide
the Node and Go versions above, and fetch the pinned map dependencies with
`(cd mapd_repo && go mod download)`.

On macOS, build host dependencies and run the source/host subset:

```sh
./dev python -m SCons -j4
./dev python tools/ci/run_predeploy.py --stage source --stage host --output /tmp/starpilot-host-checks
```

This subset does not qualify Linux native transport, vehicle/recorded suites,
or device artifacts. The full runner rejects an unsupported native-stage host
before executing checks.

Before shipping device artifacts, run `./build 4` in the source checkout after
host validation. Host tests do not replace the device build, native firmware
qualification, device startup checks, or physical vehicle testing. GitHub also
runs platform-specific build, replay and rendering jobs.

## Vehicle contract checks

Run the rebuilt feature and CI tests locally after building native dependencies:

```sh
python tools/ci/run_host_tests.py openpilot/starpilot tools/ci/tests --json-output feature-results.json
```

`tools/op.sh test` uses this wrapper too. It forwards test selection and reporting
options to `tools/test_runner.py`.
It creates disposable Params and messaging directories before any test imports,
then removes them after the test process exits, including on failure. Existing
developer settings and IPC namespaces are not used. It also sets `SCALE=1` so UI
imports do not query a desktop monitor. This is host logic testing; native visual
captures and device rendering need their own graphics context. The hosted unit
job uses the same wrapper for the complete `openpilot` test tree. Galaxy tests
require Node.js 24 on PATH or selected with `STARPILOT_NODE`.

The source-integrity job also enforces cereal's custom-fork guidance with
`tools/ci/schema_policy.py`. The pinned `car.capnp` and other upstream schemas
must remain unchanged apart from the exact additive exceptions enumerated in
`schema-policy.json`; those exceptions are checked against the pinned source. Fork fields belong inside the reserved `custom.capnp`
structs; their type IDs stay fixed and `log.capnp` may rename only the associated
reserved event aliases, keeping their ordinals and type associations. The check
allows nested custom fields while rejecting edits to upstream-owned definitions,
reused IDs and retargeted events. `schema-policy.json` records the official source
pins and schema hashes; review it alongside `upstream-sync.json` when updating
upstream. Every `.capnp` file under `openpilot/cereal` and
`opendbc_repo/opendbc/car` requires explicit policy coverage; new schemas fail
until reviewed. This guard prevents upstream schema collisions; it does not replace
append-only evolution and compatibility testing of already shipped custom fields.
Slots 1–3, 5–8 and 10–11 in `custom.capnp` were used by older fork logs and remain
empty under their original names until a reviewed, append-compatible layout is
restored. Keeping a type ID alone does not preserve the meaning of its fields;
reusing one of these slots for a different event could misread older recordings.
Slot0 preserves the historical car-control HUD and steering-limit prefix and
appends versioned nested navigation fields. Navigation readers require version2;
old car-control records do not become navigation commands.
Slot4 restores `StarPilotModelDataV2` at Event111, including its original
turn-direction field and enum, then appends a typed Vision observation. Slot9
retains all six historical model-status fields and appends SLC fields at6–30.
Native historical-reader fixtures protect both layouts and prove that an old
model-status record cannot advertise an active speed limit. This corrects the
unreleased Domathon slot9 reuse; earlier development recordings need their exact
source schema for replay. That one pre-release layout correction is explicit in
the compiled baseline; it does not permit future incompatible regeneration.
Slots 17/18/19 previously carried `MapdExtendedOut`/`MapdIn`/`MapdOut` at
Event ordinals 143/144/145; none is available for an unrelated new envelope.
Slot19 now restores `MapdOut` with all24 historical fields and three additive
fields from the pinned provider. Seven further append-only fields carry sample
status, source, GPS/computation times, generation and process session. V2 converts
the Python GPS MONOTONIC observation to BOOTTIME only after a startup/resume
fence; computation and output use BOOTTIME too. Older versions are unqualified
for diagnostics, and no version grants map-based control authority. Its referenced enums live inside the reserved
struct with their original explicit type IDs. Compiled-layout and real historical/Go
wire fixtures protect the restored contract; core `car.capnp` is unchanged.
Slots17/18 now restore the historical extended status and input layouts as well.
The newer provider adds position and loop-rate status, a JSON path input field,
and further input enum values. All older fields, helper type IDs and enum meanings
are preserved; helper types are nested inside their reserved roots. Opaque pointer
defaults are compared as serialized schema values in the compiled contract.
This schema restoration alone does not start the provider, expose settings
commands, or connect it to SLC control.
Development AOL safety and intent previously collided with 143/144 and are
retired from the compiled contract. Their transport now uses separate reserved
`Data` ordinals 124/125 with bounded, versioned flat nested payload layouts protected by the
compiled contract. The previous contract is archived in the external migration
audit. Old development recordings need source-aware conversion; merely matching
an Event ordinal must never select an AOL decoder.

Lane Change Assist uses the separate reserved `Data` ordinal 126. Its bounded
typed payload is nested under `AolAxisState` as an independent schema declaration;
it adds no fields to the published AOL state. Modeld owns this optional diagnostic
service. Its frame-matched status changes pre-change alert wording and grants no
control authority; missing status does not block ordinary engagement. The compiled
contract protects the new payload and enums as well as every prior layout.

The native StarPilot test suite also runs `test_custom_schema_evolution.py`.
`custom-schema-contract.json` records the compiled layouts of the first populated
custom messages. This check allows additions while preserving their field names,
types, offsets, defaults, union tags and enum ordinals. Field names are protected
as an application API in addition to the wire layout. Extend the contract from
a reviewed committed schema when a new message generation becomes a baseline;
never regenerate it just to silence an incompatible change. This does not convert
recordings made with older divergent vehicle schemas.
The reviewed baseline includes the SLC and independent-axis message families.
The unit job also executes the native Panda protocol test with fake transport;
it exercises the parser and negotiation state used by pandad without a device.
`test_aol_wire.cc` asserts the native safety encoder's bounded flat payload;
the matching Python fixture decodes its exact bytes. A full Linux pandad build
is still required for native call-site coverage on a Linux target.

The default `tools/op.sh test` discovers the `openpilot/` tree. Vendored dependency
tests need explicit jobs. The root workflow runs these host-only suites:

```sh
python tools/ci/run_vehicle_tests.py --suite interfaces --output ci-results/interfaces
python tools/ci/run_vehicle_tests.py --suite safety-debug --output ci-results/safety-debug
python tools/ci/run_vehicle_tests.py --suite safety-release --output ci-results/safety-release
```

Add `--collect-only` to inspect the selected IDs without running tests. Collection
is explicitly marked `not_run`. Each run writes `plan.json`, complete per-test
`results.json`, and `coverage.json` with source/dependency identity, native library
hashes, actual safety compiler commands and version, outcomes and uncovered areas. The safety
library used by behavioral tests is compiled once, loaded explicitly, and used in
one test process; no worker can silently rebuild a different loaded variant.
The runner also compares the selected vehicle/control source areas before and
after execution, including uncommitted patches and untracked files. A changed
snapshot fails the gate while retaining every individual test outcome. Keep
results outside those source areas. These endpoint checks do not detect a change
that is reverted during execution; qualification runs still require an isolated,
stable checkout. Native binary provenance remains separate from source snapshots.
The debug suite also retains the existing two compile-only variant tests.
`FUZZ_SEED` defaults to `0` for
reproducible input generation. An explicit `MAX_EXAMPLES` override is recorded.

The interface suite recursively includes `test_*.py` files throughout `opendbc/car`,
including brand-specific tests. Only the exact route module `car/tests/test_models.py`
is excluded. Each module's source hash and collected count are recorded; a module
that silently collects zero tests fails the gate. Files containing module-level
pytest tests or plain pytest classes run once through pytest, including any unittest
classes in those mixed files; other files retain the unittest runner. Both runners
execute serially in the same process with the pinned native library. AST checks
reject declared test functions and methods without a collected counterpart,
including when other tests in that module were collected.
It asserts exact equality between the current platform registry and concrete
generated interface tests: a missing, duplicate or extra platform fails collection.
Abstract-class skips cannot satisfy platform coverage.
Every mapped concrete interface test must pass: a class-level skip stays visible
in the report and fails the interface coverage gate. Initialization and collection
errors also produce error reports, including when a native import fails.
The suite also runs the existing
platform, limits, fingerprint, docs and route-declaration checks. A route exemption
is reported as missing route coverage, not as a tested vehicle.

`test_models.py` generates its route-backed classes only when directly executed.
Importing it with generic discovery would produce abstract skips, not a full
vehicle replay. Historical route/schema qualification remains a separate gate;
this workflow does not fetch those routes or regenerate expected outputs.

## Recorded vehicle regressions

`run_recorded_vehicle_tests.py` runs the pinned public Model Y CAN fixture through
current parser, controller and native safety tests. DEBUG includes stock and
alpha-long configurations; RELEASE includes stock only. Alpha-long exclusion is
recorded explicitly, and missing, skipped or errored selected cases fail the run.
This checks recorded CAN and synthetic controller behavior, not the user's
weekend failure, physical harness operation or complete vehicle identification.

```sh
./dev python tools/ci/run_recorded_vehicle_tests.py --variant debug --cache /absolute/cache/path --output /absolute/results/path --download
```

Use `--variant release` for the separate RELEASE library. `--download` permits
only the manifest's public fixture URLs before execution; cached compressed
bytes must match their pinned size and SHA-256. Omit it for fully offline use.
Each process owns temporary Params and IPC, disables replay networking, records
actual controller configuration and native library identity, and rejects source
changes during the run. Use a new result directory to retain earlier evidence.
The hosted `recorded_vehicles` matrix runs both variants and retains reports even
on failure. A local pass does not establish the result of a later GitHub run.

The debug safety suite includes all top-level safety test files with `ALLOW_DEBUG`.
The release safety suite compiles without that flag and checks the entire enum
against the explicit release hook registry. Its behavioral cases are deliberately
limited to no-output/silent, stock Tesla (including FSD14), Mazda, stock-longitudinal
Toyota torque, GM camera/EV and four additional manual camera-ACC variants, Bolt
Pedal, intercepted GM ASCM, stock SDGM, nine stock conventional-cruise gateway
variants, Ford ownership/Transit steering contracts, six manual Honda/Acura Nidec
variants, three manual radarless Honda/Acura Bosch variants, two manual Subaru
angle-steering variants, four manual MRR35 Hyundai/Genesis angle variants, three
manual Hyundai/Kia angle hybrids, two manual CCNC angle SUVs, and Carnival alternate-button resume. The Carnival tests use
the runner's recorded safety library and include a real stock-cruise RX sequence
with the exact frame emitted by the host controller. It also checks that the
DEBUG-only Honda Bosch longitudinal path cannot grant AOL requests in RELEASE,
including the classic Bosch family controller frames and brake-source variants.
The Ioniq 6 tests enumerate every bit-15 safety parameter and require RELEASE
to deny all dedicated longitudinal/AOL profiles. Their DEBUG controller and
takeover cases remain explicit skips in the RELEASE result.
The selected classes are listed in `RELEASE_TARGETS`;
other release behaviors are uncovered, not silently skipped into a green result.
The suite is not a whole-fleet release-mode safety qualification.

Two separate hosted jobs compile Panda firmware with DEBUG and RELEASE flags.
Both use the checked-in development certificate. The recorder requires an actual
main-source compile command with matching flags and captures ELF/binary hashes and
the version stamp. These jobs do not use release credentials, flash hardware or
qualify firmware compatibility. Build logs and provenance are retained on failure.

All jobs run on hosted Ubuntu without a device or self-hosted runner. A passing
interface test or safety hook unit test does not cover additional downstream car
ports, independent lateral/longitudinal modes, real CAN forwarding, hardware,
timing, logs from another schema, AGNOS, or deployment/rollback behavior. Skips
remain explicit in the JSON report; they do not count as passes.

After the interface suite, the workflow runs the
[exact fleet coverage gate](FLEET_COVERAGE.md) and saves its report in the same
artifact. This step fails while required ports, current interface results or
recorded configuration/mode evidence are missing. It currently supplies no mode
evidence, so the fleet gate remains uncovered even if every interface test passes.
This is intentional during reconstruction: successful unit tests alone must not
produce a fleet-wide green result. Recorded mode evidence needs its own reviewed
producer before it can be connected here. The gate also runs after an interface
failure; available collection and execution records remain in the artifact.

The small collection/provenance fixtures need only the standard library:

```sh
python -m unittest discover -s tools/ci/tests -v
```

The map-provider job runs `tools/ci/run_map_tests.py` with the Go version pinned
in `mapd_repo/go.mod`. It records test outcomes, vet/build results, dependency
pin, source hashes and embedded build identifiers. It does not start the provider
or fetch maps. Runtime integration and a Linux ARM64/device build remain separate
checks; see `mapd_repo/INTEGRATION.md`.

The unit job additionally requires the real Go-to-host map messaging test after
building the host's native dependencies. It supplies pinned Go 1.25.1 and the
repository Python environment, then runs this from `mapd_repo`:

```sh
STARPILOT_SHADOW_IPC_REQUIRED=1 STARPILOT_SHADOW_EXEC_REQUIRED=1 \
STARPILOT_PYTHON=/absolute/path/to/.venv/bin/python \
  go test -mod=readonly -race -run '^TestShadow(GoPythonIPC|ExecutableHostGpsIPC)$' -count=1 -v
```

Both tests use synthetic GPS/tiles and a disposable IPC namespace. The first
uses a Go pump and publisher harness; the second builds and starts the actual
shadow executable under isolated settings, then passes host GPS through the Go
subscriber and reads its output in Python. Neither uses installed maps or the
full provider mode. Missing host dependencies fail these required tests. The
standalone provider suite reports explicit skips when their required targets
are not selected; those skips are covered by the required unit-job step, not
counted as passes.

The Ioniq 6 development branch retains custom AGNOS `19.8.1`, matching the
separately installed image. `AGNOS_UPDATE_POLICY=retain` prevents the launcher, background
updater, and development branch helper from replacing that OS. A version
mismatch blocks startup/update finalization and reports the required version.
Other branches without this policy keep their explicit upstream update behavior.
The retained version is an installation policy; it does not establish native
ABI, camera, model inference or device compatibility with the upstream baseline.
`openpilot/system/updated/tests/test_retained_agnos.py` exercises these paths
using disposable OS markers, fake hardware and intercepted firmware calls.

For a read-only parked trial prerequisite report, run
`python3 tools/ci/run_device_preflight.py --font-dir /path/to/complete/reviewed/fonts --json-output /path/to/report.json`.
The standard-library driver reads the retained AGNOS and Python policy from
`launch_env.sh` and `pyproject.toml`, checks the UI's existing bitmap-font and
artwork manifests, and tries selected library imports in isolated, timed Python
children. It reads `/VERSION` only on a Linux ARM64 host; on a desktop, target
OS status is unavailable. It never starts services, accesses controls or
qualifies graphics, camera, CAN, model inference or driving. Missing optional
font input and absent device checks stay visible rather than becoming passes.
The import probes put this source tree's vendored Python roots first and reject
any loaded openpilot, msgq, opendbc or tinygrad module from another checkout.
The JSON `prerequisites` field is `pass`, `fail` or `incomplete`; command exit
codes are 0, 1 and 2 respectively. Even `pass` is a prerequisite report, never
a device or driving qualification.

The separate safety-qualification workflow runs C-line coverage, pinned
opendbc/Panda MISRA analysis, Panda host tests, and mutation inventory/full
mutation in isolated jobs. It uses the root locked `safety` extra;
it does not call the nested opendbc or Panda setup scripts, which would sync or
upgrade separate environments. A local disposable checkout can run one gate with
`python tools/ci/run_safety_qualification.py --gate coverage --output /new/evidence/dir`
(other gates: `opendbc-misra`, `panda-misra`, `panda-host`, `mutation-list`,
`mutation-full`). Reports include source hashes, imported module origins, exact
commands, full logs, test/skip counts, and an explicit pass/fail result. Coverage
requires 100% of upstream checked C lines; full mutation requires zero surviving
or infrastructure-error mutants and first runs the full unmutated test catalog.
`HITL` is explicitly unset: Panda/Jungle/vehicle hardware tests remain a separate
bench gate and their skips are recorded, never labeled as host passes.
