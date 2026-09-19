# Normal replay session seeds

`./onroad --roadscore <routeid>` chooses one fresh unsigned 32-bit session seed
before launching preparation or replay. It prints the seed and records it in
`session_seed.json`, settings and the completed launch record. Native and remote
workers receive the same seed. Ambient legacy seed variables do not silently
pin ordinary launches to the reference seed.

`./onroad --roadscore <routeid> --roadscore-seed 73921` explicitly repeats the
session's sampling stream. Preparation and continuation seeds retain the existing
`roadscore-sample-v1` derivation. The worker rejects missing seeds rather than
falling back to 33602. A running worker with another seed remains protected from
accidental reuse; this change does not kill another owner's service or implement
resident reconditioning.

Official judging passes its existing route-derived seed explicitly and tags its
origin. The launcher rejects a mismatch. Route-to-seed derivation, quality gates,
retry policy and historical ledgers are unchanged; a changed implementation still
requires a new verified judging freeze before new official runs.

Normal replay now runs to route EOF unless `--duration` is supplied. Showcase
selection does not introduce route allowlists or special event timestamps.

CPU tests establish seed selection, deterministic derivation, judging isolation
and propagation; they do not establish musical quality or hardware acceptance.
Repeatability also requires the same conditioning/model/code and causal input
sequence. Archives retain the exact heard output and accepted generation decisions
when exact historical playback is required.

Pending gated acceptance: ordinary-command launches of the same route with fresh
seeds must produce different compositions under one unchanged strategy; explicit
seed repeats must reproduce musical generation under matching inputs/configuration.
Prompt/tensor adaptation and presentation/UI integration are separate candidates.
No claim of end-to-end acceptance is made before the reviewed hardware run.
