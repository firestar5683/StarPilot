# Local event integration candidate

This candidate combines the compact UI, judging preparation/export fixes, and
fail-closed judging preflight. No hardware validation follows from local tests.

## Hardware handoff and first run

Only the explicitly authorized hardware owner may execute this sequence.

1. Inventory the current device revision, working changes, real offroad state,
   owned processes, GPU/link health, mute safeguards, caches and original attempt
   ledgers. Preserve the device's existing theme changes. Do not stop another
   owner's processes. Reuse verified device caches before transferring assets.
2. Stage only the reviewed source diff from `90bd992ced` to this candidate using
   a local patch/direct transfer. Check applicability first; no remote Git push,
   no replacement of generated files, routes, private ledgers or frozen policies.
3. Verify actual firmware power state, not just the environment. Historical caps
   may persist: an unset `AM_POWER_LIMIT` requests driver default but does not
   prove the physical limit reverted. Establish the supported stock/default
   setting and read it back before calling a run full speed. No speculative
   resets or wattage sweeps. Preserve any reproduced link failure before using
   an explicitly versioned practical mitigation.
4. Prepare Prism on the device with `AM_POWER_LIMIT` removed from the environment
   (the ACE worker no longer supplies an implicit 30 W cap). Use the established
   regression route for the first full-speed native replay, muted, with the
   integrated overlay. Keep UI capture/audit and the unchanged causal guard.
5. Validate visible READY/GENERATING/DEGRADED, buffer and gesture behavior. Then
   perform Bluetooth listening only with the user attending and explicitly
   verified sink/volume. Do not globally remove mute safeguards.

Native preparation command, only after the checks above:

```sh
env -u AM_POWER_LIMIT /usr/local/venv/bin/python /data/roadscore/prototype/worker_service.py start --composer ace --profile prism
```

Native regression invocation uses the already verified private route variable:

```sh
env -u AM_POWER_LIMIT /data/openpilot/onroad --routeid "$REGRESSION_ROUTE" --roadscore --composer ace --profile prism --muted
```

For every significant run, save requested and verified actual power mode/cap,
preparation timing, warm generation RTF, decoder time, GPU/link samples,
underflows, accepted-music holds and minimum playback buffer. Retain native
summary, trace, audio callback log, UI audit and preparation/generation metadata.
Missing telemetry is unknown, never a passing measurement. Investigate callback
misses if reproduced and materially blocking; the old A underflow did not show a
GPU fault or depleted buffer.

## Versioned judging continuation

Do not invoke the legacy batch scheduler: it uses the historical unversioned
ledger directory. Invoke the guarded runner one ready label at a time under the
single hardware owner's supervision.

The new handoff schema requires an explicit `configuration.policy_version`,
`hardware_mode: full-speed`, `power_limit_watts: null`, generation authorization,
and per-label readiness with no blockers. Capped mitigation requires a distinct
policy version and explicit numeric limit. The runner strips inherited power
caps for full-speed mode and refuses legacy manifests for new attempts.

After reconciling device cache contents, create a new private runtime handoff
from the prepared export. Retain mapping/seeds and the explicit full-route and
457-second range decisions. Do not relabel, tune per route, or substitute a
partial log silently. Freeze the reviewed common runtime, quality/gesture and
profile file hashes in `configuration.freeze.private.json` beside that handoff;
it must be nonempty and every hash must verify before any attempt starts.

New ledgers and preparations live under
`results/community_judging/<policy_version>/`. Historical A's technically invalid
result and B's `paused_by_user` preparation remain unchanged. B may begin its
first replay in the new common version; A's technically invalid repeat must
retain a provenance reference to the original. All comparable official results
must use this same new policy; never mix the old 45 W run into a full-speed cohort.

```sh
/usr/local/venv/bin/python /data/roadscore/tools/judging_run.py "$PRIVATE_MANIFEST" --label "$LABEL"
```

A finished process is not necessarily a technical pass: require the native audit
before listing a valid demo. Preserve invalid audio as diagnostic evidence,
separate from the valid listening shortlist. Human ranking remains the user's.
Live input/coexistence changes are separate and must not be staged prematurely.
