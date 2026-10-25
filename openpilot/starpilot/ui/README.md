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

To run the manager-supervised desktop device, use `./device c3` or
`./device c4` (defaults to C4). This starts the real manager, which owns the
native UI and local/LAN Galaxy service in the same isolated host runtime. Cloud
registration is disabled; it needs no separate Galaxy process. The host
launcher completes the camera-dependent first-run tutorial so the off-road UI
opens directly. The full device command requires Linux; Bluetooth needs BlueZ.
It is verified on Ubuntu under WSL2; native Linux also needs systemd and a
working display. The separate `./c3` and `./c4` UI launchers also support macOS.
Stop it with Ctrl+C. Galaxy listens on port 8082.

For phone access from the LAN, put the following in `%UserProfile%\.wslconfig`
on Windows, then run `wsl --shutdown` in PowerShell to apply it:

```ini
[wsl2]
networkingMode=mirrored
```

For Bluetooth, also set `[boot]` and `systemd=true` in Ubuntu's `/etc/wsl.conf`
before shutting down WSL.

Run these rules once in **Administrator PowerShell**. TCP 8082 serves Galaxy;
UDP 5353 lets the phone app discover it:

```powershell
New-NetFirewallHyperVRule -Name "OpenpilotGalaxy" -DisplayName "Openpilot Galaxy" `
  -Direction Inbound -VMCreatorId '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' `
  -Protocol TCP -LocalPorts 8082
New-NetFirewallHyperVRule -Name "OpenpilotGalaxyDiscovery" -DisplayName "Openpilot Galaxy discovery" `
  -Direction Inbound -VMCreatorId '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' `
  -Protocol UDP -LocalPorts 5353
```

After restarting WSL, `./device c4` shows the laptop's LAN IP in Network
settings. Open `http://<laptop-LAN-IP>:8082` on the phone. On the Windows laptop,
use `http://127.0.0.1:8082`. Mirrored networking provides LAN access without a
port proxy. [Microsoft's WSL networking guide](https://learn.microsoft.com/windows/wsl/networking)
documents the mode and firewall rules.

For Bluetooth on Ubuntu 24.04 WSL with this laptop's Intel `8087:0033` adapter:

1. In **Administrator PowerShell**, run `usbipd list`, then
   `usbipd bind --force --busid 1-10`. `1-10` was this laptop's Intel adapter;
   use its current bus ID if the list changes. A Windows restart may be needed
   to release the built-in adapter.
2. From the repository root in Ubuntu, run
   `sudo ./tools/setup_wsl_intel_bluetooth.sh` once. It installs BlueZ and
   Intel firmware, configures the WSL firmware loader at boot, and grants the
   current Linux user limited Bluetooth service controls.
3. Launch `./device c4`; it attaches the already shared adapter to WSL.
   If USB/IP reports *Device in error state* after a Windows restart, run
   `pnputil /enable-device "USB\VID_8087&PID_0033\5&3B784BF&0&10"` in
   Administrator PowerShell, using the current instance ID from `usbipd state`
   if it changes, then launch again.

Check `bluetoothctl list` in Ubuntu for a controller, then turn Bluetooth on in
the device settings. Galaxy's phone bridge advertises as `Galaxy`. Windows cannot
use the USB Bluetooth adapter while it is attached to WSL. Galaxy over LAN works
without Bluetooth. [Microsoft's USB guide](https://learn.microsoft.com/windows/wsl/connect-usb)
documents the USB/IP handoff.

### Return Bluetooth to Windows

Stop `./device` first (Ctrl+C or close its window). In **Administrator
PowerShell**, find the Intel adapter's current bus ID with `usbipd list`, then
run:

```powershell
usbipd unbind --busid 1-10
usbipd list
```

Replace `1-10` if its bus ID changed. The adapter should show `Not shared` and
appear again in Windows Bluetooth settings. Because setup used `bind --force`,
`usbipd detach` alone may leave Windows Bluetooth unavailable; `unbind` removes
the sharing registration and detaches it if needed. If Windows still shows the
adapter as disabled, enable it in Device Manager or run
`pnputil /enable-device "USB\VID_8087&PID_0033\5&3B784BF&0&10"` with its current
instance ID, then restart Windows if necessary. This does not affect Galaxy's
LAN access.

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
