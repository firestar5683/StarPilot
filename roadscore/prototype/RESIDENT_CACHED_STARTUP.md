# Opt-in current-bank resident service

This candidate is OFF by default and has not passed native cold/warm audio equivalence. The normal baseline still owns and stops its worker.

After baseline evidence is protected, the sole hardware owner can validate with `ROADSCORE_RESIDENT=1 ./onroad --roadscore route1 --muted`. The first launch still loads models and compiles. After a successful preparation the power supervisor remains alive; its PID and process-start ticks are recorded in `generated/resident_owner.json`. Stop that exact verified owner with SIGTERM to restore its CPU settings and stop its GPU child. Do not kill unrelated workers.

Each subsequent launch chooses its normal fresh seed and requests a token-bound idle preparation. The worker retains DiT/VAE/decoder objects and compiled graphs, but recreates CachedComposition, retry estimator, accepted-history map, and initial audio/latent state. Seed, profile, policy and conditioning-bank hash must all match the request acknowledgment. A lease prevents reset while audio playback owns the files. Same-seed reproduction still rebuilds the session; it never replays a consumed prepared initial automatically. No preparation runs alongside playback.

Measure actual first accepted audio, startup-to-READY, and replay start; the initial buffer remains 112 seconds until measured native throughput supports a smaller value. Use identical explicit seeds for the cold/warm equivalence check, comparing initial PCM/latent and quality decisions. Then verify a normal launch logs a different seed. Preserve the preceding archive before switching sessions. No performance or audible equivalence claim follows from the CPU tests.

Do not hot-switch conditioning banks or reuse a timed-out request. Bank changes or outstanding requests fail closed and require the hardware owner to inspect preserved state. A worker exception ends its power supervisor, which restores CPU settings. This is a local opt-in event service, not an installed boot daemon.
