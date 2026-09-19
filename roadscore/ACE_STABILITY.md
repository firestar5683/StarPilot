# ACE port stability — September 16 investigation

**The fixed-window native path is faster than playback and has passed substantial repeatability/replay tests. Overall acceptance remains blocked by model-generated interior silence and an unresolved GPU/link failure.** Do not call this production-stable or claim every transition is seamless.

[Listening review](results/ace_stability_20260916/index.html) · [Detailed evidence](results/ace_stability_20260916/INVESTIGATION.md)

All work is private under Desktop/RoadScore or the offroad bench. Baseline tag: `ace-stability-baseline-b719139`. No new models, training, public StarPilot changes, or physical audio output.

## What matches the reference

The deterministic harness exports the actual conditioning, explicit noise, source prefix/mask, eight diffusion steps, final latents and decoded PCM. Official Mac FP32 and native Chestnut FP16 consume the same rounded boundary values. Three new identities—Prism, Aurora and Circuit—have paired 30/45/60s outputs. Final latent relative RMS differences range approximately 0.45–2.75%; the page preserves localized differences for human listening rather than labeling them inaudible.

Five identical native Prism30 runs have identical latent and PCM hashes, with RTF 0.5295–0.5320. The first thirteen jobs of separate continuation processes are also identical until adaptive endpoint choices make their subsequent inputs diverge.

Same-latent VAE comparisons at 30/45/60s and the matched transition have 0.070–0.088% waveform RMS error, envelope correlation above 0.9999999 and zero measured sample lag in every one-second window. The tested decoder does not introduce the suspected rhythm displacement.

Teacher-forced Circuit30 forwards isolate native velocity error at 0.877% initially, falling to 0.231–0.269% in later steps. Capturing all 24 layers at steps 0 and 7 found gradual small FP16 differences, without an abrupt order-of-magnitude break at sliding/full-attention boundaries. End-to-end diffusion amplifies those differences. Mixed FP32 residual accumulation improves two examples but worsens a third; it was not promoted. Artificial conditioning padding is masked; actual prepared tokens are all valid.

Repaint semantics match official behavior: 25 latent frames/s, 1920 PCM samples/frame, mask true means generate, a 12-frame boundary blend, and exact source preservation outside the blend. Source prefixes are taken from the actual committed previous latent tail.

The human-approved old Mac transition cannot be reproduced exactly: original random reference crops/VAE sampling state were not saved, and the single-item planner path did not obey the supplied seed. Original planner codes were recovered. The review supplies both a closer recovered-code reconstruction and a new original-settings pair with fully captured identical inputs. Neither is falsely labeled the identical old performance.

## Silence: two mechanisms, one still unresolved

The old long terminal silences appear in the official reference before decoding or concatenation. The planner predicted endings, and copying those silent tails carried them into subsequent prefixes. No-fade text and longer declared duration alone did not fix this.

The private ACE candidate now generates a 45s lookahead window, preserves 8s, and normally commits through 36s: 28s of new material. A generated-energy endpoint check trims a premature terminal fade before selecting the next source tail. Intentional outros may fade. This repaired the tested initial section flow and completed a 20-job adaptive soak.

**This is not a general no-silence guarantee.** Full-route audio later exposed a 5.1s community chorus gap and a 2.7s curve-run gap. The exact community input reproduces the gap on official Mac, with committed latent RMS difference 1.070%. Its preceding source tail remains active. The curve verse gap is also reproduced on official Mac (committed latent RMS difference0.770%); this is not confined to chorus prompts. Four alternate seeds still produce 2.2–7.1s quiet; changing the role to verse also fails. Stronger/weaker repaint injection does not remove it. A 16s prefix fixes that one example but leaves too little new music to sustain real-time output. A 4s prefix fails with a nine-second gap on another seed. Refreshing the timbre reference from the actual preceding audio changed exactly one conditioning token but also failed across three seeds. No such workaround was promoted.

The remaining demonstrated blocker is model/conditioning-dependent leading/interior silence, not transport starvation, final concatenation, an inherited silent prefix, or a native-only VAE error. The endpoint guard cannot detect it. Full musical acceptance remains failed; rerolls and crossfades are not presented as a repair.

## Speed and bounded runtime

| Generated duration | Warm sampling + decode | RTF |
|---|---:|---:|
| 15s | 9.16s | 0.611 |
| 20s | 10.53s | 0.527 |
| 24s | 32.01s | 1.334 |
| 28s | 16.71s | 0.597 |
| 30s | 15.96s | 0.532 |
| 32s | 39.15s | 1.223 |
| 36s | 49.26s | 1.368 |
| 40s | 20.78s | 0.520 |
| 45s | 22.68s | 0.504 |
| 48s | 35.98s | 0.750 |
| 52s | 57.41s | 1.104 |
| 56s | decode failed | unavailable |
| 60s | 79.93s | 1.332 |

These are full-duration RTFs; continuation must divide by retained **new** music. The adaptive 20-job chain retained 555s in 454.17s sampling/decode (RTF 0.818). Worst warm full-job RTF was 0.964. Two endpoints trimmed to 32/35s. Host high-water was 478.6MiB; sampled physical GPU allocation including allocator cache reached 5.791GB. First fixed-window soak also completed 20 continuations without a hang.

