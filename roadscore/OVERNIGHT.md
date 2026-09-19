# Overnight continuation from e8f3069

Session safety: `.session-muted` on Mac and bench overrides every audio endpoint. Mac system output muted. No Bluetooth operations. All launches explicitly muted; speaker verification deferred to human.

Human confirms native normal comma UI works. Preserve this result and all integration fixtures. New music research prioritizes breakbeat explicit song sections; prior musical freeze superseded.

Work queue (unchecked means not demonstrated):
- [ ] P0–P8: engineering experiments and captures complete; identifiable roles/coherence require human listening; late prediction cases documented
- [x] P9: full Mac fresh runs; measured stability, bounded recovery unit-tested (not arbitrary outage guarantee)
- [x] P10/P13/P14: compact intent/readiness overlay, native assets reused
- [x] P11/P12: profiles and residency measurements complete;30–45s target NOT met
- [x] P15/P16: shared settings, positional CLI, explicit automated mute; Bluetooth extension documented
- [x] P17/P18: form archive, stored no-GPU regression, live storage design
- [x] P19–P21: three routes and native replay regression; host ownership
- [ ] P22–P25: long-form artifacts, transition diagnostics and listening gate complete; audible coherence/downbeats pending human; no fine-tuning
- [x] Final cleanup, worker-exit CPU restoration, ordinary UI restoration, mute audit, accurate STATUS

Experiments: `results/overnight/`. Existing evidence remains unchanged. No acoustic musical judgments can be verified unattended; generated captures and measured properties are evidence for subsequent human review.

First checks: 32 tests passed. Positional muted stored replay passed on Mac for 15 seconds with an invalid bench host: no GPU invoked, contiguous samples verified, zero output flags, 0.146 ms maximum alignment error. Overlay wrapper retained the real normal UI. Musical role labels remain unverified pending listening; runtime planner is experimental and not enabled by default.

Checkpoint a001dcb adds an opt-in generated-section bank. Cached candidates provide immediate road-event response; fresh GPU continuations replace role material only at phrase boundaries. These are generated sources, not prerecorded substitutes. Roles, inferred bars and harmonic coherence remain listening hypotheses. Current full Mac run uses this experimental mode; it must not be called a musical pass merely because the scheduler works.

First controlled results: strong anchors retained highly similar waveforms (verse/chorus correlation 0.823, verse/bridge 0.896); 22-frame anchors increased contrast (0.267 and 0.552). The common pulse estimator reports 92.3 BPM despite the requested 138 BPM, demonstrating tempo/meter ambiguity or prompt noncompliance. No true downbeat labels are available. A second pass will avoid imposing a potentially incompatible key on the reference and use chained generated context.

Measured worker startup after removing full second generation: 127.017 s (imports/input 3.795, DiT load 17.224, decoder load 6.448, first generation 95.367, decoder capture 3.918). This is a process-cold restart with existing compiler cache, not a post-boot measurement. Opt-in trusted local TinyJit snapshot experiment prepared; no default snapshot loading enabled.

39 unit tests pass, including sample-exact section landing, fresh-material replacement only on a phrase boundary, causal curve cooldown, arrival supersession and bounded late-packet skipping without timeline drift. These establish mechanics, not musical coherence. Mac system output reports muted with volume zero; selected device is built-in MacBook speakers. Bench ALSA exposes onboard MultiMedia1; RoadScore has not enabled or selected Bluetooth output.

Full Mac community result `normal_1789525740`: natural route exhaustion, 571.8 audio seconds, 21 fresh jobs, eleven fresh job IDs observed at played phrase boundaries, zero renderer underruns/emergency repeats, zero host starvation/late frames/output flags/sequence gaps. Minimum source buffer 10.05 s; max host alignment error 0.606 ms; max measured PCM transport delay 140.9 ms. All jobs satisfy logged causal input cutoffs. Score archived with decisions and song-form events. This clean run does not guarantee arbitrary network outages are solved; bounded recovery is unit-tested and would mark any concealed loss explicitly.

Stored replay of that score remains no-GPU and exact-sample verified. The normal UI overlay now uses the GUI render hook, native GPU textures and smaller ASCII-safe labels; a silent VFR capture uses observed UI-frame and audio-sample timestamps (`normal_1789526728/synchronized.mp4`). No acoustic validation claimed.

Snapshot restoration experiment: 62.532 s ready (22.292 s restore, 36.410 s initial generation, 0.759 s decoder preparation), peak host 1301 MiB vs ~175 MiB uncached worker. First-run comparison differed. Two identical steady-state restored requests match each other bit-for-bit; uncached steady-state cross-check is still required before enabling restore by default. Snapshot stays opt-in.

First full-run steering-proxy audit exposes late structural requests on some curves; this is not a complete before-steering pass. The next generic scheduler regression uses integrated *current model-predicted* turning angle to recognize substantial turns earlier, requires at least three seconds of predicted lead, and begins the preparatory fill on the next inferred beat while reserving the major landing for a bar. No route timestamps/labels/configuration are introduced. Offline proxy definitions and all unmatched/late cases are preserved.

**Snapshot validation failure and quarantine:** uncached steady-state requests match each other, but differ from restored steady-state requests. Therefore the 62.5 s restore is NOT an accepted startup path. Follow-up/style/text-only outputs made by that worker were moved under `results/overnight/rejected_graph_restore` on both hosts and removed from the primary review. They must not be used to judge musical capability. The normal-runtime eighteen-candidate screen and full Mac route are unaffected. Source inspection found this tinygrad revision does not advance `UOp.unique_num` during unpickling, and the worker allocated input buffers before restoring saved buffers; a narrowly scoped collision-prevention retry is prepared but not yet validated. Normal-worker regeneration is required.

