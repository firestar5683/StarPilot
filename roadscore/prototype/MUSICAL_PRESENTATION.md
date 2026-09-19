# Optional presentation candidate — offline review only

No hardware deployment or fresh model generation is authorized by this candidate.
Composition owns hooks, section identity, variation, returns and macrostructure.
This layer never selects a seed, changes conditioning/sections, shifts source
samples, replaces a source phrase, or changes the generation queue.

Baseline remains `--render-mode gold-core`, with all three flags absent/false:

```
"signal_shaker": {"enabled": false},
"core_apex": {"enabled": false},
"engagement_presentation": {"version": 2, "enabled": false}
```

The flags are read at startup. Enabling any layer requires gold-core, ensuring
there is no inherited EventDSP/MusicalDSP chain. Do not cherry-pick the earlier
engagement application patch on top; its pure implementation was adapted here.

## Exact cue proposal

- **Signal:** one deterministic, precomputed band-limited shaker grain motif on
  eighth notes; no pitches, crashes, sample per blink, random callback selection,
  or blink-phase reset. True signal observations keep one sequence alive across
  up to1.2s off gaps. At most32 grains per sequence; peak contribution at most
  .012 (config internally capped .02), alternating light accents. Stale/invalid
  signal input ends the sequence; existing grains release within160ms. The
  original core is never ducked, normalized, filtered or limited by this layer.
- **Curve/apex:** optional, separate audition. One700ms, at most1dB breath in the
  existing source ending at the estimated, subdivision-aligned apex. The peak
  is precisely original unity audio, not a new crash/tone or volume boost.
  At least8s between treatments and at most3 per60s. Repeated event observations
  do not retrigger the same activation. No musical section planning occurs.
- **Engagement:** optional, separately auditioned. Version2 adapts a25c38d6f1:
  active reaches exact original samples in220ms; inactive ramps650ms into a
  gentler4.5kHz low-pass,85%width,-1dB state (the prior prototype used1.5kHz,
  65%width,-2dB). Only valid fresh `selfdriveState.active` controls it; stale,
  invalid/future timestamps and transport gaps>1s choose contained. Not
  `enabled`, cruise state, speed, route annotations or estimated driver intent.
  This optional contrast intentionally colors inactive audio; choose it only
  after hearing the separate comparison. No Bluetooth/physical validation.

## Beat confidence and safe omission

Grid assessment runs once before callbacks, from generated audio, not route
lookahead. It checks tempo peak versus competing acoustic peaks, agreement with
prepared profile BPM prior (128 for Prism,116 for Aurora; no route tuning), and phase drift between two15s windows. This is an
estimate, not a verified downbeat. Unknown/ambiguous grid means **no shaker or
apex treatment**. No runtime force override is exposed.

The approved planned60 has estimated127.66BPM, pulse confidence0.418, phase
confidence0.700, but competing171.43/85.71 peaks dominate; coherence fails.
Therefore the confidence-gated audition is sample-identical to core. The
provisional128BPM shaker/apex auditions intentionally force an OFFLINE hypothesis
so the user can review timbre; they are not authorization or proof of alignment.
Do not enable rhythmic cues in the first device demo until rhythm is verified.

## Offline artifacts and event provenance

`render_presentation_auditions.py SOURCE OUTPUT` renders five independent arms:
core, confidence-gated shaker, provisional128BPM shaker, engagement alone,
provisional apex alone. The source is the exact approved planned60 FLOAT WAV;
no regeneration, normalization, limiter or extra gain. Event times are explicitly
**synthetic**, not extracted driving events: signal8–14/32–38s with blinking,
active16–28/42–56s, apex22/46s. Actual selected-route timestamps remain a separate
handoff and must not be falsely associated with this sample.

Report stores source/file hashes, cue frames, confidence, phase hypothesis and
Mac processing timings. App stores actual source-state freshness with every
captured block, plus shaker/apex event files in the normal archive. Added
selfdriveState telemetry is excluded from generation input_times because it is
presentation-only; original causal generation inputs stay unchanged.

No callback I/O, model work, FFT, random draw or blocking lock. Grains/filter and
workspaces initialize before playback; per-block numpy/scipy operations allocate
bounded arrays. Offline speed is not native callback or coexistence validation.
The exact default gold-core bypass and core input immutability are covered by
unit tests. Physical playback and demo settings need the explicit user plan gate.

`tools/presentation_conservative_v1.json` is the proposed generic configuration
fragment for the combined plan review, not a changed default or deployment.
It has no route identifiers, cue timestamps, seed or conditioning override.
The normal launcher must use gold-core when this fragment is eventually selected;
copying the fragment is not itself an instruction to run hardware. Defaults in
existing runtime configurations remain unchanged. Full archive source hashes and
runtime configuration record the selected presentation policy version.
