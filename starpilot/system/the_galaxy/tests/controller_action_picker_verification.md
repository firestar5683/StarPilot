# Controller action picker verification

Base: `9d1043ad0114c65cadd5e1030d2562ef041fdb10` (Dom).
Read-only `git ls-remote` observed upstream Dom at `a695335f216795183e61bff3eb6b84f1dfc55268`; this change intentionally stays on the requested integration baseline.

## Scope

Presentation-only shared native dialog, integrated into the actual classic Arrow `wheel_controls.js` and Big Dipper Vue `WheelControls.js`. The source API's `section` supplies categories; all delivered options retain their key, label, description and order. No duplicate action catalogue, backend edits, Params writes, device operations, deployment, restart, push, or PR updates.

Existing per-theme speed-value calculations remain distinct (`||` classic, `??` Dipper). The selection callback uses the original request handler; opening, searching and cancelling never write. The chooser reads the current option list and offroad/busy guard while open. A saved unavailable key remains visible without becoming an eligible choice.

## Reproduce browser test

Install Playwright into an isolated environment and install its Chromium headless shell, then run from the repository root:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/.picker-browsers" .picker-venv/bin/python starpilot/system/the_galaxy/tests/controller_action_picker_browser.py --output "$PWD/picker-evidence"
```

The test launches a loopback static server and loads the shipped Arrow/Vue components and each theme's real styles. Its status API is **simulated**, not a vehicle connection. It executes the baseline's pure option builders with all eligible catalogue keys/capabilities enabled: a **190-option coverage superset**, not a claim that a particular car offers all 190 actions. It also asserts unchanged source files for those builders.

Verified matrix: both themes × desktop 1440×1000 at CSS zoom 1/1.5 (DPR 1), phone 390×844 at zoom 1/1.25 (DPR 3), landscape 844×390 at zoom 1 (DPR 2). Phone/landscape opening uses actual touch events.

Each case checks:
- All 190 original identifiers/order plus the existing empty option; all 11 source categories and searching every identifier.
- Description search, global search after category selection, no-match state, clear assignment.
- Current selection, cancel/Escape with zero writes, keyboard wrapping and restored trigger focus, reopen/readback.
- Exact speed assignment payload retaining value 47; ordinary assignment to slot 9; Learn Button payload offset 12.
- Saved unavailable selection retained, removal from the live eligible list, onroad transition disabling changes.
- Viewport bounds, scrollable result list, no description overflowing its button, zero browser page errors.

Browser output: `picker-evidence/report.json`, `original-options.json`, ten PNG screenshots. Screenshots were visually inspected; this caught and corrected text inheritance and row-shrink problems beyond geometry checks.

Existing focused suite:
```sh
.picker-venv/bin/python -m pytest -o addopts='' --confcutdir=starpilot/system/the_galaxy/tests starpilot/system/the_galaxy/tests/test_ui_vue_frontend.py -q
```
Result: 25 passed (three missing-plugin configuration warnings). The ordinary repository pytest invocation is blocked by missing `capnp`; the focused static frontend suite does not require vehicle conftest or xdist. Browser tests are independent of those native dependencies.

## Integration

Cherry-pick the isolated commit or apply the exported patch; include **both new shared assets** with both caller updates. No backend closure or service restart is needed by this patch alone. Personality/model-manager changes are expected to use other component files, but combined integration and the newer upstream tree still require review and combined device testing. No real hardware button/control execution, Safari/iOS, or on-device validation was performed.