Native curve regression `normal_1789527539`: warm launcher 15.016 s, 176.3 rendered seconds, zero output underruns/emergency repeats. Existing normal UI retained. On the unambiguous matched steering-proxy turn, request at 129.9 s, PRECHORUS waveform at 130.65 s, steering onset at 135.8 s, CHORUS landing at 137.8 s: preparatory material starts 5.15 s before the proxy. A second requested bridge falls beyond the captured window and is not counted as demonstrated. Native archival initially omitted the new form file; the general copy list is fixed and this completed run's exact preserved form metadata was recovered into its score archive.

Native arrival regression `normal_1789527744`: natural final-segment exhaustion, 254.3 rendered seconds, warm launch 16.502 s, nine fresh jobs, no output underruns or emergency repeats. All five active roles appeared (VERSE/PRECHORUS/CHORUS/BRIDGE/OUTRO), arrival triggered at replay t=239.146 s, and cadence/silence were captured. Minimum generation buffer 9.526 s; all job input cutoffs causal. Both newly generated native scores are now mirrored into the private Mac route-owned library; ordinary route data was not redownloaded.

Final normal-runtime followups regenerated successfully: seven chained candidates, six synthwave/funk candidates and three text-only controls. Their provenance ties each result to the normal worker log. Snapshot collision-prevention retry still failed: base/chorus/bridge became identical. The optimization is rejected, snapshot quarantined, normal worker restored. No musical evaluation should use the rejected outputs.

Second full Mac run `normal_1789528719`:571.8s,21jobs,seven fresh job IDs played,zero host starvation/late frames/flags/sequence gaps,zero renderer underflows/repeats. Minimum buffer10.283s,max alignment0.709ms,max transport123.3ms. Native stored replay `normal_1789529531` with no worker:contiguous samples verified,zero flags,no generation,3.375ms max alignment.

Audit exposed an exact-block-boundary preparation handoff defect: control could clear a due prechorus before the callback consumed it. Complete preparation+landing plans are now queued atomically once, with explicit arrival supersession. Two targeted callback tests added;48tests pass. Further full-route regression running before final acceptance.

Resident lifecycle first pass: explicit service reused by native replay,56.3s captured with zero underruns/repeats/output flags; launcher preserved service ownership. Stop succeeded and restored saved CPU settings exactly. Short capture remained `last_generated`; preferred176.3s demo was not replaced. Preparation was197.036s, not a warm-launch measurement: the replay joined while service was still preparing. The service's one-second safety loop spawned a1.3-second native Python import each time; changed to a cached native Params reader with fresh IsOnroad reads.49unit tests pass, including reader freshness. New preparation/profile and full queued-plan regression follow.

Resident preparation after cached Params reader:185.432s (imports3.690,DiT17.807,decoder8.755,first-generation148.449,decoder-capture6.256). This is slower than earlier127s process-cold measurements; no stable lower bound or post-boot claim. The change removes measured monitor overhead but does not establish the30–45s target. Third full Mac regression started only after READY, so its launcher time is a true resident-worker measurement.

**Final queued-plan regression `normal_1789530053`:**571.8audio seconds,naturalEOF,21fresh jobs,eightfresh job IDs heard,all11scheduledprechoruses reachedactualwaveforms. Zero host starvation/lateframes/outputflags/sequencegaps;zero renderer underflows/emergencyrepeats. Maxalignment0.525ms,maxtransport108.8ms,minbuffer8.926s;warmresidentlauncher23.568s. Median generation20.199s/21.920unique seconds(RTF0.921),hostpeak178.16MiB,trackedGPU1111.85MiB. Seven unambiguous community steering matches:three useful3.20/5.75/3.30s leads,two near-zero0.20/0.05s,two late1.50/1.15s. Mechanics fixed;prediction of steering entry and human visual timing are not universal passes.

Resident service stopped,ready markerremoved,CPU before/aftermatched. Final score mirrored privately tobench. Final Mac stored replay `normal_1789530685` used an unavailable compute address:40seconds,exactcontiguoussamples,zeroflags,no generation,maxalignment0.229ms. Silent VFR UI/audio capture41.022s saved;video and all listening media have no autoplay. Final native stored regression follows below.


Final native stored replay `normal_1789530751`:latest community score copied privately from Mac,15s,exact contiguous samples,zero flags,no generator,maxalignment2.250ms. Native ordinary UI restored(PID174039,no replay prefix). No owned worker/service/app/replay processes;no ready marker;realIsOnroad false. Worker exit before/after CPU snapshots matched. A subsequent live snapshot had big cores offline, matching native hardwared power-save behavior; we did not undo manager power saving. Initial cleanup assertion expected live equality too strictly; corrected evidence explicitly distinguishes restoration at exit from subsequent manager state (`bench_cleanup_final.json`).

Final Mac system output volume0,mutedtrue;both.session-mutedlocks retained. No speaker output intentionally enabled,no Bluetooth output enabled,bench remained muted. Public tree status identical to mid-run snapshot.49tests pass;review links/poster/media validated,all local,no autoplay. STATUS.md is authoritative for current results and specific remaining human/model/runtime limitations. No push/upload/PR,MusicGen untouched.
