# Deterministic ACE boundary validation

All artifacts are private in `../../results/ace_stability_20260916`. No script here enables physical audio. Leave both `.session-muted` locks in place. Native experiments require the offroad bench and exclusive `generated/gpu.lock`; stop the explicitly owned resident service before standalone GPU work.

A case directory contains actual encoder states/mask, 128-channel source/chunk context, explicit noise and optional repaint source/mask. `case.json` preserves settings and provenance. `bundle.py` can build a portable case from a prepared runtime profile and an actual previous latent file. Noise is materialized, not merely assumed reproducible from a seed.

`reference.py` runs the official Torch model and VAE on Mac. Set `ACE_ROUND_INPUTS=1` to compare the same FP16 boundary values as native, using FP32 reference arithmetic. `ACE_REFERENCE_PLAN` points to a JSON list with `case`, optional `output`, `seed`, `previous`, `commit_seconds` and `adaptive_commit`. A previous path is relative to the evidence root. Each step, final latents and PCM are saved. A linked reference chain uses its own previous output and is not an identical-input pair after trajectories diverge; explicit captured native sources are used for strict paired continuations.

`native.py` consumes the same case directories via `ACE_VALIDATION_PLAN`, under the existing `prototype/power_worker.py` supervisor. `ACE_OBSERVED_DECODE=1` enables upload/execute/readback fences and failure-time link diagnostics. It records cold warmups, sampling/decode/wall time, live/peak tracked allocation, sampled physical allocator occupancy and host high-water. Physical occupancy includes cache and is not a sampled transient peak. A failed decode is not a generation success even if final latents exist.

`compare.py`, `precision_audit.py`, `layer_audit.py` and `vae_compare.py` isolate trajectory/forward/layer/decode differences. Some aggregate scripts replace their JSON output: include all desired cases when regenerating a complete report. Teacher-forced forwards are diagnostics, not end-to-end generations.

`audit_sequence.py` measures all generated quiet spans, committed endpoints and prefix preservation; it renders a file-only linked flow. `archive_energy.py` audits actual replay archives, including intentional ending silence. `gap_audit.py` preserves counterfactual failures rather than selecting a lucky seed. RMS alone does not establish musical quality.

`replay_regressions.py` launches the normal onroad workflow with explicit mute, a generic watchdog and native EOF completion. It requires an observed started UI during replay, not at final EOF when the UI correctly becomes offroad. Its transport pass is independent of musical acceptance. `transport_audit.py` uses every received packet, including those later dropped, to separate delivery from export timing; generation overlap is correlation only.

`review.py` generates the private file-only listening page with no autoplay or remote resources. Human listening remains required for port fidelity, continuity and gesture salience.
