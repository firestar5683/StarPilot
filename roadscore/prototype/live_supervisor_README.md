# Live supervisor candidate: unavailable until target adapter validation

`live_controller.LiveController(root=Path)` provides the Galaxy contract:
`status()` returns available/enabled/state/can_enable/reason/session_id, and
`set_enabled(bool)` starts parked preparation or stops only owned live processes.
OFF bypasses health/parked gates. ON rechecks current health server-side.

A real `live_target_adapter` now provides the local Unix-socket client and
`live_target_daemon` owns persistent lifecycle/watchdog state. Galaxy requests do
not own children. The daemon starts on demand only on /TICI; Mac clients report
unavailable and never SSH. Its required `live_health.LiveHealth(root)` collector
is developed separately and must be integrated. Missing collector remains a
clear startup failure, never a fabricated readiness result.

The daemon starts direct ACE via run_worker.sh with a fresh seed, current checked
conditioning bank, unchanged quality policy and existing worker GPU lock. It
holds native_session.lock, refuses any external GPU owner, verifies initial audio
against exact owned worker PID/seed/profile/bank, and waits for accepted READY.
No bench supervisor, CPU writes, manager changes, replay Params, or fake messages
are used. Configuration comes from generated/live_config.json (profile,
plan_bank, initial_buffer_seconds, optional explicit power_limit_watts). No
inherited cap or hidden new cap is selected. Normal baseline config/identity must
already exist; no arbitrary fallback conditioning is generated.

`prepare_diagnostic()` is a separate bounded parked-only action: genuine fresh
preflight/model-local evidence is required, but **production coexistence
authorization is not required** so it can be measured. It launches only the muted
worker and never app/audio. Health evidence is recorded in a unique local
results/live/<session>/ directory through preparation and at most120 seconds of
ready observation. It cannot confirm driver-ready or automatically promote itself. Once the owner
records genuine measured coexistence authorization, an explicit ON request can
promote the same parked READY session after all production guards pass; this is
recorded separately and still requires driver-ready. Keeping that worker avoids
a circular requirement to prove fresh worker health after first killing it.
Diagnostic readiness alone is not GPU/coexistence approval.

Production ON uses the original full authorization guards. Live readiness requires
a fresh current-status record with route=live and advancing playback as well as
the app ready file; a PortAudio initialization marker alone is insufficient. Explicit
`confirm_driver_ready(session_id, audible=False)` rechecks the exact prepared
session and fresh parked health, then starts app --input live using the real
default namespace. Audible output must be explicitly requested and still passes
the app's existing output/mute checks. Prior results/current is preserved inside
the new session directory rather than deleted. Root's independent app live-input
and stale-input guard integration is required before target playback validation.

OFF immediately signals ONLY child process groups whose Popen handles this daemon
owns, cancels queued starts, and reaps them with bounded SIGKILL fallback. It does
not pgrep/killall, adopt external PIDs, or stop another supervisor. Normal daemon
termination also stops children; hard power loss/SIGKILL requires hardware-owner
inspection before restart and is not a license to kill an unrelated worker.

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
