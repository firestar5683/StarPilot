# StarPilot native UI

StarPilot uses separate large (C3) and compact (C4) layouts over the native
camera, model renderer and application lifecycle. The same presentation
components serve the device and Galaxy's sample layout preview.

## Runtime ownership

- `runtime_app.py` connects the native navigation, touch handling, camera layers
  and settings owners. It cancels pending gestures when pages change.
- `runtime_snapshot.py` projects service observations and saved preferences into
  display state. Message validity, age and drive identity remain separate from
  saved configuration.
- `shell.py` combines Home, Settings and Onroad. Renderers consume snapshots;
  input handlers emit requests to the owner responsible for the action.
- `onroad.py` composes profile-specific widgets, overlays and alerts.
  `onroad_customization.py` owns the versioned layout and color document;
  the Galaxy editor and native renderers use the same widget registry.
- `ui_state.py` in `selfdrive/ui` follows hardwared's effective started state.
  Physical ignition remains separate. Camera reception, model filters and
  transition updates must continue when a settled opaque settings page skips
  their painting.

Preference editors do not grant driving authority. Feature owners validate
configuration changes; control consumers and native safety retain their own
checks. A speed-limit action carries the displayed decision's session and
identity, which the planner verifies before accepting it. Hiding or moving a
widget must preserve the corresponding hit target and must not hide alerts.

Shared feature contracts live with [speed limits](../speed_limits/README.md),
[conditional modes](../conditional_mode/README.md),
[lateral control](../lateral/README.md), [AOL](../aol/README.md),
[longitudinal control](../longitudinal/README.md),
[models](../models/README.md) and [Galaxy](../galaxy/README.md).

## Running and previewing

From the repository root, `./c3` and `./c4` launch the large and compact UI in
an isolated host runtime. Each accepts an optional leading build-job count.
`SP_C3_COMPILE_ONLY=1` or `SP_C4_COMPILE_ONLY=1` prepares that runtime without
opening a window. Host settings are kept in its private Params store.

For a deterministic presentation capture with supplied sample state:

```sh
./dev python -m openpilot.starpilot.ui.preview_shell \
  --profile compact \
  --font-directory openpilot/starpilot/ui/assets/fonts \
  --asset-directory openpilot/selfdrive/assets \
  --output /tmp/starpilot-ui-preview
```

Use `--profile large` for C3. `preview_typography`, `preview_home`,
`preview_settings`, `preview_device`, `preview_software` and
`preview_slc_actions` provide narrower fixtures; each exposes its arguments
with `--help`. Previews require a graphics context. They do not launch driving
services, operate a vehicle or establish device performance.

## Performance diagnostics

`UI_FRAME_TIMING=1 ./c4` (or `./c3`) enables phase timing. UI Debug Mode also
shows FPS and enables timing. Slow-frame warnings separate drawing, caller
updates and presentation wall time from thread CPU time; camera, model and
other nested phases help locate the work. Nested timings overlap and must not
be added together.

Without continuous tracing, a slow-frame warning starts a bounded diagnostic
window: up to 360 slow samples over six seconds, followed by a 60-second
cooldown. The log reports per-phase medians and maxima. Frame pacing and the
`uiDebug` message schema are unchanged.

Compare the same source, assets, saved layout, input sequence and render mode
when measuring an optimization. Preserve update and input behavior as well as
pixels. Offscreen rendering and component timings exclude parts of the running
application; verify sustained performance on the device with its normal camera
and model workload.

## Assets and recovery

`startup.py` validates bundled fonts and artwork before acquiring graphics
resources. Missing or modified assets select the upstream UI and log the
reason. `STARPILOT_UI=upstream` explicitly selects that recovery presentation.
`STARPILOT_UI_DEV=1` instead fails visibly when custom assets are invalid; the
explicit upstream selection takes precedence.

`STARPILOT_UI_FONT_DIR` can point to a complete, validated Inter/Unifont bitmap
set. Sora's Home wordmark uses its bundled bitmap. Font descriptors, atlases and
artwork have source-controlled hash manifests. Keep their glyph metrics and
profile scales together; do not regenerate atlases as part of a routine build.
Close owned fonts and textures before destroying the graphics context.

The adjacent [LICENSE](LICENSE) and [asset notices](assets/README.md) retain
applicable code, font and image attribution. Hash validation establishes asset
identity, not redistribution rights.
