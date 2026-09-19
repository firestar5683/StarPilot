# Normal-session hook planning

Candidate source only: no v2 plans/tensors, audio, or native integration yet. The
normal command remains `./onroad --roadscore <route>`. GOLD33602 and the approved
planned60 are references, never default inputs to a new composition.

**Integration API**

1. The normal caller owns session seed selection: fresh random seed per launch,
   logged for reproduction; explicit override repeats it; official judging keeps
   its existing deterministic route seed policy.
2. `HostHookAdapter(existing_assets_root).fingerprints()` identifies existing
   model files, official ACE source and adapter. It hashes severalGB once, without
   model generation/downloads. The adapter lazily loads one serialized Mac model.
3. `request_plan(session_seed, plan_index, profile, section, window_seconds,
   model_fingerprint, preparation_fingerprint, hook_reference_sha256,
   committed_prefix_sha256, previous_plan_sha256)` creates the complete request.
   These are keyword arguments. Initial index0 has no context hashes; subsequent
   requests require all three. Supported bounded windows are30/45/60seconds.
4. `PlanCache(root).resolve(request, adapter, sources=...)` prepares automatically
   on a miss and returns `(directory, cache_hit)`. For continuation, sources maps
   `hook_reference` to this run's accepted hook WAV and `committed_prefix` to a
   NumPy1×200×64 file containing its latest committed8s latent. Initial sources
   are empty. Native worker binding to the returned directory remains unimplemented;
   do not overwrite existing profile directories as a substitute.

Semantic seed is separately derived with
`roadscore-semantic-plan-v1:<session_seed>:<plan_index>:<profile>`. Native sampling
keeps the normal runtime's generation seed policy. Cache identity includes the
session, role, duration, prompts, versions and musical context hashes. Fresh seeds
cannot reuse another run's plan; identical reproduction requests can. Cached
assets contain semantic codes and verified tensors, never old PCM. Invalid/stale
entries fail explicitly. `next_section()` offers verse/build/chorus/verse/bridge/
chorus progression; current arrival intent selects outro. Advance after acceptance.

**Musical behavior and preparation**

Each composition establishes its own compact4–6note hook and rhythmic answer.
Verses fragment it, builds intensify, choruses return the complete motif, bridges
transform rhythm/register, and outros resolve it. Profile identity persists in
all prompts: Prism128BPM/Dminor, or Aurora116BPM/Aminor. Actual hook audio and the
committed prefix anchor subsequent plans; no future route events or fixed route
schedule enters the request.

The host adapter runs semantic planning, captures tensors before audio diffusion,
then combines planned future hints with the committed8s prefix and existing
12frame/.5 repaint recipe. This new combination requires native validation.
Changing prompt strings alone does not update running conditioning. No v2
preparation or generation has run, and existing worker/CLI files are untouched.

Planning requires the previous accepted prefix, so it adds a causal dependency.
Historical60s LM work alone took≈13s. Start preparation as soon as that prefix
exists while buffered music plays; include planning in buffer budgets and measure
sustained throughput before claiming uninterrupted arbitrary-duration operation.
Use the best validated normal composer until this candidate qualifies.

**Predeclared validation after combined-plan approval**

- CPU: fresh-seed separation, exact cache reuse, context/version invalidation,
  missing-code/PCM rejection, exact prefix and unchanged future planned hints.
- Fixed test session seeds:11701223,280714055,3910408210, same route/policy/gates.
  Each gets an initial and at least two chained windows. Keep every result,
  failure and automatic reroll; no seed substitutions or best-seed selection.
- Check actual planner codes/seeds, reproducibility, input chain and hook identity;
  measure preparation/generation/decode/RTF, buffer minimum, holds/underflows and
  GPU/link health through the normal command.
- User assesses all three: memorable melody, recognizable return, meaningful
  development, no unrelated lead or loop collapse. Include only validated pieces
  in the combined demo; presentation remains subordinate.
