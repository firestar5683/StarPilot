# StarPilot runtime contracts

Feature-specific behavior belongs with its owner. The [UI guide](ui/README.md)
describes presentation and input boundaries; the contracts below cover shared
audio settings and retained-state migration.

## Alert levels and sound packs

`audio/alert_volume.py` defines seven audible-alert families. Saved integer
`101`, or an absent value, means Auto. Manual levels range from 0–100%, except
Soft and Immediate Warnings, which have a 25% minimum. The immediate warning,
including a selfdrive timeout warning, still ramps to full volume. `soundd`
validates saved levels and refreshes them outside its audio callback. Opening
Settings does not create default values or reset other alert families.

`audio/sound_pack.py` loads the selected installed pack and falls back to the
stock clip when a replacement is missing or invalid. It accepts bounded,
uncompressed mono 48 kHz, 16-bit WAV files; decoded samples are immutable.
`audio/downloads.py` installs catalogued packs with size/hash validation,
bounded extraction and parked-state checks. Sound selection is independent of
onroad colors and layouts. Code tests do not establish audible quality on the
device.

## Settings preservation

`state_migration.py` separates exact recovery from importing preferences:

- `snapshot_settings(namespace, storage)` archives every raw value before cleanup,
  including unknown keys, empty files, binary caches and credentials. It uses the
  native Params lock, private permissions, content hashes and durable writes.
- `restore_snapshot(snapshot, namespace)` verifies the entire archive before
  restoring exact bytes into an unused namespace. It refuses to overwrite an
  existing namespace. This is an offline recovery operation, not an upgrade.
- `validate_bundle(bundle)` checks the versioned neutral settings format.
  `decode_bundle(encoded)` also rejects duplicate JSON members before validation.
  `stage_settings(bundle, storage, namespace)` saves it privately outside Params without
  activating any value. Pending settings have explicit types and raw-byte hashes;
  omitted settings have reasons. Archive and source hashes identify provenance,
  but a syntactically valid bundle is not evidence of feature compatibility.
- `prepare_manager_start(params, storage)` runs before boot logging, clearing
  settings, defaults or registration. Initial startup only accepts an empty
  namespace or reviewed Boolean preferences. Other state is archived and startup
  stops for migration. Subsequent startup rejects unknown keys, malformed
  reviewed preferences and incompatible cache envelopes. Its profile marker
  identifies the namespace and schema epoch; each cache must pass its own
  schema and producer checks, even in a previously initialized namespace.

Event cache writers use version 2 envelopes. Their fingerprint covers the Event
wrapper, common fields and the selected service's complete schema, so unrelated
union members can change without invalidating saved calibration or learned values.
Physical wrapper changes or changes to a stored service still require migration.
Version 1 envelopes remain readable only when their full schema matches the
current runtime; reads do not rewrite them. CarParams envelopes remain version 1.

Before activating an update, `prepare_manager_start(params, storage, dry_run=True)`
checks the retained namespace with the candidate's compiled schemas and registry.
It does not qualify a profile, create recovery files or alter saved values. A
successful check describes that snapshot of state; normal startup still performs
the admission checks before launching processes.

The initial Boolean allowlist is `AlwaysOnLateral`, `IsMetric`, `RecordAudio`,
`RecordFront`, `RecordFrontLock`, `ShowDebugInfo`, `GsmMetered` and
`OpenpilotEnabledToggle`. Saved values must be canonical `0` or `1` bytes.
`AlwaysOnLateral` defaults to false for a fresh namespace; an existing true or
false value is preserved. Registering this preference does not enable lateral
control or claim that the feature has been ported.

The neutral bundle has `format: "starpilot-settings"`, integer `version: 1`,
`source`, `preferences`, `pending` and `omitted`. Source metadata includes the full
source revision, registry SHA-256 and raw snapshot SHA-256. Optional cache fallback
requires a separate `cache_snapshot_sha256`. A raw snapshot hash is the SHA-256
of sorted `{key, sha256, size}` entries encoded as JSON with sorted object keys,
ASCII escaping and separators `(',', ':')`.

Never interpret archived vehicle parameters or logs using a different schema just
because field numbers match. Binary caches, credentials, control-policy settings
and pending feature settings each require their own migration policy. Staging
alone never marks a profile ready. Stop services before export, restore or any
future activation; older runtimes may write a separate cache outside the native
Params lock. Keep private archives outside Params and source repositories.

## Schema-aware caches

`schema_cache.py` stores a versioned envelope in each managed cache value. Payload,
producer contract, key, service, transitive compiled-schema fingerprint and content
hash are written atomically through the existing native Params queue. Live
`CarParams`, messaging and Panda wire formats remain unchanged.

