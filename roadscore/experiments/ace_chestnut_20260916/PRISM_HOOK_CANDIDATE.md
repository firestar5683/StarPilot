# Prism hook candidate — proposal, not deployed

Base: `06c8e7ffe8` (isolated GOLD60 diagnostic), itself based on `a12d1b7854`.
Protected GOLD and user-approved planned60 assets remain unchanged.

## Musical intent

`prism_hook_spec.py` defines one shared full Prism identity and hook contract for
initial, verse, build/prechorus, chorus, bridge and outro. Every role retains
128 BPM, D minor, crystal pluck/glass lead timbre, syncopated bass and tight drums.
The hook has a recognizable four-note rising contour, signature syncopated rhythm
and short answering phrase. Verses expose fragments; builds intensify them;
choruses state the complete original; the bridge transforms rhythm/register while
keeping identity; the return restores the original phrase and outro resolves it.
This replaces the old generic restrained-verse emphasis and keeps specific hook
and instrumental instructions present across all role prompts. It cannot guarantee
memorability or uniqueness without listening. Fixed seeds intentionally reproduce
the same composition; route-derived seeds distinguish comparable route runs.

## Proposed first demo composition

The first candidate is one coherent LM-planned60-second composition, not repeated
8-second-context verses. At the requested128BPM,32bars occupy60seconds:

| Target time | Role | Musical development |
|---|---|---|
|0–3.75s|Introduction,2bars|State recognizable hook|
|3.75–18.75s|Verse,8bars|Lighter fragments, breathing space and answer|
|18.75–26.25s|Build,4bars|Rising register/subdivisions of same motif|
|26.25–41.25s|Chorus,8bars|Complete melody, fuller bass and drums|
|41.25–48.75s|Bridge,4bars|Spacious contrasting transformation|
|48.75–56.25s|Chorus reprise,4bars|Return the unmistakable original|
|56.25–60s|Outro,2bars|Answer and resolution|

These are prompt targets, **not verified generated timestamps**. Do not force
audio cuts or treat these times as detected beats/section boundaries. An actual
generated performance may not follow them. The fixed narrative is independent
of recorded future route events; operator excerpt selection does not grant
runtime access to future telemetry. Current delivered conditions may later inform
causal adaptation, but this candidate does not implement it.

Prefer a60-second route excerpt for this first musical test. A90–120second route
requires a newly prepared longer semantic plan, larger native shape validation,
or a tested continuation strategy. Do not loop this60s piece, stretch its timing,
or restart its initial plan and call that coherent longer-form composition.

Presentation is subordinate: proposed cue/engagement lanes must not overwrite
the hook or rhythmic phase. If a cue conflicts, omit/simplify it. This composition
lane does not add signal, curve, engagement or other sonification. The master
will combine the route, composition, one signal motif, one curve treatment and
one engagement transition in the operator proposal before new generation.

## Actual preparation status and path

**Prompt specification only. No new conditioning tensors, semantic codes, native
audio, or deployed behavior yet.** Three CPU specification tests pass. Local Mac
ACE packages and existing9.4GB model assets are available; no model downloads are
needed. New preparation is paused for the combined demo-plan review.

`prepare_prism_hook.py` is an opt-in Mac preparation tool. Default mode saves the
specification only. `--prepare` initializes the existing official ACE/1.7BLM,
uses `thinking=True` and fixed seed33602 (or deterministic route-derived seed),
records actual returned semantic codes/seed/LM costs, then captures full60s
encoder/context tensors immediately before DiT diffusion. It refuses repaint,
missing semantic planning, nonfinite/wrong-duration tensors and an unavailable
MLX interception path. It never executes native hardware or intentionally
generates audio. Candidate output uses a new private directory; protected files
and active profiles are never replaced. Exact prompt and tensor hashes are saved.

The full composition caption/section text are what this first preparation feeds
into the model. Per-role continuation contracts are saved for future use but
**are not prepared role tensors** and are not wired into current worker startup.
Editing these strings cannot alter deployed prepared embeddings. All role-based
continuation restoration remains future work after the full-plan musical test.

Historical preparation recorded12.4s for the old60s LM plan, plus text/conditioning
and cold model load; budget minutes rather than promise that runtime. Longer
hook text may change encoder length/cost. Tensor output should be a few MiB
(1500×128 float32 context≈0.73MiB plus variable-length encoder≈1–severalMiB), not
new multi-GB weights. Model loading can consume substantial RAM; current observed
diskfree was≈7GB. The approved past run is the playback fallback while preparing.

After review: run one captured plan, check its actual codes/tensors and provenance;
have hardware owner review a candidate-capable isolated native harness (the GOLD
probe intentionally pins original asset hashes and must reject this new case);
then generate one fixed-seed sample with rawgain processing, inspect/listen,
and only afterward integrate subordinate presentation. No seed auditions or
per-route cherry-picking. Master/user musical acceptance remains the gate.
