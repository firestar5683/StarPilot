# Preserved USB AMD decoder failure

This is a private, offroad-only reproduction using the existing trained native VAE and an actual saved56s latent output. No DiT, planner, route replay or physical audio is required. Do not run it beside another GPU owner. The private supervisor verifies offroad state, preserves CPU settings and serializes GPU ownership.

The entry point is `decode_recovery_probe.py`, selected through `ROADSCORE_WORKER` under `/data/roadscore/prototype/power_worker.py`. It attempts five decodes of `results/ace_stability_20260916/cases/shape_56/native_0/latents.npy`. Set `ACE_DECODE_PROBE_NAME` to a new local evidence name so the earlier reports are not overwritten. It uses fixed375-frame windows and250-frame cores with explicit upload, execute and readback completion. No automatic reset/retry is implemented here.

Observed failures:

1. Original duration sweep:56s diffusion completes; decoder readback waits for timeline3796, observed0.
2. VAE-only probe: two identical successful outputs, then repeat3/chunk6 fails at compute after upload; target383, observed0. Physical allocation2.470GB, host high-water385.6MiB.
3. Instrumented VAE-only probe: four identical successful outputs, then repeat5/chunk4 (latent start750) fails at compute after upload; target473, observed0, timeout30s. Physical allocation2.470GB, host high-water385.4MiB.

The third probe reads controller registerB450 through the existing owner after the driver hang handler raises and before decoder/process teardown:0x0. After explicitly stopping that owned supervisor, a separate read-only `link_audit.py` sees0x58 and GPUbus4 config returns Unsupported Request. The existing offroad power-cycle helper restores healthy0x78. CPU restoration is recorded. The successful third-probe PCM hashes all equal the earlier successful probe outputs; warm decode9.21–9.52s, cold177.63s.

The unchanged tensor and differing failed repeats/chunks establish an intermittent lower-level runtime/link problem. They do not establish which hardware, controller, driver or recovery action initiates it. The failure-time read occurs after the driver's own hang handling, so it cannot identify pre-timeout link state. Memory pressure, DiT presence and shape switching are not necessary conditions. Explicit fences alone are not a repair. Fixed45s continuation has much stronger successful soak/replay evidence, but that does not prove immunity.

Evidence is in `results/ace_stability_20260916/`: `hang_56.json`, `decode56_failure.json`, `decode56_failure_time_summary.json`, their named logs, successful saved outputs and recovery logs. Preserve these failures when evaluating future changes. No firmware/controller modifications were undertaken.
