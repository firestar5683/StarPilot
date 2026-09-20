# Live supervisor candidate: unavailable until target adapter validation

`live_controller.LiveController(root=Path)` provides the Galaxy contract:
`status()` returns available/enabled/state/can_enable/reason/session_id, and
`set_enabled(bool)` starts parked preparation or stops only owned live processes.
OFF bypasses health/parked gates. ON rechecks current health server-side.

**There is no installed target adapter in this change.** Default status is
available=false, can_enable=false. No process launches, hardware probes, Params
writes, car-control publishers, model selection, or device access occur here.
This is reviewed orchestration policy plus an explicit disabled integration
boundary, not a road-tested live service.

The controller expects `live_target_adapter.create(root)` to return a persistent
service client with status(), health_and_authorization(), enable(observation,
authorization), and stop_owned(). Its daemon can use LiveSupervisor. It must
atomically revalidate on start and tick frequently enough to meet the health
freshness bound. Fresh accepted worker readiness must match the exact session
seed/bank/profile; an old worker_ready file is not sufficient.

The adapter must collect genuine modelV2/carState/manager/device/Chestnut health.
Observation age must be <=1 second. Input booleans must reflect per-message ages,
model frameDropPerc/modelExecutionTime and process health under an owner-validated
budget; a recent collector timestamp must not make stale source messages fresh.
Parkedness comes from fresh standstill/speed/gear evidence, **not IsOnroad=false**;
an ignition-on parked car is permitted. Verify actual driving-model placement
is local from current modeld/Chestnut telemetry, including UsbGpu* Params and
chestnutState as appropriate, without writing them. User's requested small model
alone does not prove local execution. Missing/unknown placement fails closed.
Persist explicit user authorization and verified coexistence bound to current
car and code/config baseline. No such verification is manufactured here.

Sequence: authorized healthy parked environment -> PREPARING -> accepted READY
-> explicit driver-ready confirmation of the exact session while parked ->
STARTING -> verified app/audio readiness -> LIVE. Movement before driver-ready,
stale health, modeld degradation, or worker/app failure invokes owned-only stop.
No auto-resume after failure. Driver-ready is not inferred from enable or from
vehicle movement. No navigation is required; app --input live must use fresh
current messages only and preserve the no-future-input policy.

ACE worker can run directly with current cached conditioning, fresh session seed,
quality policy, and GPU/session locks. `run_worker.sh` supplies interpreter/device
and conservative thread-count environment. It does not mutate CPU settings.
**Do not use power_worker.py or worker_service.py for this lane**: both remain
intentionally offroad/bench guarded; power_worker also changes CPU online bits,
clock/governor and affinity. Do not weaken those guards, stop manager/modeld, set
replay namespaces, publish fake carState, or reset another worker. Target adapter
must refuse another GPU/session owner and retain only its own process-group
handles for stop. Preserve active results/current and create unique session
archives; output/Bluetooth setup requires root lifecycle integration.

Actual ACE/modeld CPU/memory/thermal coexistence has not been measured. Chestnut
model allocation, USB link faults and normal CPU scheduling can still affect the
platform. Offroad resident results do not establish driving coexistence. The
candidate stays unavailable until the sole hardware owner validates the read-only
collector and coexistence baseline; explicit driver-ready is separately required
before an attended road test.
