# Big Dipper personality browser regression

This launches real Chromium against the checked-in Vue component, CSS, Settings and SettingTree. All HTTP is intercepted with a **synthetic** personality fixture and checked-in layout. It never contacts a Comma and does not establish physical-device acceptance.

Install Playwright in your normal test environment, then run from any directory:

```sh
node starpilot/system/the_galaxy/tests/browser/personality_profiles.cjs
```

If Playwright is outside this repository, use `NODE_PATH` to its `node_modules`. Optional environment variables:

- `CHROMIUM_EXECUTABLE`: existing Chromium/headless-shell executable; otherwise Playwright's installed browser is used.
- `PERSONALITY_BROWSER_OUTPUT`: screenshot and JSON result directory (defaults to a temporary-directory subfolder).
- `PERSONALITY_DPR`: device scale factor (default 1; verification also runs 2 and 3 with touch capability).
- `PERSONALITY_POLL_ONLY=1`: focused polling-flicker regression (`personality_poll.cjs`): stable computed button appearance over delayed reads, clicks wait for fresh context, road transitions reject queued writes, overlapping clicks serialize and unmount cancels waiting actions.

Coverage: every profile/category graph, numeric commit/reset, graph scales and units, historical high-point preservation, mouse/touch/cancel, pending context and focused number preservation, failed-save verified recovery, malformed graph metadata, all advanced numeric controls and integer validation, Custom-only inputs, master-off profile visibility, Settings deep links, replacement search, dark/light screenshots, and viewport/zoom drag checks. The imported `personality_lifecycle.cjs` adds delayed HTTP and readback failures, duplicate-write prevention, off-road transitions during gestures/pending changes, lost capture, and unmount during drag/poll/PUT (including remount readback and suppressed late effects).

Graph editing matches classic Galaxy: pointer movement previews locally, release commits once, pointercancel/lost capture restores the saved curve without writing, and numeric changes commit immediately. No explicit Save/Discard or route draft cache remains. Pending context reads finish before the unchanged write guards are rechecked; editing is locked during pending writes. Failed/uncertain writes reload authoritative saved state, remain locked if readback fails, and explain recovery only after verification. Already-sent writes cannot be cancelled by unmount; remount reads their actual result. Advanced percentages retain commit-on-change. Custom selection sends an empty curve so the unchanged backend chooses the effective starting curve (including legacy data); Reset sends the reference explicitly. The fixture simplifies backend preset initialization, so server initialization semantics are verified by `test_personality_profiles_api.py`, not this fixture.

Screenshot checks cover CSS zoom, not browser chrome zoom. DPR and touch are browser emulation, not a physical screen. The harness waits for real transient snackbars to disappear before precision drag checks, since a toast can cover the target at extreme zoom.