`put_cache` requires a typed message from the current compiled producer schema.
It preserves the caller's blocking/asynchronous write choice. `get_cache` only
returns verified payload bytes; incompatible data stays untouched and is a cache
miss. Startup archives and blocks incompatible existing state before processes
can replace it. Fingerprints are prepared before realtime processing loops.

Managed keys are `CarParamsCache`, `CarParamsPersistent`, `CarParamsPrevRoute`,
`CalibrationParams`, `LiveParametersV2`, `LiveTorqueParameters` and `LiveDelay`.
The retired `LocationFilterInitialState` has no conversion contract and blocks
startup if present. A numeric schema ID or successful decode is insufficient
provenance: enum meanings and fields can change while IDs remain constant.

An envelope protects against accidental schema reuse; it is not a signature or
an automatic semantic conversion. Producers must use current observations or
verified cache data. Parsing unqualified historical bytes with today's schema
and then wrapping them does not make those bytes compatible.

Historical-log cache seeding requires a source-schema conversion contract.
Process replay rejects unqualified warm-start state before writing Params.
Interactive replay only seeds raw live parameters in an explicit `replay-`
namespace and does not seed persistent caches. Historical process-replay results
remain unqualified until their source schemas and conversion fixtures are supplied.

Enveloped caches are incompatible with runtimes expecting bare serialized bytes.
A downgrade requires an offline recovery or explicit conversion; switching Git
branches alone is not a supported rollback. No deployment is qualified here.

Run native persistence checks after building the Params library:

```sh
python -m unittest openpilot.starpilot.tests.test_state_migration -v
```

## Host actuator boundary

`tests/test_control_host_boundary.py` exercises the actual upstream `Controls`
constructor, longitudinal controller and native `carControl` publication in
disposable Params and IPC namespaces. Synthetic messages pass through the real
SubMaster input API. The two configurations deliberately supply a Model Y
candidate with system or stock longitudinal ownership; they do not identify a
physical vehicle or EPS firmware.

The checks warm the acceleration controller, then supply longitudinal override,
lateral fault, disable, a continuing negative plan and explicit re-enable inputs.
Inactive host longitudinal control must publish zero acceleration even with a
nonzero plan or earlier positive output. The lateral-fault case checks the host
activation flag while longitudinal control continues. Cancellation and override
publication are checked independently. Native libraries and source hashes are
recorded by the explicit probe.

This is a host input/output contract. It does not prove button or AOL policy,
message freshness handling, emitted CAN, Panda permission, stock vehicle response
or rearm behavior. Those need separate integrated evidence. A controller test
which directly injects stale nonzero acceleration cannot assume this host
neutralization step already ran.

## Modern Tesla integration

`tests/test_tesla_contract.py` checks known EPS firmware classification, controller
command fields and counts, counter progression, override behavior and C safety
decisions. Each test process compiles and loads its own temporary DEBUG safety
library. Firmware identification and direct controller inputs are separate checks.

`tests/test_tesla_host_integration.py` joins actual parsed CAN state, the upstream
Controls object, native `carControl` publication, the unchanged received command,
the vehicle interface/controller and C safety hooks. Two known Model Y EPS profiles
each exercise 120 consecutive logical frames. Override and disable each start with
a positive host acceleration output and must neutralize it through the emitted CAN
fields. Packet counts, counter continuity across transitions and native publication
identity are asserted. Logical CAN time is separate from measured publication time.

Host enable, override and plan messages are supplied test inputs. Stock cruise CAN
and native safety permission remain present during host disable; raw cancellation
commands do not simulate the vehicle responding. These tests do not establish AOL,
longitudinal-only policy, automatic rearm, physical hardware identity, release
firmware behavior or qualification of a car. Direct controller calls still require
the host to neutralize inactive acceleration. Sustained stock-ACC cancellation,
full process coordination and physical response require separate evidence.

## CAN subscription contract

`tests/test_can_subscription_contract.py` exercises the actual upstream Python
parser and packer with synthetic messages. A subscription frequency of `NaN`
excludes that message from aggregate alive checks. Zero instead requires its
presence and learns its frequency from received packets. Ported subscriptions
must express the intended behavior explicitly for each message and vehicle.

Optional signals keep zero timestamps until first received and retain their last
timestamps after reception stops. Aggregate `can_valid` therefore does not establish
their freshness. Consumers must independently check freshness and applicability
before using them. Continuing optional traffic also must not hide loss of a
required message. These checks do not qualify message integrity algorithms,
native safety, physical CAN or any vehicle.