Cold resident startup took roughly 758s to prepare a 56s buffer. First model job wall time was 538.37s, second 177.22s, plus loading/startup. Warm RTF does not imply fast launch: prepare the resident worker in advance.

Duration performance is non-monotonic and depends on sequence/tile shapes. A padded 60s experiment improved throughput, but failed the earlier single-forward 1% peak-error criterion. This pass's accumulated final-latent metrics are different measurements, not a retroactive pass. Alignment changes were not promoted.

## GPU failure remains a blocker

Three preserved 56s decode failures required explicit offroad link recovery. The first followed a duration sweep. An isolated VAE-only repeat then reproduced failure on its third decode, after two bit-identical successful decodes, using only 2.470GB physical allocation and explicit transfer/compute fences. No DiT or shape changes were needed. The sixth fixed decoder chunk finished upload, then waited unsuccessfully for compute timeline 383 (observed zero).

After terminating that failed process, USB bridge config remained readable, link register B450 was 0x58 rather than healthy 0x78, and GPU config reads returned Unsupported Request. Existing power-cycle recovery restored 0x78. This establishes link failure after the incident; it does not prove which component initiated it. The final VAE-only probe completed four identical decodes (cold177.63s, warm9.21–9.52s), then failed on repeat5/chunk4 after upload: timeline473, observed0. The diagnostic read B450=0x0 after the driver hang handler but before decoder/process teardown; after terminating the owned process it was0x58, with Unsupported Request from GPU config. Recovery restored0x78. This failure occurred at a different repeat/chunk than the earlier probe, confirming intermittency rather than a deterministic third-repeat boundary. It used2.470GB allocation and385.4MiB host high-water before failure. Fences alone are not a fix. No firmware work or silent auto-recovery was added.

## Replay evidence

All three complete native runs reached EOF with normal camera/path/lane UI, navigation, causal cereal and fresh Chestnut generation. None had an underflow, fallback, output flag, future-input violation or GPU hang.

| Route fixture | Captured | Accepted jobs | Minimum buffer |
|---|---:|---:|---:|
| Arrival | 253.9s | 7 | 5.4s |
| Community | 572.4s | 19 | 5.9s |
| Curve | 403.2s | 13 | 3.9s |

The first curve attempt was partial and remains separately preserved. Full-route transport passes do not override the musical silence failures above. Archived route-owned scores remain private.

Native stored playback of the new arrival archive passed 120s with no generation, zero output flags, contiguous samples and maximum measured clock alignment 10.67ms. Mac stored playback passed 90s with zero flags and contiguous samples: 0.438ms maximum alignment on the earlier normal-UI run, 2.5ms on the new archive's explicit headless run. A new normal-UI Mac launch failed because its display was asleep; that failure is retained, not disguised as a UI pass.

Mac fresh ACE transport passed a180s headless launch (176.5s source packets, six fresh jobs): zero late frames/starved callbacks/output flags,0.34ms maximum presentation error. All1,765packets were logged before drops; max delivery154ms, p99≈103ms. During-generation delivery p99≈103.3ms versus103.5ms outside generation gives no evidence that this run’s ACE calls caused the earlier transport failure. The earlier344ms delivery spike remains preserved; normal Mac UI transport under load is not cleared by a headless pass. The250ms buffer and acceptance thresholds are unchanged. Fresh native SA3 fallback normal_1789600873 also passed a120s launch:116.6s captured, three fresh jobs atRTF0.776–0.780, minimum buffer9.326s, zero underflow/fallback/output flag/future-input violation, normal camera/path/lane UI verified. Cold readiness180.09s.

## Profiles, gestures and limits

Three prepared profiles have initial/verse/prechorus/chorus/bridge/outro tensors, 6.1–6.7MB each plus shared trained weights. Identity preparation remains Mac-assisted; runtime DiT, Euler sampling and VAE execute on Chestnut, with CPU noise generation, endpoint checks and arrangement. Aurora and Circuit each completed all six native initial/section jobs using actual prior outputs, with exact prefix preservation. Maximum new-region quiet was0.1s/0.2s respectively in these bounded chains; retained-new continuation RTF was0.799–0.889. Combined host high-water478.8MiB and sampled physical allocator occupancy5.792GB. Their official reference chains also pass the energy check. These are prepared demo candidates, not human-approved profiles or full-route-tested substitutes for Prism.

Bridges request contrast through texture/instrumentation while preserving tonal center, without forced modulation. V3 adds a brighter rim/shaker turn motif and layered unpitched curve impact. Twelve gesture tests passed; V2 remains selectable. Human salience and musical fidelity require listening. The private unit suite passed 69 checks during this pass.

SA3 remains the default fallback path; MusicGen is untouched. Set `ROADSCORE_ACE_WINDOWED=0` for the prior ACE wrapper. Session mute locks remain active. No speakers or Bluetooth output have been enabled. Final checks confirm no owned workers/replays remain; GPU/session/display locks are free, the normal UI and manager are running, and the bench is offroad. The supervisor’s before/after CPU snapshots match. Normal offroad power management subsequently offlined the big cores; no further override was applied. Mac system mute is true, default output remains built-in (muted), no Bluetooth audio output is listed, and both session mute locks remain. No speaker or Bluetooth output was intentionally enabled; bench tests remained muted.
