# Experiment ledger

Baseline: `b132721`, preserved tag `unattended-before-b132721`.

1. **Genre screen:** six distinct prompt families, same seed8101,30.093 seconds each, approximately19.3 seconds generation. Electronic, synthwave and funk selected for continuation comparisons on objective rhythmic/spectral behavior; no subjective winner asserted.
2. **Development controls:** fixed versus refreshed anchor, same seeds/section requests. Refreshed anchor did not clearly increase measured development. More contrasting prompts alone also had modest effects.
3. **Anchor removal:** harmonic/timbral distances increase substantially, but18.3 seconds fall below−50dB and repeated joins approach silence. Rejected. No silence repair or time stretching was applied.
4. **Short anchor:**22 latent frames /2.043 seconds instead of44 /4.087; four continuations total125.945 seconds. Zero100ms near-silence blocks, modestly greater final-section harmonic change. Preserved for listening; live default unchanged.
5. **Curve audit:** all three full cached routes scanned offline. Fixed steering definitions, raw prediction candidates, persistence, activation, commands and audio residuals are recorded. Future labels are evaluation-only and never runtime inputs. The0.6 trial created an extra event and delayed a subsequent sharp turn; it was not adopted and the bench default is restored to0.8. Low-speed sharp turns remain failures; do not infer success from convenient gentle curves alone.
6. **Style responses:** same source/captured event stream A/B for electronic, synthwave and funk. Deterministic processing changes existing generated material; it does not supply prerecorded songs or percussion assets.
7. **Native replay:** first transport test found a native all-service socket collision; an explicit UI/music service set avoids it. The initial set omitted encode-index services, preventing camera delivery. Adding roadEncodeIdx fixes this. This debugging history matters: early native recordings are not proof that camera reception worked.
8. **Native evidence:** third-route run confirms camera reception. Final run further confirms actual nonempty path/lane and camera-texture draw calls. No custom renderer or modeld rerun.
9. **Clock correction:** first-message wall anchoring showed up to0.17 seconds of misleading source/output alignment. Per-message delivery plus an SSH round-trip clock measurement replaces it in final diagnostics. A later offset discontinuity after the completed capture was excluded, not hidden.
10. **Deadline regression:** native_cold and native_gc are rejected as clean playback demonstrations because of output flags. GC instrumentation links every miss to85–96ms full collections. Direct result lookup plus pre-stream GC freezing yields a clean180.2-second final capture. Dynamic GC remains enabled; finalization unfreezes the heap.
11. **Arrival:** final different-route capture is clean, same causal trigger,1.691-second source-dependent runway, five-second resolving gesture. Original liked Horizon cadence is retained.
12. **Shutdown:** manually owned worker stopped, launcher-owned cold cleanup independently exercised, saved CPU states equal restored states. All captured audio blocks are muted.

Primary evidence lives in `results/unattended/listen.html`, `native_final`, `native_final_arrival`, `genre_screen.json`, `development_metrics.json`, `development_boundaries.json`, `curve_timing.json`, `threshold_sensitivity.json` and the synchronized timing JSON files. Raw diagnostics and rejected experiments remain secondary.

Current recommendation: keep native SA3 with active context and fixed anchor for the demo; offer several generated musical identities and early style-specific event realizations. Treat richer composition and universal turn anticipation as unresolved product work. Run an unseen compatible community route as the next acceptance test.
