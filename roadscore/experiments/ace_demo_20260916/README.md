# Prism demo hardening

Baseline: `08ba22e`, preserved as `ace-demo-baseline-08ba22e`.

`test_quality.py` and `fixtures.py` validate the frozen conservative pre-commit detector against known recorded failures and labeled controls. `test_runtime.py` covers deterministic holds, section grammar, profile selection, timeout containment and unchanged turn motifs. `native_suite.py` exercises known bad seeds and the sequential fixed-window soak on the explicitly owned bench GPU. `chunk_repro.py` isolates one decoder chunk with resident input, optional readback and an idle interval. No script opens an audio output device.

Native worker policy: Prism primary; Aurora backup; Circuit archive only. Fixed initial30/continuation45 shapes, 8 seconds of source context, adaptive interior endpoint. Every committed new region is checked before it can enter playback. Maximum two deterministic rerolls. The next attempt requires estimated generation time plus 10 seconds of safety margin. Startup prepares at least112 seconds; requests begin at90 seconds remaining. Exhausted requests use explicit accepted-tail holds. Two consecutive exhausted requests stop new requests and mark degraded playback. No automatic backend switch or hardware reset.

Rerolls are not assumed to repair conditioning-dependent failures. The benchmark preserves every rejected seed and waveform. A hold is not a successful fresh generation. The full-route audit reports these separately.

GPU timeout containment bypasses the driver's interrupt-reset diagnostic hook after capturing read-only failure evidence. This is local to the private ACE owner; tinygrad and public StarPilot remain unmodified. The hardware fault is not claimed fixed.

See `results/ace_demo_20260916/PROGRESS.md` for current evidence and `DEMO_CHECKLIST.md` for explicit preparation/recovery steps. Listening acceptance remains human work.

`resident_flow.py` takes the private replay-session lock and submits six ordinary musical requests to an already READY Prism worker, starting from a current-pass generated verse. It produces the focused verse/build/chorus/verse/bridge/chorus/outro review without route inputs. `replays.py` uses the existing native EOF/camera/path/lane audit for full route runs and repairs local archive links after retrieval. `archive_audit.py` reports every2s quiet span, including intentional endings, without feeding any result back into runtime.
